#!/usr/bin/env python3
"""Scaffold common notes artifacts for a paper project.

Artifacts (under <project-dir>/notes/):
- claim-registry.md
- literature-matrix.md
- response-to-reviewers.md

This is framework-agnostic and helps keep artifacts consistent.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paper_utils import get_assets_dir, now_iso


ARTIFACTS = {
    "claim-registry": {
        "template": "claim-registry-template.md",
        "output": "claim-registry.md",
    },
    "literature-matrix": {
        "template": "literature-matrix-template.md",
        "output": "literature-matrix.md",
    },
    "response-to-reviewers": {
        "template": "response-to-reviewers-template.md",
        "output": "response-to-reviewers.md",
    },
}


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def read_template(name: str) -> str:
    path = get_assets_dir() / name
    if not path.exists():
        raise FileNotFoundError(f"template not found: {name}")
    return path.read_text(encoding="utf-8")


def replace_if_present(text: str, placeholder: str, value: str | None) -> str:
    if value is None:
        return text
    v = value.strip()
    if not v:
        return text
    return text.replace(placeholder, v)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold notes artifacts for a paper project.")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Paper project directory (default: .).",
    )
    parser.add_argument(
        "--artifact",
        required=True,
        choices=sorted(ARTIFACTS.keys()),
        help="Which artifact to scaffold.",
    )
    parser.add_argument("--topic", help="Optional topic string for templates.")
    parser.add_argument("--mode", help="Optional mode string for templates.")
    parser.add_argument("--paper-title", help="Optional paper title for templates.")
    parser.add_argument("--round", dest="review_round", help="Optional review round (e.g., R1, R2).")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite target file if it exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        return fail("project dir not found")
    if not project_dir.is_dir():
        return fail("project dir is not a directory")

    spec = ARTIFACTS[args.artifact]
    template_text = read_template(spec["template"])

    text = template_text.replace("<ISO8601 timestamp>", now_iso())
    text = replace_if_present(text, "<topic>", args.topic)
    text = replace_if_present(text, "<mode>", args.mode)
    text = replace_if_present(text, "<paper title>", args.paper_title)
    text = replace_if_present(text, "<round>", args.review_round)

    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    out_path = notes_dir / spec["output"]
    if out_path.exists() and not args.overwrite:
        return fail(f"notes/{spec['output']} already exists (use --overwrite to replace)")

    out_path.write_text(text.rstrip() + "\n", encoding="utf-8")
    print(f"Created: notes/{spec['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

