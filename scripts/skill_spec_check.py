#!/usr/bin/env python3
"""Validate SKILL.md against the Agent Skills specification.

Version: 2026-09-05-v1

The Agent Skills spec (agentskills.io) defines exactly six frontmatter fields:
`name`, `description`, `license`, `compatibility`, `metadata` and
`allowed-tools`. Claude Code accepts additional fields of its own, but
claude.ai skill uploads, the Skills API and `package_skill.py` reject an
unexpected key outright. A skill meant to be distributed must therefore stay
inside the six.

Rules (each reported with a rule id):

  SPEC001  an unexpected frontmatter key
  SPEC002  a missing required key (`name`)
  SPEC003  `name` is not lowercase-hyphenated, or is longer than 64 characters
  SPEC004  `description` is missing, or longer than 1024 characters
  SPEC005  `compatibility` is longer than 500 characters
  SPEC006  `metadata` is not a mapping
  SPEC007  the frontmatter does not start on line 1
  STRUCT01 the SKILL.md body is longer than the recommended 500 lines
  STRUCT02 a file linked from SKILL.md does not exist
  STRUCT03 `allowed-tools` is neither a string nor a list of strings

Usage:
  python scripts/skill_spec_check.py
  python scripts/skill_spec_check.py --skill path/to/SKILL.md
  python scripts/skill_spec_check.py --strict     # warnings become failures
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

BANNER = "skill_spec_check 2026-09-05-v1"

SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
REQUIRED_FIELDS = {"name"}

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500
MAX_BODY_LINES = 500

# Markdown links to a local file, ignoring URLs and pure anchors.
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)#][^)]*)\)")


@dataclass
class Issue:
    """One specification violation, or one recommendation."""

    rule: str
    message: str
    severity: str = "error"

    def render(self) -> str:
        return f"[{self.severity}] {self.rule} {self.message}"


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter, body). Frontmatter is None when it is absent or misplaced."""
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines(keepends=True)
    for index in range(1, len(lines)):
        if lines[index].rstrip() == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1 :])
    return None, text


def parse_frontmatter(raw: str) -> dict[str, object]:
    """Parse the small YAML subset the spec needs: scalars, folded blocks, lists, one nested map.

    This deliberately avoids a PyYAML dependency; the core workflow ships with
    no third-party requirements and this gate must run in the same environment.
    """
    result: dict[str, object] = {}
    lines = raw.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#") or line.startswith((" ", "\t")):
            continue
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()

        if rest in {">", "|", ">-", "|-"}:
            block: list[str] = []
            while index < len(lines) and (not lines[index].strip() or lines[index].startswith((" ", "\t"))):
                block.append(lines[index].strip())
                index += 1
            joined = " ".join(part for part in block if part)
            result[key] = joined
            continue

        if rest:
            result[key] = rest.strip("'\"")
            continue

        # An empty value introduces either a list or a nested map.
        collected_list: list[str] = []
        collected_map: dict[str, str] = {}
        while index < len(lines) and (not lines[index].strip() or lines[index].startswith((" ", "\t"))):
            child = lines[index].strip()
            index += 1
            if not child:
                continue
            if child.startswith("- "):
                collected_list.append(child[2:].strip().strip("'\""))
            elif ":" in child:
                child_key, _, child_value = child.partition(":")
                collected_map[child_key.strip()] = child_value.strip().strip("'\"")
        result[key] = collected_list if collected_list else collected_map
    return result


def check_frontmatter(fields: dict[str, object]) -> list[Issue]:
    issues: list[Issue] = []

    for key in sorted(set(fields) - SPEC_FIELDS):
        issues.append(
            Issue(
                "SPEC001",
                f"unexpected frontmatter key {key!r}; the spec allows only "
                f"{', '.join(sorted(SPEC_FIELDS))}",
            )
        )

    for key in sorted(REQUIRED_FIELDS - set(fields)):
        issues.append(Issue("SPEC002", f"missing required frontmatter key {key!r}"))

    name = fields.get("name")
    if isinstance(name, str):
        if not NAME_PATTERN.match(name):
            issues.append(Issue("SPEC003", f"name {name!r} must be lowercase letters, digits and hyphens"))
        if len(name) > MAX_NAME:
            issues.append(Issue("SPEC003", f"name is {len(name)} characters; the limit is {MAX_NAME}"))

    description = fields.get("description")
    if not isinstance(description, str) or not description.strip():
        issues.append(Issue("SPEC004", "description is missing; Claude uses it to decide when to load the skill"))
    elif len(description) > MAX_DESCRIPTION:
        issues.append(
            Issue("SPEC004", f"description is {len(description)} characters; the limit is {MAX_DESCRIPTION}")
        )

    compatibility = fields.get("compatibility")
    if isinstance(compatibility, str) and len(compatibility) > MAX_COMPATIBILITY:
        issues.append(
            Issue(
                "SPEC005",
                f"compatibility is {len(compatibility)} characters; the limit is {MAX_COMPATIBILITY}",
            )
        )

    if "metadata" in fields and not isinstance(fields["metadata"], dict):
        issues.append(Issue("SPEC006", "metadata must be a mapping of key to value"))

    tools = fields.get("allowed-tools")
    if tools is not None and not isinstance(tools, (str, list)):
        issues.append(Issue("STRUCT03", "allowed-tools must be a string or a list of strings"))

    return issues


def check_body(body: str, skill_path: Path) -> list[Issue]:
    issues: list[Issue] = []

    line_count = len(body.splitlines())
    if line_count > MAX_BODY_LINES:
        issues.append(
            Issue(
                "STRUCT01",
                f"SKILL.md body is {line_count} lines; move detail into references/ "
                f"to stay under {MAX_BODY_LINES}",
                severity="warning",
            )
        )

    root = skill_path.parent
    for target in sorted(set(LINK_PATTERN.findall(body))):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        candidate = (root / target.split("#", 1)[0]).resolve()
        if not candidate.exists():
            issues.append(Issue("STRUCT02", f"SKILL.md links to {target!r}, which does not exist"))

    return issues


def check_skill(skill_path: Path) -> list[Issue]:
    """Run every rule against one SKILL.md."""
    text = skill_path.read_text(encoding="utf-8")
    raw, body = split_frontmatter(text)
    if raw is None:
        return [Issue("SPEC007", "no YAML frontmatter; the opening '---' must be the first line of the file")]
    return check_frontmatter(parse_frontmatter(raw)) + check_body(body, skill_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SKILL.md against the Agent Skills specification.")
    parser.add_argument("--skill", default=None, help="path to SKILL.md (default: the repository's own)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args()

    skill_path = Path(args.skill) if args.skill else Path(__file__).resolve().parent.parent / "SKILL.md"
    if not skill_path.is_file():
        print(f"error: no such file: {skill_path}", file=sys.stderr)
        return 2

    issues = check_skill(skill_path)
    for issue in issues:
        print(issue.render())

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    if errors or (args.strict and warnings):
        print(f"\n{BANNER}: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"{BANNER}: {skill_path.name} conforms to the spec ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
