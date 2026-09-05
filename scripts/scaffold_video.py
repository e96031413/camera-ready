#!/usr/bin/env python3
"""Scaffold Remotion video project from Beamer slides PDF and TTS audio."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import now_iso, get_template_dir


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------


def _check_pdftoppm() -> bool:
    """Return True if pdftoppm is available, else try pdf2image fallback."""
    if shutil.which("pdftoppm"):
        return True
    # Try pdf2image as a fallback
    try:
        subprocess.run(
            [sys.executable, "-c", "from pdf2image import convert_from_path"],
            capture_output=True, encoding="utf-8", errors="replace",
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _check_node() -> bool:
    """Return True if node and npm are available."""
    return shutil.which("node") is not None and shutil.which("npm") is not None


# ---------------------------------------------------------------------------
# PDF to PNG conversion
# ---------------------------------------------------------------------------


def _convert_pdf_to_png(pdf_path: Path, frames_dir: Path, dpi: int) -> list[Path]:
    """Convert PDF to PNG images via pdftoppm and return sorted file list."""
    frames_dir.mkdir(parents=True, exist_ok=True)

    if shutil.which("pdftoppm"):
        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-r",
                str(dpi),
                str(pdf_path),
                str(frames_dir / "slide"),
            ],
            check=True,
        )
    else:
        # Fallback: use pdf2image Python library
        subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from pdf2image import convert_from_path; "
                    f"imgs = convert_from_path('{pdf_path}', dpi={dpi}); "
                    "[img.save(f'{frames_dir}/slide-{{i+1:02d}}.png') "
                    "for i, img in enumerate(imgs)]"
                ),
            ],
            check=True,
        )

    # Collect generated PNGs and rename to 3-digit zero-padded names
    raw_files = sorted(frames_dir.glob("slide-*.png"))
    renamed: list[Path] = []
    for idx, fpath in enumerate(raw_files, start=1):
        new_name = f"slide-{idx:03d}.png"
        new_path = frames_dir / new_name
        if fpath.name != new_name:
            fpath.rename(new_path)
        renamed.append(new_path)

    return renamed


# ---------------------------------------------------------------------------
# Slide / audio matching
# ---------------------------------------------------------------------------


def _build_slides_data(
    frame_paths: list[Path],
    manifest: dict,
    fps: int,
    default_duration: float,
) -> list[dict]:
    """Match slide images to audio entries from the TTS manifest."""
    audio_entries: list[dict] = manifest.get("slides", [])

    # Build a lookup: slide index (1-based) -> audio entry
    audio_by_index: dict[int, dict] = {}
    for entry in audio_entries:
        # Entries may carry an explicit "slideIndex" or be sequential
        idx = entry.get("slideIndex")
        if idx is not None:
            audio_by_index[idx] = entry
    # If no slideIndex keys, assume sequential mapping starting at 1
    if not audio_by_index:
        for i, entry in enumerate(audio_entries, start=1):
            audio_by_index[i] = entry

    slides_data: list[dict] = []
    for seq, fpath in enumerate(frame_paths, start=1):
        entry = audio_by_index.get(seq)
        if entry is not None:
            duration_s = (
                entry.get("duration_seconds")
                or entry.get("duration")
                or default_duration
            )
            audio_filename = (
                entry.get("audio_path", "").split("/")[-1]
                or entry.get("audioFile")
                or f"slide-{seq:03d}.mp3"
            )
            title = entry.get("title", f"Slide {seq}")
            slides_data.append(
                {
                    "imagePath": f"frames/{fpath.name}",
                    "audioPath": f"audio/{audio_filename}",
                    "durationInFrames": math.ceil(duration_s * fps),
                    "title": title,
                }
            )
        else:
            # No narration for this slide — use default duration
            slides_data.append(
                {
                    "imagePath": f"frames/{fpath.name}",
                    "audioPath": None,
                    "durationInFrames": math.ceil(default_duration * fps),
                    "title": f"Slide {seq}",
                }
            )

    return slides_data


# ---------------------------------------------------------------------------
# Remotion project scaffolding
# ---------------------------------------------------------------------------


def _copy_template(template_dir: Path, remotion_dir: Path, force: bool) -> None:
    """Copy the Remotion template, skipping node_modules."""
    if remotion_dir.exists() and not force:
        raise FileExistsError(
            f"{remotion_dir} already exists (use --force to overwrite)"
        )

    def _ignore_node_modules(directory: str, contents: list[str]) -> list[str]:
        return ["node_modules"] if "node_modules" in contents else []

    shutil.copytree(
        template_dir,
        remotion_dir,
        ignore=_ignore_node_modules,
        dirs_exist_ok=force,
    )


def _create_symlinks(remotion_dir: Path, video_dir: Path) -> None:
    """Create symlinks in remotion/public/ pointing to frames/ and audio/."""
    public_dir = remotion_dir / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    targets = {
        "frames": os.path.relpath(video_dir / "frames", public_dir),
        "audio": os.path.relpath(video_dir / "audio", public_dir),
    }

    for name, rel_target in targets.items():
        link_path = public_dir / name
        if link_path.exists() or link_path.is_symlink():
            if link_path.is_symlink():
                link_path.unlink()
            elif link_path.is_dir():
                shutil.rmtree(link_path)

        if platform.system() == "Windows":
            # Symlinks may require elevated privileges on Windows — fall back to copy
            source = video_dir / name
            if source.exists():
                shutil.copytree(str(source), str(link_path))
        else:
            os.symlink(rel_target, link_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold Remotion video project from Beamer slides PDF and TTS audio.",
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Paper project directory (contains slides/slides.pdf and slides/video/manifest.json).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for PDF to PNG conversion (default: 300).",
    )
    parser.add_argument(
        "--transition-duration",
        type=float,
        default=0.5,
        help="Transition duration in seconds (default: 0.5).",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Video FPS (default: 30).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing Remotion project.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()

    slides_dir = project_dir / "slides"
    pdf_path = slides_dir / "slides.pdf"
    video_dir = slides_dir / "video"
    manifest_path = video_dir / "manifest.json"

    # ------------------------------------------------------------------
    # 1. Validate prerequisites
    # ------------------------------------------------------------------
    if not pdf_path.exists():
        return fail(f"slides/slides.pdf not found in {project_dir}")

    if not manifest_path.exists():
        return fail(
            f"slides/video/manifest.json not found — "
            f"run synthesize_tts.py first"
        )

    if not _check_pdftoppm():
        return fail(
            "pdftoppm not found and pdf2image is not installed. "
            "Install poppler-utils (apt install poppler-utils) or "
            "pip install pdf2image"
        )

    if not _check_node():
        return fail("node/npm not found on PATH — required for Remotion")

    # ------------------------------------------------------------------
    # 2. Convert PDF to PNG images
    # ------------------------------------------------------------------
    frames_dir = video_dir / "frames"
    frame_paths = _convert_pdf_to_png(pdf_path, frames_dir, args.dpi)

    if not frame_paths:
        return fail("PDF conversion produced no images")

    print(f"Extracted {len(frame_paths)} slide images at {args.dpi} DPI")

    # ------------------------------------------------------------------
    # 3. Read manifest
    # ------------------------------------------------------------------
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # 4. Match slides to audio
    # ------------------------------------------------------------------
    default_no_audio_duration = 3.0  # seconds for slides without narration
    slides_data = _build_slides_data(
        frame_paths, manifest, args.fps, default_no_audio_duration
    )

    # ------------------------------------------------------------------
    # 5. Copy Remotion template
    # ------------------------------------------------------------------
    template_video_dir = get_template_dir() / "video"
    remotion_dir = video_dir / "remotion"

    if not template_video_dir.exists():
        return fail(f"Remotion template not found at {template_video_dir}")

    try:
        _copy_template(template_video_dir, remotion_dir, args.force)
    except FileExistsError as exc:
        return fail(str(exc))

    # ------------------------------------------------------------------
    # 6. Generate props.json
    # ------------------------------------------------------------------
    transition_frames = math.ceil(args.transition_duration * args.fps)
    public_dir = remotion_dir / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    props = {
        "fps": args.fps,
        "transitionDurationFrames": transition_frames,
        "slides": slides_data,
    }

    props_path = public_dir / "props.json"
    props_path.write_text(
        json.dumps(props, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # ------------------------------------------------------------------
    # 7. Create symlinks in remotion/public/
    # ------------------------------------------------------------------
    _create_symlinks(remotion_dir, video_dir)

    # ------------------------------------------------------------------
    # 8. Run npm install
    # ------------------------------------------------------------------
    print("Running npm install in Remotion project...")
    result = subprocess.run(
        ["npm", "install"],
        cwd=str(remotion_dir),
        capture_output=True, encoding="utf-8", errors="replace",
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return fail("npm install failed")

    # ------------------------------------------------------------------
    # 9. Print summary
    # ------------------------------------------------------------------
    audio_count = sum(1 for s in slides_data if s["audioPath"] is not None)
    total_duration_s = sum(s["durationInFrames"] / args.fps for s in slides_data)
    audio_duration_s = sum(
        s["durationInFrames"] / args.fps
        for s in slides_data
        if s["audioPath"] is not None
    )
    # Estimated video includes inter-slide transitions
    num_transitions = max(len(slides_data) - 1, 0)
    estimated_duration_s = total_duration_s + num_transitions * args.transition_duration

    print(
        f"\nVideo project scaffolded:\n"
        f"  Slides: {len(slides_data)} images\n"
        f"  Audio: {audio_count} tracks ({audio_duration_s:.1f}s)\n"
        f"  Transitions: {args.transition_duration}s fade\n"
        f"  Estimated video: {estimated_duration_s:.0f}s\n"
        f"  Remotion project: slides/video/remotion/\n"
        f"\n"
        f"Next: python3 scripts/render_video.py --project-dir {project_dir}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
