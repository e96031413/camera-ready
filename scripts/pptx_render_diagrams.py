#!/usr/bin/env python3
"""Batch diagram renderer: JSON → SVG/PNG images.

Routes to Graphviz, Mermaid, TikZ, or PDF figure extraction.

Usage:
  python pptx_render_diagrams.py diagrams.json diagrams/                       # default theme
  python pptx_render_diagrams.py diagrams.json diagrams/ --theme midnight      # themed
  python pptx_render_diagrams.py diagrams.json diagrams/ --dpi 600             # higher DPI for extracts
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

THEMES = {
    "academic_light": {
        "pos": "0173B2", "neg": "DE8F05", "emp": "029E73",
        "pri": "1A1A2E", "sec": "4A4A5A", "bg": "F8F9FA", "card": "0173B215",
    },
    "midnight": {
        "pos": "4FC3F7", "neg": "FFB74D", "emp": "81C784",
        "pri": "EAEAEA", "sec": "B0B0C0", "bg": "1A1A2E", "card": "4FC3F715",
    },
    "ocean": {
        "pos": "0173B2", "neg": "DE8F05", "emp": "029E73",
        "pri": "1A1A2E", "sec": "3A5A6E", "bg": "FFFFFF", "card": "065A8215",
    },
    "forest": {
        "pos": "0173B2", "neg": "DE8F05", "emp": "029E73",
        "pri": "2C3E2D", "sec": "4A5A4A", "bg": "F5F5F0", "card": "2C5F2D15",
    },
    "sandwich": {
        "pos": "0173B2", "neg": "DE8F05", "emp": "029E73",
        "pri": "2D3436", "sec": "555555", "bg": "FFFFFF", "card": "0173B215",
    },
}


def _svg_dimensions(svg_path: str) -> tuple[float, float]:
    """Extract width/height in pt from SVG."""
    with open(svg_path, encoding="utf-8") as f:
        head = f.read(3000)
    # width="...pt" height="...pt"
    wm = re.search(r'width="([0-9.]+)pt"', head)
    hm = re.search(r'height="([0-9.]+)pt"', head)
    if wm and hm:
        return float(wm.group(1)), float(hm.group(1))
    # width="...px" (assume 96dpi → *0.75 for pt)
    wm = re.search(r'width="([0-9.]+)', head)
    hm = re.search(r'height="([0-9.]+)', head)
    if wm and hm:
        return float(wm.group(1)) * 0.75, float(hm.group(1)) * 0.75
    # viewBox fallback
    vb = re.search(r'viewBox="[0-9.\-]+ [0-9.\-]+ ([0-9.]+) ([0-9.]+)"', head)
    if vb:
        return float(vb.group(1)), float(vb.group(2))
    return 0.0, 0.0


def _inject_graphviz_theme(dot_code: str, colors: dict) -> str:
    """Inject theme defaults into DOT code."""
    theme_attrs = (
        f'  graph [bgcolor="transparent"];\n'
        f'  node [style="filled,rounded", fillcolor="#{colors["bg"]}", '
        f'fontcolor="#{colors["pri"]}", color="#{colors["pos"]}", '
        f'fontname="Calibri", fontsize=11];\n'
        f'  edge [color="#{colors["sec"]}", fontcolor="#{colors["sec"]}", '
        f'fontname="Calibri", fontsize=10];\n'
    )
    # Insert after first '{' in digraph/graph declaration
    m = re.search(r'((?:di)?graph\s+\w*\s*\{)', dot_code, re.IGNORECASE)
    if m:
        pos = m.end()
        return dot_code[:pos] + "\n" + theme_attrs + dot_code[pos:]
    return dot_code


def render_graphviz(entry: dict, outdir: Path, colors: dict) -> dict:
    """Render Graphviz DOT → SVG."""
    fid = entry["id"]
    final = outdir / f"{fid}.svg"
    if final.exists():
        w, h = _svg_dimensions(str(final))
        return {"file": str(final), "format": "svg", "width_pt": w, "height_pt": h}

    dot_code = _inject_graphviz_theme(entry["code"], colors)
    engine = entry.get("engine", "dot")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as f:
        f.write(dot_code)
        dot_path = f.name

    try:
        r = subprocess.run(
            [engine, "-Tsvg", "-o", str(final), dot_path],
            capture_output=True, encoding="utf-8", errors="replace", text=True, timeout=30,
        )
        if r.returncode != 0 or not final.exists():
            return {"error": f"{engine} failed: {(r.stderr or '')[:300]}"}
        w, h = _svg_dimensions(str(final))
        return {"file": str(final), "format": "svg", "width_pt": w, "height_pt": h}
    finally:
        os.unlink(dot_path)


def render_mermaid(entry: dict, outdir: Path, colors: dict) -> dict:
    """Render Mermaid diagram → SVG via mmdc."""
    fid = entry["id"]
    final = outdir / f"{fid}.svg"
    if final.exists():
        w, h = _svg_dimensions(str(final))
        return {"file": str(final), "format": "svg", "width_pt": w, "height_pt": h}

    config = {
        "theme": "base",
        "themeVariables": {
            "primaryColor": f"#{colors['card'][:6]}",
            "primaryTextColor": f"#{colors['pri']}",
            "primaryBorderColor": f"#{colors['pos']}",
            "lineColor": f"#{colors['sec']}",
            "secondaryColor": f"#{colors['bg']}",
            "tertiaryColor": f"#{colors['bg']}",
        },
    }

    with tempfile.TemporaryDirectory(prefix="mermaid_") as tmpdir:
        mmd_path = os.path.join(tmpdir, f"{fid}.mmd")
        cfg_path = os.path.join(tmpdir, "config.json")
        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(entry["code"])
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(config, f)

        r = subprocess.run(
            ["mmdc", "-i", mmd_path, "-o", str(final), "-c", cfg_path,
             "--backgroundColor", "transparent"],
            capture_output=True, encoding="utf-8", errors="replace", text=True, timeout=30,
        )
        if r.returncode != 0 or not final.exists():
            return {"error": f"mmdc failed: {(r.stderr or '')[:300]}"}

    w, h = _svg_dimensions(str(final))
    return {"file": str(final), "format": "svg", "width_pt": w, "height_pt": h}


def render_tikz(entry: dict, outdir: Path, colors: dict) -> dict:
    """Render TikZ → SVG (or PNG fallback)."""
    fid = entry["id"]
    fg = entry.get("fg_color", colors["pri"])

    for ext in ("svg", "png"):
        final = outdir / f"{fid}.{ext}"
        if final.exists():
            if ext == "svg":
                w, h = _svg_dimensions(str(final))
                return {"file": str(final), "format": "svg", "width_pt": w, "height_pt": h}
            elif Image:
                img = Image.open(str(final))
                return {"file": str(final), "format": "png",
                        "width_px": img.size[0], "height_px": img.size[1], "dpi": 300}

    tex_src = (
        r"\documentclass[border=2pt]{standalone}" "\n"
        r"\usepackage{tikz,amsmath,amssymb}" "\n"
        r"\usetikzlibrary{arrows.meta,positioning,calc,shapes,fit,backgrounds}" "\n"
        r"\usepackage{xcolor}" "\n"
        f"\\definecolor{{fgcolor}}{{HTML}}{{{fg}}}\n"
        f"\\definecolor{{pos}}{{HTML}}{{{colors['pos']}}}\n"
        f"\\definecolor{{neg}}{{HTML}}{{{colors['neg']}}}\n"
        f"\\definecolor{{emp}}{{HTML}}{{{colors['emp']}}}\n"
        r"\begin{document}" "\n"
        r"\color{fgcolor}" "\n"
        f"{entry['code']}\n"
        r"\end{document}" "\n"
    )

    with tempfile.TemporaryDirectory(prefix="tikz_") as tmpdir:
        tex_path = os.path.join(tmpdir, f"{fid}.tex")
        pdf_path = os.path.join(tmpdir, f"{fid}.pdf")
        cropped_path = os.path.join(tmpdir, f"{fid}-crop.pdf")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_src)

        r = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
            capture_output=True, encoding="utf-8", errors="replace", text=True, timeout=30,
        )
        if not os.path.exists(pdf_path):
            tail = (r.stderr or r.stdout or "")[-500:]
            return {"error": f"xelatex failed: {tail}"}

        subprocess.run(["pdfcrop", pdf_path, cropped_path],
                       capture_output=True, encoding="utf-8", errors="replace", timeout=15)
        src_pdf = cropped_path if os.path.exists(cropped_path) else pdf_path

        # Try SVG via dvisvgm
        svg_final = outdir / f"{fid}.svg"
        r2 = subprocess.run(
            ["dvisvgm", "--pdf", "--no-fonts", "--exact-bbox", src_pdf, "-o", str(svg_final)],
            capture_output=True, encoding="utf-8", errors="replace", text=True, timeout=15,
        )
        if r2.returncode == 0 and svg_final.exists():
            w, h = _svg_dimensions(str(svg_final))
            return {"file": str(svg_final), "format": "svg", "width_pt": w, "height_pt": h}

        # PNG fallback
        png_prefix = os.path.join(tmpdir, f"{fid}-out")
        subprocess.run(
            ["pdftoppm", "-png", "-r", "300", "-singlefile", src_pdf, png_prefix],
            capture_output=True, encoding="utf-8", errors="replace", timeout=15,
        )
        tmp_png = f"{png_prefix}.png"
        if not os.path.exists(tmp_png):
            return {"error": "TikZ: both dvisvgm and pdftoppm failed"}

        png_final = outdir / f"{fid}.png"
        if Image:
            img = Image.open(tmp_png).convert("RGBA")
            pixels = img.load()
            w_px, h_px = img.size
            for yy in range(h_px):
                for xx in range(w_px):
                    rr, g, b, a = pixels[xx, yy]
                    if rr > 240 and g > 240 and b > 240:
                        pixels[xx, yy] = (rr, g, b, 0)
            img.save(str(png_final))
        else:
            import shutil
            shutil.copy2(tmp_png, str(png_final))
            w_px, h_px = 0, 0
        return {"file": str(png_final), "format": "png",
                "width_px": w_px, "height_px": h_px, "dpi": 300}


def extract_figure(entry: dict, outdir: Path, dpi: int = 300) -> dict:
    """Extract a figure from a PDF page via pdftoppm + optional Pillow crop."""
    fid = entry["id"]
    source = entry["source"]
    page = entry.get("page", 1)

    png_final = outdir / f"{fid}.png"
    if png_final.exists() and Image:
        img = Image.open(str(png_final))
        return {"file": str(png_final), "format": "png",
                "width_px": img.size[0], "height_px": img.size[1], "dpi": dpi}

    if not os.path.exists(source):
        return {"error": f"Source PDF not found: {source}"}

    with tempfile.TemporaryDirectory(prefix="extract_") as tmpdir:
        prefix = os.path.join(tmpdir, "page")
        r = subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
             "-singlefile", source, prefix],
            capture_output=True, encoding="utf-8", errors="replace", timeout=30,
        )
        tmp_png = f"{prefix}.png"
        if not os.path.exists(tmp_png):
            return {"error": f"pdftoppm failed for page {page}: {(r.stderr or b'').decode()[:200]}"}

        if Image:
            img = Image.open(tmp_png)
            crop = entry.get("crop")
            if crop:
                # crop: [left, upper, right, lower] as fractions 0-1 of image dimensions
                w_px, h_px = img.size
                box = (
                    int(crop[0] * w_px), int(crop[1] * h_px),
                    int(crop[2] * w_px), int(crop[3] * h_px),
                )
                img = img.crop(box)
            img.save(str(png_final))
            w_px, h_px = img.size
            if w_px < 800 or h_px < 800:
                print(f"  WARNING: {fid} resolution {w_px}x{h_px} — may be blurry when projected",
                      file=sys.stderr)
        else:
            import shutil
            shutil.copy2(tmp_png, str(png_final))
            w_px, h_px = 0, 0

    return {"file": str(png_final), "format": "png",
            "width_px": w_px, "height_px": h_px, "dpi": dpi}


def main():
    parser = argparse.ArgumentParser(description="Batch diagram renderer")
    parser.add_argument("diagrams", help="Path to diagrams.json")
    parser.add_argument("outdir", help="Output directory")
    parser.add_argument("--theme", default="academic_light",
                        choices=list(THEMES.keys()), help="Color theme")
    parser.add_argument("--dpi", type=int, default=300,
                        help="DPI for PDF figure extraction (default: 300)")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    colors = THEMES[args.theme]

    with open(args.diagrams, encoding="utf-8") as f:
        diagrams = json.load(f)

    renderers = {
        "graphviz": lambda e: render_graphviz(e, outdir, colors),
        "mermaid": lambda e: render_mermaid(e, outdir, colors),
        "tikz": lambda e: render_tikz(e, outdir, colors),
        "extract": lambda e: extract_figure(e, outdir, args.dpi),
    }

    manifest = {}
    errors = []

    for entry in diagrams:
        fid = entry["id"]
        dtype = entry.get("type", "graphviz")
        renderer = renderers.get(dtype)
        if not renderer:
            errors.append(f"  {fid}: unknown type '{dtype}'")
            manifest[fid] = {"error": f"unknown type '{dtype}'"}
            continue
        result = renderer(entry)
        if "error" in result:
            errors.append(f"  {fid}: {result['error']}")
        manifest[fid] = result

    manifest_path = outdir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Rendered {len(diagrams) - len(errors)}/{len(diagrams)} diagrams → {outdir}/")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
