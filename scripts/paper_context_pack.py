#!/usr/bin/env python3
"""Create a lightweight context pack for Paper-Reviewer rounds.

This is intentionally deterministic and privacy-safe:
- Do not print absolute filesystem paths.
- Do not quote internal URLs from logs or notes.

Outputs:
  - <project-dir>/notes/review-context.md
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from paper_utils import count_bibtex_entries, count_citations


_SECTION_RE = re.compile(r"\\section\{([^}]+)\}")
_SUBSECTION_RE = re.compile(r"\\subsection\{([^}]+)\}")
_OVERFULL_RE = re.compile(r"Overfull \\\\hbox")
_UNDEFINED_CITATION_RE = re.compile(r"Citation .* undefined")
_UNDEFINED_REFERENCE_RE = re.compile(r"Reference .* undefined")

MAX_SECTIONS = 32
MAX_SUBSECTIONS = 64
MAX_SUBSECTION_PREVIEW = 20
MAX_INCOMPLETE_ISSUES = 20
MAX_BIB_YEARS_PREVIEW = 8
MAX_MISSING_BIB_KEYS_PREVIEW = 20
MAX_CLAIM_VERDICTS_PREVIEW = 6


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


@dataclass(frozen=True)
class IssuesSummary:
    issues_filename: str
    by_phase: dict[str, int]
    by_status: dict[str, int]
    target_citations: int
    verified_citations: int
    incomplete_ids: list[str]


@dataclass(frozen=True)
class ClaimRegistrySummary:
    total: int
    filled_verdicts: int
    blockers: int
    by_verdict: dict[str, int]


def parse_args() -> Path | int:
    parser = argparse.ArgumentParser(description="Create notes/review-context.md for reviewer rounds.")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Paper project directory containing main.tex/ref.bib/plan/issues/notes (default: .).",
    )
    args = parser.parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        return fail("project dir not found")
    if not project_dir.is_dir():
        return fail("project dir is not a directory")
    if not (project_dir / "main.tex").exists():
        return fail("main.tex not found in project dir")
    return project_dir


def _find_latest_file(directory: Path, suffix: str) -> Path | None:
    if not directory.exists():
        return None
    candidates = sorted(p for p in directory.glob(f"*{suffix}") if p.is_file())
    return candidates[-1] if candidates else None


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
    incomplete: list[str] = []

    for row in rows:
        phase = (row.get("Phase") or "").strip() or "?"
        status = (row.get("Status") or "").strip() or "?"
        by_phase[phase] = by_phase.get(phase, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1

        target += _safe_int(row.get("Target_Citations") or "")
        verified += _safe_int(row.get("Verified_Citations") or "")

        issue_id = (row.get("ID") or "").strip()
        if issue_id and status not in {"DONE", "SKIP"}:
            incomplete.append(issue_id)

    incomplete = sorted(incomplete)[:MAX_INCOMPLETE_ISSUES]
    return IssuesSummary(
        issues_filename=latest.name,
        by_phase=dict(sorted(by_phase.items())),
        by_status=dict(sorted(by_status.items())),
        target_citations=target,
        verified_citations=verified,
        incomplete_ids=incomplete,
    )


def extract_outline(tex_text: str) -> dict[str, list[str]]:
    sections = [s.strip() for s in _SECTION_RE.findall(tex_text) if s.strip()]
    subsections = [s.strip() for s in _SUBSECTION_RE.findall(tex_text) if s.strip()]
    return {"sections": sections[:MAX_SECTIONS], "subsections": subsections[:MAX_SUBSECTIONS]}


def summarize_compile_signals(project_dir: Path) -> dict[str, int] | None:
    log_path = project_dir / "main.log"
    if not log_path.exists():
        return None
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return {
        "overfull_hbox": len(_OVERFULL_RE.findall(text)),
        "undefined_citations": len(_UNDEFINED_CITATION_RE.findall(text)),
        "undefined_references": len(_UNDEFINED_REFERENCE_RE.findall(text)),
    }

def summarize_claim_registry(project_dir: Path) -> ClaimRegistrySummary | None:
    notes_dir = project_dir / "notes"
    csv_path = notes_dir / "claim-registry.csv"
    if not csv_path.exists():
        return None

    by_verdict: dict[str, int] = {}
    total = 0
    filled = 0
    blockers = 0

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            issue_id = (row.get("ID") or "").strip()
            if not issue_id:
                continue
            total += 1
            verdict = (row.get("Verdict") or "").strip()
            if verdict:
                filled += 1
            verdict_key = (verdict or "UNSET").strip()
            by_verdict[verdict_key] = by_verdict.get(verdict_key, 0) + 1
            if verdict_key.upper() in {"MAJOR_DISTORTION", "UNVERIFIABLE"}:
                blockers += 1

    return ClaimRegistrySummary(
        total=total,
        filled_verdicts=filled,
        blockers=blockers,
        by_verdict=dict(sorted(by_verdict.items(), key=lambda kv: (-kv[1], kv[0]))),
    )


def _render_header(project_name: str) -> list[str]:
    return [
        "# Review Context Pack",
        "",
        f"- Created at: {now_iso()}",
        f"- Paper project: {project_name}",
        "",
    ]


def _render_draft_structure(outline: dict[str, list[str]]) -> list[str]:
    lines: list[str] = ["## Draft structure", ""]
    if outline["sections"]:
        lines.append("- Sections:")
        lines.extend([f"  - {name}" for name in outline["sections"]])
    else:
        lines.append("- Sections: (none detected)")

    if outline["subsections"]:
        lines.append("- Subsections (subset):")
        lines.extend([f"  - {name}" for name in outline["subsections"][:MAX_SUBSECTION_PREVIEW]])

    lines.append("")
    return lines


def _render_issues(issues: IssuesSummary | None) -> list[str]:
    lines: list[str] = ["## Issues status (latest)", ""]
    if issues is None:
        lines.append("- Issues CSV: (not found)")
        lines.append("")
        return lines

    lines.append(f"- Issues CSV: `{issues.issues_filename}`")
    lines.append(f"- By phase: {', '.join(f'{k}={v}' for k, v in issues.by_phase.items())}")
    lines.append(f"- By status: {', '.join(f'{k}={v}' for k, v in issues.by_status.items())}")
    if issues.target_citations > 0:
        pct = (issues.verified_citations / issues.target_citations) * 100
        lines.append(f"- Citation progress (from issues): {issues.verified_citations}/{issues.target_citations} ({pct:.1f}%)")
    if issues.incomplete_ids:
        lines.append(f"- Incomplete issues (subset): {', '.join(issues.incomplete_ids)}")
    lines.append("")
    return lines


def _render_citations_and_bib(citation_stats: dict, bib_stats: dict) -> list[str]:
    lines: list[str] = ["## Citations & BibTeX", ""]
    lines.append(
        f"- main.tex: {citation_stats.get('total', 0)} cite uses, {citation_stats.get('unique', 0)} unique keys"
    )
    lines.append(f"- ref.bib: {bib_stats.get('total', 0)} entries")
    by_year = bib_stats.get("by_year") or {}
    if by_year:
        items = sorted(by_year.items(), key=lambda kv: (-int(kv[0]), kv[0]))
        top = ", ".join(f"{year}:{count}" for year, count in items[:MAX_BIB_YEARS_PREVIEW])
        lines.append(f"- BibTeX by year (subset): {top}")

    missing = sorted(set(citation_stats.get("keys") or []) - set(bib_stats.get("keys") or []))
    if missing:
        lines.append(f"- Missing BibTeX keys (subset): {', '.join(missing[:MAX_MISSING_BIB_KEYS_PREVIEW])}")

    lines.append("")
    return lines


def _render_compile_signals(compile_signals: dict[str, int] | None) -> list[str]:
    lines: list[str] = ["## Compile signals (if available)", ""]
    if compile_signals is None:
        lines.append("- main.log: (not found)")
    else:
        lines.append(f"- Overfull \\\\hbox: {compile_signals['overfull_hbox']}")
        lines.append(f"- Undefined citations: {compile_signals['undefined_citations']}")
        lines.append(f"- Undefined references: {compile_signals['undefined_references']}")
    lines.append("")
    return lines


def _render_integrity_artifacts(claims: ClaimRegistrySummary | None, project_dir: Path) -> list[str]:
    lines: list[str] = ["## Integrity artifacts (if available)", ""]
    if claims is None:
        lines.append("- Claim registry: (not found)")
    else:
        lines.append(
            f"- Claim registry: total={claims.total}, filled_verdicts={claims.filled_verdicts}, blockers={claims.blockers}"
        )
        if claims.by_verdict:
            preview = ", ".join(f"{k}:{v}" for k, v in list(claims.by_verdict.items())[:MAX_CLAIM_VERDICTS_PREVIEW])
            lines.append(f"- Verdicts (subset): {preview}")

    bib_audit = project_dir / "notes" / "bibtex-audit.md"
    if bib_audit.exists():
        lines.append("- BibTeX audit: notes/bibtex-audit.md")
    else:
        lines.append("- BibTeX audit: (not found)")

    lines.append("- Recommended gate: `python3 scripts/integrity_gate.py --project-dir <paper_dir> --stage pre-review`")
    lines.append("")
    return lines


def _render_privacy_gate() -> list[str]:
    return [
        "## Privacy gate",
        "",
        "- Must pass: `python3 scripts/paper_privacy_scan.py --project-dir <paper_dir>`",
        "",
    ]


def build_markdown(
    *,
    project_name: str,
    outline: dict[str, list[str]],
    issues: IssuesSummary | None,
    citation_stats: dict,
    bib_stats: dict,
    compile_signals: dict[str, int] | None,
    claim_registry: ClaimRegistrySummary | None,
    project_dir: Path,
) -> str:
    chunks: list[list[str]] = [
        _render_header(project_name),
        _render_draft_structure(outline),
        _render_issues(issues),
        _render_citations_and_bib(citation_stats, bib_stats),
        _render_integrity_artifacts(claim_registry, project_dir),
        _render_compile_signals(compile_signals),
        _render_privacy_gate(),
    ]

    lines: list[str] = []
    for chunk in chunks:
        lines.extend(chunk)
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parsed = parse_args()
    if isinstance(parsed, int):
        return parsed

    project_dir = parsed
    tex_text = (project_dir / "main.tex").read_text(encoding="utf-8", errors="replace")

    outline = extract_outline(tex_text)
    issues = summarize_issues(project_dir)
    citation_stats = count_citations(project_dir / "main.tex")
    bib_stats = count_bibtex_entries(project_dir / "ref.bib")
    compile_signals = summarize_compile_signals(project_dir)
    claim_registry = summarize_claim_registry(project_dir)

    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    out_path = notes_dir / "review-context.md"
    out_path.write_text(
        build_markdown(
            project_name=project_dir.name,
            outline=outline,
            issues=issues,
            citation_stats=citation_stats,
            bib_stats=bib_stats,
            compile_signals=compile_signals,
            claim_registry=claim_registry,
            project_dir=project_dir,
        ),
        encoding="utf-8",
    )
    print(f"Created: notes/review-context.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
