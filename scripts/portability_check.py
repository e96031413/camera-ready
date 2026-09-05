#!/usr/bin/env python3
"""Cross-platform portability lint for this repository's Python sources.

Version: 2026-09-05-v1

Windows, Linux and macOS disagree about three things that silently corrupt a
paper pipeline: the default text encoding (cp1252/cp950 on Windows, UTF-8
elsewhere), the path separator, and where a temporary directory lives. Python
does not warn about any of them, so this script is the gate.

Checks (each reported with file, line and rule id):

  ENC001  open()/read_text()/write_text() in text mode without encoding=
  ENC002  subprocess call capturing text output without an explicit encoding
  PATH001 a hardcoded POSIX-only absolute path ('/tmp', '/usr/', ...)
  PROC001 subprocess with shell=True
  DOC001  'python3' inside a documentation code fence (Windows ships 'python')

A '# portability: ignore' comment on a line suppresses every finding on it, in
Python sources and in documentation fences alike.

Usage:
  python scripts/portability_check.py                 # lint scripts/ and tests/
  python scripts/portability_check.py --docs          # also lint *.md fences
  python scripts/portability_check.py --path scripts/foo.py
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

BANNER = "portability_check 2026-09-05-v1"

# Attribute calls named open() that are not the text-mode builtin.
NON_TEXT_OPEN_OWNERS = {
    "tarfile",
    "zipfile",
    "gzip",
    "bz2",
    "lzma",
    "Image",
    "io",
    "socket",
    "webbrowser",
    "shelve",
    "sqlite3",
}

POSIX_ONLY_PREFIXES = ("/tmp", "/var/folders", "/usr/", "/opt/", "/home/", "/dev/")  # portability: ignore -- this is the rule table itself

SUBPROCESS_CALLS = {"run", "check_output", "Popen", "call", "check_call"}


@dataclass
class Finding:
    """One portability hazard at one source location."""

    path: Path
    line: int
    rule: str
    message: str

    def render(self, root: Path) -> str:
        try:
            shown = self.path.resolve().relative_to(root).as_posix()
        except ValueError:
            shown = self.path.as_posix()
        return f"{shown}:{self.line}: {self.rule} {self.message}"


def call_owner_and_name(node: ast.Call) -> tuple[str | None, str | None]:
    """Return (owner, name) for a call, where owner is the attribute's base name."""
    func = node.func
    if isinstance(func, ast.Attribute):
        owner = func.value.id if isinstance(func.value, ast.Name) else None
        return owner, func.attr
    if isinstance(func, ast.Name):
        return None, func.id
    return None, None


def has_keyword(node: ast.Call, name: str) -> bool:
    return any(kw.arg == name for kw in node.keywords)


def is_binary_mode(node: ast.Call) -> bool:
    """True when an open() call requests a binary mode, where encoding is invalid."""
    mode = None
    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
        mode = node.args[1].value
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode = kw.value.value
    return isinstance(mode, str) and "b" in mode


SUPPRESSION = re.compile(r"#\s*portability:\s*ignore")


def suppressed_lines(source: str) -> set[int]:
    """Return the line numbers carrying a '# portability: ignore' marker.

    The marker suppresses every finding reported on that line. Put it on the
    line a deliberate platform-specific literal appears on, such as a Linux
    binary search path.
    """
    return {
        number
        for number, line in enumerate(source.splitlines(), 1)
        if SUPPRESSION.search(line)
    }


