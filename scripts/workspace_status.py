#!/usr/bin/env python3
"""Generate a human-readable status summary for a paper project workspace.

Scans the issues CSV, notes artifacts, and main.tex to produce a structured
workspace status report at notes/STATUS.md.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from paper_utils import count_bibtex_entries, count_citations, now_iso

# Valid statuses (matches validate_paper_issues.py)
_STATUSES = ("TODO", "DOING", "DONE", "SKIP")

# 10-column header (original format)
_HEADER_10 = [
    "ID", "Phase", "Title", "Description", "Target_Citations",
    "Visualization", "Acceptance", "Status", "Verified_Citations", "Notes",
]
# 12-column header (extended format with Depends_On, Owner)
_HEADER_12 = _HEADER_10 + ["Depends_On", "Owner"]


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Issues CSV parsing
# ---------------------------------------------------------------------------

def find_latest_csv(issues_dir: Path) -> Path | None:
    """Return the latest CSV file in the issues directory (by name sort)."""
    if not issues_dir.is_dir():
        return None
    csvs = sorted(issues_dir.glob("*.csv"))
    return csvs[-1] if csvs else None


def parse_issues(csv_path: Path) -> dict:
    """Parse an issues CSV and return status/phase counts.

    Returns
    -------
    dict with keys:
        status_counts : dict[str, int]   – per-status totals
        phase_status  : dict[str, dict[str, int]] – per-phase per-status
        total         : int
    """
    status_counts: dict[str, int] = {s: 0 for s in _STATUSES}
    phase_status: dict[str, dict[str, int]] = {}

    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        rows = [r for r in reader if any(c.strip() for c in r)]

    if not rows:
        return {"status_counts": status_counts, "phase_status": phase_status, "total": 0}

    header = rows[0]
    ncols = len(header)

    # Determine column indices flexibly
    if ncols >= 12 and header[:12] == _HEADER_12:
        status_idx = 7
        phase_idx = 1
    elif ncols >= 10 and header[:10] == _HEADER_10:
        status_idx = 7
        phase_idx = 1
    else:
        # Fallback: try to find by header name
        try:
            status_idx = header.index("Status")
            phase_idx = header.index("Phase")
        except ValueError:
            return {"status_counts": status_counts, "phase_status": phase_status, "total": 0}

    for row in rows[1:]:
        if len(row) <= max(status_idx, phase_idx):
            continue
        status = row[status_idx].strip()
        phase = row[phase_idx].strip()

        if status in status_counts:
            status_counts[status] += 1

        if phase not in phase_status:
            phase_status[phase] = {s: 0 for s in _STATUSES}
        if status in phase_status[phase]:
            phase_status[phase][status] += 1

    total = sum(status_counts.values())
    return {"status_counts": status_counts, "phase_status": phase_status, "total": total}


# ---------------------------------------------------------------------------
# LaTeX metrics
# ---------------------------------------------------------------------------

def parse_tex_metrics(content: str) -> dict:
    """Extract section/figure/table counts from LaTeX content."""
    sections = re.findall(r"\\section\{([^}]+)\}", content)
    subsections = re.findall(r"\\subsection\{([^}]+)\}", content)
    figure_count = len(re.findall(r"\\begin\{figure\*?\}", content))
    table_count = len(re.findall(r"\\begin\{table\*?\}", content))
    return {
        "sections": len(sections),
        "subsections": len(subsections),
        "figures": figure_count,
        "tables": table_count,
    }


# ---------------------------------------------------------------------------
# Artifact detection
# ---------------------------------------------------------------------------

def _check_dir(path: Path, glob_pattern: str) -> tuple[bool, int]:
    """Return (exists, file_count) for a directory with a glob filter."""
    if not path.is_dir():
        return False, 0
    files = list(path.glob(glob_pattern))
    return len(files) > 0, len(files)


def detect_artifacts(project_dir: Path) -> list[tuple[str, bool]]:
    """Check existence of expected artifacts.

    Returns a list of (display_label, exists) tuples.
    """
    artifacts: list[tuple[str, bool]] = []

    # main.tex
    artifacts.append(("main.tex", (project_dir / "main.tex").exists()))

    # ref.bib
    artifacts.append(("ref.bib", (project_dir / "ref.bib").exists()))

    # plan/ directory
    plan_exists, plan_count = _check_dir(project_dir / "plan", "*.md")
    artifacts.append((f"plan/ ({plan_count} file{'s' if plan_count != 1 else ''})", plan_exists))

    # issues/ directory
    issues_exists, issues_count = _check_dir(project_dir / "issues", "*.csv")
    artifacts.append((f"issues/ ({issues_count} file{'s' if issues_count != 1 else ''})", issues_exists))

    # notes/ individual files
    artifacts.append(("notes/literature-notes.md", (project_dir / "notes" / "literature-notes.md").exists()))

    # claim-registry: .md or .csv
    claim_exists = (
        (project_dir / "notes" / "claim-registry.md").exists()
        or (project_dir / "notes" / "claim-registry.csv").exists()
    )
    artifacts.append(("notes/claim-registry.md", claim_exists))

    artifacts.append(("notes/bibtex-audit.md", (project_dir / "notes" / "bibtex-audit.md").exists()))
    artifacts.append(("notes/self-review.md", (project_dir / "notes" / "self-review.md").exists()))
    artifacts.append(("notes/anti-ai-report.md", (project_dir / "notes" / "anti-ai-report.md").exists()))

    # evidence-packs/
    ep_exists, ep_count = _check_dir(project_dir / "notes" / "evidence-packs", "*.json")
    artifacts.append((
        f"notes/evidence-packs/ ({ep_count} pack{'s' if ep_count != 1 else ''})",
        ep_exists,
    ))

    artifacts.append(("notes/logic-selfloop.md", (project_dir / "notes" / "logic-selfloop.md").exists()))
    artifacts.append(("notes/argument-selfloop.md", (project_dir / "notes" / "argument-selfloop.md").exists()))
    artifacts.append(("notes/voice-selfloop.md", (project_dir / "notes" / "voice-selfloop.md").exists()))
    artifacts.append(("notes/STATUS.md", (project_dir / "notes" / "STATUS.md").exists()))

    # slides/
    slides_dir = project_dir / "slides"
    artifacts.append(("slides/", slides_dir.is_dir() and any(slides_dir.iterdir())))

    return artifacts


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_status_md(
    *,
    timestamp: str,
    issues: dict | None,
    tex_metrics: dict | None,
    cite_info: dict,
    bib_info: dict,
    artifacts: list[tuple[str, bool]],
) -> str:
    """Render the full STATUS.md content."""
    lines: list[str] = [
        "# Workspace Status",
        f"Generated: {timestamp}",
        "",
    ]

    # -- Progress ----------------------------------------------------------
    lines.append("## Progress")
    if issues is not None and issues["total"] > 0:
        sc = issues["status_counts"]
        total = issues["total"]
        done = sc["DONE"]
        doing = sc["DOING"]
        todo = sc["TODO"]
        skip = sc["SKIP"]
        completion = (done / total * 100) if total > 0 else 0.0
        lines.append(
            f"- Issues: {done} DONE / {doing} DOING / {todo} TODO / {skip} SKIP (total: {total})"
        )
        lines.append(f"- Completion: {completion:.1f}%")
    else:
        lines.append("- Issues: (no issues CSV found)")
    lines.append("")

    # -- Paper Metrics -----------------------------------------------------
    lines.append("## Paper Metrics")
    if tex_metrics is not None:
        lines.append(f"- Sections: {tex_metrics['sections']}")
        lines.append(f"- Subsections: {tex_metrics['subsections']}")
        lines.append(f"- Figures: {tex_metrics['figures']}")
        lines.append(f"- Tables: {tex_metrics['tables']}")
    else:
        lines.append("- (main.tex not found)")

    lines.append(
        f"- Citations (in text): {cite_info['total']} total, {cite_info['unique']} unique"
    )
    lines.append(f"- BibTeX entries: {bib_info['total']}")
    lines.append("")

    # -- Artifacts ---------------------------------------------------------
    lines.append("## Artifacts")
    for label, exists in artifacts:
        mark = "x" if exists else " "
        lines.append(f"- [{mark}] {label}")
    lines.append("")

    # -- Issues by Phase ---------------------------------------------------
    if issues is not None and issues["phase_status"]:
        lines.append("## Issues by Phase")
        lines.append("| Phase | TODO | DOING | DONE | SKIP |")
        lines.append("|-------|------|-------|------|------|")
        for phase in sorted(issues["phase_status"]):
            ps = issues["phase_status"][phase]
            lines.append(
                f"| {phase} | {ps['TODO']} | {ps['DOING']} | {ps['DONE']} | {ps['SKIP']} |"
            )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    """Generate notes/STATUS.md for a paper workspace."""
    parser = argparse.ArgumentParser(
        description="Generate a workspace status summary (notes/STATUS.md).",
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Paper project directory.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        # Informational tool – print a warning but still exit 0
        print(f"warning: project dir not found: {project_dir}", file=sys.stderr)
        return 0

    timestamp = now_iso()

    # -- Issues ------------------------------------------------------------
    issues_dir = project_dir / "issues"
    csv_path = find_latest_csv(issues_dir)
    issues: dict | None = None
    if csv_path is not None:
        try:
            issues = parse_issues(csv_path)
        except Exception as exc:  # noqa: BLE001
            print(f"warning: failed to parse {csv_path.name}: {exc}", file=sys.stderr)

    # -- TeX metrics -------------------------------------------------------
    main_tex = project_dir / "main.tex"
    tex_metrics: dict | None = None
    if main_tex.exists():
        content = main_tex.read_text(encoding="utf-8", errors="replace")
        tex_metrics = parse_tex_metrics(content)

    # -- Citations / BibTeX ------------------------------------------------
    cite_info = count_citations(main_tex)
    bib_info = count_bibtex_entries(project_dir / "ref.bib")

    # -- Artifacts ---------------------------------------------------------
    artifacts = detect_artifacts(project_dir)

    # -- Generate & write --------------------------------------------------
    report = generate_status_md(
        timestamp=timestamp,
        issues=issues,
        tex_metrics=tex_metrics,
        cite_info=cite_info,
        bib_info=bib_info,
        artifacts=artifacts,
    )

    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    status_path = notes_dir / "STATUS.md"
    status_path.write_text(report, encoding="utf-8")

    print(f"Status written to: notes/STATUS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
