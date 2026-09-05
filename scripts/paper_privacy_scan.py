#!/usr/bin/env python3
"""Scan a paper project for sensitive tokens (privacy gate).

Focus: prevent leaking internal URLs, absolute filesystem paths, and secret-like env contents
into the paper project artifacts.

Exit code:
  0 - pass
  1 - violations found

Notes:
- This tool intentionally avoids printing the matched sensitive strings.
- This tool intentionally avoids printing absolute filesystem paths.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


_URL_RE = re.compile(r"https?://[^\s\)\]]+")
_ABS_UNIX_PATH_RE = re.compile(r"(?<!\w)/(?:home|Users|var|etc|opt|srv|mnt|media)/[^\s`\"']+")

_INTERNAL_TLDS = (".local", ".lan", ".internal")
_INTERNAL_SUBSTRINGS = (".internal.",)
_INTERNAL_HOSTS = {"localhost", "0.0.0.0"}

_SECRET_ASSIGN_RE = re.compile(
    r"(?i)\b("
    r"OPENAI_API_KEY|API_KEY|SECRET_KEY|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|"
    r"DATABASE_URL|ACCESS_TOKEN|TOKEN|PASSWORD|PRIVATE_KEY"
    r")\b\s*=\s*\S{4,}"
)
_OPENAI_KEY_RE = re.compile(r"sk-[A-Za-z0-9]{20,}")
_PRIVATE_KEY_BLOCK_RE = re.compile(r"-----BEGIN (?:RSA|OPENSSH) PRIVATE KEY-----")

MAX_VIOLATIONS_TO_PRINT = 80


@dataclass(frozen=True)
class Violation:
    kind: str
    rel_path: str
    line: int
    rule: str


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def parse_args() -> Path | int:
    parser = argparse.ArgumentParser(description="Scan paper project for privacy leaks.")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Paper project directory containing main.tex (default: .).",
    )
    args = parser.parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        return fail("project dir not found")
    if not project_dir.is_dir():
        return fail("project dir is not a directory")
    if not (project_dir / "main.tex").exists():
        return fail("main.tex not found in project dir")
    return project_dir


def is_internal_host(host: str) -> bool:
    h = host.strip().lower()
    if not h:
        return False
    if ":" in h:
        h = h.split(":", 1)[0]
    if h in _INTERNAL_HOSTS:
        return True
    if any(h.endswith(tld) for tld in _INTERNAL_TLDS):
        return True
    if any(token in h for token in _INTERNAL_SUBSTRINGS):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def rel_path(path: Path, project_dir: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except ValueError:
        return path.name


def iter_scan_files(project_dir: Path) -> list[Path]:
    files: list[Path] = [project_dir / "main.tex"]
    for extra in [project_dir / "ref.bib"]:
        if extra.exists():
            files.append(extra)

    for folder, pattern in [
        (project_dir / "plan", "*.md"),
        (project_dir / "notes", "*.md"),
        (project_dir / "issues", "*.csv"),
    ]:
        if not folder.exists():
            continue
        files.extend(sorted(p for p in folder.glob(pattern) if p.is_file()))

    # De-duplicate while preserving order
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in files:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def scan_text(*, text: str, rel_path_str: str) -> list[Violation]:
    violations: list[Violation] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if _ABS_UNIX_PATH_RE.search(line):
            violations.append(
                Violation(kind="abs_path", rel_path=rel_path_str, line=idx, rule="absolute unix path")
            )

        for match in _URL_RE.findall(line):
            parsed = urlparse(match)
            host = parsed.netloc
            if is_internal_host(host):
                violations.append(
                    Violation(kind="internal_url", rel_path=rel_path_str, line=idx, rule="internal host url")
                )

        if _SECRET_ASSIGN_RE.search(line):
            violations.append(
                Violation(kind="secret_assign", rel_path=rel_path_str, line=idx, rule="secret-like assignment")
            )

        if _OPENAI_KEY_RE.search(line):
            violations.append(Violation(kind="secret_key", rel_path=rel_path_str, line=idx, rule="api key token"))

        if _PRIVATE_KEY_BLOCK_RE.search(line):
            violations.append(
                Violation(kind="private_key_block", rel_path=rel_path_str, line=idx, rule="private key block")
            )

    return violations


def main() -> int:
    parsed = parse_args()
    if isinstance(parsed, int):
        return parsed

    project_dir = parsed
    violations: list[Violation] = []
    for path in iter_scan_files(project_dir):
        text = path.read_text(encoding="utf-8", errors="replace")
        violations.extend(scan_text(text=text, rel_path_str=rel_path(path, project_dir)))

    if not violations:
        print("Privacy scan passed.")
        return 0

    print(f"error: privacy scan failed ({len(violations)} violation(s))", file=sys.stderr)
    for v in violations[:MAX_VIOLATIONS_TO_PRINT]:
        print(f"error: {v.kind}: `{v.rel_path}`#L{v.line} ({v.rule})", file=sys.stderr)
    if len(violations) > MAX_VIOLATIONS_TO_PRINT:
        print("error: (truncated)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
