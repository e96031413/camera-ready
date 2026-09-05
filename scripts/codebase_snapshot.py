#!/usr/bin/env python3
"""Generate a codebase snapshot for a paper project (codebase-grounded workflow).

Outputs:
  - <project-dir>/notes/codebase-snapshot.md
  - <project-dir>/notes/codebase-snapshot.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from codebase_snapshot_core import SnapshotConfig, build_snapshot
from codebase_snapshot_render import render_snapshot_markdown


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def parse_args() -> SnapshotConfig | int:
    parser = argparse.ArgumentParser(description="Generate notes/codebase-snapshot.md for a paper project.")
    parser.add_argument("--codebase-dir", required=True, help="Project codebase directory to scan.")
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Paper project directory (output root; will write into <project-dir>/notes/).",
    )
    args = parser.parse_args()

    codebase_dir = Path(args.codebase_dir).expanduser().resolve()
    project_dir = Path(args.project_dir).expanduser().resolve()

    if not codebase_dir.exists():
        return fail(f"codebase dir not found: {codebase_dir}")
    if not codebase_dir.is_dir():
        return fail(f"codebase dir is not a directory: {codebase_dir}")
    if not project_dir.exists():
        return fail(f"project dir not found: {project_dir}")
    if not project_dir.is_dir():
        return fail(f"project dir is not a directory: {project_dir}")

    return SnapshotConfig(codebase_dir=codebase_dir, project_dir=project_dir)


def write_outputs(project_dir: Path, snapshot: dict) -> Path:
    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    md_path = notes_dir / "codebase-snapshot.md"
    json_path = notes_dir / "codebase-snapshot.json"

    md_path.write_text(render_snapshot_markdown(snapshot), encoding="utf-8")
    json_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return md_path


def main() -> int:
    parsed = parse_args()
    if isinstance(parsed, int):
        return parsed

    config = parsed
    snapshot = build_snapshot(config)
    md_path = write_outputs(config.project_dir, snapshot)
    print(f"Created: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

