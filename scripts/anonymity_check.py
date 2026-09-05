#!/usr/bin/env python3
"""Check a paper project for double-blind anonymity violations.

Scans the LaTeX sources, the bibliography, and the compiled PDF's metadata for
things that identify the authors:

  BLOCKER -- author macros, \\thanks, acknowledgements, funding statements,
             email addresses, named repository URLs, PDF author metadata.
  WARN    -- personal or institutional domains, ORCID iDs, first-person
             self-citation phrasing ("our previous work", "we showed in [3]").
  INFO    -- things worth a human glance: anonymous-preview repository links,
             identity-holding files, and the style files that were skipped.

This tool reports; it never edits. A clean run is evidence, not proof: it
cannot tell that "the Zurich group" is you, and it cannot read your figures.
Read every flagged line, then read the paper yourself.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BLOCKER = "BLOCKER"
WARN = "WARN"
INFO = "INFO"

_SEVERITY_ORDER = {BLOCKER: 0, WARN: 1, INFO: 2}

# Author-written sources. Class and style files are excluded on purpose: they
# *define* \author and \thanks, so scanning them reports the template's own
# macro definitions as author identity. They come from the venue, not from you.
TEX_SUFFIXES = {".tex", ".bib", ".bbl"}
STYLE_SUFFIXES = {".sty", ".cls", ".bst", ".clo"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "runs", "out"}

# Files whose whole purpose is to hold identity. They are excluded from the
# scan because flagging every line of them is noise, not signal -- but their
# presence is reported so the author remembers to keep them out of the
# submission tarball.
IDENTITY_FILES = {"authors.tex", "camera-ready.tex"}


class Finding:
    """One anonymity problem."""

    def __init__(self, severity: str, rule: str, location: str, line_no: int, evidence: str, fix: str) -> None:
        self.severity = severity
        self.rule = rule
        self.location = location
        self.line_no = line_no
        self.evidence = evidence.strip()[:160]
        self.fix = fix


# (severity, rule name, pattern, remedy)
_SOURCE_RULES: list[tuple[str, str, re.Pattern, str]] = [
    (
        BLOCKER,
        "author macro",
        re.compile(r"\\(author|IEEEauthorblockN|IEEEauthorblockA|affil|affiliation)\s*(\[|\{)"),
        "Replace with the style file's anonymous author block (most venues provide one).",
    ),
    (
        BLOCKER,
        "thanks/footnote",
        re.compile(r"\\thanks\s*\{"),
        "\\thanks almost always carries funding or contact details. Remove it for submission.",
    ),
    (
        BLOCKER,
        "acknowledgements",
        re.compile(r"\\(section|subsection)\*?\s*\{[^}]*(Acknowledg|Funding)", re.IGNORECASE),
        "Move acknowledgements to the camera-ready version only.",
    ),
    (
        BLOCKER,
        "acknowledgement environment",
        re.compile(r"\\begin\{(acks|acknowledgements|acknowledgments)\}", re.IGNORECASE),
        "Move acknowledgements to the camera-ready version only.",
    ),
    (
        BLOCKER,
        "email address",
        re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
        "Remove the address. Anonymous submissions carry no contact details.",
    ),
    (
        BLOCKER,
        "named code repository",
        re.compile(
            r"https?://(?:www\.)?(?:github\.com|gitlab\.com|bitbucket\.org|huggingface\.co)/"
            r"(?!anonymous)[A-Za-z0-9_.\-]+",
            re.IGNORECASE,
        ),
        "Use an anonymized mirror (e.g. anonymous.4open.science) during review.",
    ),
    (
        WARN,
        "ORCID",
        re.compile(r"orcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[\dX]", re.IGNORECASE),
        "An ORCID iD identifies the author. Remove it for submission.",
    ),
    (
        WARN,
        "personal or institutional URL",
        re.compile(
            r"https?://[A-Za-z0-9.\-]*\.(?:edu|ac\.[a-z]{2}|edu\.[a-z]{2})(?:/|\b)",
            re.IGNORECASE,
        ),
        "A university domain identifies the group. Remove or anonymize the link.",
    ),
    (
        WARN,
        "first-person self-citation",
        re.compile(
            r"\b(our|my)\s+(previous|prior|earlier|recent|own)\s+(work|paper|study|method|approach|system|framework)\b",
            re.IGNORECASE,
        ),
        "Rewrite in the third person: \"Prior work [12] showed\", not \"our previous work [12]\".",
    ),
    (
        WARN,
        "first-person reference to a citation",
        re.compile(
            r"\b(we|I)\s+(showed|proposed|introduced|presented|developed|published|reported)\b[^.]{0,60}?"
            r"(\\cite|\\citep|\\citet|\[\d)",
            re.IGNORECASE,
        ),
        "Rewrite in the third person, or the citation reveals who \"we\" are.",
    ),
    (
        WARN,
        "de-anonymizing phrase",
        re.compile(
            r"\b(as\s+(?:we|I)\s+(?:have\s+)?(?:shown|argued|described)|in\s+(?:our|my)\s+(?:lab|group|institution|company))\b",
            re.IGNORECASE,
        ),
        "Rewrite to avoid referring to the authors' own body of work or affiliation.",
    ),
    (
        INFO,
        "anonymous repository link",
        re.compile(r"https?://anonymous\.4open\.science/\S+", re.IGNORECASE),
        "Correct for review. Check the mirror itself contains no names, LICENSE author, or git history.",
    ),
]

# LaTeX comments are stripped before scanning, except for these: an author name
# left in a comment still ships inside the .tex file you upload.
_COMMENT_RULES: list[tuple[str, str, re.Pattern, str]] = [
    (
        WARN,
        "identity in a LaTeX comment",
        re.compile(r"%.*?([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})"),
        "Comments ship inside the uploaded .tex source. Delete the line, or run "
        "arxiv_package.py, which strips comments.",
    ),
]

_PDF_AUTHOR_RE = re.compile(rb"/(Author|Creator|Producer|Title)\s*\(([^)]{0,200})\)")
_PDF_XMP_AUTHOR_RE = re.compile(rb"<(?:dc|pdf|xmp):(?:creator|Author)[^>]*>(.{0,300}?)</", re.DOTALL)


def strip_comments(text: str) -> tuple[str, list[str]]:
    """Return (source with comments blanked, original lines).

    Comments are blanked rather than deleted so line numbers stay accurate.
    """
    stripped_lines = []
    for line in text.splitlines():
        result = []
        index = 0
        while index < len(line):
            char = line[index]
            if char == "\\" and index + 1 < len(line):
                result.append(line[index : index + 2])
                index += 2
                continue
            if char == "%":
                break
            result.append(char)
            index += 1
        stripped_lines.append("".join(result))
    return "\n".join(stripped_lines), text.splitlines()


def iter_source_files(project_dir: Path) -> tuple[list[Path], int]:
    """Return (author-written files to scan, count of style files skipped)."""
    files = []
    skipped_styles = 0
    for path in sorted(project_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(project_dir).parts):
            continue
        suffix = path.suffix.lower()
        if suffix in STYLE_SUFFIXES:
            skipped_styles += 1
            continue
        if suffix in TEX_SUFFIXES:
            files.append(path)
    return files, skipped_styles


def scan_source(path: Path, project_dir: Path) -> list[Finding]:
    """Scan one LaTeX or bibliography file."""
    rel = path.relative_to(project_dir).as_posix()
    if path.name.lower() in IDENTITY_FILES:
        return [
            Finding(
                INFO,
                "identity file present",
                rel,
                0,
                path.name,
                "This file holds author identity by design. Confirm it is not \\input by the "
                "submission build, and keep it out of the submission tarball.",
            )
        ]

    text = path.read_text(encoding="utf-8", errors="replace")
    stripped, original_lines = strip_comments(text)
    findings = []

    for line_no, line in enumerate(stripped.splitlines(), start=1):
        if not line.strip():
            continue
        for severity, rule, pattern, fix in _SOURCE_RULES:
            match = pattern.search(line)
            if match:
                findings.append(Finding(severity, rule, rel, line_no, match.group(0), fix))

    for line_no, line in enumerate(original_lines, start=1):
        for severity, rule, pattern, fix in _COMMENT_RULES:
            match = pattern.search(line)
            if match:
                findings.append(Finding(severity, rule, rel, line_no, match.group(1), fix))

    return findings


def scan_pdf(pdf_path: Path, project_dir: Path) -> list[Finding]:
    """Scan a compiled PDF's document information dictionary and XMP metadata."""
    rel = pdf_path.relative_to(project_dir).as_posix()
    try:
        data = pdf_path.read_bytes()
    except OSError as exc:
        return [Finding(INFO, "pdf unreadable", rel, 0, str(exc), "Recompile the paper.")]

    findings = []
    # LaTeX writes a neutral Producer/Creator; a name in Author is the real risk.
    for match in _PDF_AUTHOR_RE.finditer(data):
        key = match.group(1).decode("latin-1")
        value = match.group(2).decode("latin-1", errors="replace").strip()
        if not value:
            continue
        if key == "Author":
            findings.append(
                Finding(
                    BLOCKER,
                    "PDF author metadata",
                    rel,
                    0,
                    f"/{key} ({value})",
                    "Set \\hypersetup{pdfauthor={}} in the preamble, or remove the "
                    "\\author macro, and recompile.",
                )
            )
        elif key == "Title" and "@" in value:
            findings.append(
                Finding(
                    BLOCKER,
                    "PDF title metadata",
                    rel,
                    0,
                    f"/{key} ({value})",
                    "Set \\hypersetup{pdftitle={...}} to the paper title only.",
                )
            )

    for match in _PDF_XMP_AUTHOR_RE.finditer(data):
        value = re.sub(rb"<[^>]+>", b" ", match.group(1)).decode("utf-8", errors="replace").strip()
        if value:
            findings.append(
                Finding(
                    WARN,
                    "PDF XMP metadata",
                    rel,
                    0,
                    value,
                    "XMP metadata is written from the same source as /Author. Clear it and recompile.",
                )
            )

    return findings


