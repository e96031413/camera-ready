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
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from claim_registry import scan_prose_lines
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
    # 2026-09-05-v2: term counts feed a TF-IDF cosine, and the label marks a
    # paragraph that opens a parallel series (F1:, P2:, \textbf{Lead-in.}).
    term_counts: dict[str, int] = field(default_factory=dict)
    is_labelled: bool = False


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


# 2026-09-05-v2: word-overlap alone called every deliberately parallel paragraph
# an island. Coherence is now a TF-IDF cosine over the whole document, and a
# labelled series is exempt from the linkage checks it is designed to violate.
_LABEL_OPENERS = (
    re.compile(r"^\s*\\textbf\{[^}]{2,60}\}[.:]?\s"),
    re.compile(r"^\s*\\item\b"),
    re.compile(r"^\s*[A-Z]{1,3}\d{1,2}\s*[:.]\s"),
    re.compile(r"^\s*\(?\d{1,2}[.)]\s"),
)


def _term_counts(text: str) -> dict[str, int]:
    """Bag of content terms for one paragraph, using the key-noun vocabulary."""
    plain = _LATEX_STRIP_CMDS_RE.sub(r"\1", text)
    plain = _CITE_CMD_RE.sub("", plain)
    plain = _LATEX_STRIP_BARE_RE.sub("", plain)
    plain = plain.replace("{", "").replace("}", "").replace("~", " ")
    plain = _WHITESPACE_RE.sub(" ", plain).lower()
    counts: dict[str, int] = {}
    for word in re.findall(r"[a-z]{4,}", plain):
        if word in _STOP_WORDS:
            continue
        counts[word] = counts.get(word, 0) + 1
    return counts


def _is_labelled(text: str) -> bool:
    """True when the paragraph opens a parallel series rather than continuing prose."""
    head = text.lstrip()
    return any(pattern.match(head) for pattern in _LABEL_OPENERS)


def build_idf(paragraphs: list["Paragraph"]) -> dict[str, float]:
    """Inverse document frequency over paragraphs, the corpus being the paper."""
    total = len(paragraphs)
    if total == 0:
        return {}
    document_frequency: dict[str, int] = {}
    for para in paragraphs:
        for term in para.term_counts:
            document_frequency[term] = document_frequency.get(term, 0) + 1
    return {
        term: math.log((total + 1) / (freq + 1)) + 1.0 for term, freq in document_frequency.items()
    }


