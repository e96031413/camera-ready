#!/usr/bin/env python3
"""Generate and validate a venue paper checklist (e.g. NeurIPS) for a project.

Reads the question set from assets/checklists/<venue>.md (neurips, icml, iclr,
acl, aaai, cvpr), scans main.tex for detectable signals (limitations section, error bars/seeds, compute details,
code/data release URLs), and writes a worksheet to notes/paper-checklist.md.
Detected signals are shown as hints only — Answer/Justification are always
left blank for the author to fill in; this script never fabricates a
checklist answer.

Also emits a LaTeX pre-fill SCAFFOLD (checklist.tex) with paraphrased question
text -- NOT submission-ready. Before submitting, replace it with the verbatim
checklist block from the current venue .sty/template (most venues require the
questions/guidelines to be unmodified), then fill in \\answerYes{}/\\answerNo{}/
\\answerNA{}. --validate checks the notes/ worksheet only, as a QA gate.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from paper_utils import get_assets_dir, now_iso
from venue_config import VenueConfigError, load_venue


def available_venues() -> list[str]:
    """Return the venue slugs that have a checklist question set."""
    directory = get_assets_dir() / "checklists"
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.md"))


def venue_display(venue: str) -> str:
    """Return a human-friendly display name for a venue slug.

    Reads assets/venues/<venue>.yaml when one exists so the display name stays
    in one place. Falls back to the upper-cased slug for a checklist that has
    no venue config yet.
    """
    slug = venue.lower()
    try:
        return str(load_venue(slug)["display_name"])
    except (VenueConfigError, KeyError):
        return slug.upper()


_ITEM_RE = re.compile(
    r"^## (\d+)\. (.+?)\n\*\*Question:\*\* (.+?)\n\*\*Guidance:\*\* (.+?)(?=\n## |\Z)",
    re.MULTILINE | re.DOTALL,
)

# Signal detectors. Each entry is (topic pattern, content pattern, hint).
#
# Detectors match on the checklist item's TOPIC, not its number: item 2 is
# "Limitations" at NeurIPS but "Risks" at ACL, so numbering is not portable
# across venues. A match is a hint for the author, never an auto-answer.
_SIGNAL_DETECTORS: list[tuple[re.Pattern, re.Pattern, str]] = [
    (
        re.compile(r"limitation", re.IGNORECASE),
        re.compile(r"\\section\*?\{[^}]*[Ll]imitation", re.IGNORECASE),
        "Limitations section found",
    ),
    (
        re.compile(r"theor|proof", re.IGNORECASE),
        re.compile(r"\\begin\{(theorem|proof|lemma)\}", re.IGNORECASE),
        "Theorem/proof environment found",
    ),
    (
        re.compile(
            r"open access|code availability|code and data|reproducibility assets|existing packages",
            re.IGNORECASE,
        ),
        re.compile(r"(github\.com|anonymous\.4open\.science|zenodo\.org|huggingface\.co)"),
        "Code/data hosting URL found",
    ),
    (
        re.compile(
            r"experimental setting|experimental setup|hyperparameter|implementation detail",
            re.IGNORECASE,
        ),
        re.compile(
            r"\\section\*?\{[^}]*(Experimental Setup|Implementation Details|Hyperparameter)",
            re.IGNORECASE,
        ),
        "Experimental setup/hyperparameter section found",
    ),
    (
        re.compile(r"significance|variability|number of runs|descriptive statistics", re.IGNORECASE),
        re.compile(r"(\\pm|stderr|std\s*err|confidence interval|error bar|\bseeds?\b)", re.IGNORECASE),
        "Error bar / seed / significance language found",
    ),
    (
        re.compile(r"compute", re.IGNORECASE),
        re.compile(r"\b(GPU|TPU|V100|A100|H100|compute hours?)\b", re.IGNORECASE),
        "Compute resource mention found",
    ),
    (
        re.compile(r"broader impact|societal", re.IGNORECASE),
        re.compile(r"\\section\*?\{[^}]*(Broader Impact|Societal Impact)", re.IGNORECASE),
        "Broader/societal impact section found",
    ),
    (
        re.compile(r"ethic", re.IGNORECASE),
        re.compile(r"\\section\*?\{[^}]*Ethic", re.IGNORECASE),
        "Ethics statement section found",
    ),
    (
        re.compile(r"llm|ai assistant", re.IGNORECASE),
        re.compile(r"\b(GPT-4|ChatGPT|large language model|LLM)\b"),
        "LLM mention found (verify whether it is a core method component)",
    ),
    (
        re.compile(r"anonym", re.IGNORECASE),
        re.compile(r"\\(author|thanks|IEEEauthorblockN)\b"),
        "Author macro present (run anonymity_check.py before answering)",
    ),
]


def load_checklist(venue: str) -> list[dict]:
    """Load and parse a checklist question set from assets/checklists/<venue>.md."""
    path = get_assets_dir() / "checklists" / f"{venue.lower()}.md"
    if not path.exists():
        known = ", ".join(available_venues()) or "(none)"
        raise FileNotFoundError(
            f"no checklist asset for venue '{venue}': {path}. Available venues: {known}"
        )
    content = path.read_text(encoding="utf-8")
    items = []
    for match in _ITEM_RE.finditer(content):
        number, topic, question, guidance = match.groups()
        items.append(
            {
                "number": int(number),
                "topic": topic.strip(),
                "question": question.strip().replace("\n", " "),
                "guidance": guidance.strip().replace("\n", " "),
            }
        )
    return items


def detect_signals(tex_content: str, items: list[dict]) -> dict[int, str]:
    """Return {item_number: hint text} for detectable signals in main.tex.

    Items are matched by topic so the same detector set works for every venue.
    """
    signals: dict[int, str] = {}
    for item in items:
        for topic_pattern, content_pattern, description in _SIGNAL_DETECTORS:
            if topic_pattern.search(item["topic"]) and content_pattern.search(tex_content):
                signals[item["number"]] = description
                break
    return signals


def generate_worksheet(items: list[dict], signals: dict[int, str], venue: str, timestamp: str) -> str:
    """Generate the notes/paper-checklist.md worksheet."""
    lines = [
        f"# {venue_display(venue)} Paper Checklist Worksheet",
        f"Generated: {timestamp}",
        "",
        "Answer/Justification are always left as `[TODO]` — this tool never fabricates",
        "a checklist answer. \"Detected signal\" is a hint from scanning main.tex, not a verdict.",
        "",
    ]
    for item in items:
        lines.append(f"## {item['number']}. {item['topic']}")
        lines.append(f"**Question:** {item['question']}")
        lines.append(f"**Guidance:** {item['guidance']}")
        if item["number"] in signals:
            lines.append(f"**Detected signal:** {signals[item['number']]}")
        lines.append("**Answer:** [TODO: Yes/No/NA]")
        lines.append("**Justification:** [TODO]")
        lines.append("")
    return "\n".join(lines)


def generate_tex(items: list[dict], venue: str) -> str:
    """Generate a checklist.tex fragment using the official answer macros."""
    lines = [
        f"% {venue_display(venue)} Paper Checklist — generated worksheet.",
        "%",
        "% THIS IS A PRE-FILL SCAFFOLD, NOT A SUBMISSION-READY CHECKLIST.",
        "% The question/guidance text below is PARAPHRASED, not the verbatim block from",
        "% the venue style file. Before submitting, replace this entire section with the",
        "% verbatim \\section{...Paper Checklist} block from the current venue .sty/template",
        "% (the venue rules typically require the questions and guidelines to be unmodified),",
        "% then fill in \\answerYes{}/\\answerNo{}/\\answerNA{} and a justification for each item.",
        "%",
        "\\section*{" + f"{venue_display(venue)} Paper Checklist (SCAFFOLD -- replace before submission)" + "}",
        "\\begin{enumerate}",
    ]
    for item in items:
        lines.append(f"  \\item {{\\bf {item['topic']}}}")
        lines.append(f"    \\begin{{itemize}}")
        lines.append(f"    \\item[] Question: {item['question']}")
        lines.append("    % Answer: replace this comment with exactly one of \\answerYes{}, \\answerNo{}, \\answerNA{}")
        lines.append("    \\item[] Answer: TODO")
        lines.append("    \\item[] Justification: TODO")
        lines.append(f"    \\end{{itemize}}")
    lines.append("\\end{enumerate}")
    return "\n".join(lines)


_VALID_ANSWERS = {"yes", "no", "na", "n/a"}


def validate_worksheet(content: str) -> list[str]:
    """Return a list of problems found in a filled-in worksheet (empty = pass)."""
    problems = []
    for match in re.finditer(r"^## (\d+)\. (.+)$", content, re.MULTILINE):
        number, topic = match.groups()
        # Grab the block for this item up to the next '## ' heading.
        start = match.end()
        next_heading = content.find("\n## ", start)
        block = content[start:] if next_heading == -1 else content[start:next_heading]

        answer_match = re.search(r"\*\*Answer:\*\*\s*(.+)", block)
        answer = answer_match.group(1).strip() if answer_match else ""
        if answer.lower() not in _VALID_ANSWERS:
            problems.append(f"Item {number} ({topic}): answer must be exactly one of Yes/No/NA (got: {answer or 'blank'})")
            continue

        if answer.lower() in ("no", "yes"):
            just_match = re.search(r"\*\*Justification:\*\*\s*(.+)", block)
            if not just_match or "[TODO" in just_match.group(1) or not just_match.group(1).strip():
                problems.append(f"Item {number} ({topic}): answer is '{answer}' but justification is missing")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate/validate a venue paper checklist worksheet for a project."
    )
    parser.add_argument(
        "--project-dir",
        help="Paper project directory containing main.tex. Required unless --list-venues is given.",
    )
    parser.add_argument(
        "--venue",
        default="neurips",
        help="Venue checklist to use (default: neurips). One of: " + (", ".join(available_venues()) or "none found"),
    )
    parser.add_argument(
        "--list-venues",
        action="store_true",
        help="Print the venues that have a checklist question set, then exit.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate an existing notes/paper-checklist.md instead of generating one.",
    )
    parser.add_argument(
        "--emit-tex",
        action="store_true",
        help="Also write checklist.tex (pre-fill SCAFFOLD, not submission-ready -- see module docstring) to the project directory.",
    )
    args = parser.parse_args()

    if args.list_venues:
        for slug in available_venues():
            print(f"{slug:10} {venue_display(slug)}")
        return 0

    if not args.project_dir:
        print("error: --project-dir is required (or use --list-venues)", file=sys.stderr)
        return 1

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        print(f"error: project dir not found: {project_dir}", file=sys.stderr)
        return 1

    try:
        items = load_checklist(args.venue)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    notes_dir = project_dir / "notes"
    worksheet_path = notes_dir / "paper-checklist.md"

    if args.validate:
        if not worksheet_path.exists():
            print(f"error: worksheet not found: {worksheet_path}", file=sys.stderr)
            return 1
        content = worksheet_path.read_text(encoding="utf-8")
        problems = validate_worksheet(content)
        if problems:
            print(f"Checklist validation FAILED ({len(problems)} problem(s)):")
            for problem in problems:
                print(f"  - {problem}")
            return 1
        print(f"Checklist validation passed: {worksheet_path}")
        return 0

    main_tex = project_dir / "main.tex"
    tex_content = main_tex.read_text(encoding="utf-8", errors="replace") if main_tex.exists() else ""
    signals = detect_signals(tex_content, items)

    timestamp = now_iso()
    worksheet = generate_worksheet(items, signals, args.venue, timestamp)
    notes_dir.mkdir(parents=True, exist_ok=True)
    worksheet_path.write_text(worksheet, encoding="utf-8")
    print(f"Checklist worksheet written to: {worksheet_path}")

    if args.emit_tex:
        tex = generate_tex(items, args.venue)
        tex_path = project_dir / "checklist.tex"
        tex_path.write_text(tex, encoding="utf-8")
        print(f"Checklist LaTeX fragment written to: {tex_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
