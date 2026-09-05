#!/usr/bin/env python3
"""Convert paper figures (PDF/PNG/JPG) to poster-ready PNGs and measure aspect ratios.

Cross-platform replacement for macOS sips:
  - PDF→PNG: pdftoppm -png -r <dpi> -singlefile
  - Dimensions: Pillow Image.open().size

Usage:
  python3 scripts/poster_convert_figures.py --source-dir <figures_dir> --output-dir <poster_dir>
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import get_skill_root


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _check_pdftoppm() -> bool:
    return shutil.which("pdftoppm") is not None


def _check_pillow() -> bool:
    try:
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False


def _convert_pdf_to_png(
    pdf_path: Path, output_path: Path, dpi: int, max_dimension: int
) -> bool:
    """Convert a single PDF file to PNG using pdftoppm."""
    if not _check_pdftoppm():
        print(f"warning: pdftoppm not available, skipping {pdf_path.name}", file=sys.stderr)
        return False

    stem = output_path.stem
    out_dir = output_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), "-singlefile", str(pdf_path), str(out_dir / stem)],
        capture_output=True, encoding="utf-8", errors="replace",
        text=True,
    )
    if result.returncode != 0:
        print(f"warning: pdftoppm failed for {pdf_path.name}: {result.stderr.strip()}", file=sys.stderr)
        return False

    generated = out_dir / f"{stem}.png"
    if not generated.exists():
        return False

    # Resize if exceeds max_dimension
    if _check_pillow():
        from PIL import Image
        img = Image.open(generated)
        w, h = img.size
        if max(w, h) > max_dimension:
            ratio = max_dimension / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            img.save(generated)
            print(f"  resized {generated.name}: {w}x{h} -> {new_size[0]}x{new_size[1]}")

    return True


def _copy_image(src: Path, dst: Path, max_dimension: int) -> bool:
    """Copy an image file, optionally resizing if too large."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

    if _check_pillow():
        from PIL import Image
        img = Image.open(dst)
        w, h = img.size
        if max(w, h) > max_dimension:
            ratio = max_dimension / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            img.save(dst)
            print(f"  resized {dst.name}: {w}x{h} -> {new_size[0]}x{new_size[1]}")

    return True


def _measure_aspect_ratio(path: Path) -> dict | None:
    """Measure image dimensions and classify aspect ratio."""
    if not _check_pillow():
        return None

    from PIL import Image
    try:
        img = Image.open(path)
        w, h = img.size
    except Exception:
        return None

    ratio = w / h if h > 0 else 1.0

    if ratio > 2.0:
        category = "wide"
    elif ratio > 1.2:
        category = "landscape"
    elif ratio > 0.8:
        category = "square"
    else:
        category = "portrait"

    return {
        "file": path.name,
        "width": w,
        "height": h,
        "ratio": round(ratio, 3),
        "category": category,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert paper figures to poster-ready PNGs and measure aspect ratios."
    )
    parser.add_argument("--source-dir", required=True, help="Directory containing paper figures")
    parser.add_argument("--output-dir", required=True, help="Poster output directory (e.g., poster/)")
    parser.add_argument("--max-dimension", type=int, default=3000, help="Max pixel dimension (default: 3000)")
    parser.add_argument("--dpi", type=int, default=300, help="PDF rasterization DPI (default: 300)")
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)

    if not source_dir.is_dir():
        return fail(f"source directory not found: {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect figure files
    extensions = {".pdf", ".png", ".jpg", ".jpeg", ".svg"}
    figures = sorted(f for f in source_dir.iterdir() if f.suffix.lower() in extensions)

    if not figures:
        return fail(f"no figure files found in {source_dir}")

    print(f"Found {len(figures)} figure(s) in {source_dir}")

    converted = 0
    skipped = 0
    aspect_report: list[dict] = []

    for fig in figures:
        dst_name = fig.stem + ".png"
        dst_path = output_dir / dst_name

        if fig.suffix.lower() == ".pdf":
            print(f"  converting {fig.name} -> {dst_name}")
            if _convert_pdf_to_png(fig, dst_path, args.dpi, args.max_dimension):
                converted += 1
            else:
                skipped += 1
                continue
        elif fig.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            print(f"  copying {fig.name} -> {dst_name}")
            _copy_image(fig, dst_path, args.max_dimension)
            converted += 1
        elif fig.suffix.lower() == ".svg":
            print(f"  skipping SVG (manual conversion needed): {fig.name}")
            skipped += 1
            continue

        # Measure aspect ratio
        ar = _measure_aspect_ratio(dst_path)
        if ar:
            aspect_report.append(ar)

    # Write aspect ratio report
    report_path = output_dir / "figure-aspects.json"
    report = {
        "total_figures": len(figures),
        "converted": converted,
        "skipped": skipped,
        "figures": aspect_report,
        "column_assignment_guide": {
            "wide": [f["file"] for f in aspect_report if f["category"] == "wide"],
            "landscape": [f["file"] for f in aspect_report if f["category"] == "landscape"],
            "square": [f["file"] for f in aspect_report if f["category"] == "square"],
            "portrait": [f["file"] for f in aspect_report if f["category"] == "portrait"],
        },
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nAspect ratio report: {report_path}")

    # Print column assignment guide
    print("\nColumn assignment guide:")
    for cat in ["wide", "landscape", "square", "portrait"]:
        files = report["column_assignment_guide"][cat]
        if files:
            print(f"  {cat}: {', '.join(files)}")

    print(f"\nDone: {converted} converted, {skipped} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
