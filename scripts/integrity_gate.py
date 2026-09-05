#!/usr/bin/env python3
"""Integrity gate runner (pre-review + final).

This script provides a *checkable* gate for:
- privacy scan (no internal URLs / abs paths / secrets)
- BibTeX audit (duplicates + recency threshold)
- claim registry completion + blocker verdicts

It does not verify claims automatically; it enforces that the verification work
is *recorded* in the claim registry and that no blocking verdicts remain.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


_VERDICT_BLOCKERS = {"MAJOR_DISTORTION", "UNVERIFIABLE"}


@dataclass(frozen=True)
class ClaimGateSummary:
    total: int
    filled: int
    blockers: int


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def scripts_dir() -> Path:
    return skill_root() / "scripts"


def run_script(script_name: str, args: list[str]) -> int:
    # Use a relative script path to avoid leaking absolute paths in tracebacks.
    script_rel = str(Path("scripts") / script_name)
    cmd = [sys.executable, script_rel] + args
    proc = subprocess.run(cmd, cwd=str(skill_root()))
    return proc.returncode


def _split_md_table_row(line: str) -> list[str]:
    # Split on unescaped pipes, preserving escaped "\|" inside cells.
    if not line.strip().startswith("|"):
        return []
    s = line.strip()
    cells: list[str] = []
    buf: list[str] = []
    prev = ""
    for ch in s:
        if ch == "|" and prev != "\\":
            cell = "".join(buf).strip()
            cells.append(cell)
            buf = []
        else:
            buf.append(ch)
        prev = ch
    # Drop leading/trailing empty cells from "| ... |"
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    # Unescape "\|" back to "|"
    return [c.replace("\\|", "|").strip() for c in cells]


def summarize_claim_registry(project_dir: Path) -> ClaimGateSummary | None:
    notes_dir = project_dir / "notes"
    csv_path = notes_dir / "claim-registry.csv"
    md_path = notes_dir / "claim-registry.md"

    rows: list[dict[str, str]] = []
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append({k: (v or "").strip() for k, v in row.items()})
    elif md_path.exists():
        text = md_path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if not line.strip().startswith("|"):
                continue
            # Skip header separators
            if re.match(r"^\|\s*-+\s*\|", line):
                continue
            cells = _split_md_table_row(line)
            if len(cells) < 6:
                continue
            if cells[0].strip().upper() == "ID":
                continue
            rows.append(
                {
                    "ID": cells[0],
                    "Section": cells[1],
                    "Claim": cells[2],
                    "Citations_Evidence": cells[3],
                    "Verdict": cells[4],
                    "Notes": cells[5],
                }
            )
    else:
        return None

    data_rows = [r for r in rows if (r.get("ID") or "").strip()]
    total = len(data_rows)
    filled = 0
    blockers = 0
    for r in data_rows:
        verdict = (r.get("Verdict") or "").strip()
        if verdict:
            filled += 1
        if verdict.upper() in _VERDICT_BLOCKERS:
            blockers += 1
    return ClaimGateSummary(total=total, filled=filled, blockers=blockers)


def required_sample_count(total: int, *, sample_ratio: float, min_sample: int) -> int:
    if total <= 0:
        return 0
    if total <= min_sample:
        return total
    return max(min_sample, int(math.ceil(total * sample_ratio)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run integrity gate checks for a paper project.")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Paper project directory (default: .).",
    )
    parser.add_argument(
        "--stage",
        default="pre-review",
        choices=["pre-review", "final"],
        help="Gate stage: pre-review (Stage 2.5) or final (Stage 4.5).",
    )
    parser.add_argument(
        "--sample-ratio",
        type=float,
        default=0.30,
        help="Pre-review required verification ratio (default: 0.30).",
    )
    parser.add_argument(
        "--min-sample",
        type=int,
        default=10,
        help="Pre-review minimum verified claims (default: 10).",
    )
    parser.add_argument(
        "--window-years",
        type=int,
        default=3,
        help="Recent window for BibTeX audit (default: 3).",
    )
    parser.add_argument(
        "--min-recent-ratio",
        type=float,
        default=0.70,
        help="Minimum recent ratio (total entries) for BibTeX audit (default: 0.70).",
    )
    parser.add_argument(
        "--skip-privacy-scan",
        action="store_true",
        help="Skip paper_privacy_scan.py (not recommended).",
    )
    parser.add_argument(
        "--skip-bibtex-audit",
        action="store_true",
        help="Skip bibtex_audit.py (not recommended).",
    )
    parser.add_argument(
        "--skip-claim-registry",
        action="store_true",
        help="Skip claim registry checks (not recommended).",
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

    if args.sample_ratio <= 0 or args.sample_ratio > 1:
        return fail("--sample-ratio must be in (0, 1]")
    if args.min_sample < 0:
        return fail("--min-sample must be >= 0")

    stage = args.stage
    ok = True

    print(f"Integrity gate: stage={stage}")

    if not args.skip_privacy_scan:
        print("- Running privacy scan...")
        code = run_script("paper_privacy_scan.py", ["--project-dir", str(project_dir)])
        if code != 0:
            ok = False
    else:
        print("- Privacy scan: SKIPPED")

    if not args.skip_bibtex_audit:
        print("- Running BibTeX audit...")
        bib_args = [
            "--project-dir",
            str(project_dir),
            "--window-years",
            str(int(args.window_years)),
            "--min-recent-ratio",
            str(float(args.min_recent_ratio)),
            "--fail-on-duplicate-keys",
            "--overwrite",
        ]
        if stage == "final":
            bib_args.append("--fail-on-missing-year")
        code = run_script("bibtex_audit.py", bib_args)
        if code != 0:
            ok = False
    else:
        print("- BibTeX audit: SKIPPED")

    if not args.skip_claim_registry:
        summary = summarize_claim_registry(project_dir)
        if summary is None:
            print("- Claim registry: MISSING (generate with claim_registry.py --write-csv)")
            ok = False
        else:
            required = (
                summary.total
                if stage == "final"
                else required_sample_count(summary.total, sample_ratio=float(args.sample_ratio), min_sample=int(args.min_sample))
            )
            print(
                f"- Claim registry: total={summary.total}, filled_verdicts={summary.filled}, blockers={summary.blockers}, required={required}"
            )
            if summary.blockers > 0:
                ok = False
            if summary.filled < required:
                ok = False
    else:
        print("- Claim registry: SKIPPED")

    if ok:
        print("Integrity gate: PASS")
        return 0
    print("Integrity gate: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
