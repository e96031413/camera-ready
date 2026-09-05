#!/usr/bin/env python3
"""Generate a thumbnail grid from a PPTX file.

Usage: python pptx_thumbnail.py input.pptx [output_prefix] [--cols N]
Requires: soffice (LibreOffice), pdftoppm (Poppler), Pillow.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow required. pip install Pillow", file=sys.stderr)
    sys.exit(1)


def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} input.pptx [output_prefix] [--cols N]", file=sys.stderr)
        sys.exit(1)

    pptx_path = sys.argv[1]
    output_prefix = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "thumbnails"
    cols = 3
    for i, arg in enumerate(sys.argv):
        if arg == "--cols" and i + 1 < len(sys.argv):
            cols = int(sys.argv[i + 1])

    scripts_dir = Path(__file__).parent
    soffice_py = scripts_dir / "pptx_soffice.py"

    with tempfile.TemporaryDirectory(prefix="thumb_") as tmpdir:
        try:
            subprocess.run(
                [sys.executable, str(soffice_py), "--headless", "--convert-to", "pdf",
                 "--outdir", tmpdir, pptx_path],
                check=True, capture_output=True, encoding="utf-8", errors="replace",
            )
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors="replace") if e.stderr else ""
            print(f"Error: PDF conversion failed (is LibreOffice/soffice installed?)\n{stderr}", file=sys.stderr)
            sys.exit(1)

        pdf_name = Path(pptx_path).stem + ".pdf"
        pdf_path = os.path.join(tmpdir, pdf_name)

        try:
            subprocess.run(
                ["pdftoppm", "-png", "-r", "150", pdf_path, os.path.join(tmpdir, "slide")],
                check=True, capture_output=True, encoding="utf-8", errors="replace",
            )
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors="replace") if e.stderr else ""
            print(f"Error: PDF-to-image conversion failed (is Poppler's pdftoppm installed?)\n{stderr}", file=sys.stderr)
            sys.exit(1)

        slide_imgs = sorted(Path(tmpdir).glob("slide-*.png"))
        if not slide_imgs:
            print("No slides found", file=sys.stderr)
            sys.exit(1)

        thumb_w, thumb_h = 400, 225
        padding = 10
        label_h = 20
        rows = (len(slide_imgs) + cols - 1) // cols
        grid_w = cols * (thumb_w + padding) + padding
        grid_h = rows * (thumb_h + label_h + padding) + padding

        grid = Image.new("RGB", (grid_w, grid_h), "white")
        draw = ImageDraw.Draw(grid)

        for i, img_path in enumerate(slide_imgs):
            row, col = divmod(i, cols)
            x = padding + col * (thumb_w + padding)
            y = padding + row * (thumb_h + label_h + padding)

            img = Image.open(img_path)
            img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
            grid.paste(img, (x, y))

            label = f"Slide {i + 1}"
            draw.text((x + 2, y + thumb_h + 2), label, fill="black")

        out_path = f"{output_prefix}.jpg"
        grid.save(out_path, quality=90)
        print(f"Thumbnail grid: {out_path} ({len(slide_imgs)} slides, {cols} cols)")


if __name__ == "__main__":
    main()
