#!/usr/bin/env python3
"""Generate and validate a reporting-guideline worksheet.

Version: 2026-09-05-v1

Outside computer science, the checklist that decides a paper's fate is not the
venue's own: it is the reporting guideline for the study design. PRISMA for a
systematic review, CONSORT for a randomized trial, STROBE for an observational
study, COREQ or SRQR for qualitative work, CHERRIES for a web survey, CARE for
a case report, JARS for APA journals.

This script reads a question set from assets/checklists/<guideline>.md, scans
the manuscript for detectable signals, and writes a worksheet to
notes/reporting-<guideline>.md with every answer left blank. It never answers
a question. --validate then checks that a human filled it in.

The worksheet is a working document. Journals that require a guideline want
their own official checklist file submitted with the manuscript; each question
set names where to download it.

Usage:
  python scripts/reporting_guideline.py --list
  python scripts/reporting_guideline.py --guideline prisma2020 --project-dir papers/my-review
  python scripts/reporting_guideline.py --guideline prisma2020 --project-dir papers/my-review --validate
  python scripts/reporting_guideline.py --for-discipline medicine
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from paper_utils import enable_utf8_stdout, get_assets_dir, now_iso

BANNER = "reporting_guideline 2026-09-05-v1"

VALID_ANSWERS = {"yes", "no", "na", "n/a"}

# Item headings look like '## 1. Title' or '## 1a. Title'.
ITEM_PATTERN = re.compile(
    r"^## ([0-9]+[a-z]?)\. (.+?)\n\*\*Question:\*\* (.+?)\n\*\*Guidance:\*\* (.+?)(?=\n## |\Z)",
    re.MULTILINE | re.DOTALL,
)

# Venue checklists live in the same folder; these are not reporting guidelines.
VENUE_CHECKLISTS = {"neurips", "icml", "iclr", "acl", "aaai", "cvpr"}

# (topic pattern, manuscript pattern, hint). A match is a hint, never an answer.
SIGNAL_DETECTORS: list[tuple[re.Pattern, re.Pattern, str]] = [
    (
        re.compile(r"registration|protocol", re.IGNORECASE),
        re.compile(r"(PROSPERO|ClinicalTrials\.gov|NCT\d{8}|ISRCTN|OSF\.io|preregist)", re.IGNORECASE),
        "manuscript mentions a registry or preregistration identifier",
    ),
    (
        re.compile(r"ethic|consent|IRB", re.IGNORECASE),
        re.compile(r"(ethics (committee|approval)|institutional review board|IRB|informed consent)", re.IGNORECASE),
        "manuscript mentions ethics approval or informed consent",
    ),
    (
        re.compile(r"funding|support", re.IGNORECASE),
        re.compile(r"(funded by|grant (no|number)|funding statement|no funding)", re.IGNORECASE),
        "manuscript mentions funding",
    ),
    (
        re.compile(r"competing|conflict", re.IGNORECASE),
        re.compile(r"(competing interest|conflict of interest|declare no)", re.IGNORECASE),
        "manuscript mentions competing interests",
    ),
    (
        re.compile(r"availability|data|code", re.IGNORECASE),
        re.compile(r"(data availability|available at|github\.com|osf\.io|zenodo\.org|dryad)", re.IGNORECASE),
        "manuscript mentions a data or code location",
    ),
    (
        re.compile(r"flow|selection|participant", re.IGNORECASE),
        re.compile(r"(flow (diagram|chart)|PRISMA flow|CONSORT flow)", re.IGNORECASE),
        "manuscript mentions a flow diagram",
    ),
    (
        re.compile(r"sample size|power", re.IGNORECASE),
        re.compile(r"(power analysis|sample size (was )?(calculat|determin)|G\*Power)", re.IGNORECASE),
        "manuscript mentions a sample size calculation",
    ),
    (
        re.compile(r"limitation", re.IGNORECASE),
        re.compile(r"(\\section\*?\{[^}]*[Ll]imitation|^#+ .*[Ll]imitation)", re.IGNORECASE | re.MULTILINE),
        "manuscript has a limitations section",
    ),
    (
        re.compile(r"reflexiv|researcher", re.IGNORECASE),
        re.compile(r"(reflexivit|positionalit)", re.IGNORECASE),
        "manuscript mentions reflexivity or positionality",
    ),
    (
        re.compile(r"saturation", re.IGNORECASE),
        re.compile(r"(saturation|information power)", re.IGNORECASE),
        "manuscript mentions data saturation",
    ),
    (
        re.compile(r"software", re.IGNORECASE),
        re.compile(r"(NVivo|ATLAS\.ti|MAXQDA|Dedoose|R version|SPSS|Stata|SAS)", re.IGNORECASE),
        "manuscript names analysis software",
    ),
    (
        re.compile(r"certainty|GRADE|risk of bias", re.IGNORECASE),
        re.compile(r"(GRADE|RoB 2|ROBINS-I|QUADAS|Newcastle-Ottawa|risk of bias)", re.IGNORECASE),
        "manuscript names a risk-of-bias or certainty tool",
    ),
]


def checklists_dir() -> Path:
    return get_assets_dir() / "checklists"


def available_guidelines() -> list[str]:
    """Return the reporting-guideline slugs, excluding the venue checklists."""
    directory = checklists_dir()
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.md") if p.stem not in VENUE_CHECKLISTS)


def load_guideline(guideline: str) -> tuple[str, list[dict]]:
    """Return (header text, items) for one guideline question set."""
    slug = guideline.strip().lower()
    path = checklists_dir() / f"{slug}.md"
    if not path.is_file():
        known = ", ".join(available_guidelines()) or "(none)"
        raise FileNotFoundError(f"no question set for guideline {slug!r}: {path}. Available: {known}")

    content = path.read_text(encoding="utf-8")
    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else slug

    items = []
    for match in ITEM_PATTERN.finditer(content):
        number, topic, question, guidance = match.groups()
        items.append(
            {
                "number": number,
                "topic": topic.strip(),
                "question": question.strip().replace("\n", " "),
                "guidance": guidance.strip().replace("\n", " "),
            }
        )
    if not items:
        raise ValueError(f"{path.name}: no items parsed; check the '## N. Topic' heading format")
    return title, items


def find_manuscript(project_dir: Path) -> Path | None:
    """Return the manuscript to scan for signals, preferring LaTeX then Markdown."""
    for name in ("main.tex", "manuscript.tex", "paper.tex", "main.md", "manuscript.md"):
        candidate = project_dir / name
        if candidate.is_file():
            return candidate
    return None


def detect_signals(text: str, items: list[dict]) -> dict[str, str]:
    """Return {item number: hint}. Items are matched by topic, not by number."""
    signals: dict[str, str] = {}
    for item in items:
        haystack = f"{item['topic']} {item['question']}"
        for topic_pattern, content_pattern, hint in SIGNAL_DETECTORS:
            if topic_pattern.search(haystack) and content_pattern.search(text):
                signals[item["number"]] = hint
                break
    return signals


def generate_worksheet(title: str, guideline: str, items: list[dict], signals: dict[str, str]) -> str:
    """Render the worksheet with every answer left blank."""
    lines = [
        f"# {title} — Worksheet",
        f"Generated: {now_iso()} by {BANNER}",
        "",
        "Answer and Location are always left as [TODO]. This tool never answers a",
        "reporting-guideline question: the answer depends on what you actually did.",
        '"Detected signal" comes from scanning the manuscript text and is a hint, not a verdict.',
        "",
        "Answer each item Yes, No, or NA. Yes needs a Location (section, page, table or",
        "figure). No and NA need a one-line reason in Location.",
        "",
        f"Validate with: python scripts/reporting_guideline.py --guideline {guideline} "
        "--project-dir <dir> --validate",
        "",
    ]
    for item in items:
        lines.append(f"## {item['number']}. {item['topic']}")
        lines.append(f"**Question:** {item['question']}")
        lines.append(f"**Guidance:** {item['guidance']}")
        if item["number"] in signals:
            lines.append(f"**Detected signal:** {signals[item['number']]}")
        lines.append("**Answer:** [TODO: Yes/No/NA]")
        lines.append("**Location:** [TODO]")
        lines.append("")
    return "\n".join(lines)


def validate_worksheet(content: str) -> list[str]:
    """Return the problems in a filled-in worksheet; empty means it passes."""
    problems: list[str] = []
    headings = list(re.finditer(r"^## ([0-9]+[a-z]?)\. (.+)$", content, re.MULTILINE))
    if not headings:
        return ["worksheet has no items; regenerate it"]

    for index, match in enumerate(headings):
        number, topic = match.groups()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
        block = content[match.end() : end]

        answer_match = re.search(r"\*\*Answer:\*\*\s*(.*)", block)
        answer = answer_match.group(1).strip() if answer_match else ""
        if answer.lower() not in VALID_ANSWERS:
            problems.append(
                f"Item {number} ({topic}): answer must be Yes, No or NA "
                f"(got: {answer or 'blank'})"
            )
            continue

        location_match = re.search(r"\*\*Location:\*\*\s*(.*)", block)
        location = location_match.group(1).strip() if location_match else ""
        if not location or "[TODO" in location:
            problems.append(f"Item {number} ({topic}): answered {answer!r} but Location is empty")

    return problems


def worksheet_path(project_dir: Path, guideline: str) -> Path:
    return project_dir / "notes" / f"reporting-{guideline}.md"


def cmd_list() -> int:
    guidelines = available_guidelines()
    if not guidelines:
        print("No reporting guidelines installed under assets/checklists/.")
        return 1
    print(f"{len(guidelines)} reporting guideline(s):\n")
    for slug in guidelines:
        try:
            title, items = load_guideline(slug)
        except (OSError, ValueError) as exc:
            print(f"  {slug:<14} INVALID: {exc}")
            continue
        print(f"  {slug:<14} {len(items):>3} items  {title.split(' — ')[0]}")
    return 0


def cmd_for_discipline(discipline: str) -> int:
    from discipline_profile import DisciplineError, load_discipline

    try:
        config = load_discipline(discipline)
    except DisciplineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    guidelines = config.get("reporting_guidelines") or []
    if not guidelines:
        print(f"{config['display_name']} has no reporting-guideline tradition.")
        return 0
    print(f"{config['display_name']} — guidelines to choose from, by study design:\n")
    for slug in guidelines:
        title, items = load_guideline(slug)
        print(f"  {slug:<14} {len(items):>3} items  {title.split(' — ')[0]}")
    print("\nPick the one matching your design; running more than one is normal for mixed methods.")
    return 0


def main() -> int:
    enable_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="Generate and validate a reporting-guideline worksheet (PRISMA, CONSORT, STROBE, COREQ, ...)."
    )
    parser.add_argument("--list", action="store_true", help="list installed reporting guidelines")
    parser.add_argument("--for-discipline", help="show the guidelines a discipline uses")
    parser.add_argument("--guideline", help="guideline slug, e.g. prisma2020")
    parser.add_argument("--project-dir", help="the paper directory holding notes/")
    parser.add_argument("--validate", action="store_true", help="check a filled-in worksheet instead of generating one")
    parser.add_argument("--force", action="store_true", help="overwrite an existing worksheet")
    args = parser.parse_args()

    if args.list:
        return cmd_list()
    if args.for_discipline:
        return cmd_for_discipline(args.for_discipline)

    if not args.guideline or not args.project_dir:
        parser.print_help()
        print("\nerror: --guideline and --project-dir are both required", file=sys.stderr)
        return 2

    guideline = args.guideline.strip().lower()
    project_dir = Path(args.project_dir)
    if not project_dir.is_dir():
        print(f"error: no such directory: {project_dir}", file=sys.stderr)
        return 2

    try:
        title, items = load_guideline(guideline)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out_path = worksheet_path(project_dir, guideline)

    if args.validate:
        if not out_path.is_file():
            print(f"error: no worksheet at {out_path}; generate it first", file=sys.stderr)
            return 2
        problems = validate_worksheet(out_path.read_text(encoding="utf-8"))
        if problems:
            print(f"{len(problems)} unfinished item(s) in {out_path}:\n")
            for problem in problems:
                print(f"  {problem}")
            print(f"\n{BANNER}: FAIL")
            return 1
        print(f"{BANNER}: {out_path.name} is complete — {len(items)} items answered with locations")
        return 0

    if out_path.exists() and not args.force:
        print(f"error: {out_path} already exists; pass --force to overwrite", file=sys.stderr)
        return 2

    manuscript = find_manuscript(project_dir)
    signals: dict[str, str] = {}
    if manuscript is not None:
        signals = detect_signals(manuscript.read_text(encoding="utf-8", errors="replace"), items)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(generate_worksheet(title, guideline, items, signals), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"  {len(items)} items, {len(signals)} detected signal(s)")
    if manuscript is None:
        print("  No manuscript found to scan; every item starts with no hint.")
    print(f"  Answer every item, then re-run with --validate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