def render(findings: list[Finding], project_dir: Path, scanned: int) -> str:
    """Render the findings report."""
    lines = [
        "Anonymity check (double-blind submission)",
        f"Project: {project_dir}",
        f"Scanned: {scanned} file(s)",
        "",
    ]

    if not findings:
        lines += [
            "  No anonymity violations detected.",
            "",
            "This is evidence, not proof. A scanner cannot tell that a described "
            "system, dataset, or 'the group at X' identifies you, and it does not "
            "read your figures. Read the paper as a reviewer would before submitting.",
        ]
        return "\n".join(lines)

    counts = {level: sum(1 for f in findings if f.severity == level) for level in (BLOCKER, WARN, INFO)}
    for level in (BLOCKER, WARN, INFO):
        level_findings = [f for f in findings if f.severity == level]
        if not level_findings:
            continue
        lines.append(f"## {level} ({len(level_findings)})")
        lines.append("")
        for finding in level_findings:
            where = f"{finding.location}:{finding.line_no}" if finding.line_no else finding.location
            lines.append(f"  [{finding.severity}] {where}")
            lines.append(f"      rule:     {finding.rule}")
            lines.append(f"      evidence: {finding.evidence}")
            lines.append(f"      fix:      {finding.fix}")
            lines.append("")

    lines.append(
        f"Summary: {counts[BLOCKER]} blocker(s), {counts[WARN]} warning(s), {counts[INFO]} note(s)."
    )
    if counts[BLOCKER]:
        lines.append("Do not submit until every BLOCKER is resolved.")
    lines.append(
        "A clean run is evidence, not proof. Read every flagged line, and read the "
        "paper as a reviewer would."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a paper project for double-blind anonymity violations."
    )
    parser.add_argument("--project-dir", required=True, help="Paper project directory.")
    parser.add_argument(
        "--pdf",
        default="main.pdf",
        help="Compiled PDF to inspect for identifying metadata (default: main.pdf).",
    )
    parser.add_argument(
        "--no-pdf", action="store_true", help="Skip the PDF metadata scan."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on WARN as well as BLOCKER. Use this at the final QA gate.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"error: project dir not found: {project_dir}", file=sys.stderr)
        return 1

    source_files, skipped_styles = iter_source_files(project_dir)
    if not source_files:
        print(f"error: no LaTeX or bibliography files found under {project_dir}", file=sys.stderr)
        return 1

    findings: list[Finding] = []
    for path in source_files:
        findings.extend(scan_source(path, project_dir))

    scanned = len(source_files)
    if not args.no_pdf:
        pdf_path = project_dir / args.pdf
        if pdf_path.is_file():
            findings.extend(scan_pdf(pdf_path, project_dir))
            scanned += 1

    if skipped_styles:
        findings.append(
            Finding(
                INFO,
                "style files not scanned",
                f"{skipped_styles} .cls/.sty/.bst file(s)",
                0,
                "class and style files define the author macros",
                "These come from the venue, not from you. Scanning them would report the "
                "template's own macro definitions as author identity.",
            )
        )

    findings.sort(key=lambda f: (_SEVERITY_ORDER[f.severity], f.location, f.line_no))
    print(render(findings, project_dir, scanned))

    blocking = {BLOCKER, WARN} if args.strict else {BLOCKER}
    return 1 if any(f.severity in blocking for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
