#!/usr/bin/env python3
"""Load, emit and enforce citation styles from assets/styles/*.yaml.

Version: 2026-09-05-v1

A citation style is a drop-in profile, not code. Adding APA, MLA, Chicago,
Vancouver or a house style means adding one YAML file; nothing in this script
knows the name of any particular style.

Each profile carries three things the workflow needs:

  1. The LaTeX preamble that makes the style compile (package line, language
     mapping, bibliography command, backend).
  2. The pandoc CSL identifier, for the Word and Markdown output path.
  3. The BibTeX fields the style needs per entry type, so an entry that will
     render as an incomplete reference fails a gate instead of a review.

Commands:
  list                          # every installed style
  show <style>                  # the full profile, optionally as JSON
  preamble <style>              # the LaTeX block to paste into a preamble
  validate <style> --bib FILE   # required fields present in every entry?

Examples:
  python scripts/citation_style.py list
  python scripts/citation_style.py preamble apa7
  python scripts/citation_style.py validate vancouver --bib ref.bib
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from paper_utils import enable_utf8_stdout, get_assets_dir
from venue_config import VenueConfigError, parse_simple_yaml

BANNER = "citation_style 2026-09-05-v1"

REQUIRED_FIELDS: dict[str, type] = {
    "style": str,
    "display_name": str,
    "family": str,
    "disciplines": list,
    "latex_backend": str,
    "latex_package_line": str,
    "latex_bibliography_line": str,
    "latex_cite_parenthetical": str,
    "latex_cite_narrative": str,
    "bib_processor": str,
    "csl_id": str,
    "reference_url": str,
}

VALID_BACKENDS = {"biblatex", "natbib", "bst"}
VALID_PROCESSORS = {"biber", "bibtex", "none"}
VALID_FAMILIES = {"author-date", "author-page", "numeric", "note"}

# Entry types the profiles declare required fields for.
ENTRY_TYPES = ("article", "book", "inproceedings", "thesis", "misc")


class StyleError(ValueError):
    """Raised when a style is unknown or its profile is off-schema."""


def styles_dir() -> Path:
    return get_assets_dir() / "styles"


def list_styles() -> list[str]:
    directory = styles_dir()
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.yaml"))


def validate_style(config: dict, *, path_label: str) -> list[str]:
    """Return schema problems for one profile; empty means valid."""
    problems: list[str] = []

    for field, expected in REQUIRED_FIELDS.items():
        if field not in config:
            problems.append(f"{path_label}: missing required field '{field}'")
            continue
        if config[field] is None:
            problems.append(f"{path_label}: field '{field}' must not be null")
        elif not isinstance(config[field], expected):
            problems.append(
                f"{path_label}: field '{field}' must be {expected.__name__}, "
                f"got {type(config[field]).__name__}"
            )

    backend = config.get("latex_backend")
    if isinstance(backend, str) and backend not in VALID_BACKENDS:
        problems.append(f"{path_label}: 'latex_backend' must be one of {sorted(VALID_BACKENDS)}")

    processor = config.get("bib_processor")
    if isinstance(processor, str) and processor not in VALID_PROCESSORS:
        problems.append(f"{path_label}: 'bib_processor' must be one of {sorted(VALID_PROCESSORS)}")

    family = config.get("family")
    if isinstance(family, str) and family not in VALID_FAMILIES:
        problems.append(f"{path_label}: 'family' must be one of {sorted(VALID_FAMILIES)}")

    url = config.get("reference_url")
    if isinstance(url, str) and not url.startswith(("http://", "https://")):
        problems.append(f"{path_label}: 'reference_url' must be an http(s) URL")

    for entry_type in ENTRY_TYPES:
        key = f"required_fields_{entry_type}"
        if key in config and not isinstance(config[key], list):
            problems.append(f"{path_label}: '{key}' must be a list")

    return problems


def load_style(style: str, *, validate: bool = True) -> dict:
    """Load assets/styles/<style>.yaml. Raises StyleError."""
    slug = style.strip().lower()
    path = styles_dir() / f"{slug}.yaml"
    if not path.is_file():
        available = ", ".join(list_styles()) or "none installed"
        raise StyleError(f"unknown citation style {style!r}. Available: {available}")

    try:
        config = parse_simple_yaml(path.read_text(encoding="utf-8"), path_label=path.name)
    except VenueConfigError as exc:
        raise StyleError(str(exc)) from exc

    if validate:
        problems = validate_style(config, path_label=path.name)
        if problems:
            raise StyleError("\n".join(problems))
    return config


def render_preamble(config: dict) -> str:
    """Return the LaTeX preamble block for a style, ready to paste."""
    lines = [
        f"% Citation style: {config['display_name']} ({config['style']})",
        f"% Reference: {config['reference_url']}",
        f"% Bibliography processor: {config['bib_processor']}",
    ]
    packages = config.get("latex_required_packages") or []
    if packages:
        lines.append(f"% Requires TeX packages: {', '.join(packages)}")

    language = (config.get("latex_language_setup") or "").strip()
    if language:
        lines.append(language)

    lines.append(config["latex_package_line"])

    extra = (config.get("latex_extra_preamble") or "").strip()
    if extra:
        lines.append(extra)

    if config["latex_backend"] == "biblatex":
        lines.append("\\addbibresource{ref.bib}")
    else:
        lines.append(config["latex_bibliography_line"])

    lines.append("")
    lines.append("% In the body, cite with:")
    lines.append(f"%   parenthetical: {config['latex_cite_parenthetical']}{{key}}")
    lines.append(f"%   narrative:     {config['latex_cite_narrative']}{{key}}")
    lines.append("% At the end of the document:")
    if config["latex_backend"] == "biblatex":
        lines.append(f"%   {config['latex_bibliography_line']}")
    else:
        lines.append("%   \\bibliography{ref}")
    return "\n".join(lines) + "\n"


ENTRY_PATTERN = re.compile(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", re.DOTALL)
FIELD_PATTERN = re.compile(r"^\s*([A-Za-z_-]+)\s*=", re.MULTILINE)

# Entry types that map onto one set of required fields.
ENTRY_ALIASES = {
    "article": "article",
    "book": "book",
    "inbook": "book",
    "incollection": "book",
    "inproceedings": "inproceedings",
    "conference": "inproceedings",
    "proceedings": "inproceedings",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "thesis": "thesis",
    "misc": "misc",
    "online": "misc",
    "unpublished": "misc",
    "techreport": "misc",
}


def parse_bib_entries(text: str) -> list[tuple[str, str, set[str]]]:
    """Return (entry_type, key, field names) for every entry in a .bib file."""
    entries = []
    for match in ENTRY_PATTERN.finditer(text):
        entry_type = match.group(1).lower()
        key = match.group(2).strip()
        fields = {name.lower() for name in FIELD_PATTERN.findall(match.group(3))}
        entries.append((entry_type, key, fields))
    return entries


def validate_bib(config: dict, bib_text: str) -> list[str]:
    """Return one message per entry that lacks a field the style needs."""
    problems: list[str] = []
    for entry_type, key, fields in parse_bib_entries(bib_text):
        bucket = ENTRY_ALIASES.get(entry_type)
        if bucket is None:
            continue
        required = config.get(f"required_fields_{bucket}") or []
        # A requirement written as 'doi|url' is satisfied by any one alternative.
        missing = [
            name
            for name in required
            if not any(alt.strip().lower() in fields for alt in str(name).split("|"))
        ]
        if missing:
            problems.append(
                f"{key} (@{entry_type}): {config['display_name']} needs "
                f"{', '.join(missing)}"
            )
    return problems


def cmd_list(args) -> int:
    styles = list_styles()
    if args.json:
        print(json.dumps(styles, indent=2))
        return 0
    if not styles:
        print("No styles installed under assets/styles/.")
        return 1
    print(f"{len(styles)} citation style(s):\n")
    for slug in styles:
        try:
            config = load_style(slug)
        except StyleError as exc:
            print(f"  {slug:<22} INVALID: {exc}")
            continue
        disciplines = ", ".join(config.get("disciplines") or [])
        print(f"  {slug:<22} {config['display_name']} [{config['family']}] -> {disciplines}")
    return 0


def cmd_show(args) -> int:
    config = load_style(args.style)
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


def cmd_preamble(args) -> int:
    config = load_style(args.style)
    text = render_preamble(config)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"Wrote {out_path}")
    else:
        print(text, end="")
    return 0


def cmd_validate(args) -> int:
    config = load_style(args.style)
    bib_path = Path(args.bib)
    if not bib_path.is_file():
        print(f"error: no such file: {bib_path}", file=sys.stderr)
        return 2

    problems = validate_bib(config, bib_path.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps({"style": config["style"], "problems": problems}, indent=2))
        return 1 if problems else 0

    if problems:
        print(f"{len(problems)} entr(ies) missing fields required by {config['display_name']}:\n")
        for problem in problems:
            print(f"  {problem}")
        print(f"\n{BANNER}: FAIL")
        return 1
    print(f"{BANNER}: every entry in {bib_path.name} has the fields {config['display_name']} needs")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load, emit and enforce citation styles.")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="list installed styles")

    show = sub.add_parser("show", help="print one style profile")
    show.add_argument("style")

    preamble = sub.add_parser("preamble", help="emit the LaTeX preamble for a style")
    preamble.add_argument("style")
    preamble.add_argument("--out", help="write to this file instead of stdout")

    validate = sub.add_parser("validate", help="check a .bib against a style's field requirements")
    validate.add_argument("style")
    validate.add_argument("--bib", required=True, help="path to the .bib file")

    return parser


def main() -> int:
    enable_utf8_stdout()
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        "list": cmd_list,
        "show": cmd_show,
        "preamble": cmd_preamble,
        "validate": cmd_validate,
    }
    try:
        return handlers[args.command](args)
    except StyleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
