#!/usr/bin/env python3
"""Generate poster project directory from paper source and HTML template.

Creates poster/ directory structure, copies template, patches dimensions/columns,
and optionally extracts content from paper main.tex.

Usage:
  python3 scripts/poster_generate.py --project-dir <paper_dir> [--dimensions A0] [--orientation landscape] [--columns 3]
  python3 scripts/poster_generate.py --project-dir <dir> --standalone  # no paper extraction
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import get_skill_root


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


# Standard poster sizes in mm (width, height) — always stored as (w, h)
POSTER_SIZES: dict[str, tuple[int, int]] = {
    "A0": (841, 1189),
    "A1": (594, 841),
    "24x36": (610, 914),
    "36x48": (914, 1219),
    "48x36": (1219, 914),
}


def parse_dimensions(dim_str: str) -> tuple[int, int]:
    """Parse dimension string into (width_mm, height_mm)."""
    upper = dim_str.upper()
    if upper in POSTER_SIZES:
        return POSTER_SIZES[upper]

    # Try WxH format (in mm)
    match = re.match(r"(\d+)\s*[xX×]\s*(\d+)", dim_str)
    if match:
        return int(match.group(1)), int(match.group(2))

    raise ValueError(f"Unknown dimension format: {dim_str}. Use A0, A1, 24x36, 36x48, or WxH (mm).")


def apply_orientation(w: int, h: int, orientation: str) -> tuple[int, int]:
    """Ensure dimensions match requested orientation."""
    if orientation == "landscape" and h > w:
        return h, w
    if orientation == "portrait" and w > h:
        return h, w
    return w, h


def patch_html_dimensions(html: str, w_mm: int, h_mm: int) -> str:
    """Patch poster dimensions in HTML template."""
    # Patch @page size
    html = re.sub(
        r"@page\s*\{\s*size:\s*\d+mm\s+\d+mm",
        f"@page {{ size: {w_mm}mm {h_mm}mm",
        html,
    )
    # Patch body width/height
    html = re.sub(
        r"body\s*\{([^}]*?)width:\s*\d+mm",
        lambda m: f"body {{{m.group(1)}width: {w_mm}mm",
        html,
    )
    html = re.sub(
        r"(body\s*\{[^}]*?)height:\s*\d+mm",
        lambda m: f"{m.group(1)}height: {h_mm}mm",
        html,
    )
    # Patch JS constants
    html = re.sub(r"const POSTER_W_MM\s*=\s*\d+", f"const POSTER_W_MM = {w_mm}", html)
    html = re.sub(r"const POSTER_H_MM\s*=\s*\d+", f"const POSTER_H_MM = {h_mm}", html)
    return html


def patch_html_columns(html: str, num_columns: int) -> str:
    """Patch default column count in DEFAULT_LAYOUT."""
    if num_columns == 3:
        return html  # Template default is 3 columns

    if num_columns == 2:
        layout = """const DEFAULT_LAYOUT = {
  columns: [
    { id: 'col1', widthMm: 380, cards: ['tldr', 'method'] },
    { id: 'col2', widthMm: null, cards: ['results', 'quant', 'concl'] },
  ],
};"""
    elif num_columns == 4:
        layout = """const DEFAULT_LAYOUT = {
  columns: [
    { id: 'col1', widthMm: 200, cards: ['tldr'] },
    { id: 'col2', widthMm: null, cards: ['method'] },
    { id: 'col3', widthMm: null, cards: ['results', 'quant'] },
    { id: 'col4', widthMm: 180, cards: ['concl'] },
  ],
};"""
    else:
        return html  # Only 2-4 columns supported

    html = re.sub(
        r"const DEFAULT_LAYOUT\s*=\s*\{[^;]*\};",
        layout,
        html,
        flags=re.DOTALL,
    )
    return html


def extract_paper_metadata(project_dir: Path) -> dict[str, str]:
    """Extract title, authors, abstract from main.tex if available."""
    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        return {}

    text = main_tex.read_text(encoding="utf-8", errors="replace")
    metadata: dict[str, str] = {}

    # Title
    title_match = re.search(r"\\title\{([^}]+)\}", text)
    if title_match:
        metadata["title"] = title_match.group(1).strip()

    # Authors (simplified extraction)
    author_match = re.search(r"\\author\{([^}]+)\}", text, re.DOTALL)
    if author_match:
        raw = author_match.group(1)
        # Remove LaTeX commands, keep text
        clean = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", raw)
        clean = re.sub(r"\\[a-zA-Z]+", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        metadata["authors"] = clean

    # Abstract
    abstract_match = re.search(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.DOTALL
    )
    if abstract_match:
        abstract = abstract_match.group(1).strip()
        # Truncate to 2-3 sentences for poster
        sentences = re.split(r"(?<=[.!?])\s+", abstract)
        metadata["abstract"] = " ".join(sentences[:3])

    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate poster project directory from paper source and HTML template."
    )
    parser.add_argument("--project-dir", required=True, help="Paper/project root directory")
    parser.add_argument(
        "--dimensions", default="A0",
        help="Poster size: A0, A1, 24x36, 36x48, or WxH in mm (default: A0)",
    )
    parser.add_argument(
        "--orientation", default="landscape", choices=["portrait", "landscape"],
        help="Poster orientation (default: landscape)",
    )
    parser.add_argument("--columns", type=int, default=3, choices=[2, 3, 4], help="Number of columns (default: 3)")
    parser.add_argument("--standalone", action="store_true", help="Skip paper content extraction")
    parser.add_argument("--force", action="store_true", help="Overwrite existing poster/")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    poster_dir = project_dir / "poster"

    if poster_dir.exists() and not args.force:
        return fail(f"poster/ already exists. Use --force to overwrite: {poster_dir}")

    # Parse dimensions
    try:
        w_mm, h_mm = parse_dimensions(args.dimensions)
    except ValueError as e:
        return fail(str(e))

    w_mm, h_mm = apply_orientation(w_mm, h_mm, args.orientation)
    print(f"Poster dimensions: {w_mm}mm × {h_mm}mm ({args.orientation})")

    # Read template
    skill_root = get_skill_root()
    template_path = skill_root / "assets" / "template" / "poster" / "template.html"
    if not template_path.exists():
        return fail(f"template not found: {template_path}")

    html = template_path.read_text(encoding="utf-8")

    # Patch dimensions and columns
    html = patch_html_dimensions(html, w_mm, h_mm)
    html = patch_html_columns(html, args.columns)

    # Extract paper metadata if not standalone
    if not args.standalone:
        metadata = extract_paper_metadata(project_dir)
        if metadata.get("title"):
            html = html.replace("FILL_IN_TITLE", metadata["title"])
            html = html.replace("PAPER_TITLE", metadata["title"])
            print(f"  title: {metadata['title']}")
        if metadata.get("authors"):
            html = html.replace("FILL_IN_AUTHORS", metadata["authors"])
            print(f"  authors: {metadata['authors'][:60]}...")

    # Create directory structure
    poster_dir.mkdir(parents=True, exist_ok=True)
    (poster_dir / "logos").mkdir(exist_ok=True)

    # Write poster HTML
    index_path = poster_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    print(f"\nCreated: {index_path}")

    # Generate QR code placeholder instructions
    print(f"Created: {poster_dir / 'logos/'}")
    print(f"\n--- Next Steps ---")
    print(f"1. Convert figures:  python3 scripts/poster_convert_figures.py --source-dir {project_dir}/figures --output-dir {poster_dir}")
    print(f"2. Generate QR code: curl -sL -o {poster_dir}/qr.png \"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=YOUR_PROJECT_URL\"")
    print(f"3. Add logos to:     {poster_dir}/logos/")
    print(f"4. Open in browser:  {index_path}")
    print(f"5. Edit CARD_REGISTRY in index.html with paper content")
    print(f"6. Optimize layout:  python3 scripts/poster_optimize.py --project-dir {project_dir} --sweep --pdf")
    print(f"7. Validate:         python3 scripts/poster_validate.py --project-dir {project_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
