#!/usr/bin/env python3
"""Create a paper plan and/or issues CSV for an IEEE paper project.

This script supports a gated workflow:
  1) Create a draft plan (for user review)
  2) After user confirmation, create the issues CSV (execution contract)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from paper_utils import (
    build_issues_filename,
    build_plan_filename,
    check_latex_available,
    format_yaml_value,
    get_assets_dir,
    now_iso,
    now_timestamp,
    slugify,
    validate_slug,
    validate_timestamp,
)


def read_template(template_name: str) -> str:
    """Read a template file from assets."""
    template_path = get_assets_dir() / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def replace_placeholders(content: str, replacements: dict[str, str]) -> str:
    """Replace placeholders in template content."""
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    return content


def kickoff_gate_confirmed(plan_path: Path) -> bool:
    """Return True if the plan indicates the kickoff gate is confirmed."""
    if not plan_path.exists():
        return False
    text = plan_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if re.search(r"^\s*-\s*\[\s*[xX]\s*\]\s*User confirmed scope \+ outline", line):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a paper plan for an IEEE paper project.")
    parser.add_argument("--topic", required=True, help="Paper topic description.")
    parser.add_argument(
        "--paper-type",
        default="review",
        choices=["review", "codebase", "conference"],
        help="Paper type: review | codebase | conference (default: review).",
    )
    parser.add_argument(
        "--venue",
        choices=["NeurIPS", "ICML", "ICLR", "ACL", "AAAI", "CVPR"],
        help="Conference venue (required when --paper-type conference).",
    )
    parser.add_argument(
        "--stage",
        default="plan",
        choices=["plan", "issues"],
        help="What to create: plan | issues (default: plan).",
    )
    parser.add_argument(
        "--complexity",
        default="medium",
        choices=["simple", "medium", "complex"],
        help="Plan complexity: simple|medium|complex.",
    )
    parser.add_argument(
        "--timestamp",
        help="Optional timestamp override (YYYY-MM-DD_HH-mm-ss). Required for --stage issues.",
    )
    parser.add_argument(
        "--slug",
        help="Optional slug override for filenames (lower-case, hyphen-delimited).",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for plan and issues files (default: current directory).",
    )
    parser.add_argument(
        "--check-latex",
        action="store_true",
        help="Check if LaTeX is available and set latex_available accordingly.",
    )
    parser.add_argument(
        "--with-literature-notes",
        action="store_true",
        help="Create notes/literature-notes.md to track paper summaries per citation key.",
    )
    parser.add_argument(
        "--codebase-dir",
        help="Project codebase directory (required when --paper-type codebase).",
    )
    args = parser.parse_args()

    topic = args.topic.strip()
    if not topic:
        print("error: Topic cannot be empty.", file=sys.stderr)
        return 1

    slug = args.slug.strip() if args.slug else slugify(topic)
    try:
        validate_slug(slug)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.timestamp:
        timestamp = args.timestamp.strip()
        try:
            validate_timestamp(timestamp)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    else:
        if args.stage == "issues":
            print("error: --timestamp is required when using --stage issues.", file=sys.stderr)
            return 1
        timestamp = now_timestamp()

    # Check LaTeX availability
    latex_info = check_latex_available()
    latex_available = latex_info["available"]

    if args.check_latex:
        print(f"LaTeX available: {latex_available}")
        if latex_available:
            print(f"  pdflatex: {latex_info['pdflatex']}")
            print(f"  bibtex: {latex_info['bibtex']}")
            if latex_info["latexmk"]:
                print(f"  latexmk: {latex_info['latexmk']}")
            print(f"  Recommended: {latex_info['recommended']}")
        else:
            print("  LaTeX not found. Paper will be created without compilation.")
            print("  User can compile later with Overleaf or local LaTeX installation.")

    if args.paper_type == "codebase" and args.with_literature_notes:
        print("error: --with-literature-notes is only supported for --paper-type review.", file=sys.stderr)
        return 1

    if args.paper_type == "conference" and not args.venue:
        print("error: --venue is required when --paper-type conference.", file=sys.stderr)
        return 1

    if args.paper_type == "codebase":
        if not args.codebase_dir:
            print("error: --codebase-dir is required when --paper-type codebase.", file=sys.stderr)
            return 1

    venue_page_limits: dict[str, int] = {
        "NeurIPS": 9,
        "ICML": 8,
        "ICLR": 9,
        "ACL": 8,
        "AAAI": 7,
        "CVPR": 8,
    }

    if args.paper_type == "conference":
        issues_template_name = "paper-issues-conference-template.csv"
        plan_template_name = "paper-plan-conference-template.md"
    elif args.paper_type == "codebase":
        issues_template_name = "paper-issues-codebase-template.csv"
        plan_template_name = "paper-plan-codebase-template.md"
    else:
        issues_template_name = "paper-issues-template.csv"
        plan_template_name = "paper-plan-template.md"

    # Read and process templates
    try:
        issues_template = read_template(issues_template_name)
        plan_template = read_template(plan_template_name) if args.stage == "plan" else None
        literature_template = (
            read_template("literature-notes-template.md")
            if args.with_literature_notes and args.stage == "issues"
            else None
        )
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir).resolve()

    codebase_dir = Path(args.codebase_dir).expanduser().resolve() if args.codebase_dir else None
    if args.paper_type == "codebase" and codebase_dir is not None and not codebase_dir.exists():
        print(f"error: --codebase-dir not found: {codebase_dir}", file=sys.stderr)
        return 1

    codebase_name = codebase_dir.name if codebase_dir is not None else ""

    venue_name = args.venue if args.venue else ""
    page_limit = str(venue_page_limits.get(venue_name, "")) if venue_name else ""

    replacements = {
        "<paper topic>": topic,
        "<topic>": topic,
        "<ISO8601 timestamp>": now_iso(),
        "<YYYY-MM-DD_HH-mm-ss>": timestamp,
        "<slug>": slug,
        "<true|false>": "true" if latex_available else "false",
        "<paper_dir>": ".",
        "<codebase_dir>": codebase_name,
        "<codebase_name>": codebase_name,
        "<venue>": venue_name,
        "<N>": page_limit,
    }

    # Replace placeholders
    plan_content = (
        replace_placeholders(plan_template, replacements)
        if plan_template
        else None
    )
    issues_content = issues_template  # CSV doesn't need placeholder replacement
    literature_content = (
        replace_placeholders(literature_template, replacements)
        if literature_template
        else None
    )

    # Build output paths
    plan_dir = output_dir / "plan"
    issues_dir = output_dir / "issues"

    plan_filename = build_plan_filename(timestamp, slug)
    issues_filename = build_issues_filename(timestamp, slug)

    plan_path = plan_dir / plan_filename
    issues_path = issues_dir / issues_filename
    literature_dir = output_dir / "notes"
    literature_path = literature_dir / "literature-notes.md"

    # Check for existing / prerequisite files
    if args.stage == "issues" and not plan_path.exists():
        print(
            f"error: Plan not found (create the plan first): {plan_path}",
            file=sys.stderr,
        )
        return 1
    if args.stage == "plan" and plan_path.exists():
        print(f"error: Plan already exists: {plan_path}", file=sys.stderr)
        return 1
    if args.stage == "issues" and issues_path.exists():
        print(f"error: Issues file already exists: {issues_path}", file=sys.stderr)
        return 1
    if literature_content and literature_path.exists():
        print(f"error: Literature notes already exists: {literature_path}", file=sys.stderr)
        return 1
    if args.stage == "issues" and not kickoff_gate_confirmed(plan_path):
        print(
            "error: Kickoff gate is not confirmed in the plan. "
            "Edit the plan and check the box '- [x] User confirmed scope + outline in chat' before creating issues.",
            file=sys.stderr,
        )
        return 1

    # Build frontmatter for plan
    frontmatter_lines = [
        "---",
        f"mode: {format_yaml_value('paper-plan')}",
        f"paper_type: {format_yaml_value(args.paper_type)}",
        f"topic: {format_yaml_value(topic)}",
        f"timestamp: {format_yaml_value(timestamp)}",
        f"slug: {format_yaml_value(slug)}",
        f"created_at: {format_yaml_value(now_iso())}",
        f"complexity: {format_yaml_value(args.complexity)}",
    ]
    if args.paper_type == "codebase" and codebase_dir:
        frontmatter_lines.append(f"codebase_name: {format_yaml_value(codebase_name)}")
    if args.paper_type == "conference" and args.venue:
        frontmatter_lines.append(f"venue: {format_yaml_value(args.venue)}")
        frontmatter_lines.append(f"page_limit: {venue_page_limits.get(args.venue, '')}")
    frontmatter_lines.append(f"latex_available: {str(latex_available).lower()}")
    frontmatter_lines.append("---\n")
    frontmatter = "\n".join(frontmatter_lines)

    # Remove template frontmatter from plan content
    if plan_content and plan_content.lstrip().startswith("---"):
        # Find the second --- and remove everything before it
        first_dash = plan_content.find("---")
        second_dash = plan_content.find("---", first_dash + 3)
        if second_dash != -1:
            plan_content = plan_content[second_dash + 3:].lstrip()

    # Write files
    if args.stage == "plan":
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(frontmatter + (plan_content or "") + "\n", encoding="utf-8")
        print(f"Created plan: {plan_path}")
    if args.stage == "issues":
        issues_dir.mkdir(parents=True, exist_ok=True)
        issues_path.write_text(issues_content, encoding="utf-8")
        print(f"Created issues: {issues_path}")
    if literature_content:
        literature_dir.mkdir(parents=True, exist_ok=True)
        literature_path.write_text(literature_content.rstrip() + "\n", encoding="utf-8")
        print(f"Created literature notes: {literature_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
