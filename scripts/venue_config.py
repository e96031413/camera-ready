#!/usr/bin/env python3
"""Load venue configurations from assets/venues/*.yaml.

The core workflow must run with no third-party packages, so this module ships
a deliberately small YAML *subset* parser instead of depending on PyYAML. It
supports exactly what the venue files need:

  key: scalar          # str, int, bool, or null
  key: []              # explicit empty list
  key:                 # list of scalars
    - item
  key: >               # folded block scalar, joined into one line
    first line
    second line
  key: |               # literal block scalar, line breaks kept
    first line
    second line
  # comment lines and blank lines

Anything else -- nested mappings, flow mappings, anchors, quoted keys --
raises VenueConfigError. That is intentional: the venue files
are configuration, not a place for YAML cleverness, and a strict parser keeps
contributors inside the schema.
"""

from __future__ import annotations

import argparse
import json
import sys

from paper_utils import get_assets_dir

# Fields every venue file must define, with the type each must have.
REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "venue": str,
    "display_name": str,
    "full_name": str,
    "reference_year": int,
    "page_limit_main": int,
    "columns": str,
    "font_size": str,
    "anonymous": bool,
    "required_sections": list,
    "style_file": str,
    "style_file_url": str,
    "author_guide_url": str,
    "checklist_required": bool,
    "checklist_asset": str,
}

VALID_COLUMNS = {"single", "two"}


class VenueConfigError(ValueError):
    """Raised when a venue YAML file is missing, malformed, or off-schema."""


def _parse_scalar(raw: str, *, path_label: str, line_no: int):
    """Parse a YAML scalar from the supported subset."""
    text = raw.strip()
    if text.startswith("#"):
        text = ""
    # Strip a trailing inline comment, but only when it is clearly separated.
    # URLs contain '#' with no preceding space, so this leaves them intact.
    hash_at = text.find(" #")
    if hash_at != -1:
        text = text[:hash_at].strip()

    if text in ("", "null", "~"):
        return None
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if text == "[]":
        return []
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text.startswith("[") or text.startswith("{"):
        raise VenueConfigError(
            f"{path_label}:{line_no}: flow collections are not supported; "
            "use a block list ('- item' on its own line) or []"
        )
    try:
        return int(text)
    except ValueError:
        return text


def parse_simple_yaml(content: str, *, path_label: str = "<string>") -> dict:
    """Parse the supported YAML subset into a dict. Raises VenueConfigError."""
    result: dict = {}
    current_key: str | None = None
    block_key: str | None = None
    block_fold: bool = True
    block_lines: list[str] = []

    def close_block() -> None:
        """Store the accumulated block scalar under its key."""
        nonlocal block_key, block_lines
        if block_key is None:
            return
        if block_fold:
            text = " ".join(part.strip() for part in block_lines if part.strip())
        else:
            text = "\n".join(part.strip() for part in block_lines).strip("\n")
        result[block_key] = text
        block_key, block_lines = None, []

    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.rstrip()

        # A block scalar continues while lines are blank or indented.
        if block_key is not None:
            if not line.strip() or line.startswith((" ", "\t")):
                block_lines.append(line)
                continue
            close_block()

        if not line.strip() or line.lstrip().startswith("#"):
            continue

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("- "):
            if current_key is None:
                raise VenueConfigError(f"{path_label}:{line_no}: list item before any key")
            if indent == 0:
                raise VenueConfigError(f"{path_label}:{line_no}: list items must be indented")
            value = result[current_key]
            if not isinstance(value, list):
                raise VenueConfigError(
                    f"{path_label}:{line_no}: key '{current_key}' already has a scalar value; "
                    "it cannot also take list items"
                )
            value.append(_parse_scalar(stripped[2:], path_label=path_label, line_no=line_no))
            continue

        if indent != 0:
            raise VenueConfigError(
                f"{path_label}:{line_no}: nested mappings are not supported "
                f"(indented key: {stripped.split(':', 1)[0]!r}); use a flat key instead"
            )
        if ":" not in stripped:
            raise VenueConfigError(f"{path_label}:{line_no}: expected 'key: value', got {stripped!r}")

        key, _, rest = stripped.partition(":")
        key = key.strip()
        if not key:
            raise VenueConfigError(f"{path_label}:{line_no}: empty key")
        if key in result:
            raise VenueConfigError(f"{path_label}:{line_no}: duplicate key {key!r}")

        # A block scalar indicator opens a multi-line value: '>' folds the lines
        # into one paragraph, '|' keeps the line breaks.
        if rest.strip() in (">", ">-", "|", "|-"):
            block_key = key
            block_fold = rest.strip().startswith(">")
            block_lines = []
            current_key = key
            continue

        parsed = _parse_scalar(rest, path_label=path_label, line_no=line_no)
        # A bare 'key:' opens a block list; it stays an empty list if no items follow.
        result[key] = [] if parsed is None and not rest.strip() else parsed
        current_key = key

    close_block()
    return result


