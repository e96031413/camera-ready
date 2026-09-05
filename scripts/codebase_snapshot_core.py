#!/usr/bin/env python3
"""Core logic for generating a codebase snapshot (dependency-free).

This module is intentionally stdlib-only. It is imported by codebase_snapshot.py.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DEFAULT_IGNORE_DIRS = frozenset(
    {
        ".git",
        ".idea",
        ".next",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".venv",
        ".vscode",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "venv",
    }
)

MAX_LANGUAGE_ITEMS = 12
MAX_TOP_LEVEL_ITEMS = 20
MAX_README_LINES = 24
MAX_LIST_ITEMS = 30

# Avoid consuming trailing Markdown/parenthesis punctuation so we don't break link syntax.
_URL_RE = re.compile(r"https?://[^\s\)\]]+")
_ABS_UNIX_PATH_RE = re.compile(r"(?<!\w)/(?:home|Users|var|etc|opt|srv|mnt|media)/[^\s`]+")


@dataclass(frozen=True)
class SnapshotConfig:
    codebase_dir: Path
    project_dir: Path


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run_git_head(codebase_dir: Path) -> str | None:
    if not (codebase_dir / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(codebase_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    head = proc.stdout.strip()
    return head if head else None


def should_ignore_dir(dirname: str) -> bool:
    if dirname in DEFAULT_IGNORE_DIRS:
        return True
    return dirname.startswith(".") and dirname not in {".codex", ".claude"}


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def _redact_readme_line(line: str) -> str:
    """
    Redact potentially sensitive tokens from README excerpts.

    Rationale:
    - Codebase-grounded papers should not leak internal URLs or absolute filesystem paths.
    - README excerpts are used as lightweight context; URLs/paths are rarely needed here.
    """
    redacted = _URL_RE.sub("<URL_REDACTED>", line)
    redacted = _ABS_UNIX_PATH_RE.sub("<PATH_REDACTED>", redacted)
    return redacted


def read_readme_excerpt(codebase_dir: Path) -> list[str]:
    candidates = [
        codebase_dir / "README.md",
        codebase_dir / "README.rst",
        codebase_dir / "README.txt",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        lines = [
            _redact_readme_line(line.rstrip())
            for line in safe_read_text(candidate).splitlines()
            if line.strip()
        ]
        return lines[:MAX_README_LINES]
    return []


def list_root_manifests(codebase_dir: Path) -> list[str]:
    names = [
        "README.md",
        "README.rst",
        "README.txt",
        "architecture.md",
        "AGENTS.md",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "Pipfile",
        "package.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "package-lock.json",
        "Makefile",
        "docker-compose.yml",
        "Dockerfile",
    ]
    return [name for name in names if (codebase_dir / name).exists()]


def parse_package_json(codebase_dir: Path) -> dict | None:
    path = codebase_dir / "package.json"
    if not path.exists():
        return None
    try:
        return json.loads(safe_read_text(path))
    except json.JSONDecodeError:
        return {"_error": "package.json is not valid JSON"}


def read_requirements_lines(codebase_dir: Path) -> list[str]:
    path = codebase_dir / "requirements.txt"
    if not path.exists():
        return []
    lines = []
    for raw in safe_read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
        if len(lines) >= MAX_LIST_ITEMS:
            break
    return lines


def scan_tree_stats(codebase_dir: Path) -> dict:
    extension_counts: dict[str, int] = {}
    top_level_files: dict[str, int] = {}
    top_level_dirs: dict[str, int] = {}
    total_files = 0

    for dirpath, dirnames, filenames in os.walk(codebase_dir):
        dirnames[:] = [d for d in dirnames if not should_ignore_dir(d)]

        rel = Path(dirpath).relative_to(codebase_dir)
        top = rel.parts[0] if rel.parts else "(root)"

        if rel.parts:
            top_level_dirs[top] = top_level_dirs.get(top, 0) + 1

        for filename in filenames:
            if filename.startswith("."):
                continue
            total_files += 1
            top_level_files[top] = top_level_files.get(top, 0) + 1
            ext = Path(filename).suffix.lower() or "<noext>"
            extension_counts[ext] = extension_counts.get(ext, 0) + 1

    return {
        "total_files": total_files,
        "extension_counts": extension_counts,
        "top_level_files": top_level_files,
        "top_level_dirs": top_level_dirs,
    }


def summarize_extension_counts(extension_counts: dict[str, int]) -> list[tuple[str, int]]:
    items = sorted(extension_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return items[:MAX_LANGUAGE_ITEMS]


def summarize_top_level_counts(counts: dict[str, int]) -> list[tuple[str, int]]:
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return items[:MAX_TOP_LEVEL_ITEMS]


def build_snapshot(config: SnapshotConfig) -> dict:
    tree = scan_tree_stats(config.codebase_dir)
    extension_counts = tree["extension_counts"]
    top_level_files = tree["top_level_files"]

    return {
        "created_at": now_iso(),
        "codebase_name": str(config.codebase_dir.name),
        "paper_project_name": str(config.project_dir.name),
        "git_head": run_git_head(config.codebase_dir),
        "root_manifests": list_root_manifests(config.codebase_dir),
        "readme_excerpt": read_readme_excerpt(config.codebase_dir),
        "total_files": tree["total_files"],
        "extension_counts": extension_counts,
        "extension_counts_summary": summarize_extension_counts(extension_counts),
        "top_level_files": top_level_files,
        "top_level_files_summary": summarize_top_level_counts(top_level_files),
        "top_level_dirs": tree["top_level_dirs"],
        "package_json": parse_package_json(config.codebase_dir),
        "requirements_txt": read_requirements_lines(config.codebase_dir),
    }
