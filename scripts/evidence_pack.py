#!/usr/bin/env python3
"""Generate per-section evidence packs for the writing phase.

Outputs (under <project-dir>/notes/evidence-packs/):
  - <section_id>.json for each \\section found in main.tex

Design goals:
- Deterministic and lightweight (stdlib-only).
- Privacy-safe: do not print absolute filesystem paths.
- Evidence packs provide structured input for section-level writing.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from paper_utils import now_iso, check_refined_guard


_SECTION_RE = re.compile(r"\\section\{([^}]+)\}")
_SUBSECTION_RE = re.compile(r"\\subsection\{([^}]+)\}")
_CITE_CMD_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}")
_COMMENT_RE = re.compile(r"(?<!\\)%.*$")
_BIB_ENTRY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)
_BIB_STOP_RE = re.compile(
    r"\\bibliography\{|\\begin\{thebibliography\}", re.IGNORECASE
)

# Sections to skip (frontmatter / backmatter)
_SKIP_SECTIONS = re.compile(
    r"(?i)^(abstract|acknowledgment|acknowledgement|references|bibliography)$"
)


def fail(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


def strip_comments(line: str) -> str:
    return _COMMENT_RE.sub("", line)


def parse_bib_keys(bib_text: str) -> list[str]:
    """Extract all BibTeX entry keys from bib file content."""
    keys: list[str] = []
    for m in _BIB_ENTRY_RE.finditer(bib_text):
        key = m.group(1).strip()
        if key:
            keys.append(key)
    return sorted(set(keys))


def extract_section_cites(text: str) -> list[str]:
    """Extract unique citation keys from a block of LaTeX text."""
    keys: list[str] = []
    for m in _CITE_CMD_RE.finditer(text):
        for raw in m.group(1).split(","):
            key = raw.strip()
            if key:
                keys.append(key)
    return sorted(set(keys))


def parse_sections(tex_text: str) -> list[dict]:
    """Parse main.tex into a list of section dicts with subsections and raw text.

    Returns a list of dicts:
      {
        "title": str,
        "subsections": [{"title": str, "text": str}, ...],
        "text": str,  # full text including subsection text
      }

    Sections matching _SKIP_SECTIONS or appearing after the bibliography
    stop marker are excluded.
    """
    lines = tex_text.splitlines()
    sections: list[dict] = []
    current_section: dict | None = None
    current_subsection: dict | None = None
    stopped = False

    def _flush_sub() -> None:
        nonlocal current_subsection
        if current_subsection is not None and current_section is not None:
            current_section["subsections"].append(current_subsection)
        current_subsection = None

    def _flush_sec() -> None:
        nonlocal current_section
        _flush_sub()
        if current_section is not None:
            title = current_section["title"]
            if not _SKIP_SECTIONS.match(title):
                sections.append(current_section)
        current_section = None

    for raw in lines:
        if stopped:
            break
        if _BIB_STOP_RE.search(raw):
            stopped = True
            break

        line = strip_comments(raw).rstrip("\n")

        sec_m = _SECTION_RE.search(line)
        if sec_m:
            _flush_sec()
            current_section = {
                "title": sec_m.group(1).strip(),
                "subsections": [],
                "text_lines": [],
            }
            continue

        sub_m = _SUBSECTION_RE.search(line)
        if sub_m and current_section is not None:
            _flush_sub()
            current_subsection = {
                "title": sub_m.group(1).strip(),
                "text_lines": [],
            }
            continue

        # Accumulate text lines
        if current_subsection is not None:
            current_subsection["text_lines"].append(line)
        if current_section is not None:
            current_section["text_lines"].append(line)

    _flush_sec()

    # Convert text_lines to joined text, build subsection title list
    result: list[dict] = []
    for sec in sections:
        text = "\n".join(sec["text_lines"])
        subsections: list[dict] = []
        for sub in sec["subsections"]:
            subsections.append({
                "title": sub["title"],
                "text": "\n".join(sub["text_lines"]),
            })
        result.append({
            "title": sec["title"],
            "subsections": subsections,
            "text": text,
        })
    return result


def load_issues_budgets(issues_csv_path: Path) -> dict[str, int]:
    """Load per-issue Target_Citations from the issues CSV.

    Returns a dict mapping issue Title (lowercased) -> Target_Citations int.
    This is a best-effort match: the issues CSV Title is matched against
    section titles case-insensitively.
    """
    budgets: dict[str, int] = {}
    if not issues_csv_path.exists():
        return budgets

    with issues_csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = (row.get("Title") or "").strip().lower()
            raw = (row.get("Target_Citations") or "").strip()
            if title and raw:
                try:
                    budgets[title] = int(raw)
                except ValueError:
                    pass
    return budgets


def load_literature_notes(lit_path: Path) -> str:
    """Read literature notes markdown if it exists."""
    if not lit_path.exists():
        return ""
    return lit_path.read_text(encoding="utf-8", errors="replace")


def build_evidence_pack(
    *,
    section_id: str,
    section_title: str,
    subsections: list[str],
    citation_budget: int,
    available_citations: list[str],
) -> dict:
    """Build a single evidence pack dict."""
    return {
        "section_id": section_id,
        "section_title": section_title,
        "subsections": subsections,
        "citation_budget": citation_budget,
        "available_citations": available_citations,
        "claims": [],
        "anchors": [],
        "gaps": [],
        "created_at": now_iso(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate per-section evidence packs (JSON) for the writing phase."
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Paper project directory containing main.tex (default: .).",
    )
    parser.add_argument(
        "--issues-csv",
        help="Path to issues CSV with Target_Citations column.",
    )
    parser.add_argument(
        "--default-budget",
        type=int,
        default=8,
        help="Default citation budget per section when not specified in issues CSV (default: 8).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite evidence packs even if .refined marker exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        return fail("project dir not found")
    if not project_dir.is_dir():
        return fail("project dir is not a directory")

    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        return fail("main.tex not found in project dir")

    # Read main.tex
    tex_text = main_tex.read_text(encoding="utf-8", errors="replace")

    # Parse sections
    sections = parse_sections(tex_text)
    if not sections:
        return fail("no sections found in main.tex")

    # Read ref.bib keys
    bib_path = project_dir / "ref.bib"
    all_bib_keys: list[str] = []
    if bib_path.exists():
        bib_text = bib_path.read_text(encoding="utf-8", errors="replace")
        all_bib_keys = parse_bib_keys(bib_text)

    # Load issues CSV budgets (optional)
    budgets: dict[str, int] = {}
    if args.issues_csv:
        issues_path = Path(args.issues_csv).expanduser().resolve()
        if not issues_path.exists():
            return fail(f"issues CSV not found: {issues_path.name}")
        budgets = load_issues_budgets(issues_path)

    # Create output directory
    packs_dir = project_dir / "notes" / "evidence-packs"
    packs_dir.mkdir(parents=True, exist_ok=True)

    # Generate evidence packs
    created = 0
    sec_num = 0
    for sec in sections:
        sec_num += 1
        section_id = str(sec_num)
        section_title = sec["title"]

        # Build subsection labels (e.g. "1.1 Self-Attention")
        subsection_labels: list[str] = []
        for sub_idx, sub in enumerate(sec["subsections"], start=1):
            subsection_labels.append(f"{sec_num}.{sub_idx} {sub['title']}")

        # Determine citation budget
        budget = args.default_budget
        title_lower = section_title.lower()
        if title_lower in budgets:
            budget = budgets[title_lower]

        # Find citations already used in this section's text
        section_cites = extract_section_cites(sec["text"])
        # Intersect with bib keys to get only valid available citations
        available = sorted(set(section_cites) & set(all_bib_keys))

        pack = build_evidence_pack(
            section_id=section_id,
            section_title=section_title,
            subsections=subsection_labels,
            citation_budget=budget,
            available_citations=available,
        )

        out_path = packs_dir / f"{section_id}.json"

        # Check refined guard before writing
        if not check_refined_guard(out_path, force=args.force):
            continue

        out_path.write_text(
            json.dumps(pack, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        created += 1

    print(f"Created {created} evidence packs in notes/evidence-packs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
