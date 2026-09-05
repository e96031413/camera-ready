#!/usr/bin/env python3
"""Compare manuscripts from different pipelines on machine-checkable metrics. 2026-09-05-v1.

The open question about gated writing is whether the gates buy anything a
reviewer would notice. Answering it needs the same task run through more than
one pipeline and the outputs measured the same way. This tool measures; it does
not run the pipelines, and it takes no position on which arm should win.

Each arm is a finished paper project directory (main.tex, ref.bib, notes/).
Metrics, all computed from files:

  references            entries in ref.bib
  identified            share of entries carrying an arXiv id or DOI
  placeholders          entries whose key or note marks them unverified
  cited_but_missing     \\cite keys with no entry in ref.bib
  entries_uncited       entries never cited in the manuscript
  verified              share reported VERIFIED by a stored verification run
  hallucinated          entries a stored verification run called hallucinated
  required_sections     share of the discipline's mandatory sections present
  claims_with_verdicts  share of claim-registry rows carrying a verdict
  ai_patterns           count from a stored anti-AI report
  pages                 page count from a compiled main.log

An arm that never ran a gate simply has no report to read, and the metric is
reported as absent rather than as zero. Absent is not a score.

Usage:
  python scripts/benchmark_compare.py --arm gated=runs/gated --arm ungated=runs/ungated
  python scripts/benchmark_compare.py --arm a=path --discipline computer-science --out notes/benchmark.md
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import now_iso

BANNER = "benchmark_compare 2026-09-05-v1"

_BIB_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)
_BIB_ENTRY_RE = re.compile(r"@\w+\s*\{([^,]+),(.*?)(?=\n@|\Z)", re.DOTALL)
_CITE_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}")
_SECTION_RE = re.compile(r"\\section\*?\{([^}]+)\}")
_PAGES_RE = re.compile(r"Output written on .*?\((\d+) pages?", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"PLACEHOLDER_|\[VERIFY\]", re.IGNORECASE)
_VERIFY_ROW_RE = re.compile(r"^\|\s*(VERIFIED|SUSPICIOUS|HALLUCINATED|SKIPPED)\s*\|\s*(\d+)", re.MULTILINE)
_AI_PATTERNS_RE = re.compile(r"(\d+)\s+patterns?", re.IGNORECASE)


@dataclass
class ArmMetrics:
    name: str
    path: str
    values: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def bib_entries(bib_text: str) -> dict[str, str]:
    return {m.group(1).strip(): m.group(2) for m in _BIB_ENTRY_RE.finditer(bib_text)}


def cited_keys(tex_text: str) -> set[str]:
    keys: set[str] = set()
    for match in _CITE_RE.finditer(tex_text):
        for raw in match.group(1).split(","):
            key = raw.strip()
            if key:
                keys.add(key)
    return keys


def verification_counts(report_text: str) -> dict[str, int]:
    """Counts from a citation-verification report's summary table."""
    counts = {k: int(v) for k, v in _VERIFY_ROW_RE.findall(report_text)}
    return counts


def discipline_sections(discipline: str) -> list[str]:
    try:
        from discipline_profile import load_discipline
    except ImportError:
        return []
    try:
        profile = load_discipline(discipline)
    except Exception:
        return []
    sections = profile.get("required_sections")
    return [str(s) for s in sections] if isinstance(sections, list) else []


def measure(name: str, project_dir: Path, discipline: str | None) -> ArmMetrics:
    arm = ArmMetrics(name=name, path=project_dir.name)
    tex_text = read_file(project_dir / "main.tex")
    bib_text = read_file(project_dir / "ref.bib")

    if not tex_text:
        arm.notes.append("no main.tex")
    if not bib_text:
        arm.notes.append("no ref.bib")

    entries = bib_entries(bib_text)
    arm.values["references"] = len(entries)

    if entries:
        identified = sum(
            1
            for body in entries.values()
            if re.search(r"\b(eprint|doi)\s*=", body, re.IGNORECASE)
        )
        arm.values["identified"] = round(identified / len(entries), 3)
        placeholders = sum(1 for key, body in entries.items() if _PLACEHOLDER_RE.search(key + body))
        arm.values["placeholders"] = placeholders

    if tex_text:
        keys = cited_keys(tex_text)
        arm.values["cited_but_missing"] = len(keys - set(entries))
        arm.values["entries_uncited"] = len(set(entries) - keys)

        if discipline:
            required = discipline_sections(discipline)
            if required:
                present = {s.lower() for s in _SECTION_RE.findall(tex_text)}
                has_abstract = "\\begin{abstract}" in tex_text
                found = 0
                for section in required:
                    needle = section.lower()
                    if needle == "abstract" and has_abstract:
                        found += 1
                    elif any(needle in candidate for candidate in present):
                        found += 1
                arm.values["required_sections"] = round(found / len(required), 3)

    verification = read_file(project_dir / "notes" / "citation-verification.md")
    if verification:
        counts = verification_counts(verification)
        total = sum(counts.values())
        if total:
            arm.values["verified"] = round(counts.get("VERIFIED", 0) / total, 3)
            arm.values["hallucinated"] = counts.get("HALLUCINATED", 0)
    else:
        arm.notes.append("no citation-verification report")

    registry = project_dir / "notes" / "claim-registry.csv"
    if registry.is_file():
        rows = list(csv.DictReader(io.StringIO(read_file(registry))))
        if rows:
            filled = sum(1 for r in rows if str(r.get("Verdict", "")).strip())
            arm.values["claims_with_verdicts"] = round(filled / len(rows), 3)
    else:
        arm.notes.append("no claim registry")

    anti_ai = read_file(project_dir / "notes" / "anti-ai-report.md")
    if anti_ai:
        match = _AI_PATTERNS_RE.search(anti_ai)
        if match:
            arm.values["ai_patterns"] = int(match.group(1))
    else:
        arm.notes.append("no anti-AI report")

    log_text = read_file(project_dir / "main.log")
    match = _PAGES_RE.search(log_text)
    if match:
        arm.values["pages"] = int(match.group(1))
    else:
        arm.notes.append("no compiled main.log")

    return arm


