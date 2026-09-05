#!/usr/bin/env python3
"""Generate a preview thumbnail from poster PDF.

Uses pdftoppm for cross-platform PDF→PNG conversion.

Usage:
  python3 scripts/poster_thumbnail.py --poster-pdf poster/poster.pdf [--output poster/poster-thumbnail.png] [--dpi 150]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a preview thumbnail from poster PDF."
    )
    parser.add_argument("--poster-pdf", required=True, help="Path to poster PDF")
    parser.add_argument("--output", default=None, help="Output PNG path (default: same dir as PDF)")
    parser.add_argument("--dpi", type=int, default=150, help="Render DPI (default: 150)")
    args = parser.parse_args()

    pdf_path = Path(args.poster_pdf)
    if not pdf_path.exists():
        return fail(f"PDF not found: {pdf_path}")

    if not shutil.which("pdftoppm"):
        return fail("pdftoppm not found. Install poppler-utils: apt install poppler-utils")

    output_path = Path(args.output) if args.output else pdf_path.with_suffix(".png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # pdftoppm with -singlefile outputs <prefix>.png
    stem = output_path.stem
    out_dir = output_path.parent

    result = subprocess.run(
        [
            "pdftoppm", "-png", "-r", str(args.dpi), "-singlefile",
            str(pdf_path), str(out_dir / stem),
        ],
        capture_output=True, encoding="utf-8", errors="replace",
        text=True,
    )

    if result.returncode != 0:
        return fail(f"pdftoppm failed: {result.stderr.strip()}")

    generated = out_dir / f"{stem}.png"
    if not generated.exists():
        return fail("pdftoppm produced no output")

    # Rename if needed (pdftoppm always appends .png)
    if generated != output_path:
        generated.rename(output_path)

    print(f"Thumbnail generated: {output_path}")

    # Report dimensions if Pillow available
    try:
        from PIL import Image
        img = Image.open(output_path)
        print(f"  dimensions: {img.size[0]}x{img.size[1]}")
    except ImportError:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
