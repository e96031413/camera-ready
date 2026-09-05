#!/usr/bin/env python3
"""Audit ref.bib for duplicates, missing years, and recency ratio.

Outputs:
  - <project-dir>/notes/bibtex-audit.md

Design goals:
- stdlib-only, deterministic output
- does not print absolute filesystem paths
- supports optional gating via exit codes (threshold flags)
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from paper_utils import now_iso, check_refined_guard


_ENTRY_START_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)
_YEAR_RE = re.compile(r"(?im)\byear\s*=\s*[{\"']?\s*(\d{4})\s*[}\"']?")

_FRONTMATTER_BOUNDARY_RE = re.compile(r"^\s*---\s*$")
_FRONTMATTER_TIMESTAMP_RE = re.compile(r"^\s*timestamp\s*:\s*(.+?)\s*$")


@dataclass(frozen=True)
class BibEntry:
    key: str
    year: int | None


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _find_latest_file(directory: Path, *, suffix: str) -> Path | None:
    if not directory.exists():
        return None
    candidates = sorted(p for p in directory.glob(f"*{suffix}") if p.is_file())
    return candidates[-1] if candidates else None


def _strip_yaml_quotes(value: str) -> str:
    v = value.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1].strip()
    return v


def infer_as_of_year(project_dir: Path) -> int:
    plan_dir = project_dir / "plan"
    latest_plan = _find_latest_file(plan_dir, suffix=".md")
    if latest_plan is None:
        return datetime.now().astimezone().year

    text = latest_plan.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    # Parse YAML frontmatter only (first --- ... --- block)
    if not lines or not _FRONTMATTER_BOUNDARY_RE.match(lines[0]):
        return datetime.now().astimezone().year

    in_frontmatter = True
    for line in lines[1:]:
        if _FRONTMATTER_BOUNDARY_RE.match(line):
            break
        if not in_frontmatter:
            continue
        m = _FRONTMATTER_TIMESTAMP_RE.match(line)
        if not m:
            continue
        ts = _strip_yaml_quotes(m.group(1))
        if re.match(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$", ts):
            return int(ts[:4])
        if re.match(r"^\d{4}-\d{2}-\d{2}", ts):
            return int(ts[:4])
        break

    return datetime.now().astimezone().year


def parse_bib_entries(bib_text: str) -> list[BibEntry]:
    entries: list[BibEntry] = []
    starts = list(_ENTRY_START_RE.finditer(bib_text))
    if not starts:
        return entries

    for idx, m in enumerate(starts):
        key = m.group(1).strip()
        start = m.start()
        end = starts[idx + 1].start() if idx + 1 < len(starts) else len(bib_text)
        chunk = bib_text[start:end]
        year_match = _YEAR_RE.search(chunk)
        year = int(year_match.group(1)) if year_match else None
        if key:
            entries.append(BibEntry(key=key, year=year))
    return entries


def compute_recent_ratio(entries: list[BibEntry], *, as_of_year: int, window_years: int) -> dict:
    total = len(entries)
    years = [e.year for e in entries if e.year is not None]
    with_year = len(years)
    missing_year = total - with_year
    if window_years <= 0:
        threshold = as_of_year
    else:
        threshold = as_of_year - window_years + 1
    recent = sum(1 for y in years if y >= threshold)
    ratio_total = (recent / total) if total > 0 else 0.0
    ratio_known = (recent / with_year) if with_year > 0 else 0.0
    return {
        "threshold_year": threshold,
        "recent": recent,
        "ratio_total": ratio_total,
        "ratio_known": ratio_known,
        "missing_year": missing_year,
        "with_year": with_year,
        "total": total,
    }


def render_report(
    *,
    created_at: str,
    as_of_year: int,
    window_years: int,
    min_recent_ratio: float | None,
    entries: list[BibEntry],
    duplicates: list[str],
    missing_year_keys: list[str],
) -> str:
    years_counter: Counter[int] = Counter(e.year for e in entries if e.year is not None)
    year_items = sorted(years_counter.items(), key=lambda kv: (-kv[0], kv[1]))
    stats = compute_recent_ratio(entries, as_of_year=as_of_year, window_years=window_years)
    threshold = stats["threshold_year"]
    ratio_total = stats["ratio_total"]
    ratio_known = stats["ratio_known"]

    lines: list[str] = [
        "# BibTeX Audit",
        "",
        f"- Created at: {created_at}",
        f"- As-of year: {as_of_year}",
        f"- Recent window (years): {window_years} (threshold: ≥ {threshold})",
    ]
    if min_recent_ratio is not None:
        lines.append(f"- Min recent ratio (total): {min_recent_ratio:.2f}")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Total entries: {stats['total']}",
            f"- Entries with year: {stats['with_year']}",
            f"- Missing year: {stats['missing_year']}",
            f"- Duplicate keys: {len(duplicates)}",
            f"- Recent entries (≥ {threshold}): {stats['recent']}",
            f"- Recent ratio (total): {ratio_total:.3f}",
            f"- Recent ratio (known-year only): {ratio_known:.3f}",
            "",
        ]
    )

    if duplicates:
        lines.extend(["## Duplicate keys", ""] + [f"- `{k}`" for k in duplicates] + [""])
    else:
        lines.extend(["## Duplicate keys", "", "- (none)", ""])

    if missing_year_keys:
        lines.extend(["## Missing year", ""] + [f"- `{k}`" for k in missing_year_keys] + [""])
    else:
        lines.extend(["## Missing year", "", "- (none)", ""])

    lines.append("## By year (descending)")
    lines.append("")
    if year_items:
        for year, count in year_items[:24]:
            lines.append(f"- {year}: {count}")
    else:
        lines.append("- (no year fields detected)")
    lines.append("")

    lines.append("## Recommendations")
    lines.append("")
    lines.append("- Fix duplicate BibTeX keys (merge or rename keys).")
    lines.append("- Ensure every entry has a `year` field.")
    lines.append("- Improve recency ratio by adding recent, high-quality sources where appropriate.")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit ref.bib (duplicates, missing years, recency).")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Paper project directory containing ref.bib and plan/ (default: .).",
    )
    parser.add_argument(
        "--as-of-year",
        type=int,
        help="Override as-of year (default: infer from latest plan frontmatter; else current year).",
    )
    parser.add_argument(
        "--window-years",
        type=int,
        default=3,
        help="Recent window size in years (default: 3).",
    )
    parser.add_argument(
        "--min-recent-ratio",
        type=float,
        help="If set, fail when recent ratio (total entries) is below this value (0..1).",
    )
    parser.add_argument(
        "--fail-on-duplicate-keys",
        action="store_true",
        help="Fail if duplicate BibTeX keys are found.",
    )
    parser.add_argument(
        "--fail-on-missing-year",
        action="store_true",
        help="Fail if any entry is missing a year field.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite notes/bibtex-audit.md if present.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        return fail("project dir not found")
    if not project_dir.is_dir():
        return fail("project dir is not a directory")

    bib_path = project_dir / "ref.bib"
    if not bib_path.exists():
        return fail("ref.bib not found in project dir")

    as_of_year = int(args.as_of_year) if args.as_of_year else infer_as_of_year(project_dir)
    window_years = int(args.window_years)
    if window_years <= 0:
        return fail("--window-years must be >= 1")

    bib_text = bib_path.read_text(encoding="utf-8", errors="replace")
    entries = parse_bib_entries(bib_text)

    key_counts = Counter(e.key for e in entries)
    duplicates = sorted([k for k, c in key_counts.items() if c > 1])
    missing_year_keys = sorted([e.key for e in entries if e.year is None])

    min_recent_ratio = args.min_recent_ratio
    if min_recent_ratio is not None and not (0.0 <= min_recent_ratio <= 1.0):
        return fail("--min-recent-ratio must be in [0, 1]")

    report = render_report(
        created_at=now_iso(),
        as_of_year=as_of_year,
        window_years=window_years,
        min_recent_ratio=min_recent_ratio,
        entries=entries,
        duplicates=duplicates,
        missing_year_keys=missing_year_keys,
    )

    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    out_path = notes_dir / "bibtex-audit.md"
    if out_path.exists() and not args.overwrite:
        return fail("notes/bibtex-audit.md already exists (use --overwrite to replace)")

    # Refinement marker guard
    if not check_refined_guard(out_path, force=args.overwrite):
        return 1

    out_path.write_text(report, encoding="utf-8")

    stats = compute_recent_ratio(entries, as_of_year=as_of_year, window_years=window_years)
    ok = True
    if args.fail_on_duplicate_keys and duplicates:
        ok = False
    if args.fail_on_missing_year and missing_year_keys:
        ok = False
    if min_recent_ratio is not None and stats["ratio_total"] < min_recent_ratio:
        ok = False

    print(
        "Created: notes/bibtex-audit.md "
        f"(entries={stats['total']}, duplicates={len(duplicates)}, missing_year={stats['missing_year']}, recent_ratio_total={stats['ratio_total']:.3f})"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

