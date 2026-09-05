#!/usr/bin/env python3
"""Check a paper project against its target venue's formatting requirements.

Runs four checks and prints a PASS/FAIL/WARN table:

  1. Page limit      -- main-text pages against the venue limit, read from the
                        compiled main.log and main.aux.
  2. Required sections -- every section the venue mandates appears in main.tex.
  3. Style file      -- the venue's style file is present and loaded.
  4. Anonymity       -- for double-blind venues, points at anonymity_check.py.

The gate reports; it does not edit. Exit code 1 means at least one FAIL.

Page counting reuses compile_paper.py, so the project must have been compiled
first: main.log and main.aux are the source of truth. Counting pages from the
LaTeX source is guesswork, and this gate exists precisely because guesswork
about page limits gets papers desk rejected.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from compile_paper import parse_label_page, parse_total_pages
from venue_config import VenueConfigError, list_venues, load_venue

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
SKIP = "SKIP"

_SECTION_RE = re.compile(r"\\(?:sub)*section\*?\s*\{([^}]*)\}")
_INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
_STYLE_LOAD_RE_TEMPLATE = r"\\(?:usepackage|documentclass)(?:\[[^\]]*\])?\s*\{{[^}}]*{stem}[^}}]*\}}"


class Check:
    """One gate result."""

    def __init__(self, name: str, status: str, detail: str) -> None:
        self.name = name
        self.status = status
        self.detail = detail


def read_tex_sources(project_dir: Path) -> str:
    """Return main.tex plus every \\input/\\include file, concatenated.

    Papers routinely split sections into separate .tex files. A section check
    that only reads main.tex would report a false FAIL on those projects.
    """
    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        return ""
    content = main_tex.read_text(encoding="utf-8", errors="replace")
    parts = [content]
    seen: set[Path] = {main_tex.resolve()}

    pending = list(_INPUT_RE.findall(content))
    while pending:
        raw = pending.pop().strip()
        candidate = project_dir / (raw if raw.endswith(".tex") else f"{raw}.tex")
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen or not candidate.is_file():
            continue
        seen.add(resolved)
        included = candidate.read_text(encoding="utf-8", errors="replace")
        parts.append(included)
        pending.extend(_INPUT_RE.findall(included))

    return "\n".join(parts)


def strip_comments(tex: str) -> str:
    """Remove LaTeX line comments, preserving escaped percent signs."""
    out = []
    for line in tex.splitlines():
        result = []
        index = 0
        while index < len(line):
            char = line[index]
            if char == "\\" and index + 1 < len(line):
                result.append(line[index : index + 2])
                index += 2
                continue
            if char == "%":
                break
            result.append(char)
            index += 1
        out.append("".join(result))
    return "\n".join(out)


def check_page_limit(project_dir: Path, config: dict, label: str) -> Check:
    """Compare main-text page count against the venue limit."""
    limit = config["page_limit_main"]
    log_path = project_dir / "main.log"
    aux_path = project_dir / "main.aux"

    total_pages = parse_total_pages(log_path)
    if total_pages is None:
        return Check(
            f"Page limit ({limit} pages)",
            SKIP,
            f"no page count in {log_path.name}; compile the paper first "
            "(python scripts/compile_paper.py --project-dir <paper_dir>)",
        )

    bib_start = parse_label_page(aux_path, label)
    if bib_start is None:
        if total_pages <= limit:
            return Check(
                f"Page limit ({limit} pages)",
                PASS,
                f"{total_pages} total pages, within the limit even counting references. "
                f"Add \\label{{{label}}} at the bibliography start for a main-text-only count.",
            )
        return Check(
            f"Page limit ({limit} pages)",
            WARN,
            f"{total_pages} total pages including references, and label '{label}' is not in "
            f"{aux_path.name}, so main-text pages cannot be separated. Add "
            f"\\label{{{label}}} immediately before the bibliography and recompile.",
        )

    main_text_pages = max(bib_start - 1, 0)
    if main_text_pages <= limit:
        return Check(
            f"Page limit ({limit} pages)",
            PASS,
            f"{main_text_pages} main-text pages, {total_pages} total.",
        )
    return Check(
        f"Page limit ({limit} pages)",
        FAIL,
        f"{main_text_pages} main-text pages, {main_text_pages - limit} over the limit "
        f"({total_pages} total). Cut content -- do not shrink margins, font size, or line "
        "spacing; venues check for that and reject it.",
    )


def check_required_sections(tex: str, config: dict) -> list[Check]:
    """Check that every section the venue requires appears in the sources."""
    required = config.get("required_sections") or []
    if not required:
        return [Check("Required sections", PASS, "this venue mandates no extra sections")]

    present = [title.strip() for title in _SECTION_RE.findall(tex)]
    normalized = [re.sub(r"[^a-z]", "", title.lower()) for title in present]

    checks = []
    for requirement in required:
        needle = re.sub(r"[^a-z]", "", requirement.lower())
        # Substring both ways so "Limitations" matches a "Limitations and Future
        # Work" heading, and "Ethics Statement" matches a heading titled "Ethics".
        # The length floor stops a one-word heading from matching everything.
        found = any(
            needle in title or (len(title) >= 5 and title in needle)
            for title in normalized
            if title
        )
        checks.append(
            Check(
                f"Required section: {requirement}",
                PASS if found else FAIL,
                "found in the LaTeX sources"
                if found
                else f"no \\section matching '{requirement}'. This venue requires it; "
                "a missing mandatory section is a desk-reject risk.",
            )
        )
    return checks


def check_style_file(project_dir: Path, tex: str, config: dict) -> Check:
    """Check that the venue style file is present in the project and loaded."""
    style_file = config["style_file"]
    stem = Path(style_file).stem
    # Match the family, not the year: neurips_2025 vs neurips_2026.
    family = re.sub(r"[_\-]?(19|20)\d{2}.*$", "", stem) or stem

    candidates = sorted(project_dir.glob("*.sty")) + sorted(project_dir.glob("*.cls"))
    matching = [p.name for p in candidates if family.lower() in p.stem.lower()]

    loaded = re.search(
        _STYLE_LOAD_RE_TEMPLATE.format(stem=re.escape(family)), tex, re.IGNORECASE
    )

    if matching and loaded:
        return Check("Venue style file", PASS, f"{', '.join(matching)} present and loaded")
    if matching and not loaded:
        return Check(
            "Venue style file",
            FAIL,
            f"{', '.join(matching)} is in the project but main.tex does not load it. "
            f"The paper is being typeset with the wrong layout.",
        )
    if loaded and not matching:
        return Check(
            "Venue style file",
            FAIL,
            f"main.tex loads a '{family}' style but no matching .sty/.cls is in "
            f"{project_dir.name}. Compilation will fail on a clean checkout. "
            f"Run: python scripts/venue_setup.py --venue {config['_slug']} "
            f"--project-dir {project_dir}",
        )
    return Check(
        "Venue style file",
        FAIL,
        f"expected {style_file} (or the current year's edition) in the project. "
        f"Run: python scripts/venue_setup.py --venue {config['_slug']} "
        f"--project-dir {project_dir}",
    )


def check_anonymity(config: dict) -> Check:
    """Report whether an anonymity check is required for this venue."""
    if not config.get("anonymous"):
        return Check("Anonymity", SKIP, "this venue does not review anonymously")
    return Check(
        "Anonymity",
        WARN,
        "double-blind venue -- this gate does not check identity. Run: "
        "python scripts/anonymity_check.py --project-dir <paper_dir>",
    )


def render(checks: list[Check], config: dict, project_dir: Path) -> str:
    """Render the PASS/FAIL table."""
    width = max(len(check.name) for check in checks)
    lines = [
        f"Format gate: {config['display_name']} "
        f"({config['page_limit_main']}-page limit, {config['columns']}-column, {config['font_size']})",
        f"Project: {project_dir}",
        f"Config:  assets/venues/{config['_slug']}.yaml (written against the {config['reference_year']} edition)",
        "",
    ]
    for check in checks:
        lines.append(f"  [{check.status}] {check.name.ljust(width)}  {check.detail}")

    failures = sum(1 for check in checks if check.status == FAIL)
    warnings = sum(1 for check in checks if check.status == WARN)
    lines.append("")
    if failures:
        lines.append(f"FAILED: {failures} blocking problem(s), {warnings} warning(s).")
    else:
        lines.append(f"PASSED: no blocking problems, {warnings} warning(s).")
    lines.append(
        "This gate checks what a script can check. Read the author guide: "
        f"{config['author_guide_url']}"
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a paper project against its target venue's formatting requirements."
    )
    parser.add_argument("--project-dir", help="Paper project directory containing main.tex.")
    parser.add_argument("--venue", help="Venue slug, e.g. neurips, icml, iclr, acl, aaai, cvpr.")
    parser.add_argument(
        "--bib-label",
        default="sec:bib",
        help="Label placed at the bibliography start, used to separate main text from references "
        "(default: sec:bib).",
    )
    parser.add_argument(
        "--list-venues", action="store_true", help="Print the available venue slugs, then exit."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat WARN as failure. Use this at the final QA gate.",
    )
    args = parser.parse_args()

    if args.list_venues:
        print("\n".join(list_venues()))
        return 0

    if not args.project_dir or not args.venue:
        print("error: --project-dir and --venue are required (or use --list-venues)", file=sys.stderr)
        return 1

    try:
        config = load_venue(args.venue)
    except VenueConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"error: project dir not found: {project_dir}", file=sys.stderr)
        return 1
    if not (project_dir / "main.tex").exists():
        print(f"error: no main.tex in {project_dir}", file=sys.stderr)
        return 1

    tex = strip_comments(read_tex_sources(project_dir))

    checks = [check_page_limit(project_dir, config, args.bib_label)]
    checks.extend(check_required_sections(tex, config))
    checks.append(check_style_file(project_dir, tex, config))
    checks.append(check_anonymity(config))

    print(render(checks, config, project_dir))

    blocking = {FAIL, WARN} if args.strict else {FAIL}
    return 1 if any(check.status in blocking for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
