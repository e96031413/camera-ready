#!/usr/bin/env python3
"""Perform automated self-review checks on a paper project.

Parses main.tex and ref.bib to produce a structured self-review report
at notes/self-review.md.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from paper_utils import now_iso


def parse_tex_structure(content: str) -> dict:
    """Extract structural information from LaTeX content."""
    sections: list[str] = re.findall(r"\\section\{([^}]+)\}", content)
    subsections: list[str] = re.findall(r"\\subsection\{([^}]+)\}", content)

    # Abstract
    abstract_match = re.search(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}", content, re.DOTALL
    )
    has_abstract = abstract_match is not None
    abstract_word_count = 0
    if abstract_match:
        abstract_text = abstract_match.group(1)
        # Strip LaTeX commands for approximate word count
        cleaned = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", abstract_text)
        cleaned = re.sub(r"\\[a-zA-Z]+", "", cleaned)
        cleaned = re.sub(r"[{}~$%&]", " ", cleaned)
        abstract_word_count = len(cleaned.split())

    # Citations
    cite_matches = re.findall(r"\\cite\{([^}]+)\}", content)
    total_cites = 0
    for match in cite_matches:
        keys = [k.strip() for k in match.split(",")]
        total_cites += len(keys)

    # Figures and tables
    figure_count = len(re.findall(r"\\begin\{figure\*?\}", content))
    table_count = len(re.findall(r"\\begin\{table\*?\}", content))

    # Check for figures with captions
    figures_with_captions = len(
        re.findall(r"\\begin\{figure\*?\}.*?\\caption\{", content, re.DOTALL)
    )

    # Limitations / discussion section
    has_limitations = bool(
        re.search(r"\\section\{.*(?:limitation|discussion).*\}", content, re.IGNORECASE)
    )

    # ReferencesStart marker
    has_references_marker = "\\label{ReferencesStart}" in content

    return {
        "sections": sections,
        "subsections": subsections,
        "has_abstract": has_abstract,
        "abstract_word_count": abstract_word_count,
        "total_cites": total_cites,
        "figure_count": figure_count,
        "table_count": table_count,
        "figures_with_captions": figures_with_captions,
        "has_limitations": has_limitations,
        "has_references_marker": has_references_marker,
    }


def parse_bib(content: str) -> dict:
    """Extract information from BibTeX content."""
    entry_pattern = re.compile(
        r"@(\w+)\{([^,]+),\s*(.*?)\n\}", re.DOTALL
    )
    entries = entry_pattern.findall(content)
    total = len(entries)

    missing_fields: list[str] = []
    for entry_type, key, body in entries:
        if entry_type.lower() in ("comment", "string", "preamble"):
            continue
        key = key.strip()
        has_year = bool(re.search(r"\byear\s*=", body, re.IGNORECASE))
        has_title = bool(re.search(r"\btitle\s*=", body, re.IGNORECASE))
        has_author = bool(re.search(r"\bauthor\s*=", body, re.IGNORECASE))
        missing = []
        if not has_year:
            missing.append("year")
        if not has_title:
            missing.append("title")
        if not has_author:
            missing.append("author")
        if missing:
            missing_fields.append(f"{key} (missing: {', '.join(missing)})")

    return {
        "total": total,
        "missing_fields": missing_fields,
    }


def generate_report(
    tex_info: dict,
    bib_info: dict,
    timestamp: str,
) -> str:
    """Generate the self-review report as Markdown."""
    yes_no = lambda b: "Yes" if b else "No"  # noqa: E731

    lines = [
        "# Self-Review Report",
        f"Generated: {timestamp}",
        "",
        "## Structure",
        f"- Sections: {len(tex_info['sections'])}",
        f"- Subsections: {len(tex_info['subsections'])}",
        f"- Abstract present: {yes_no(tex_info['has_abstract'])}",
        f"- Abstract word count: ~{tex_info['abstract_word_count']}",
        f"- Has limitations section: {yes_no(tex_info['has_limitations'])}",
        f"- Has ReferencesStart marker: {yes_no(tex_info['has_references_marker'])}",
        "",
        "## Citations",
        f"- Total \\cite commands: {tex_info['total_cites']}",
        f"- Total bib entries: {bib_info['total']}",
    ]

    if bib_info["missing_fields"]:
        lines.append(f"- Entries with missing fields: {len(bib_info['missing_fields'])}")
        for entry in bib_info["missing_fields"]:
            lines.append(f"  - {entry}")
    else:
        lines.append("- Entries with missing fields: 0")

    lines.extend(
        [
            "",
            "## Figures & Tables",
            f"- Figures: {tex_info['figure_count']}",
            f"- Tables: {tex_info['table_count']}",
            f"- Figures with captions: {tex_info['figures_with_captions']}",
            "",
            "## Checklist",
            "- [ ] Abstract has problem/method/results/contributions",
            "- [ ] Limitations section present",
            "- [ ] All figures have captions",
            "- [ ] Citation count meets target (60-80 for review, varies for conference)",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    """Run self-review checks and output report."""
    parser = argparse.ArgumentParser(
        description="Perform automated self-review checks on a paper project."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Paper project directory containing main.tex.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        print(f"error: project dir not found: {project_dir}", file=sys.stderr)
        return 1

    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        print(f"error: main.tex not found in {project_dir}", file=sys.stderr)
        return 1

    ref_bib = project_dir / "ref.bib"

    # Parse main.tex
    tex_content = main_tex.read_text(encoding="utf-8", errors="replace")
    tex_info = parse_tex_structure(tex_content)

    # Parse ref.bib
    if ref_bib.exists():
        bib_content = ref_bib.read_text(encoding="utf-8", errors="replace")
        bib_info = parse_bib(bib_content)
    else:
        bib_info = {"total": 0, "missing_fields": []}

    # Generate report
    timestamp = now_iso()
    report = generate_report(tex_info, bib_info, timestamp)

    # Write report
    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    report_path = notes_dir / "self-review.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Self-review report written to: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
