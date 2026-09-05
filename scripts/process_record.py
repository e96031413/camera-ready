#!/usr/bin/env python3
"""Create a process record (pipeline summary + collaboration quality scaffold).

Outputs:
  - <project-dir>/notes/process-record.md

This is deterministic and privacy-safe:
- Does not print absolute filesystem paths.
- Summarizes only filenames and aggregate counts.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from paper_utils import count_bibtex_entries, count_citations, now_iso


_FRONTMATTER_BOUNDARY_RE = re.compile(r"^\s*---\s*$")
_FRONTMATTER_KV_RE = re.compile(r"^\s*([a-zA-Z0-9_]+)\s*:\s*(.+?)\s*$")


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _find_latest_file(directory: Path, suffix: str) -> Path | None:
    if not directory.exists():
        return None
    candidates = sorted(p for p in directory.glob(f"*{suffix}") if p.is_file())
    return candidates[-1] if candidates else None


def _strip_yaml_quotes(value: str) -> str:
    v = value.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1].strip()
    return v


def parse_plan_frontmatter(plan_path: Path) -> dict[str, str]:
    text = plan_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines or not _FRONTMATTER_BOUNDARY_RE.match(lines[0]):
        return {}
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if _FRONTMATTER_BOUNDARY_RE.match(line):
            break
        m = _FRONTMATTER_KV_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip()
        val = _strip_yaml_quotes(m.group(2))
        meta[key] = val
    return meta


@dataclass(frozen=True)
class IssuesSummary:
    issues_filename: str
    by_phase: dict[str, int]
    by_status: dict[str, int]
    target_citations: int
    verified_citations: int


def _safe_int(value: str) -> int:
    try:
        return int(value.strip())
    except ValueError:
        return 0


def summarize_issues(project_dir: Path) -> IssuesSummary | None:
    issues_dir = project_dir / "issues"
    latest = _find_latest_file(issues_dir, ".csv")
    if latest is None:
        return None

    with latest.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    by_phase: dict[str, int] = {}
    by_status: dict[str, int] = {}
    target = 0
    verified = 0

    for row in rows:
        phase = (row.get("Phase") or "").strip() or "?"
        status = (row.get("Status") or "").strip() or "?"
        by_phase[phase] = by_phase.get(phase, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1

        target += _safe_int(row.get("Target_Citations") or "")
        verified += _safe_int(row.get("Verified_Citations") or "")

    return IssuesSummary(
        issues_filename=latest.name,
        by_phase=dict(sorted(by_phase.items())),
        by_status=dict(sorted(by_status.items())),
        target_citations=target,
        verified_citations=verified,
    )


def summarize_claim_registry(project_dir: Path) -> dict[str, int] | None:
    notes_dir = project_dir / "notes"
    csv_path = notes_dir / "claim-registry.csv"
    if not csv_path.exists():
        return None
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    total = 0
    verdict_counts: dict[str, int] = {}
    for row in rows:
        if not (row.get("ID") or "").strip():
            continue
        total += 1
        verdict = (row.get("Verdict") or "").strip() or "UNSET"
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
    verdict_counts["TOTAL"] = total
    return verdict_counts


def build_markdown(
    *,
    project_name: str,
    plan_filename: str | None,
    plan_meta: dict[str, str],
    issues: IssuesSummary | None,
    citation_stats: dict,
    bib_stats: dict,
    claim_verdicts: dict[str, int] | None,
) -> str:
    lines: list[str] = [
        "# Process Record",
        "",
        f"- Created at: {now_iso()}",
        f"- Paper project: {project_name}",
    ]
    if plan_filename:
        lines.append(f"- Plan: `{plan_filename}`")
    if issues is not None:
        lines.append(f"- Issues: `{issues.issues_filename}`")
    lines.append("")

    if plan_meta:
        lines.append("## Plan metadata (frontmatter)")
        lines.append("")
        for k in ["paper_type", "topic", "timestamp", "slug", "created_at", "complexity", "codebase_name", "latex_available"]:
            if k in plan_meta:
                lines.append(f"- {k}: {plan_meta[k]}")
        lines.append("")

    lines.append("## Metrics")
    lines.append("")
    lines.append(f"- main.tex: {citation_stats.get('total', 0)} cite uses, {citation_stats.get('unique', 0)} unique keys")
    lines.append(f"- ref.bib: {bib_stats.get('total', 0)} entries")
    if issues is not None and issues.target_citations > 0:
        pct = (issues.verified_citations / issues.target_citations) * 100
        lines.append(f"- Citation progress (from issues): {issues.verified_citations}/{issues.target_citations} ({pct:.1f}%)")
    lines.append("")

    if issues is not None:
        lines.append("## Issues summary")
        lines.append("")
        lines.append(f"- By phase: {', '.join(f'{k}={v}' for k, v in issues.by_phase.items())}")
        lines.append(f"- By status: {', '.join(f'{k}={v}' for k, v in issues.by_status.items())}")
        lines.append("")

    lines.append("## Integrity checklist")
    lines.append("")
    lines.append("- Privacy gate: run `python3 scripts/paper_privacy_scan.py --project-dir <paper_dir>` (must pass before sharing)")
    lines.append("- BibTeX audit: run `python3 scripts/bibtex_audit.py --project-dir <paper_dir> --window-years 3`")
    lines.append("- Claim registry: generate with `python3 scripts/claim_registry.py --project-dir <paper_dir> --mode broad --write-csv`")
    lines.append("- Integrity gate (pre-review/final): `python3 scripts/integrity_gate.py --project-dir <paper_dir> --stage pre-review|final`")
    lines.append("")

    if claim_verdicts is not None:
        lines.append("### Claim registry summary (from claim-registry.csv)")
        lines.append("")
        total = claim_verdicts.get("TOTAL", 0)
        items = sorted(((k, v) for k, v in claim_verdicts.items() if k != "TOTAL"), key=lambda kv: (-kv[1], kv[0]))
        lines.append(f"- Total claims: {total}")
        if items:
            lines.append("- Verdict counts:")
            for k, v in items:
                lines.append(f"  - {k}: {v}")
        lines.append("")

    lines.append("## Collaboration quality (optional)")
    lines.append("")
    lines.append("Fill scores (1–100) + short rationale per dimension (see `references/collaboration-quality.md`):")
    lines.append("")
    lines.append("| Dimension | Score (1–100) | Rationale |")
    lines.append("|---|---:|---|")
    lines.append("| Scope control |  |  |")
    lines.append("| Traceability |  |  |")
    lines.append("| Evidence discipline |  |  |")
    lines.append("| Reproducibility |  |  |")
    lines.append("| Review responsiveness |  |  |")
    lines.append("| Privacy & safety |  |  |")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create notes/process-record.md for a paper project.")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Paper project directory containing main.tex/ref.bib/plan/issues/notes (default: .).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite notes/process-record.md if present.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        return fail("project dir not found")
    if not project_dir.is_dir():
        return fail("project dir is not a directory")
    if not (project_dir / "main.tex").exists():
        return fail("main.tex not found in project dir")

    plan_path = _find_latest_file(project_dir / "plan", ".md")
    plan_meta = parse_plan_frontmatter(plan_path) if plan_path else {}

    issues = summarize_issues(project_dir)
    citation_stats = count_citations(project_dir / "main.tex")
    bib_stats = count_bibtex_entries(project_dir / "ref.bib")
    claim_verdicts = summarize_claim_registry(project_dir)

    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    out_path = notes_dir / "process-record.md"
    if out_path.exists() and not args.overwrite:
        return fail("notes/process-record.md already exists (use --overwrite to replace)")

    out_path.write_text(
        build_markdown(
            project_name=project_dir.name,
            plan_filename=plan_path.name if plan_path else None,
            plan_meta=plan_meta,
            issues=issues,
            citation_stats=citation_stats,
            bib_stats=bib_stats,
            claim_verdicts=claim_verdicts,
        ),
        encoding="utf-8",
    )
    print("Created: notes/process-record.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