def cosine_similarity(a: dict[str, int], b: dict[str, int], idf: dict[str, float]) -> float:
    """TF-IDF cosine between two paragraphs. 0.0 when either side is empty."""
    if not a or not b:
        return 0.0
    va = {t: c * idf.get(t, 1.0) for t, c in a.items()}
    vb = {t: c * idf.get(t, 1.0) for t, c in b.items()}
    norm_a = math.sqrt(sum(v * v for v in va.values()))
    norm_b = math.sqrt(sum(v * v for v in vb.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    shared = set(va) & set(vb)
    dot = sum(va[t] * vb[t] for t in shared)
    return dot / (norm_a * norm_b)


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
    """Parse main.tex into a list of Section objects with raw lines.

    2026-09-05-v2: floats, math and code bodies are blanked first. A TikZ body
    counted as a paragraph shares no vocabulary with anything, so every such
    block used to arrive as a paragraph island.
    """
    prose = scan_prose_lines(tex_text)
    original = tex_text.splitlines()
    # Keep section headings (the scanner strips no headings, but be explicit).
    lines = [
        prose[i] if i < len(prose) else ""
        for i in range(len(original))
    ]
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
                term_counts=_term_counts(full_text),
                is_labelled=_is_labelled(full_text),
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

# Absolute floors, used when a document is too small for its own baseline.
ISLAND_SIMILARITY = 0.010
SHIFT_SIMILARITY = 0.005
# A paragraph is an island when its linkage falls this far below what linkage
# looks like elsewhere in the same paper. Papers differ in vocabulary spread, so
# the bar is relative to the document rather than a constant someone tuned once.
ISLAND_BASELINE_FRACTION = 0.25
SHIFT_BASELINE_FRACTION = 0.50


def adjacent_similarities(
    sections: list["Section"], idf: dict[str, float]
) -> list[float]:
    """Similarity of every adjacent paragraph pair in the document."""
    values: list[float] = []
    for section in sections:
        paragraphs = split_paragraphs(section)
        for a, b in zip(paragraphs, paragraphs[1:]):
            values.append(cosine_similarity(a.term_counts, b.term_counts, idf))
    return values


def baseline_similarity(values: list[float]) -> float:
    """Median adjacent-paragraph similarity: this paper's own notion of linked."""
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def suffix_terms(sections: list["Section"]) -> dict[int, set[str]]:
    """For each paragraph, the terms used anywhere later in the document.

    A concept introduced at the end of one section and picked up in the next is
    not dangling, so the look-ahead has to cross section boundaries.
    """
    ordered = [p for section in sections for p in split_paragraphs(section)]
    result: dict[int, set[str]] = {}
    seen: set[str] = set()
    for para in reversed(ordered):
        result[para.start_line] = set(seen)
        seen |= para.key_nouns
    return result


def analyze_section(
    section: Section,
    idf: dict[str, float] | None = None,
    baseline: float | None = None,
    later_terms_by_line: dict[int, set[str]] | None = None,
) -> list[Finding]:
    """Analyze a single section for logic coherence issues.

    Linkage is measured as TF-IDF cosine between neighbouring paragraphs, not as
    raw word overlap, and a run of labelled paragraphs (F1:, P2:, a bold lead-in)
    is treated as a parallel series: such paragraphs are meant to stand alone, so
    flagging them as disconnected is a false positive, not a finding.
    """
    paragraphs = split_paragraphs(section)
    if len(paragraphs) < 2:
        return []

    if idf is None:
        idf = build_idf(paragraphs)
    if baseline is None:
        baseline = baseline_similarity(adjacent_similarities([section], idf))
    island_floor = max(ISLAND_SIMILARITY, baseline * ISLAND_BASELINE_FRACTION)
    shift_floor = max(SHIFT_SIMILARITY, baseline * SHIFT_BASELINE_FRACTION)

    # A paragraph belongs to a parallel series when it is labelled and at least
    # one neighbour carries a label too.
    in_series = [
        para.is_labelled
        and (
            (i > 0 and paragraphs[i - 1].is_labelled)
            or (i + 1 < len(paragraphs) and paragraphs[i + 1].is_labelled)
        )
        for i, para in enumerate(paragraphs)
    ]

    findings: list[Finding] = []

    for i, para in enumerate(paragraphs):
        prev_para = paragraphs[i - 1] if i > 0 else None
        next_para = paragraphs[i + 1] if i < len(paragraphs) - 1 else None
        if in_series[i]:
            continue

        # --- Paragraph island check ---
        # An island shares no citations, carries no transition, and is
        # semantically unrelated to both neighbours.
        neighbours = [n for n in (prev_para, next_para) if n is not None]
        is_island = bool(neighbours) and not para.has_transition
        for neighbor in neighbours:
            if para.citation_keys & neighbor.citation_keys:
                is_island = False
                break
            if cosine_similarity(para.term_counts, neighbor.term_counts, idf) >= island_floor:
                is_island = False
                break

        if is_island:
            findings.append(Finding(
                kind="island",
                line=para.start_line,
                message="Paragraph island: unrelated to both neighbours (no shared citations, no transition)",
            ))

        # --- Abrupt topic shift (consecutive pair, only check forward) ---
        if next_para is not None and not in_series[i + 1]:
            cites_disjoint = (
                bool(para.citation_keys or next_para.citation_keys)
                and not (para.citation_keys & next_para.citation_keys)
            )
            similarity = cosine_similarity(para.term_counts, next_para.term_counts, idf)
            if cites_disjoint and not next_para.has_transition and similarity < shift_floor:
                findings.append(Finding(
                    kind="topic_shift",
                    line=next_para.start_line,
                    message=f"Abrupt topic shift between paragraphs (similarity {similarity:.2f})",
                ))

        # --- Dangling introduction ---
        # A distinctive term is introduced here, weighs heavily in this
        # paragraph, and never appears again in the section.
        if next_para is not None:
            introduced = para.key_nouns - (prev_para.key_nouns if prev_para else set())
            if later_terms_by_line is not None and para.start_line in later_terms_by_line:
                later_terms = later_terms_by_line[para.start_line]
            else:
                later_terms = set()
                for later in paragraphs[i + 1 :]:
                    later_terms |= later.key_nouns
            # Only the paragraph's own leading terms count: a word used once in
            # passing and never repeated is prose, not an abandoned concept.
            ranked = sorted(
                para.term_counts.items(),
                key=lambda kv: (kv[1] * idf.get(kv[0], 1.0), kv[0]),
                reverse=True,
            )
            leading = {term for term, count in ranked[:3] if count >= 2}
            orphaned = leading & introduced - later_terms
            if orphaned:
                findings.append(Finding(
                    kind="dangling_intro",
                    line=para.start_line,
                    message=(
                        "Dangling introduction: "
                        + ", ".join(sorted(orphaned)[:3])
                        + " introduced here and never used again"
                    ),
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

    # IDF is computed over every paragraph in the paper, so a term that is rare
    # in the document counts for more than one the paper repeats everywhere.
    all_paragraphs = [p for section in sections for p in split_paragraphs(section)]
    idf = build_idf(all_paragraphs)
    baseline = baseline_similarity(adjacent_similarities(sections, idf))
    later_terms = suffix_terms(sections)

    for section in sections:
        findings = analyze_section(section, idf, baseline, later_terms)
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
