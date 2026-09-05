#!/usr/bin/env python3
"""Optimize poster layout using Playwright for whitespace measurement and PDF export.

Uses Chromium headless to:
1. Measure whitespace via posterAPI.getWaste()
2. Sweep column widths to minimize waste (--sweep)
3. Export print-ready PDF (--pdf)
4. Save preview screenshot (--screenshot)

Usage:
  python3 scripts/poster_optimize.py --project-dir <paper_dir> [--sweep] [--pdf] [--screenshot]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _check_playwright() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Optimize poster layout with Playwright whitespace measurement and PDF export."
    )
    parser.add_argument("--project-dir", required=True, help="Paper/project root directory")
    parser.add_argument("--poster-dir", default=None, help="Poster directory (default: <project-dir>/poster)")
    parser.add_argument("--sweep", action="store_true", help="Sweep column widths to minimize whitespace")
    parser.add_argument("--sweep-step", type=int, default=10, help="Column width sweep step in mm (default: 10)")
    parser.add_argument("--pdf", action="store_true", help="Export PDF after optimization")
    parser.add_argument("--screenshot", action="store_true", help="Save preview PNG")
    args = parser.parse_args()

    if not _check_playwright():
        return fail("Playwright not installed. Run: pip install playwright && playwright install chromium")

    from playwright.sync_api import sync_playwright

    project_dir = Path(args.project_dir)
    poster_dir = Path(args.poster_dir) if args.poster_dir else project_dir / "poster"
    index_html = poster_dir / "index.html"

    if not index_html.exists():
        return fail(f"poster/index.html not found: {index_html}")

    # Read poster dimensions from HTML
    html_text = index_html.read_text(encoding="utf-8")
    import re
    w_match = re.search(r"const POSTER_W_MM\s*=\s*(\d+)", html_text)
    h_match = re.search(r"const POSTER_H_MM\s*=\s*(\d+)", html_text)
    poster_w = int(w_match.group(1)) if w_match else 841
    poster_h = int(h_match.group(1)) if h_match else 594

    print(f"Poster: {poster_w}mm × {poster_h}mm")
    print(f"Opening: {index_html}")

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 3200, "height": 2260})
        page.goto(f"file://{index_html.resolve()}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)  # Wait for React + KaTeX render

        # Measure baseline whitespace
        waste = page.evaluate("window.posterAPI.getWaste()")
        print(f"\nBaseline whitespace: {waste['total']}px")
        for d in waste.get("details", []):
            print(f"  {d['card']}: H={d['wasteH']} W={d['wasteW']} ({d['pct']}%)")

        # Column width sweep
        if args.sweep:
            print(f"\nSweeping column widths (step={args.sweep_step}mm)...")
            layout = page.evaluate("window.posterAPI.getLayout()")
            num_cols = len(layout)

            if num_cols >= 3:
                # Sweep col1 and col3 widths (col2 is flex)
                best_waste = waste["total"]
                best_c1 = layout[0]["widthMm"]
                best_c3 = layout[2]["widthMm"]
                step = args.sweep_step

                for c1 in range(150, 400, step):
                    for c3 in range(130, 320, step):
                        page.evaluate(f'window.posterAPI.setColumnWidth("col1", {c1})')
                        page.evaluate(f'window.posterAPI.setColumnWidth("col3", {c3})')
                        page.wait_for_timeout(30)
                        w = page.evaluate("window.posterAPI.getWaste().total")
                        if w < best_waste:
                            best_waste = w
                            best_c1, best_c3 = c1, c3

                # Apply best
                page.evaluate(f'window.posterAPI.setColumnWidth("col1", {best_c1})')
                page.evaluate(f'window.posterAPI.setColumnWidth("col3", {best_c3})')
                page.wait_for_timeout(500)
                print(f"  Optimal: col1={best_c1}mm, col3={best_c3}mm")
                print(f"  Whitespace reduced: {waste['total']}px → {best_waste}px")
            elif num_cols == 2:
                best_waste = waste["total"]
                best_c1 = layout[0]["widthMm"]
                step = args.sweep_step

                for c1 in range(200, 500, step):
                    page.evaluate(f'window.posterAPI.setColumnWidth("col1", {c1})')
                    page.wait_for_timeout(30)
                    w = page.evaluate("window.posterAPI.getWaste().total")
                    if w < best_waste:
                        best_waste = w
                        best_c1 = c1

                page.evaluate(f'window.posterAPI.setColumnWidth("col1", {best_c1})')
                page.wait_for_timeout(500)
                print(f"  Optimal: col1={best_c1}mm")
                print(f"  Whitespace reduced: {waste['total']}px → {best_waste}px")

        # Save config
        config = page.evaluate("window.posterAPI.getConfig()")
        config_path = poster_dir / "poster-config.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        print(f"\nConfig saved: {config_path}")

        # Screenshot
        if args.screenshot:
            screenshot_path = poster_dir / "poster-preview.png"
            page.screenshot(path=str(screenshot_path))
            print(f"Screenshot: {screenshot_path}")

        # PDF export
        if args.pdf:
            pdf_path = poster_dir / "poster.pdf"
            page.pdf(
                path=str(pdf_path),
                width=f"{poster_w}mm",
                height=f"{poster_h}mm",
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                print_background=True,
            )
            print(f"PDF exported: {pdf_path}")

        # Final waste report
        final_waste = page.evaluate("window.posterAPI.getWaste()")
        print(f"\nFinal whitespace: {final_waste['total']}px")

        report = {
            "poster_dimensions": f"{poster_w}mm x {poster_h}mm",
            "baseline_waste_px": waste["total"],
            "final_waste_px": final_waste["total"],
            "config": config,
            "waste_details": final_waste.get("details", []),
        }
        report_path = poster_dir / "optimization-report.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Report: {report_path}")

        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
