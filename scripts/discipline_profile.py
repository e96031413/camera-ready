#!/usr/bin/env python3
"""Load discipline profiles from assets/disciplines/*.yaml.

Version: 2026-09-05-v1

A discipline profile answers the questions that differ between fields before
any writing starts: which citation style is expected, whether the output is
LaTeX or Word, which reporting guideline governs the study design, which
sections and statements are mandatory, and what gets papers rejected there.

Adding a discipline means adding one YAML file. Nothing in this script knows
the name of any particular field.

Commands:
  list                   # every installed discipline
  show <discipline>      # the full profile
  requirements <d>       # the actionable checklist a paper in this field must meet

Examples:
  python scripts/discipline_profile.py list
  python scripts/discipline_profile.py requirements medicine
  python scripts/discipline_profile.py show humanities --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from citation_style import StyleError, list_styles, load_style
from paper_utils import enable_utf8_stdout, get_assets_dir
from venue_config import VenueConfigError, parse_simple_yaml

BANNER = "discipline_profile 2026-09-05-v1"

REQUIRED_FIELDS: dict[str, type] = {
    "discipline": str,
    "display_name": str,
    "default_style": str,
    "allowed_styles": list,
    "default_format": str,
    "evidence_model": str,
    "reporting_guidelines": list,
    "required_sections": list,
    "ethics_approval_required": bool,
    "preregistration_expected": bool,
    "data_availability_required": bool,
    "common_rejections": list,
    "reference_url": str,
}

VALID_FORMATS = {"latex", "docx", "markdown", "typst"}

# Boolean fields that become a required statement in the manuscript.
STATEMENT_FIELDS = {
    "ethics_approval_required": "Ethics approval / IRB statement",
    "preregistration_expected": "Preregistration or protocol reference",
    "data_availability_required": "Data availability statement",
    "code_availability_required": "Code availability statement",
    "conflict_of_interest_required": "Conflict of interest statement",
    "funding_statement_required": "Funding statement",
}


class DisciplineError(ValueError):
    """Raised when a discipline is unknown or its profile is off-schema."""


def disciplines_dir() -> Path:
    return get_assets_dir() / "disciplines"


def list_disciplines() -> list[str]:
    directory = disciplines_dir()
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.yaml"))


def guidelines_dir() -> Path:
    return get_assets_dir() / "checklists"


def validate_discipline(config: dict, *, path_label: str) -> list[str]:
    """Return schema problems for one profile; empty means valid."""
    problems: list[str] = []

    for field, expected in REQUIRED_FIELDS.items():
        if field not in config:
            problems.append(f"{path_label}: missing required field '{field}'")
            continue
        value = config[field]
        if value is None:
            problems.append(f"{path_label}: field '{field}' must not be null")
        elif not isinstance(value, expected):
            problems.append(
                f"{path_label}: field '{field}' must be {expected.__name__}, "
                f"got {type(value).__name__}"
            )

    output_format = config.get("default_format")
    if isinstance(output_format, str) and output_format not in VALID_FORMATS:
        problems.append(f"{path_label}: 'default_format' must be one of {sorted(VALID_FORMATS)}")

    installed = set(list_styles())
    default_style = config.get("default_style")
    allowed = config.get("allowed_styles")
    if isinstance(default_style, str) and installed and default_style not in installed:
        problems.append(f"{path_label}: default_style {default_style!r} has no profile in assets/styles")
    if isinstance(allowed, list) and installed:
        for style in allowed:
            if style not in installed:
                problems.append(f"{path_label}: allowed_styles entry {style!r} has no profile in assets/styles")
    if isinstance(default_style, str) and isinstance(allowed, list) and default_style not in allowed:
        problems.append(f"{path_label}: default_style {default_style!r} is not listed in allowed_styles")

    guidelines = config.get("reporting_guidelines")
    if isinstance(guidelines, list):
        for slug in guidelines:
            if not (guidelines_dir() / f"{slug}.md").is_file():
                problems.append(
                    f"{path_label}: reporting guideline {slug!r} has no question set "
                    f"at assets/checklists/{slug}.md"
                )

    url = config.get("reference_url")
    if isinstance(url, str) and not url.startswith(("http://", "https://")):
        problems.append(f"{path_label}: 'reference_url' must be an http(s) URL")

    return problems


def load_discipline(discipline: str, *, validate: bool = True) -> dict:
    """Load assets/disciplines/<discipline>.yaml. Raises DisciplineError."""
    slug = discipline.strip().lower()
    path = disciplines_dir() / f"{slug}.yaml"
    if not path.is_file():
        available = ", ".join(list_disciplines()) or "none installed"
        raise DisciplineError(f"unknown discipline {discipline!r}. Available: {available}")

    try:
        config = parse_simple_yaml(path.read_text(encoding="utf-8"), path_label=path.name)
    except VenueConfigError as exc:
        raise DisciplineError(str(exc)) from exc

    if validate:
        problems = validate_discipline(config, path_label=path.name)
        if problems:
            raise DisciplineError("\n".join(problems))
    return config


def required_statements(config: dict) -> list[str]:
    """Return the statements this discipline expects in the manuscript."""
    return [label for field, label in STATEMENT_FIELDS.items() if config.get(field) is True]


def requirements_report(config: dict) -> str:
    """Render the actionable checklist for one discipline."""
    lines: list[str] = []
    lines.append(f"# {config['display_name']} — what this field requires")
    lines.append("")
    lines.append(f"Evidence model: {config['evidence_model']}")
    lines.append(f"Default output format: {config['default_format']}")
    lines.append(f"Default citation style: {config['default_style']}")
    accepted = config.get("allowed_styles") or []
    others = [style for style in accepted if style != config["default_style"]]
    lines.append(f"Also accepted: {', '.join(others) if others else 'nothing else; this field expects one style'}")

    try:
        style = load_style(config["default_style"])
        lines.append(f"  -> {style['display_name']}, {style['family']}, processed by {style['bib_processor']}")
        lines.append(f"  -> pandoc CSL id for the Word path: {style['csl_id']}")
    except StyleError:
        lines.append("  -> style profile could not be loaded")

    lines.append("")
    lines.append("## Required sections")
    for section in config.get("required_sections") or []:
        lines.append(f"  - {section}")

    statements = required_statements(config)
    lines.append("")
    lines.append("## Required statements")
    if statements:
        for statement in statements:
            lines.append(f"  - {statement}")
    else:
        lines.append("  (none)")

    guidelines = config.get("reporting_guidelines") or []
    lines.append("")
    lines.append("## Reporting guidelines")
    if guidelines:
        lines.append("  Choose the one that matches the study design, then run:")
        for slug in guidelines:
            lines.append(f"    python scripts/reporting_guideline.py --guideline {slug} --project-dir <dir>")
    else:
        lines.append("  (none; this field has no reporting-guideline tradition)")

    lines.append("")
    lines.append("## What gets rejected here")
    for reason in config.get("common_rejections") or []:
        lines.append(f"  - {reason}")

    notes = config.get("notes")
    if notes:
        lines.append("")
        lines.append("## Notes")
        lines.append(f"  {notes}")

    lines.append("")
    lines.append(f"Reference: {config['reference_url']}")
    return "\n".join(lines) + "\n"


def cmd_list(args) -> int:
    slugs = list_disciplines()
    if args.json:
        print(json.dumps(slugs, indent=2))
        return 0
    if not slugs:
        print("No disciplines installed under assets/disciplines/.")
        return 1
    print(f"{len(slugs)} discipline(s):\n")
    for slug in slugs:
        try:
            config = load_discipline(slug)
        except DisciplineError as exc:
            print(f"  {slug:<18} INVALID: {exc}")
            continue
        print(
            f"  {slug:<18} {config['display_name']:<38} "
            f"style={config['default_style']:<20} format={config['default_format']}"
        )
    return 0


def cmd_show(args) -> int:
    config = load_discipline(args.discipline)
    if args.json:
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return 0
    for key, value in config.items():
        if isinstance(value, list):
            print(f"{key}:")
            for item in value:
                print(f"  - {item}")
        else:
            print(f"{key}: {value}")
    return 0


def cmd_requirements(args) -> int:
    config = load_discipline(args.discipline)
    report = requirements_report(config)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"Wrote {out_path}")
    else:
        print(report, end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load discipline profiles and print what a field requires.")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="list installed disciplines")

    show = sub.add_parser("show", help="print one discipline profile")
    show.add_argument("discipline")

    requirements = sub.add_parser("requirements", help="print the actionable checklist for a discipline")
    requirements.add_argument("discipline")
    requirements.add_argument("--out", help="write to this file instead of stdout")

    return parser


def main() -> int:
    enable_utf8_stdout()
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    handlers = {"list": cmd_list, "show": cmd_show, "requirements": cmd_requirements}
    try:
        return handlers[args.command](args)
    except DisciplineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
