#!/usr/bin/env python3
"""Render Remotion project to MP4 video.

Wraps ``npx remotion render`` to produce a presentation video from the
Remotion project located under slides/video/remotion/ in a paper project
directory.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import now_iso


def fail(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


def get_file_size_mb(path: Path) -> float:
    """Return file size in megabytes."""
    return path.stat().st_size / (1024 * 1024)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Remotion project to MP4 video."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Paper project directory (contains slides/video/remotion/).",
    )
    parser.add_argument(
        "--composition",
        default="Presentation",
        help="Remotion composition ID (default: Presentation).",
    )
    parser.add_argument(
        "--codec",
        default="h264",
        choices=["h264", "h265"],
        help="Video codec (default: h264).",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=18,
        help="Constant rate factor 1-51 (default: 18).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help=(
            "Render concurrency — number of frames rendered in parallel. "
            "Default: half of CPU cores (capped at 16). "
            "Higher values use more RAM but render faster."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: slides/video/output/presentation.mp4).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        return fail(f"project dir not found: {project_dir}")

    remotion_dir = project_dir / "slides" / "video" / "remotion"
    if not remotion_dir.exists() or not remotion_dir.is_dir():
        return fail("slides/video/remotion/ directory not found")

    package_json = remotion_dir / "package.json"
    if not package_json.exists():
        return fail("slides/video/remotion/package.json not found")

    # ---- Check node / npx availability ------------------------------------
    npx = shutil.which("npx")
    if not npx:
        return fail("npx not found on PATH (install Node.js)")
    node = shutil.which("node")
    if not node:
        return fail("node not found on PATH (install Node.js)")

    # ---- npm install if needed --------------------------------------------
    node_modules = remotion_dir / "node_modules"
    if not node_modules.exists():
        npm = shutil.which("npm")
        if not npm:
            return fail("npm not found on PATH; cannot install dependencies")
        print("node_modules/ not found – running npm install ...")
        result = subprocess.run(
            [npm, "install"],
            cwd=str(remotion_dir),
        )
        if result.returncode != 0:
            return fail(f"npm install failed (exit {result.returncode})")

    # ---- Determine output path --------------------------------------------
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        output_path = project_dir / "slides" / "video" / "output" / "presentation.mp4"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- Validate crf -----------------------------------------------------
    if not (1 <= args.crf <= 51):
        return fail(f"crf must be between 1 and 51, got {args.crf}")

    # ---- Locate props.json -------------------------------------------------
    props_path = remotion_dir / "public" / "props.json"
    if not props_path.exists():
        return fail(
            "public/props.json not found in Remotion project – "
            "run scaffold_video.py first"
        )

    # ---- Build render command ---------------------------------------------
    cmd: list[str] = [
        npx,
        "remotion",
        "render",
        args.composition,
        str(output_path),
        "--props",
        f"./{props_path.relative_to(remotion_dir)}",
        "--codec",
        args.codec,
        "--crf",
        str(args.crf),
    ]

    # ---- Concurrency --------------------------------------------------------
    concurrency = args.concurrency
    if concurrency is None:
        # Auto-detect: half of CPU cores, capped at 16
        concurrency = min(max(os.cpu_count() or 4, 2) // 2, 16)
    if concurrency < 1:
        return fail(f"concurrency must be >= 1, got {concurrency}")
    cmd.extend(["--concurrency", str(concurrency)])

    # Enable multiprocess on Linux for better parallelism
    if platform.system() == "Linux":
        cmd.append("--enable-multiprocess-on-linux")

    # ---- Run render (stream stdout/stderr to terminal) --------------------
    print(f"Rendering: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(remotion_dir))

    if result.returncode != 0:
        return fail(f"remotion render failed (exit {result.returncode})")

    # ---- Report success ---------------------------------------------------
    if not output_path.exists():
        return fail(f"render command succeeded but output file not found: {output_path}")

    size_mb = get_file_size_mb(output_path)
    print(f"Video rendered: {output_path} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
