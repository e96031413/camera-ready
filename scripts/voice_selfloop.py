#!/usr/bin/env python3
"""Detect generator/planner voice leaks and opener monotony in academic papers.

Scans main.tex for:
1. Zero-tolerance "generator voice" / "planner voice" patterns (instant FAIL)
2. Template phrases that exceed per-pattern caps
3. Paragraph opener monotony (>=3 consecutive paragraphs with same 2-word start)

Outputs a report to notes/voice-selfloop.md.

Exit code:
  0 - PASS (no zero-tolerance violations, no cap violations,
            opener monotony instances < 2)
  1 - FAIL (any zero-tolerance hit OR any cap exceeded OR
            opener monotony >= 2 instances)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from paper_utils import now_iso

# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

ZERO_TOLERANCE: list[str] = [
    r"(?i)\bthis subsection surveys\b",
    r"(?i)\bthis section surveys\b",
    r"(?i)\bthis pipeline\b",
    r"(?i)\bthis workspace\b",
    r"(?i)\bin this section,?\s+we\s+(survey|review|discuss|examine|explore)\b",
    r"(?i)\bthe remainder of this\b",
    r"(?i)\bwe organize this section\b",
    r"(?i)\bthis survey aims to\b",
]

ZERO_TOLERANCE_COMPILED: list[re.Pattern[str]] = [
    re.compile(p) for p in ZERO_TOLERANCE
]

PATTERN_CAPS: dict[str, int] = {
    r"(?i)\btaken together\b": 2,
    r"(?i)\bit is worth noting\b": 1,
    r"(?i)\bin summary\b": 3,
    r"(?i)\bas mentioned (earlier|above|previously)\b": 2,
}

PATTERN_CAPS_COMPILED: list[tuple[re.Pattern[str], str, int]] = [
    (re.compile(p), p, cap) for p, cap in PATTERN_CAPS.items()
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _extract_body(content: str) -> str:
    r"""Return the document body between \begin{document} and \end{document}.

    If markers are absent, return the full content.
    Also strips bibliography sections.
    """
    # Extract between \begin{document} and \end{document}
    begin = re.search(r"\\begin\{document\}", content)
    end = re.search(r"\\end\{document\}", content)
    if begin and end:
        body = content[begin.end() : end.start()]
    elif begin:
        body = content[begin.end() :]
    else:
        body = content

    # Remove content inside \begin{thebibliography}...\end{thebibliography}
    body = re.sub(
        r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
        "",
        body,
        flags=re.DOTALL,
    )

    # Remove everything after \bibliography{...}
    bib_cmd = re.search(r"\\bibliography\{[^}]*\}", body)
    if bib_cmd:
        body = body[: bib_cmd.start()]

    return body


def _content_lines(body: str) -> list[tuple[int, str]]:
    """Return (1-based line number, text) pairs, skipping LaTeX comments."""
    result: list[tuple[int, str]] = []
    for idx, line in enumerate(body.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("%"):
            continue
        result.append((idx, line))
    return result


def _line_number_in_full(body_start_offset: int, content: str, body: str, body_line: int) -> int:
    """Map a line number within *body* back to the full-file line number."""
    # Count newlines before body_start_offset in full content
    prefix = content[:body_start_offset]
    offset = prefix.count("\n")
    return offset + body_line


def _strip_latex_commands(text: str) -> str:
    r"""Strip common LaTeX commands to expose prose words."""
    # Remove \command{arg} keeping arg
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    # Remove remaining \commands
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    # Remove braces, dollars, tildes
    text = re.sub(r"[{}~$%&]", " ", text)
    return text


def _first_n_words(text: str, n: int) -> str:
    """Return the first *n* whitespace-delimited words, lowercased."""
    words = text.split()[:n]
    return " ".join(words).lower()


def _context_snippet(line: str, max_len: int = 60) -> str:
    """Return a short context snippet from a line."""
    line = line.strip()
    if len(line) <= max_len:
        return line
    return line[:max_len] + "..."


# ---------------------------------------------------------------------------
# Section detection (best-effort for monotony report)
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"\\(?:sub)*section\{([^}]+)\}")


def _current_section(lines: list[tuple[int, str]], up_to_line: int) -> str:
    """Return the most recent section/subsection title before *up_to_line*."""
    best = "(preamble)"
    for ln, text in lines:
        if ln > up_to_line:
            break
        m = _SECTION_RE.search(text)
        if m:
            best = m.group(1)
    return best


# ---------------------------------------------------------------------------
# Core scan functions
# ---------------------------------------------------------------------------


def scan_zero_tolerance(
    lines: list[tuple[int, str]],
) -> list[dict]:
    """Find zero-tolerance pattern violations.

    Returns a list of dicts with keys: pattern, line, context.
    """
    hits: list[dict] = []
    for line_num, text in lines:
        for compiled, raw in zip(ZERO_TOLERANCE_COMPILED, ZERO_TOLERANCE):
            if compiled.search(text):
                # Build a human-readable label from the regex
                label = re.sub(r"\(\?i\)", "", raw)
                label = re.sub(r"\\b", "", label)
                label = re.sub(r"\,\?", ",", label)
                label = re.sub(r"\(([^)]+)\)", r"\1", label)
                label = label.replace("\\s+", " ").strip()
                hits.append(
                    {
                        "pattern": label,
                        "line": line_num,
                        "context": _context_snippet(text),
                    }
                )
    return hits


def scan_pattern_caps(
    lines: list[tuple[int, str]],
) -> list[dict]:
    """Find patterns that exceed their per-pattern caps.

    Returns a list of dicts with keys: pattern, cap, found, lines.
    """
    # Collect occurrences per pattern
    occurrences: dict[str, list[int]] = {}
    for line_num, text in lines:
        for compiled, raw, _cap in PATTERN_CAPS_COMPILED:
            if compiled.search(text):
                occurrences.setdefault(raw, []).append(line_num)

    violations: list[dict] = []
    for compiled, raw, cap in PATTERN_CAPS_COMPILED:
        found_lines = occurrences.get(raw, [])
        if len(found_lines) > cap:
            label = re.sub(r"\(\?i\)", "", raw)
            label = re.sub(r"\\b", "", label)
            label = re.sub(r"\(([^)]+)\)", r"\1", label)
            label = label.replace("\\s+", " ").strip()
            violations.append(
                {
                    "pattern": label,
                    "cap": cap,
                    "found": len(found_lines),
                    "lines": found_lines,
                }
            )
    return violations


def scan_opener_monotony(
    body: str,
    all_lines: list[tuple[int, str]],
) -> list[dict]:
    """Detect consecutive paragraphs that open with the same 2-word pattern.

    A "paragraph" is a block of text separated by blank lines with >=2
    non-empty content lines (after stripping comments).

    Returns a list of dicts with keys: section, lines, opener.
    """
    # Split body into paragraphs.
    # We work on raw body lines (comments already excluded from all_lines,
    # but we need positional info).
    raw_lines = body.splitlines()

    # Build paragraphs: groups of consecutive non-blank, non-comment lines
    # separated by blank lines.
    paragraphs: list[dict] = []  # {start_line, opener}
    current_block: list[tuple[int, str]] = []

    for idx, raw_line in enumerate(raw_lines):
        line_num = idx + 1
        stripped = raw_line.strip()

        if stripped.startswith("%"):
            continue

        if stripped == "":
            # End of paragraph candidate
            if len(current_block) >= 2:
                first_text = current_block[0][1]
                cleaned = _strip_latex_commands(first_text)
                opener = _first_n_words(cleaned, 2)
                if opener:  # non-empty
                    paragraphs.append(
                        {
                            "start_line": current_block[0][0],
                            "opener": opener,
                        }
                    )
            current_block = []
        else:
            current_block.append((line_num, raw_line))

    # Handle final block
    if len(current_block) >= 2:
        first_text = current_block[0][1]
        cleaned = _strip_latex_commands(first_text)
        opener = _first_n_words(cleaned, 2)
        if opener:
            paragraphs.append(
                {
                    "start_line": current_block[0][0],
                    "opener": opener,
                }
            )

    # Detect runs of >=3 consecutive paragraphs with the same opener
    monotony_hits: list[dict] = []
    if len(paragraphs) < 3:
        return monotony_hits

    run_start = 0
    for i in range(1, len(paragraphs)):
        if paragraphs[i]["opener"] == paragraphs[run_start]["opener"]:
            run_len = i - run_start + 1
            if run_len >= 3:
                # Check if we already recorded this run (extend)
                run_lines = [
                    paragraphs[j]["start_line"]
                    for j in range(run_start, i + 1)
                ]
                section = _current_section(all_lines, paragraphs[run_start]["start_line"])
                # Only record once per run (update last entry if same run_start)
                if monotony_hits and monotony_hits[-1]["_run_start"] == run_start:
                    monotony_hits[-1]["lines"] = run_lines
                else:
                    monotony_hits.append(
                        {
                            "section": section,
                            "lines": run_lines,
                            "opener": paragraphs[run_start]["opener"],
                            "_run_start": run_start,
                        }
                    )
        else:
            run_start = i

    # Remove internal bookkeeping key
    for hit in monotony_hits:
        hit.pop("_run_start", None)

    return monotony_hits


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    zero_hits: list[dict],
    cap_hits: list[dict],
    monotony_hits: list[dict],
    timestamp: str,
) -> str:
    """Generate the voice-selfloop report as Markdown."""
    n_zero = len(zero_hits)
    n_cap = len(cap_hits)
    n_mono = len(monotony_hits)
    passed = n_zero == 0 and n_cap == 0 and n_mono < 2
    result_label = "PASS" if passed else "FAIL"

    lines: list[str] = [
        "# Voice Selfloop Report",
        f"Generated: {timestamp}",
        "",
        "## Summary",
        f"- Zero-tolerance violations: {n_zero}",
        f"- Pattern cap violations: {n_cap}",
        f"- Opener monotony instances: {n_mono}",
        f"- Result: {result_label}",
        "",
    ]

    # Zero-tolerance section
    lines.append("## Zero-Tolerance Violations (must fix)")
    if zero_hits:
        lines.append("| Pattern | Line | Context |")
        lines.append("|---|---|---|")
        for h in zero_hits:
            ctx = h["context"].replace("|", "\\|")
            lines.append(f'| "{h["pattern"]}" | {h["line"]} | {ctx} |')
    else:
        lines.append("None found.")
    lines.append("")

    # Pattern cap section
    lines.append("## Pattern Cap Violations")
    if cap_hits:
        lines.append("| Pattern | Cap | Found | Lines |")
        lines.append("|---|---|---|---|")
        for h in cap_hits:
            line_refs = ", ".join(str(ln) for ln in h["lines"])
            lines.append(f'| "{h["pattern"]}" | {h["cap"]} | {h["found"]} | {line_refs} |')
    else:
        lines.append("None found.")
    lines.append("")

    # Opener monotony section
    lines.append("## Opener Monotony")
    if monotony_hits:
        lines.append("| Section | Lines | Repeated Opener |")
        lines.append("|---|---|---|")
        for h in monotony_hits:
            line_refs = ", ".join(str(ln) for ln in h["lines"])
            lines.append(f'| {h["section"]} | {line_refs} | "{h["opener"]}" |')
    else:
        lines.append("None found.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Run voice selfloop scan on a paper project."""
    parser = argparse.ArgumentParser(
        description="Detect generator/planner voice leaks and opener monotony."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Paper project directory containing main.tex.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        return fail(f"project dir not found: {project_dir}")

    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        return fail(f"main.tex not found in {project_dir}")

    content = main_tex.read_text(encoding="utf-8", errors="replace")

    # Determine body start offset for line-number mapping
    begin_match = re.search(r"\\begin\{document\}", content)
    body_start_offset = begin_match.end() if begin_match else 0

    body = _extract_body(content)
    all_lines = _content_lines(body)

    # Remap line numbers to full-file positions
    body_lines_raw = body.splitlines()
    full_lines: list[tuple[int, str]] = []
    prefix_newlines = content[:body_start_offset].count("\n")
    for body_ln, text in all_lines:
        full_ln = prefix_newlines + body_ln
        full_lines.append((full_ln, text))

    # 1. Zero-tolerance scan
    zero_hits = scan_zero_tolerance(full_lines)

    # 2. Pattern cap scan
    cap_hits = scan_pattern_caps(full_lines)

    # 3. Opener monotony scan (needs raw body for paragraph splitting)
    monotony_hits = scan_opener_monotony(body, full_lines)

    # Generate report
    timestamp = now_iso()
    report = generate_report(zero_hits, cap_hits, monotony_hits, timestamp)

    # Write report
    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    report_path = notes_dir / "voice-selfloop.md"
    report_path.write_text(report, encoding="utf-8")

    n_zero = len(zero_hits)
    n_cap = len(cap_hits)
    n_mono = len(monotony_hits)
    passed = n_zero == 0 and n_cap == 0 and n_mono < 2
    result_label = "PASS" if passed else "FAIL"

    print(f"Voice selfloop scan: {result_label}")
    print(f"  Zero-tolerance violations: {n_zero}")
    print(f"  Pattern cap violations:    {n_cap}")
    print(f"  Opener monotony instances: {n_mono}")
    print(f"Report written to: {report_path}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
