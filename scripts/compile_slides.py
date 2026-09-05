#!/usr/bin/env python3
"""Compile Beamer slides with XeLaTeX (3-pass) and report diagnostics."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _which_xelatex() -> str | None:
    return shutil.which("xelatex")


def _which_bibtex() -> str | None:
    return shutil.which("bibtex")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, encoding="utf-8", errors="replace", text=True)


def parse_log_diagnostics(log_path: Path) -> dict:
    """Parse XeLaTeX log for warnings and errors."""
    if not log_path.exists():
        return {"overfull_hbox": 0, "undefined_refs": 0, "undefined_citations": 0,
                "multiply_defined": 0, "errors": 0, "pages": None}

    text = log_path.read_text(encoding="utf-8", errors="replace")

    overfull = len(re.findall(r"Overfull \\hbox", text))
    undef_refs = len(re.findall(r"LaTeX Warning: Reference .* undefined", text))
    undef_cites = len(re.findall(r"LaTeX Warning: Citation .* undefined", text))
    multiply = len(re.findall(r"multiply defined", text, re.IGNORECASE))
    errors = len(re.findall(r"^!", text, re.MULTILINE))

    pages_match = re.search(r"Output written on .*?\((\d+)\s+pages?", text)
    pages = int(pages_match.group(1)) if pages_match else None

    return {
        "overfull_hbox": overfull,
        "undefined_refs": undef_refs,
        "undefined_citations": undef_cites,
        "multiply_defined": multiply,
        "errors": errors,
        "pages": pages,
    }


def check_source_violations(tex_path: Path) -> dict:
    """Check .tex source for Hard Rule violations."""
    if not tex_path.exists():
        return {"overlays": 0, "tiny_usage": 0}

    text = tex_path.read_text(encoding="utf-8", errors="replace")

    overlays = len(re.findall(r"\\(pause|onslide|only)\b", text))
    tiny = len(re.findall(r"\\tiny\b", text))

    return {"overlays": overlays, "tiny_usage": tiny}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile Beamer slides with XeLaTeX (3-pass)."
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Directory containing the slides .tex file.",
    )
    parser.add_argument(
        "--tex-file",
        default="slides.tex",
        help="Name of the .tex file to compile (default: slides.tex).",
    )
    parser.add_argument(
        "--with-bibtex",
        action="store_true",
        help="Run bibtex between XeLaTeX passes.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    tex_path = project_dir / args.tex_file

    if not tex_path.exists():
        print(f"error: {args.tex_file} not found in {project_dir}", file=sys.stderr)
        return 1

    xelatex = _which_xelatex()
    if not xelatex:
        print("error: xelatex not found on PATH.", file=sys.stderr)
        return 1

    stem = tex_path.stem
    base_cmd = [xelatex, "-interaction=nonstopmode", "-halt-on-error", args.tex_file]

    # Pass 1
    result = run(base_cmd, project_dir)
    if result.returncode != 0:
        print(f"error: XeLaTeX pass 1 failed (exit {result.returncode})", file=sys.stderr)
        if result.stdout:
            # Print last 30 lines for context
            lines = result.stdout.strip().splitlines()
            for line in lines[-30:]:
                print(line, file=sys.stderr)
        return result.returncode

    # Optional bibtex
    if args.with_bibtex:
        bibtex = _which_bibtex()
        if bibtex:
            run([bibtex, stem], project_dir)
        else:
            print("warning: bibtex not found; skipping.", file=sys.stderr)

    # Pass 2
    result = run(base_cmd, project_dir)
    if result.returncode != 0:
        print(f"error: XeLaTeX pass 2 failed (exit {result.returncode})", file=sys.stderr)
        return result.returncode

    # Pass 3
    result = run(base_cmd, project_dir)
    if result.returncode != 0:
        print(f"error: XeLaTeX pass 3 failed (exit {result.returncode})", file=sys.stderr)
        return result.returncode

    # Diagnostics
    log_path = project_dir / f"{stem}.log"
    diag = parse_log_diagnostics(log_path)
    violations = check_source_violations(tex_path)

    print(f"\nCompilation successful: {stem}.pdf")
    if diag["pages"] is not None:
        print(f"  Pages: {diag['pages']}")
    print(f"  Overfull hbox warnings: {diag['overfull_hbox']}")
    print(f"  Undefined references: {diag['undefined_refs']}")
    print(f"  Undefined citations: {diag['undefined_citations']}")
    print(f"  Multiply defined labels: {diag['multiply_defined']}")
    print(f"  Errors in log: {diag['errors']}")

    if violations["overlays"] > 0:
        print(f"  VIOLATION: {violations['overlays']} overlay commands found (Hard Rule 1)")
    if violations["tiny_usage"] > 0:
        print(f"  VIOLATION: {violations['tiny_usage']} \\tiny usage found (Hard Rule 13)")

    has_issues = (
        diag["overfull_hbox"] > 0
        or diag["undefined_refs"] > 0
        or diag["undefined_citations"] > 0
        or violations["overlays"] > 0
        or violations["tiny_usage"] > 0
    )

    if has_issues:
        print("\nStatus: PASS WITH WARNINGS")
    else:
        print("\nStatus: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
