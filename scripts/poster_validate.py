#!/usr/bin/env python3
"""Validate poster quality and generate a validation report.

Checks structure, content, and quality metrics against poster Hard Rules.

Usage:
  python3 scripts/poster_validate.py --project-dir <paper_dir> [--poster-dir <poster_dir>]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def check_structure(html: str) -> list[dict]:
    """Check structural requirements."""
    issues: list[dict] = []

    # Count cards in CARD_REGISTRY
    card_count = len(re.findall(r"(\w+):\s*\{[\s\S]*?title:", html))
    if card_count < 3:
        issues.append({"severity": "CRITICAL", "rule": "S1", "message": f"Too few cards: {card_count} (minimum 3)"})

    # Check for grow:true cards
    grow_count = len(re.findall(r"grow:\s*true", html))
    if grow_count == 0:
        issues.append({"severity": "MAJOR", "rule": "S2", "message": "No cards with grow:true (at least one per column needed)"})

    # Count columns
    col_matches = re.findall(r"id:\s*'col\d+'", html)
    num_cols = len(col_matches)
    if num_cols > 4:
        issues.append({"severity": "MAJOR", "rule": "S3", "message": f"Too many columns: {num_cols} (max 4)"})

    # Check @page matches body
    page_match = re.search(r"@page\s*\{\s*size:\s*(\d+)mm\s+(\d+)mm", html)
    body_w_match = re.search(r"body\s*\{[^}]*width:\s*(\d+)mm", html)
    body_h_match = re.search(r"body\s*\{[^}]*height:\s*(\d+)mm", html)
    if page_match and body_w_match and body_h_match:
        pw, ph = int(page_match.group(1)), int(page_match.group(2))
        bw, bh = int(body_w_match.group(1)), int(body_h_match.group(1))
        if pw != bw or ph != bh:
            issues.append({"severity": "CRITICAL", "rule": "S4", "message": f"@page size ({pw}x{ph}) != body size ({bw}x{bh})"})

    return issues


def check_content(html: str) -> list[dict]:
    """Check content requirements."""
    issues: list[dict] = []

    # Check for FILL_IN placeholders
    fill_ins = re.findall(r"FILL_IN[:\w]*", html)
    if fill_ins:
        issues.append({
            "severity": "MAJOR",
            "rule": "C1",
            "message": f"Found {len(fill_ins)} FILL_IN placeholder(s): {', '.join(set(fill_ins)[:5])}",
        })

    # Check QR code
    if "qr.png" not in html and "qr-code" not in html.lower():
        issues.append({"severity": "MINOR", "rule": "C2", "message": "No QR code found"})

    # Check for unresolved image sources
    img_srcs = re.findall(r'src="([^"]+)"', html)
    for src in img_srcs:
        if src.startswith("http") or src.startswith("data:"):
            continue
        # Relative paths — can't verify without poster_dir, just flag suspicious ones
        if "FILL" in src.upper() or "TODO" in src.upper():
            issues.append({"severity": "MAJOR", "rule": "C3", "message": f"Unresolved image source: {src}"})

    # Check print CSS hides editor UI
    if "@media print" not in html:
        issues.append({"severity": "MAJOR", "rule": "C4", "message": "Missing @media print rules (editor UI visible in print)"})

    return issues


def check_quality(html: str) -> list[dict]:
    """Check quality requirements."""
    issues: list[dict] = []

    # Check font-scale CSS variable
    if "--font-scale" not in html:
        issues.append({"severity": "MINOR", "rule": "Q1", "message": "Missing --font-scale CSS variable"})

    # Check image sizing (must use width:100% height:100% object-fit:contain)
    if "object-fit:contain" not in html and "object-fit: contain" not in html:
        issues.append({"severity": "MAJOR", "rule": "Q2", "message": "Images missing object-fit:contain"})

    # Check self-contained (no build step references)
    if "npm run" in html or "webpack" in html or "import " in html:
        issues.append({"severity": "MAJOR", "rule": "Q3", "message": "Poster should be self-contained (no build step)"})

    return issues


def check_assets(poster_dir: Path) -> list[dict]:
    """Check asset files exist."""
    issues: list[dict] = []

    index = poster_dir / "index.html"
    if not index.exists():
        issues.append({"severity": "CRITICAL", "rule": "A1", "message": "poster/index.html not found"})
        return issues

    html = index.read_text(encoding="utf-8", errors="replace")

    # Check referenced images exist
    img_srcs = re.findall(r'src="([^"]+)"', html)
    for src in img_srcs:
        if src.startswith("http") or src.startswith("data:"):
            continue
        asset_path = poster_dir / src
        if not asset_path.exists():
            issues.append({"severity": "MAJOR", "rule": "A2", "message": f"Missing asset: {src}"})

    return issues


def calculate_score(issues: list[dict]) -> int:
    """Calculate quality score starting at 100."""
    score = 100
    for issue in issues:
        if issue["severity"] == "CRITICAL":
            score -= 15
        elif issue["severity"] == "MAJOR":
            score -= 5
        elif issue["severity"] == "MINOR":
            score -= 1
    return max(0, score)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate poster quality and generate report.")
    parser.add_argument("--project-dir", required=True, help="Paper/project root directory")
    parser.add_argument("--poster-dir", default=None, help="Poster directory (default: <project-dir>/poster)")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    poster_dir = Path(args.poster_dir) if args.poster_dir else project_dir / "poster"
    index_html = poster_dir / "index.html"

    if not index_html.exists():
        return fail(f"poster/index.html not found: {index_html}")

    html = index_html.read_text(encoding="utf-8", errors="replace")

    # Run all checks
    all_issues: list[dict] = []
    all_issues.extend(check_structure(html))
    all_issues.extend(check_content(html))
    all_issues.extend(check_quality(html))
    all_issues.extend(check_assets(poster_dir))

    score = calculate_score(all_issues)

    # Count by severity
    by_severity = {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0}
    for issue in all_issues:
        by_severity[issue["severity"]] = by_severity.get(issue["severity"], 0) + 1

    # Print results
    print(f"Poster Validation: {'PASS' if score >= 85 else 'FAIL'}")
    print(f"Score: {score}/100 (threshold: 85)")
    print(f"Issues: {by_severity['CRITICAL']} critical, {by_severity['MAJOR']} major, {by_severity['MINOR']} minor")
    print()

    for issue in sorted(all_issues, key=lambda x: {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2}[x["severity"]]):
        print(f"  [{issue['severity']}] {issue['rule']}: {issue['message']}")

    # Generate validation report
    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    report_path = notes_dir / "poster-validation.md"

    report_lines = [
        "# Poster Validation Report",
        "",
        f"**Score**: {score}/100 ({'PASS' if score >= 85 else 'FAIL'})",
        f"**Threshold**: 85",
        "",
        "## Issues",
        "",
        "| Severity | Rule | Message |",
        "|----------|------|---------|",
    ]
    for issue in sorted(all_issues, key=lambda x: {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2}[x["severity"]]):
        report_lines.append(f"| {issue['severity']} | {issue['rule']} | {issue['message']} |")

    if not all_issues:
        report_lines.append("| — | — | No issues found |")

    report_lines.extend([
        "",
        "## Scoring Rubric",
        "- Start at 100",
        "- CRITICAL: -15 each (broken layout, missing index.html)",
        "- MAJOR: -5 each (FILL_IN placeholders, missing assets, layout issues)",
        "- MINOR: -1 each (missing QR code, font-scale)",
        "",
        f"## Summary",
        f"- Critical: {by_severity['CRITICAL']}",
        f"- Major: {by_severity['MAJOR']}",
        f"- Minor: {by_severity['MINOR']}",
        f"- Final score: {score}",
        "",
    ])

    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nReport: {report_path}")

    return 0 if score >= 85 else 1


if __name__ == "__main__":
    raise SystemExit(main())
