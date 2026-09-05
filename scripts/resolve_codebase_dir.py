#!/usr/bin/env python3
"""Resolve a codebase directory from a short name (best-effort, explicit failure).

This exists to support prompts like:
  "$camera-ready 根據ai_shorts_agent的內容撰寫一篇論文"

Behavior:
- If --codebase looks like a path, treat it as a path (expanduser+resolve).
- Otherwise, search for a matching directory name under a small set of roots.
- If exactly one match is found, print its absolute path to stdout and exit 0.
- If none or multiple matches are found, exit non-zero with a clear error.

This tool is for local orchestration only. It does not write into the paper.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


SUBDIR_HINTS = ("", "src", "repos", "projects")
DEFAULT_ROOT_NAMES = ("Desktop", "dev", "projects")


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _looks_like_path(value: str) -> bool:
    if not value:
        return False
    return any(token in value for token in (os.sep, "/", "\\", "~", "."))  # accept windows-ish too


def _iter_default_roots() -> list[Path]:
    home = Path.home()
    roots: list[Path] = [Path.cwd(), home]
    for name in DEFAULT_ROOT_NAMES:
        roots.append(home / name)
    return roots


def _collect_candidate_paths(codebase_name: str, roots: list[Path]) -> list[Path]:
    candidates: list[Path] = []
    for root in roots:
        for hint in SUBDIR_HINTS:
            base = root / hint if hint else root
            path = base / codebase_name
            if path.is_dir():
                candidates.append(path.resolve())

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a codebase directory from a short name or path.")
    parser.add_argument(
        "--codebase",
        required=True,
        help="Codebase path or repo folder name (e.g., ai_shorts_agent).",
    )
    parser.add_argument(
        "--roots",
        action="append",
        default=[],
        help="Optional root directories to search (repeatable). If omitted, uses a small default set.",
    )
    args = parser.parse_args()

    raw = args.codebase.strip()
    if not raw:
        return fail("--codebase cannot be empty")

    if _looks_like_path(raw):
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            return fail("codebase path not found")
        if not path.is_dir():
            return fail("codebase path is not a directory")
        print(str(path))
        return 0

    roots = [Path(r).expanduser().resolve() for r in args.roots] if args.roots else _iter_default_roots()
    matches = _collect_candidate_paths(raw, roots)

    if not matches:
        return fail("codebase dir not found; pass a full path or provide --roots")
    if len(matches) > 1:
        print("error: multiple matches found for codebase name:", file=sys.stderr)
        for match in matches:
            print(f"error: - {match}", file=sys.stderr)
        return 1

    print(str(matches[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