def check_python(path: Path) -> list[Finding]:
    """Lint one Python file. A syntax error is reported as a finding, not raised."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [Finding(path, exc.lineno or 1, "SYN001", f"cannot parse: {exc.msg}")]

    skip = suppressed_lines(source)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if value.startswith(POSIX_ONLY_PREFIXES) and len(value) > 5:
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "PATH001",
                        f"POSIX-only path literal {value!r}; use tempfile or Path",
                    )
                )
            continue

        if not isinstance(node, ast.Call):
            continue

        owner, name = call_owner_and_name(node)

        if name in {"read_text", "write_text"} and not has_keyword(node, "encoding"):
            findings.append(
                Finding(path, node.lineno, "ENC001", f"{name}() without encoding=; add encoding='utf-8'")
            )
        elif name == "open" and owner not in NON_TEXT_OPEN_OWNERS:
            if not is_binary_mode(node) and not has_keyword(node, "encoding"):
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "ENC001",
                        "open() in text mode without encoding=; add encoding='utf-8'",
                    )
                )

        if owner == "subprocess" and name in SUBPROCESS_CALLS:
            if has_keyword(node, "shell"):
                findings.append(
                    Finding(path, node.lineno, "PROC001", "subprocess with shell=True is not portable")
                )
            decodes_text = (
                has_keyword(node, "text")
                or has_keyword(node, "universal_newlines")
                or has_keyword(node, "capture_output")
            )
            if decodes_text and not has_keyword(node, "encoding"):
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "ENC002",
                        "subprocess decodes output with the locale encoding; "
                        "add encoding='utf-8', errors='replace'",
                    )
                )

    return [f for f in findings if f.line not in skip]


DOC_PYTHON3 = re.compile(r"(?<![\w./-])python3(?![\w.-])")


def check_doc(path: Path) -> list[Finding]:
    """Lint the code fences of one Markdown file for Windows-hostile commands."""
    findings: list[Finding] = []
    inside_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            inside_fence = not inside_fence
            continue
        if inside_fence and DOC_PYTHON3.search(line) and not SUPPRESSION.search(line):
            findings.append(
                Finding(path, number, "DOC001", "'python3' in a command; Windows ships only 'python'")
            )
    return findings


def default_python_targets(root: Path) -> list[Path]:
    targets: list[Path] = []
    for folder in ("scripts", "tests"):
        directory = root / folder
        if directory.is_dir():
            targets.extend(sorted(p for p in directory.glob("*.py") if p.is_file()))
    return targets


def default_doc_targets(root: Path) -> list[Path]:
    skip = {"__pycache__", "node_modules"}
    return sorted(
        p
        for p in root.rglob("*.md")
        if not skip.intersection(p.parts)
        and not any(part.startswith(".") for part in p.relative_to(root).parts)
    )


def collect_targets(root: Path, raw_paths: list[str]) -> tuple[list[Path], list[Path]]:
    """Split the requested paths into Python targets and Markdown targets."""
    if not raw_paths:
        return default_python_targets(root), default_doc_targets(root)

    python_targets: list[Path] = []
    doc_targets: list[Path] = []
    for raw in raw_paths:
        target = Path(raw)
        if target.is_dir():
            python_targets.extend(sorted(target.rglob("*.py")))
            doc_targets.extend(sorted(target.rglob("*.md")))
        elif target.suffix == ".md":
            doc_targets.append(target)
        else:
            python_targets.append(target)
    return python_targets, doc_targets


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint Python sources for Windows/Linux/macOS portability hazards.",
    )
    parser.add_argument("--path", action="append", default=[], help="lint this file or directory (repeatable)")
    parser.add_argument("--docs", action="store_true", help="also lint Markdown code fences")
    parser.add_argument("--quiet", action="store_true", help="print only the summary line")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    python_targets, doc_targets = collect_targets(root, args.path)

    findings: list[Finding] = []
    for path in python_targets:
        if not path.is_file():
            print(f"warning: no such file: {path}", file=sys.stderr)
            continue
        findings.extend(check_python(path))
    if args.docs:
        for path in doc_targets:
            if path.is_file():
                findings.extend(check_doc(path))

    if not args.quiet:
        for finding in findings:
            print(finding.render(root))

    scanned = len(python_targets) + (len(doc_targets) if args.docs else 0)
    if findings:
        print(f"\n{BANNER}: {len(findings)} portability issue(s) across {scanned} file(s)")
        return 1
    print(f"{BANNER}: clean - {scanned} file(s) scanned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
