#!/usr/bin/env python3
"""Check paragraph-level logic coherence within each section of a LaTeX paper.

Outputs:
  - <project-dir>/notes/logic-selfloop.md

Design goals:
- stdlib-only, deterministic output
- does not print absolute filesystem paths
- heuristic detection of paragraph islands, abrupt topic shifts, and dangling introductions
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from paper_utils import now_iso


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRANSITION_WORDS = [
    "however", "moreover", "furthermore", "therefore", "consequently",
    "nevertheless", "alternatively", "specifically", "similarly",
    "in contrast", "on the other hand", "as a result", "in addition",
    "building on", "extending", "unlike", "following",
]

_SECTION_RE = re.compile(r"\\section\{([^}]+)\}")
_COMMENT_RE = re.compile(r"(?<!\\)%.*$")
_BIB_STOP_RE = re.compile(r"\\bibliography\{|\\begin\{thebibliography\}", re.IGNORECASE)

# \cite, \citet, \citep, \citeauthor, etc. (optional args supported)
_CITE_CMD_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}")

_LATEX_CMD_ONLY_RE = re.compile(r"^\\(begin|end|label|caption)\b")
_LATEX_STRIP_CMDS_RE = re.compile(
    r"\\(?:emph|textit|textbf|texttt|underline|ref|label|url)\{([^}]*)\}"
)
_LATEX_STRIP_BARE_RE = re.compile(r"\\[a-zA-Z]+")
_WHITESPACE_RE = re.compile(r"\s+")

# Nouns heuristic: words ≥ 4 chars, not common stop-words, lowercased.
_STOP_WORDS = frozenset({
    "that", "this", "with", "from", "have", "been", "were", "which",
    "their", "these", "those", "also", "than", "they", "will", "each",
    "more", "such", "when", "into", "over", "only", "very", "about",
    "some", "most", "other", "does", "what", "used", "using", "based",
    "between", "under", "where", "after", "before", "through", "while",
    "both", "same", "well", "then", "many", "much", "even", "here",
    "there", "would", "could", "should", "being", "given", "shown",
    "proposed", "paper", "section", "figure", "table", "method",
})


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    kind: str          # "island" | "topic_shift" | "dangling_intro"
    line: int          # approximate line number in main.tex
    message: str


@dataclass
class Section:
    title: str
    start_line: int
    raw_lines: list[tuple[int, str]] = field(default_factory=list)  # (lineno, text)


@dataclass
class Paragraph:
    start_line: int
    lines: list[str]
    citation_keys: set[str]
    key_nouns: set[str]
    has_transition: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _strip_comments(line: str) -> str:
    return _COMMENT_RE.sub("", line)


def _is_latex_only(line: str) -> bool:
    """Return True if the line is a pure LaTeX command (no prose content)."""
    stripped = line.strip()
    if not stripped:
        return True
    return bool(_LATEX_CMD_ONLY_RE.match(stripped))


def _extract_citations(text: str) -> set[str]:
    """Extract all citation keys from a block of text."""
    keys: set[str] = set()
    for match in _CITE_CMD_RE.finditer(text):
        for raw in match.group(1).split(","):
            key = raw.strip()
            if key:
                keys.add(key)
    return keys


def _extract_key_nouns(text: str) -> set[str]:
    """Extract heuristic key nouns from prose text."""
    # Strip LaTeX markup to get plain-ish text.
    plain = _LATEX_STRIP_CMDS_RE.sub(r"\1", text)
    plain = _CITE_CMD_RE.sub("", plain)
    plain = _LATEX_STRIP_BARE_RE.sub("", plain)
    plain = plain.replace("{", "").replace("}", "").replace("~", " ")
    plain = _WHITESPACE_RE.sub(" ", plain).lower()

    nouns: set[str] = set()
    for word in re.findall(r"[a-z]{4,}", plain):
        if word not in _STOP_WORDS:
            nouns.add(word)
    return nouns


def _has_transition(text: str) -> bool:
    """Check whether the text starts with (or contains early) a transition word/phrase."""
    # Check the first ~120 characters of the paragraph for transition cues.
    lower = text[:120].lower()
    for tw in TRANSITION_WORDS:
        if tw in lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_sections(tex_text: str) -> list[Section]:
    """Parse main.tex into a list of Section objects with raw lines."""
    lines = tex_text.splitlines()
    sections: list[Section] = []
    current: Section | None = None

    for lineno_0, raw in enumerate(lines):
        lineno = lineno_0 + 1  # 1-based

        # Stop at bibliography.
        if _BIB_STOP_RE.search(raw):
            break

        clean = _strip_comments(raw)
        sec_match = _SECTION_RE.search(clean)
        if sec_match:
            current = Section(title=sec_match.group(1).strip(), start_line=lineno)
            sections.append(current)
            continue

        if current is not None:
            current.raw_lines.append((lineno, raw))

    return sections


def split_paragraphs(section: Section) -> list[Paragraph]:
    """Split a section's raw lines into paragraphs separated by blank lines."""
    paragraphs: list[Paragraph] = []
    buf_lines: list[str] = []
    buf_start: int = 0

    def _flush() -> None:
        nonlocal buf_lines, buf_start
        # Filter out latex-only lines for content assessment.
        content_lines = [ln for ln in buf_lines if not _is_latex_only(_strip_comments(ln))]
        if len(content_lines) >= 2:
            full_text = "\n".join(buf_lines)
            paragraphs.append(Paragraph(
                start_line=buf_start,
                lines=list(buf_lines),
                citation_keys=_extract_citations(full_text),
                key_nouns=_extract_key_nouns(full_text),
                has_transition=_has_transition(full_text),
            ))
        buf_lines = []

    for lineno, raw in section.raw_lines:
        clean = _strip_comments(raw).strip()
        if clean == "":
            # Blank line = paragraph boundary.
            _flush()
            continue

        # Skip comment-only lines.
        if raw.strip().startswith("%"):
            continue

        if not buf_lines:
            buf_start = lineno
        buf_lines.append(raw)

    _flush()
    return paragraphs


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_section(section: Section) -> list[Finding]:
    """Analyze a single section for logic coherence issues."""
    paragraphs = split_paragraphs(section)
    if len(paragraphs) < 2:
        return []

    findings: list[Finding] = []

    for i, para in enumerate(paragraphs):
        prev_para = paragraphs[i - 1] if i > 0 else None
        next_para = paragraphs[i + 1] if i < len(paragraphs) - 1 else None

        # --- Paragraph island check ---
        # A paragraph with no shared citations, no transition, and no shared
        # key nouns with *either* neighbor is an island.
        is_island = True
        for neighbor in (prev_para, next_para):
            if neighbor is None:
                continue
            shared_cites = para.citation_keys & neighbor.citation_keys
            shared_nouns = para.key_nouns & neighbor.key_nouns
            if shared_cites or shared_nouns or para.has_transition:
                is_island = False
                break
        else:
            # If both neighbors are None (single paragraph), not an island.
            if prev_para is None and next_para is None:
                is_island = False

        if is_island:
            findings.append(Finding(
                kind="island",
                line=para.start_line,
                message="Paragraph island: no shared citations or transitions with neighbors",
            ))

        # --- Abrupt topic shift (consecutive pair, only check forward) ---
        if next_para is not None:
            cites_disjoint = (
                bool(para.citation_keys or next_para.citation_keys)
                and not (para.citation_keys & next_para.citation_keys)
            )
            no_transition = not next_para.has_transition
            if cites_disjoint and no_transition:
                findings.append(Finding(
                    kind="topic_shift",
                    line=next_para.start_line,
                    message="Abrupt topic shift between paragraphs",
                ))

        # --- Dangling introduction ---
        # If this paragraph introduces a distinctive term (appears only here)
        # and the next paragraph doesn't reference it at all.
        if next_para is not None:
            introduced = para.key_nouns - (prev_para.key_nouns if prev_para else set())
            if introduced and not (introduced & next_para.key_nouns):
                findings.append(Finding(
                    kind="dangling_intro",
                    line=para.start_line,
                    message="Dangling introduction: concept introduced but not referenced in next paragraph",
                ))

    return findings


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def render_report(
    *,
    created_at: str,
    sections_analyzed: int,
    island_count: int,
    shift_count: int,
    dangling_count: int,
    passed: bool,
    section_findings: list[tuple[str, list[Finding]]],
) -> str:
    result_str = "PASS" if passed else "FAIL"
    lines: list[str] = [
        "# Logic Selfloop Report",
        f"Generated: {created_at}",
        "",
        "## Summary",
        f"- Sections analyzed: {sections_analyzed}",
        f"- Paragraph islands found: {island_count}",
        f"- Abrupt topic shifts: {shift_count}",
        f"- Dangling introductions: {dangling_count}",
        f"- Result: {result_str}",
        "",
    ]

    has_findings = any(fs for _, fs in section_findings)
    if has_findings:
        lines.append("## Findings")
        lines.append("")
        for title, findings in section_findings:
            if not findings:
                continue
            lines.append(f"### Section: {title}")
            lines.append("")
            for f in findings:
                lines.append(f"- [LINE ~{f.line}] {f.message}")
            lines.append("")
    else:
        lines.append("## Findings")
        lines.append("")
        lines.append("No issues found.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check paragraph-level logic coherence within each section of a LaTeX paper."
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Paper project directory containing main.tex (default: .).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        return fail("project dir not found")
    if not project_dir.is_dir():
        return fail("project dir is not a directory")

    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        return fail("main.tex not found in project dir")

    tex_text = main_tex.read_text(encoding="utf-8", errors="replace")
    sections = parse_sections(tex_text)

    island_count = 0
    shift_count = 0
    dangling_count = 0
    section_findings: list[tuple[str, list[Finding]]] = []

    for section in sections:
        findings = analyze_section(section)
        section_findings.append((section.title, findings))
        for f in findings:
            if f.kind == "island":
                island_count += 1
            elif f.kind == "topic_shift":
                shift_count += 1
            elif f.kind == "dangling_intro":
                dangling_count += 1

    passed = island_count == 0 and shift_count <= 2

    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    out_path = notes_dir / "logic-selfloop.md"

    report = render_report(
        created_at=now_iso(),
        sections_analyzed=len(sections),
        island_count=island_count,
        shift_count=shift_count,
        dangling_count=dangling_count,
        passed=passed,
        section_findings=section_findings,
    )

    out_path.write_text(report, encoding="utf-8")

    result_str = "PASS" if passed else "FAIL"
    print(
        f"Logic selfloop: {result_str} "
        f"(sections={len(sections)}, islands={island_count}, "
        f"shifts={shift_count}, dangling={dangling_count})"
    )
    print("Created: notes/logic-selfloop.md")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
