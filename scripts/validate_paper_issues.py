#!/usr/bin/env python3
"""Validate paper issues CSV schema and required fields.

Supports both the legacy 10-column format and the enhanced 12-column format
(with Depends_On and Owner columns).  Use --legacy to accept old-format CSVs.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REQUIRED_COLUMNS = [
    "ID",
    "Phase",
    "Title",
    "Description",
    "Target_Citations",
    "Visualization",
    "Acceptance",
    "Status",
    "Verified_Citations",
    "Notes",
    "Depends_On",
    "Owner",
]

LEGACY_COLUMNS = [
    "ID",
    "Phase",
    "Title",
    "Description",
    "Target_Citations",
    "Visualization",
    "Acceptance",
    "Status",
    "Verified_Citations",
    "Notes",
]

ALLOWED_STATUS = {"TODO", "DOING", "DONE", "SKIP"}
ALLOWED_PHASES = {
    "Research", "Writing", "Integrity", "Review", "Refinement",
    "QA", "Ideation", "Slides", "Evidence", "SelfReview",
    "Post-Acceptance", "Video", "Poster",
}
ALLOWED_OWNERS = {"AI", "HUMAN", "BOTH", ""}


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def detect_dependency_cycle(deps: dict[str, list[str]]) -> list[str] | None:
    """Detect cycles in the dependency graph using DFS.

    Returns the cycle path if found, None otherwise.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in deps}
    parent: dict[str, str | None] = {node: None for node in deps}

    def dfs(u: str) -> list[str] | None:
        color[u] = GRAY
        for v in deps.get(u, []):
            if v not in color:
                continue
            if color[v] == GRAY:
                # Back edge → cycle found; reconstruct path
                cycle = [v, u]
                cur = u
                while cur != v:
                    cur = parent[cur]  # type: ignore[assignment]
                    if cur is None:
                        break
                    cycle.append(cur)
                cycle.reverse()
                return cycle
            if color[v] == WHITE:
                parent[v] = u
                result = dfs(v)
                if result is not None:
                    return result
        color[u] = BLACK
        return None

    for node in deps:
        if color[node] == WHITE:
            result = dfs(node)
            if result is not None:
                return result
    return None


USAGE = """usage: validate_paper_issues.py <issues.csv> [--strict] [--legacy]

Validate paper issues CSV schema and required fields.

Arguments:
  issues.csv    Path to the issues CSV file to validate.

Options:
  --strict      Treat non-numeric citation counts as warnings (reported).
  --legacy      Accept the legacy 10-column format (without Depends_On/Owner).
  -h, --help    Show this help message and exit.
"""