def validate_venue(config: dict, *, path_label: str) -> list[str]:
    """Return a list of schema problems (empty means the config is valid)."""
    problems: list[str] = []

    for field, expected in REQUIRED_FIELDS.items():
        if field not in config:
            problems.append(f"{path_label}: missing required field '{field}'")
            continue
        value = config[field]
        if value is None:
            problems.append(f"{path_label}: field '{field}' must not be null")
            continue
        # bool is a subclass of int; check it before the int case.
        if expected is int and isinstance(value, bool):
            problems.append(f"{path_label}: field '{field}' must be an integer, got a boolean")
            continue
        if not isinstance(value, expected):
            problems.append(
                f"{path_label}: field '{field}' must be {expected.__name__}, "
                f"got {type(value).__name__}"
            )

    if isinstance(config.get("columns"), str) and config["columns"] not in VALID_COLUMNS:
        problems.append(
            f"{path_label}: 'columns' must be one of {sorted(VALID_COLUMNS)}, "
            f"got {config['columns']!r}"
        )

    page_limit = config.get("page_limit_main")
    if isinstance(page_limit, int) and not isinstance(page_limit, bool) and page_limit <= 0:
        problems.append(f"{path_label}: 'page_limit_main' must be positive, got {page_limit}")

    for url_field in ("style_file_url", "author_guide_url"):
        url = config.get(url_field)
        if isinstance(url, str) and not url.startswith(("http://", "https://")):
            problems.append(f"{path_label}: '{url_field}' must be an http(s) URL, got {url!r}")

    sections = config.get("required_sections")
    if isinstance(sections, list):
        for item in sections:
            if not isinstance(item, str) or not item.strip():
                problems.append(f"{path_label}: 'required_sections' entries must be non-empty strings")
                break

    if config.get("checklist_required") is True:
        asset = get_assets_dir() / "checklists" / f"{config.get('checklist_asset')}.md"
        if not asset.exists():
            problems.append(
                f"{path_label}: checklist_required is true but the question set is missing: {asset}"
            )

    return problems


def venues_dir():
    """Return the assets/venues directory."""
    return get_assets_dir() / "venues"


def list_venues() -> list[str]:
    """Return the sorted slugs of every available venue."""
    directory = venues_dir()
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.yaml"))


def load_venue(venue: str, *, validate: bool = True) -> dict:
    """Load and validate assets/venues/<venue>.yaml. Raises VenueConfigError."""
    slug = venue.strip().lower()
    path = venues_dir() / f"{slug}.yaml"
    if not path.exists():
        available = ", ".join(list_venues()) or "(none)"
        raise VenueConfigError(f"unknown venue {venue!r}: no {path.name} in {venues_dir()}. Available: {available}")

    config = parse_simple_yaml(path.read_text(encoding="utf-8"), path_label=path.name)

    if validate:
        problems = validate_venue(config, path_label=path.name)
        if problems:
            raise VenueConfigError("\n".join(problems))

    config["_slug"] = slug
    config["_path"] = str(path)
    return config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect venue configurations from assets/venues/."
    )
    parser.add_argument("--venue", help="Print one venue's configuration.")
    parser.add_argument("--list", action="store_true", help="List available venue slugs.")
    parser.add_argument("--validate-all", action="store_true", help="Validate every venue file.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table.")
    args = parser.parse_args()

    if not any((args.venue, args.list, args.validate_all)):
        parser.print_help()
        return 0

    if args.list:
        slugs = list_venues()
        print(json.dumps(slugs) if args.json else "\n".join(slugs))
        return 0

    if args.validate_all:
        all_problems: list[str] = []
        for slug in list_venues():
            try:
                load_venue(slug)
            except VenueConfigError as exc:
                all_problems.extend(str(exc).splitlines())
        if all_problems:
            print(f"Venue validation FAILED ({len(all_problems)} problem(s)):")
            for problem in all_problems:
                print(f"  - {problem}")
            return 1
        print(f"Venue validation passed: {len(list_venues())} venue(s).")
        return 0

    try:
        config = load_venue(args.venue)
    except VenueConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(config, indent=2, ensure_ascii=False))
    else:
        for key, value in config.items():
            if key.startswith("_"):
                continue
            rendered = ", ".join(str(v) for v in value) if isinstance(value, list) else value
            print(f"{key:22} {rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
