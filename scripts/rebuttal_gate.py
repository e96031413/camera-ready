#!/usr/bin/env python3
"""Rebuttal gate: every review comment becomes a tracked work item. 2026-09-05-v1.

A review is only useful if the answers are traceable. Writing "Resolution: fixed"
under a comment costs nothing and proves nothing; the issues CSV is where work is
tracked in this workflow, so a comment that changes the paper has to appear
there, and a comment that changes nothing has to say so in words.

The gate reads `notes/review-comments.md` and the project's issues CSV, and for
every numbered comment requires one of:

  - an issues row that names the comment ("RC3" or "review comment 3" in the
    row ID, Title, Notes or Depends_On), or
  - a Resolution line that declines it, giving a reason.

With --emit-issues it appends a TODO row per unmapped comment instead of
failing, so the rebuttal produces the work list rather than describing it.

Roles: --scaffold writes a review skeleton with Reviewer and Area Chair
sections. The reviews themselves are written by whoever plays those roles; this
tool provides the structure and then holds the answers to it.

Exit codes: 0 every comment is tracked or explicitly declined; 1 a comment is
neither; 2 usage error.

Usage:
  python scripts/rebuttal_gate.py --project-dir <paper_dir> --scaffold
  python scripts/rebuttal_gate.py --project-dir <paper_dir>
  python scripts/rebuttal_gate.py --project-dir <paper_dir> --emit-issues
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import now_iso

BANNER = "rebuttal_gate 2026-09-05-v1"

_COMMENT_RE = re.compile(r"^#{1,6}\s*(\d+)\.\s*(.+)$", re.MULTILINE)
_RESOLUTION_RE = re.compile(r"\*{0,2}Resolution:?\*{0,2}\s*(.*)", re.IGNORECASE)
_ROLE_RE = re.compile(r"^#{1,3}\s*(Reviewer\s*\d+|Area Chair|Meta[- ]Review)\b", re.IGNORECASE | re.MULTILINE)
# A declined comment says so; anything else is a promise that needs a work item.
_DECLINE_RE = re.compile(
    r"\b(no action|declin|will not|not chang|out of scope|disagree|no change|"
    r"already (?:stated|documented|addressed)|cannot)\b",
    re.IGNORECASE,
)


@dataclass
class Comment:
    number: int
    title: str
    resolution: str
    role: str


@dataclass
class Verdict:
    comment: Comment
    status: str  # "TRACKED" | "DECLINED" | "UNTRACKED"
    detail: str


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def find_issues_csv(project_dir: Path) -> Path | None:
    candidates = sorted((project_dir / "issues").glob("*.csv"))
    return candidates[0] if candidates else None


def parse_comments(text: str) -> list[Comment]:
    """Numbered comments, each with its Resolution line and owning role, if any."""
    roles = [(m.start(), m.group(1).strip()) for m in _ROLE_RE.finditer(text)]
    matches = list(_COMMENT_RE.finditer(text))
    comments: list[Comment] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        resolution_match = _RESOLUTION_RE.search(block)
        resolution = resolution_match.group(1).strip() if resolution_match else ""
        role = ""
        for position, name in roles:
            if position < match.start():
                role = name
            else:
                break
        comments.append(
            Comment(
                number=int(match.group(1)),
                title=match.group(2).strip(),
                resolution=resolution,
                role=role,
            )
        )
    return comments


def read_issue_rows(csv_path: Path) -> list[dict]:
    text = csv_path.read_text(encoding="utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def comment_is_tracked(comment: Comment, rows: list[dict]) -> str | None:
    """Return the ID of an issues row that names this comment, if one does.

    The reference has to be explicit. A bare "R3" is not enough: the scaffolded
    issues CSV already uses R1 and R2 for research rows, and a gate that reads
    those as answers to a review is a gate that passes an unanswered review.
    """
    tokens = {
        f"rc{comment.number}",
        f"review comment {comment.number}",
        f"comment {comment.number}",
        f"reviewer comment {comment.number}",
    }
    for row in rows:
        haystack = " ".join(
            str(row.get(field, "")) for field in ("ID", "Title", "Notes", "Depends_On")
        ).lower()
        for token in tokens:
            if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack):
                return str(row.get("ID", "?"))
    return None


def judge(comments: list[Comment], rows: list[dict]) -> list[Verdict]:
    verdicts: list[Verdict] = []
    for comment in comments:
        tracked = comment_is_tracked(comment, rows)
        if tracked:
            verdicts.append(Verdict(comment, "TRACKED", f"issues row {tracked}"))
            continue
        if comment.resolution and _DECLINE_RE.search(comment.resolution):
            verdicts.append(Verdict(comment, "DECLINED", comment.resolution[:80]))
            continue
        if not comment.resolution:
            verdicts.append(Verdict(comment, "UNTRACKED", "no Resolution and no issues row"))
            continue
        verdicts.append(
            Verdict(comment, "UNTRACKED", "resolution promises a change with no issues row")
        )
    return verdicts


def emit_issue_rows(csv_path: Path, verdicts: list[Verdict]) -> int:
    """Append one TODO row per untracked comment. Returns the number appended."""
    untracked = [v for v in verdicts if v.status == "UNTRACKED"]
    if not untracked:
        return 0
    text = csv_path.read_text(encoding="utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = list(reader.fieldnames or [])
    rows = list(reader)
    if not fieldnames:
        raise ValueError("issues CSV has no header")

    existing_ids = {str(row.get("ID", "")).strip() for row in rows}
    added = 0
    for verdict in untracked:
        row_id = f"RC{verdict.comment.number}"
        while row_id in existing_ids:
            row_id += "b"
        existing_ids.add(row_id)
        row = {name: "" for name in fieldnames}
        row.update(
            {
                "ID": row_id,
                "Phase": "Review",  # the schema's vocabulary; see references/issues-csv-schema.md
                "Title": f"Answer review comment {verdict.comment.number}",
                "Description": verdict.comment.title,
                "Acceptance": "the manuscript changes, or the comment is declined in writing",
                "Status": "TODO",
                "Notes": f"raised by {verdict.comment.role or 'review'}; see notes/review-comments.md",
            }
        )
        rows.append({k: row.get(k, "") for k in fieldnames})
        added += 1

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return added


def write_report(path: Path, verdicts: list[Verdict], *, csv_name: str) -> None:
    untracked = [v for v in verdicts if v.status == "UNTRACKED"]
    lines = [
        "# Rebuttal Gate Report",
        "",
        f"- Created at: {now_iso()}",
        f"- Issues CSV: {csv_name}",
        f"- Comments: {len(verdicts)}",
        f"- Tracked: {sum(1 for v in verdicts if v.status == 'TRACKED')}"
        f"  Declined: {sum(1 for v in verdicts if v.status == 'DECLINED')}"
        f"  Untracked: {len(untracked)}",
        f"- Verdict: {'FAIL' if untracked else 'PASS'}",
        "",
        "| # | Role | Comment | Status | Detail |",
        "|---|---|---|---|---|",
    ]
    for verdict in verdicts:
        title = verdict.comment.title.replace("|", "\\|")
        if len(title) > 70:
            title = title[:67] + "..."
        detail = verdict.detail.replace("|", "\\|")
        lines.append(
            f"| {verdict.comment.number} | {verdict.comment.role or '-'} | {title} "
            f"| {verdict.status} | {detail} |"
        )
    lines += [
        "",
        "A comment is TRACKED when an issues row names it, DECLINED when the",
        "resolution says in words that nothing will change, and UNTRACKED when it",
        "promises a change nobody wrote down.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


SCAFFOLD = """# Review Comments