def main() -> int:
    if "-h" in sys.argv or "--help" in sys.argv:
        print(USAGE)
        return 0

    if len(sys.argv) < 2:
        return fail("usage: validate_paper_issues.py <issues.csv> [--strict] [--legacy]")

    path = Path(sys.argv[1])
    strict = "--strict" in sys.argv
    legacy = "--legacy" in sys.argv

    if not path.exists():
        return fail(f"file not found: {path}")

    rows: list[list[str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if any(cell.strip() for cell in row):
                rows.append(row)

    if not rows:
        return fail("csv is empty")

    header = rows[0]
    expected = LEGACY_COLUMNS if legacy else REQUIRED_COLUMNS

    if header == LEGACY_COLUMNS and not legacy:
        warn("detected legacy 10-column format; pass --legacy to suppress this warning")
        legacy = True
        expected = LEGACY_COLUMNS

    if header != expected:
        return fail(
            "invalid header. expected: "
            + ",".join(expected)
            + " | got: "
            + ",".join(header)
        )

    seen_ids: set[str] = set()
    total_target_citations = 0
    total_verified_citations = 0
    status_counts = {"TODO": 0, "DOING": 0, "DONE": 0, "SKIP": 0}
    phase_counts: dict[str, int] = {}
    dependency_graph: dict[str, list[str]] = {}
    errors = 0
    warnings = 0

    for idx, row in enumerate(rows[1:], start=2):
        if len(row) != len(expected):
            print(f"error: row {idx}: expected {len(expected)} columns, got {len(row)}", file=sys.stderr)
            errors += 1
            continue

        row_data = dict(zip(expected, row))

        # Check required fields
        for col in ["ID", "Phase", "Title", "Description", "Acceptance", "Status"]:
            if not row_data[col].strip():
                print(f"error: row {idx}: '{col}' is empty", file=sys.stderr)
                errors += 1

        # Validate Status
        status = row_data["Status"].strip()
        if status not in ALLOWED_STATUS:
            print(f"error: row {idx}: 'Status' must be one of {sorted(ALLOWED_STATUS)}, got '{status}'", file=sys.stderr)
            errors += 1
        else:
            status_counts[status] += 1

        # Validate Phase
        phase = row_data["Phase"].strip()
        if phase not in ALLOWED_PHASES:
            print(f"error: row {idx}: 'Phase' must be one of {sorted(ALLOWED_PHASES)}, got '{phase}'", file=sys.stderr)
            errors += 1
        else:
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        # Check for duplicate IDs
        issue_id = row_data["ID"].strip()
        if issue_id in seen_ids:
            print(f"error: row {idx}: duplicate ID '{issue_id}'", file=sys.stderr)
            errors += 1
        seen_ids.add(issue_id)

        # Parse citation counts
        try:
            target = int(row_data["Target_Citations"].strip())
            total_target_citations += target
        except ValueError:
            if strict:
                print(f"warning: row {idx}: 'Target_Citations' is not a number", file=sys.stderr)
                warnings += 1

        try:
            verified = int(row_data["Verified_Citations"].strip())
            total_verified_citations += verified
        except ValueError:
            if strict:
                print(f"warning: row {idx}: 'Verified_Citations' is not a number", file=sys.stderr)
                warnings += 1

        # --- Enhanced columns (non-legacy) ---
        if not legacy:
            # Validate Owner
            owner = row_data.get("Owner", "").strip()
            if owner and owner not in ALLOWED_OWNERS:
                print(
                    f"error: row {idx}: 'Owner' must be one of {sorted(o for o in ALLOWED_OWNERS if o)}"
                    f" (or empty), got '{owner}'",
                    file=sys.stderr,
                )
                errors += 1

            # Parse Depends_On
            depends_raw = row_data.get("Depends_On", "").strip()
            dep_ids: list[str] = []
            if depends_raw:
                dep_ids = [d.strip() for d in depends_raw.split(";") if d.strip()]
            dependency_graph[issue_id] = dep_ids

    # --- Post-row validation (enhanced only) ---
    if not legacy and dependency_graph:
        # Check that all referenced dependency IDs exist
        for issue_id, deps in dependency_graph.items():
            for dep_id in deps:
                if dep_id not in seen_ids:
                    print(
                        f"error: ID '{issue_id}' depends on '{dep_id}' which does not exist",
                        file=sys.stderr,
                    )
                    errors += 1

        # Cycle detection
        cycle = detect_dependency_cycle(dependency_graph)
        if cycle is not None:
            cycle_str = " -> ".join(cycle)
            print(f"error: dependency cycle detected: {cycle_str}", file=sys.stderr)
            errors += 1

    if errors > 0:
        print(f"\nValidation failed with {errors} error(s).", file=sys.stderr)
        return 1

    # Print summary
    print("Validation passed!")
    print(f"\nSummary:")
    print(f"  Total issues: {len(rows) - 1}")
    print(f"  Format: {'legacy (10-col)' if legacy else 'enhanced (12-col)'}")
    phase_parts = [f"{k}={v}" for k, v in sorted(phase_counts.items()) if v > 0]
    print(f"  By phase: {', '.join(phase_parts) if phase_parts else '(none)'}")
    print(f"  By status: TODO={status_counts['TODO']}, DOING={status_counts['DOING']}, DONE={status_counts['DONE']}, SKIP={status_counts['SKIP']}")
    print(f"  Target citations: {total_target_citations}")
    print(f"  Verified citations: {total_verified_citations}")

    if total_target_citations > 0:
        progress = (total_verified_citations / total_target_citations) * 100
        print(f"  Citation progress: {progress:.1f}%")

    if status_counts["DONE"] > 0:
        completion = (status_counts["DONE"] / (len(rows) - 1)) * 100
        print(f"  Task completion: {completion:.1f}%")

    if not legacy and dependency_graph:
        dep_count = sum(1 for deps in dependency_graph.values() if deps)
        print(f"  Issues with dependencies: {dep_count}")

    if warnings > 0:
        print(f"\n{warnings} warning(s) found.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
