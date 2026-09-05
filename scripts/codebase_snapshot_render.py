#!/usr/bin/env python3
"""Markdown rendering for codebase snapshot output."""

from __future__ import annotations

MAX_LIST_ITEMS = 30


def _render_kv_list(pairs: list[tuple[str, str]]) -> list[str]:
    return [f"- {key}: {value}" for key, value in pairs]


def _render_header(snapshot: dict) -> list[str]:
    lines: list[str] = ["# Codebase Snapshot", ""]
    pairs: list[tuple[str, str]] = [
        ("Created at", str(snapshot.get("created_at", ""))),
        ("Codebase", str(snapshot.get("codebase_name", ""))),
    ]
    git_head = snapshot.get("git_head")
    if git_head:
        pairs.append(("Git HEAD", f"`{git_head}`"))
    lines.extend(_render_kv_list(pairs))
    lines.append("")
    return lines


def _render_readme_excerpt(snapshot: dict) -> list[str]:
    excerpt = snapshot.get("readme_excerpt") or []
    if not excerpt:
        return []
    lines: list[str] = ["## README excerpt", ""]
    lines.extend([f"- {line}" for line in excerpt])
    lines.append("")
    return lines


def _render_root_manifests(snapshot: dict) -> list[str]:
    manifests = snapshot.get("root_manifests") or []
    lines: list[str] = ["## Root manifests", ""]
    if not manifests:
        lines.append("- (none detected)")
    else:
        lines.extend([f"- `{name}`" for name in manifests])
    lines.append("")
    return lines


def _render_quick_facts(snapshot: dict) -> list[str]:
    total_files = snapshot.get("total_files", 0)
    lines: list[str] = ["## Repo quick facts", ""]
    lines.append(f"- Total files (excluding ignored dirs): {total_files}")
    lines.append("")
    return lines


def _render_top_level(snapshot: dict) -> list[str]:
    lines: list[str] = ["## Top-level areas (by file count)", ""]
    for name, count in snapshot.get("top_level_files_summary", []):
        lines.append(f"- {name}: {count} files")
    lines.append("")
    return lines


def _render_extensions(snapshot: dict) -> list[str]:
    lines: list[str] = ["## Languages / file types (by extension)", ""]
    for ext, count in snapshot.get("extension_counts_summary", []):
        lines.append(f"- {ext}: {count}")
    lines.append("")
    return lines


def _render_package_json(snapshot: dict) -> list[str]:
    pkg = snapshot.get("package_json") or {}
    if not pkg:
        return []

    lines: list[str] = ["## package.json (summary)", ""]
    if "_error" in pkg:
        lines.append(f"- error: {pkg['_error']}")
        lines.append("")
        return lines

    name = str(pkg.get("name") or "").strip()
    version = str(pkg.get("version") or "").strip()
    if name:
        lines.append(f"- name: `{name}`")
    if version:
        lines.append(f"- version: `{version}`")

    scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
    if scripts:
        lines.append("- npm scripts (subset):")
        for idx, key in enumerate(sorted(scripts.keys())):
            if idx >= MAX_LIST_ITEMS:
                break
            lines.append(f"  - `{key}`")

    lines.append("")
    return lines


def _render_requirements(snapshot: dict) -> list[str]:
    reqs = snapshot.get("requirements_txt") or []
    if not reqs:
        return []
    lines: list[str] = ["## requirements.txt (subset)", ""]
    lines.extend([f"- `{dep}`" for dep in reqs])
    lines.append("")
    return lines


def render_snapshot_markdown(snapshot: dict) -> str:
    chunks: list[list[str]] = [
        _render_header(snapshot),
        _render_readme_excerpt(snapshot),
        _render_root_manifests(snapshot),
        _render_quick_facts(snapshot),
        _render_top_level(snapshot),
        _render_extensions(snapshot),
        _render_package_json(snapshot),
        _render_requirements(snapshot),
    ]
    lines: list[str] = []
    for chunk in chunks:
        lines.extend(chunk)
    return "\n".join(lines).rstrip() + "\n"