METRIC_ORDER = (
    "references",
    "identified",
    "placeholders",
    "cited_but_missing",
    "entries_uncited",
    "verified",
    "hallucinated",
    "required_sections",
    "claims_with_verdicts",
    "ai_patterns",
    "pages",
)


def render_markdown(arms: list[ArmMetrics], discipline: str | None) -> str:
    lines = [
        "# Benchmark Comparison",
        "",
        f"- Created at: {now_iso()}",
        f"- Arms: {len(arms)}",
        f"- Discipline profile: {discipline or 'not set'}",
        "",
        "Every number here is read from files the arms produced. A blank cell",
        "means the arm has no artifact to read, which is a fact about the",
        "pipeline, not a score of zero.",
        "",
        "| Metric | " + " | ".join(a.name for a in arms) + " |",
        "|---" * (len(arms) + 1) + "|",
    ]
    for metric in METRIC_ORDER:
        if not any(metric in a.values for a in arms):
            continue
        cells = []
        for arm in arms:
            value = arm.values.get(metric)
            cells.append("" if value is None else f"{value:g}" if isinstance(value, float) else str(value))
        lines.append(f"| `{metric}` | " + " | ".join(cells) + " |")

    lines += ["", "## What each arm could not be measured on", ""]
    for arm in arms:
        if arm.notes:
            lines.append(f"- **{arm.name}**: " + "; ".join(arm.notes))
        else:
            lines.append(f"- **{arm.name}**: every metric had an artifact behind it")

    lines += [
        "",
        "## What this table does not measure",
        "",
        "Scientific quality, novelty, reviewer judgement and the time a human",
        "spends repairing the draft. A pipeline can win every column here and",
        "still produce a paper nobody should publish. See docs/BENCHMARK.md for",
        "the protocol these numbers belong to.",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure finished paper projects from different pipelines the same way."
    )
    parser.add_argument(
        "--arm",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="An arm to measure. Repeatable.",
    )
    parser.add_argument("--discipline", default=None, help="Discipline profile for section checks.")
    parser.add_argument("--out", default=None, help="Markdown report path (default: notes/benchmark.md).")
    parser.add_argument("--json-out", default=None, help="Also write the raw metrics as JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.arm:
        return fail("provide at least one --arm NAME=PATH")

    arms: list[ArmMetrics] = []
    for spec in args.arm:
        if "=" not in spec:
            return fail(f"malformed --arm {spec!r}; expected NAME=PATH")
        name, _, raw_path = spec.partition("=")
        path = Path(raw_path).expanduser().resolve()
        if not path.is_dir():
            return fail(f"arm {name!r}: not a directory: {raw_path}")
        arms.append(measure(name.strip(), path, args.discipline))

    out_path = Path(args.out) if args.out else Path("notes") / "benchmark.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_markdown(arms, args.discipline), encoding="utf-8")

    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(
                {
                    "created_at": now_iso(),
                    "discipline": args.discipline,
                    "arms": [
                        {"name": a.name, "path": a.path, "metrics": a.values, "unmeasured": a.notes}
                        for a in arms
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Metrics: {json_path.as_posix()}")

    for arm in arms:
        summary = ", ".join(f"{k}={arm.values[k]:g}" if isinstance(arm.values[k], float)
                            else f"{k}={arm.values[k]}" for k in METRIC_ORDER if k in arm.values)
        print(f"  {arm.name}: {summary}")
    print(f"{BANNER}: measured {len(arms)} arm(s)")
    print(f"Report: {out_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