Written by the review roles below. One numbered comment per issue, each with a
Resolution line added during the revise phase.

## Reviewer 1

### 1. <one-line claim about a weakness>

<what is wrong, and what would fix it>
Resolution: <the change made, or why the comment is declined>

## Reviewer 2

### 2. <one-line claim about a weakness>

<what is wrong, and what would fix it>
Resolution:

## Area Chair

### 3. <the decision-relevant concern across the reviews>

<what has to be true for the paper to be accepted>
Resolution:
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Require every review comment to be tracked as work or declined in writing."
    )
    parser.add_argument("--project-dir", default=".", help="Paper project directory (default: .).")
    parser.add_argument(
        "--emit-issues",
        action="store_true",
        help="Append a TODO issues row for each untracked comment instead of failing.",
    )
    parser.add_argument(
        "--scaffold",
        action="store_true",
        help="Write a review skeleton with Reviewer and Area Chair sections, then exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        return fail("project dir not found")

    notes_dir = project_dir / "notes"
    comments_path = notes_dir / "review-comments.md"

    if args.scaffold:
        notes_dir.mkdir(parents=True, exist_ok=True)
        if comments_path.exists():
            return fail("notes/review-comments.md already exists")
        comments_path.write_text(SCAFFOLD, encoding="utf-8")
        print(f"{BANNER}: wrote notes/review-comments.md")
        print("Fill it from the review roles, then run this gate without --scaffold.")
        return 0

    if not comments_path.is_file():
        return fail("notes/review-comments.md not found (run with --scaffold to start one)")

    comments = parse_comments(comments_path.read_text(encoding="utf-8", errors="replace"))
    if not comments:
        return fail("no numbered comments found (use '## 1. <title>' headings)")

    csv_path = find_issues_csv(project_dir)
    if csv_path is None:
        return fail("no issues CSV under issues/; the rebuttal has nowhere to land")

    rows = read_issue_rows(csv_path)
    verdicts = judge(comments, rows)

    if args.emit_issues:
        try:
            added = emit_issue_rows(csv_path, verdicts)
        except ValueError as exc:
            return fail(str(exc))
        if added:
            print(f"{BANNER}: appended {added} TODO row(s) to {csv_path.name}")
            rows = read_issue_rows(csv_path)
            verdicts = judge(comments, rows)

    notes_dir.mkdir(parents=True, exist_ok=True)
    write_report(notes_dir / "rebuttal-gate.md", verdicts, csv_name=csv_path.name)

    for verdict in verdicts:
        print(f"  [{verdict.status:<9}] {verdict.comment.number}. {verdict.comment.title[:60]}")

    untracked = [v for v in verdicts if v.status == "UNTRACKED"]
    print(
        f"{BANNER}: {len(verdicts) - len(untracked)}/{len(verdicts)} comment(s) tracked or declined"
    )
    print("Report: notes/rebuttal-gate.md")
    if untracked:
        print("Add an issues row for each, or say in the Resolution that nothing changes.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
