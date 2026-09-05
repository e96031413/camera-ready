#!/usr/bin/env python3
"""Scan main.tex for common AI writing patterns.

Detects filler phrases, AI-typical vocabulary, and structural patterns
that are commonly flagged in AI-generated academic text.  Outputs a
report to notes/anti-ai-report.md.

Exit code:
  0 - LOW severity (0-5 total patterns) or PASS in strict mode
  1 - MEDIUM or HIGH severity (6+ total patterns) or FAIL in strict mode
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

FILLER_PHRASES: list[str] = [
    "due to the fact that",
    "in order to",
    "it is worth noting",
    "it should be noted",
    "plays a crucial role",
    "it is important to note",
]

AI_VOCABULARY: list[str] = [
    "additionally",
    "crucial",
    "delve",
    "enhance",
    "furthermore",
    "landscape",
    "leveraging",
    "multifaceted",
    "notably",
    "pivotal",
    "realm",
    "robust",
    "streamline",
    "tapestry",
    "transformative",
    "underscore",
    "foster",
    "paramount",
    "intricate",
    "holistic",
]

STRUCTURAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"not only\b.*\bbut also\b", re.IGNORECASE),
    re.compile(r"\bstands as a testament\b", re.IGNORECASE),
    re.compile(r"\brich (?:tapestry|heritage)\b", re.IGNORECASE),
]

# Replacement suggestions for common filler phrases
REPLACEMENTS: dict[str, str] = {
    "due to the fact that": "because",
    "in order to": "to",
    "it is worth noting": "(remove or rephrase)",
    "it should be noted": "(remove or rephrase)",
    "plays a crucial role": "is important / matters",
    "it is important to note": "(remove or rephrase)",
}

# ---------------------------------------------------------------------------
# Strict-mode definitions
# ---------------------------------------------------------------------------

# Zero-tolerance generator/planner voice (must be 0)
STRICT_ZERO_TOLERANCE: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bthis subsection surveys\b"),
    re.compile(r"(?i)\bthis section surveys\b"),
    re.compile(r"(?i)\bthis pipeline\b"),
    re.compile(r"(?i)\bthis workspace\b"),
    re.compile(r"(?i)\bin this section,?\s+we\s+(?:survey|review|discuss|examine|explore)\b"),
    re.compile(r"(?i)\bthe remainder of this\b"),
    re.compile(r"(?i)\bwe organize this section\b"),
    re.compile(r"(?i)\bthis survey aims to\b"),
]

# Per-pattern occurrence caps
STRICT_PATTERN_CAPS: dict[str, int] = {
    "taken together": 2,
    "it is worth noting": 1,
    "in summary": 3,
    "as mentioned earlier": 2,
    "as mentioned above": 2,
    "as mentioned previously": 2,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CITE_CMD_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_BIB_STOP_RE = re.compile(r"\\bibliography\{|\\begin\{thebibliography\}", re.IGNORECASE)


def _is_content_line(line: str) -> bool:
    """Return True if the line is not a LaTeX comment or pure command."""
    stripped = line.lstrip()
    if stripped.startswith("%"):
        return False
    return True


def _extract_body(content: str) -> str:
    """Extract content between \\begin{document} and \\end{document}, stopping at bibliography."""
    start = content.find("\\begin{document}")
    end = content.find("\\end{document}")
    if start != -1:
        body = content[start:]
    else:
        body = content
    if end != -1 and start != -1:
        body = content[start:end]
    # Stop at bibliography
    for m in _BIB_STOP_RE.finditer(body):
        body = body[:m.start()]
        break
    return body


def scan_content(content: str) -> list[dict]:
    """Scan LaTeX content for AI writing patterns.

    Returns a list of findings, each a dict with keys:
      pattern, count, lines
    """
    lines = content.splitlines()
    content_lines: list[tuple[int, str]] = []
    for idx, line in enumerate(lines, start=1):
        if _is_content_line(line):
            content_lines.append((idx, line))

    findings: dict[str, list[int]] = {}

    for line_num, line in content_lines:
        lowered = line.lower()

        # Filler phrases
        for phrase in FILLER_PHRASES:
            if phrase in lowered:
                findings.setdefault(phrase, []).append(line_num)

        # AI vocabulary (match as whole words)
        for word in AI_VOCABULARY:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            if pattern.search(line):
                findings.setdefault(word, []).append(line_num)

        # Structural patterns
        for pat in STRUCTURAL_PATTERNS:
            if pat.search(line):
                label = pat.pattern
                findings.setdefault(label, []).append(line_num)

    result: list[dict] = []
    for pattern_str, line_nums in sorted(findings.items()):
        result.append(
            {
                "pattern": pattern_str,
                "count": len(line_nums),
                "lines": line_nums,
            }
        )
    return result


def severity_label(total: int) -> str:
    """Return severity label based on total pattern count."""
    if total <= 5:
        return "LOW"
    if total <= 15:
        return "MEDIUM"
    return "HIGH"


# ---------------------------------------------------------------------------
# Strict-mode checks
# ---------------------------------------------------------------------------


def check_zero_tolerance(content: str) -> list[dict]:
    """Check for zero-tolerance generator/planner voice patterns."""
    violations: list[dict] = []
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        if not _is_content_line(line):
            continue
        for pat in STRICT_ZERO_TOLERANCE:
            m = pat.search(line)
            if m:
                violations.append({
                    "pattern": pat.pattern,
                    "line": idx,
                    "context": line.strip()[:100],
                })
    return violations


def check_pattern_caps(content: str) -> list[dict]:
    """Check per-pattern occurrence caps."""
    violations: list[dict] = []
    lines = content.splitlines()
    counts: dict[str, list[int]] = {}

    for idx, line in enumerate(lines, start=1):
        if not _is_content_line(line):
            continue
        lowered = line.lower()
        for phrase, cap in STRICT_PATTERN_CAPS.items():
            if phrase in lowered:
                counts.setdefault(phrase, []).append(idx)

    for phrase, line_nums in sorted(counts.items()):
        cap = STRICT_PATTERN_CAPS[phrase]
        if len(line_nums) > cap:
            violations.append({
                "pattern": phrase,
                "cap": cap,
                "found": len(line_nums),
                "lines": line_nums,
            })
    return violations


def check_mid_sentence_citation_ratio(content: str) -> dict:
    """Check that ≥30% of citations appear mid-sentence (not at sentence start/end)."""
    body = _extract_body(content)
    lines = body.splitlines()

    total_cites = 0
    mid_sentence_cites = 0

    for line in lines:
        if not _is_content_line(line):
            continue
        for m in _CITE_CMD_RE.finditer(line):
            total_cites += 1
            start_pos = m.start()
            end_pos = m.end()
            before = line[:start_pos].rstrip()
            after = line[end_pos:].lstrip()
            # Mid-sentence: has text both before and after the cite
            has_text_before = bool(before) and not before.endswith((".","!","?","{"))
            has_text_after = bool(after) and not after.startswith((".","!","?","}","\\"))
            if has_text_before and has_text_after:
                mid_sentence_cites += 1

    ratio = (mid_sentence_cites / total_cites) if total_cites > 0 else 1.0
    return {
        "total_cites": total_cites,
        "mid_sentence": mid_sentence_cites,
        "ratio": ratio,
    }


def check_opener_diversity(content: str) -> list[dict]:
    """Check for consecutive paragraphs with the same opening pattern."""
    body = _extract_body(content)
    # Split by section
    section_re = re.compile(r"\\(?:section|subsection)\{([^}]+)\}")
    sections: list[tuple[str, str]] = []
    parts = section_re.split(body)

    # parts = [pre, title1, body1, title2, body2, ...]
    for i in range(1, len(parts) - 1, 2):
        title = parts[i].strip()
        text = parts[i + 1] if i + 1 < len(parts) else ""
        sections.append((title, text))

    violations: list[dict] = []
    for sec_title, sec_text in sections:
        # Split paragraphs by blank lines
        raw_paragraphs = re.split(r"\n\s*\n", sec_text)
        openers: list[str] = []
        for para in raw_paragraphs:
            lines = [l.strip() for l in para.splitlines()
                     if l.strip() and not l.strip().startswith("%")
                     and not l.strip().startswith("\\begin")
                     and not l.strip().startswith("\\end")
                     and not l.strip().startswith("\\label")
                     and not l.strip().startswith("\\caption")]
            if len(lines) < 2:
                continue
            first_line = lines[0]
            # Remove LaTeX commands for opener comparison
            cleaned = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", first_line)
            cleaned = re.sub(r"\\[a-zA-Z]+", "", cleaned)
            cleaned = re.sub(r"[{}~$]", " ", cleaned).strip()
            words = cleaned.split()[:2]
            opener = " ".join(words).lower() if words else ""
            openers.append(opener)

        # Check for 3+ consecutive identical openers
        if len(openers) >= 3:
            for i in range(len(openers) - 2):
                if openers[i] and openers[i] == openers[i+1] == openers[i+2]:
                    violations.append({
                        "section": sec_title,
                        "opener": openers[i],
                        "count": 3,
                    })
    return violations


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    findings: list[dict],
    timestamp: str,
    *,
    strict: bool = False,
    zero_tolerance: list[dict] | None = None,
    pattern_caps: list[dict] | None = None,
    citation_ratio: dict | None = None,
    opener_issues: list[dict] | None = None,
) -> str:
    """Generate the anti-AI report as Markdown."""
    total = sum(f["count"] for f in findings)
    severity = severity_label(total)

    lines = [
        "# Anti-AI Writing Scan",
        f"Generated: {timestamp}",
        "",
        "## Summary",
        f"- Total AI patterns found: {total}",
        f"- Severity: {severity} (0-5=LOW, 6-15=MEDIUM, 16+=HIGH)",
        "",
    ]

    if findings:
        lines.append("## Findings")
        lines.append("| Pattern | Count | Lines |")
        lines.append("|---------|-------|-------|")
        for f in findings:
            line_refs = ", ".join(str(ln) for ln in f["lines"])
            lines.append(f'| "{f["pattern"]}" | {f["count"]} | {line_refs} |')
        lines.append("")

    # Recommendations
    applicable_replacements = [
        (phrase, replacement)
        for phrase, replacement in REPLACEMENTS.items()
        if any(f["pattern"] == phrase for f in findings)
    ]
    if applicable_replacements:
        lines.append("## Recommendations")
        for phrase, replacement in applicable_replacements:
            lines.append(f'- Replace "{phrase}" -> "{replacement}"')
        lines.append("")

    # Strict mode section
    if strict:
        lines.append("---")
        lines.append("")
        lines.append("## Strict Mode Checks")
        lines.append("")

        # Zero tolerance
        zt = zero_tolerance or []
        lines.append(f"### Zero-Tolerance Violations: {len(zt)}")
        if zt:
            lines.append("| Pattern | Line | Context |")
            lines.append("|---------|------|---------|")
            for v in zt:
                lines.append(f'| `{v["pattern"]}` | {v["line"]} | {v["context"]} |')
        else:
            lines.append("- (none)")
        lines.append("")

        # Pattern caps
        pc = pattern_caps or []
        lines.append(f"### Pattern Cap Violations: {len(pc)}")
        if pc:
            lines.append("| Pattern | Cap | Found | Lines |")
            lines.append("|---------|-----|-------|-------|")
            for v in pc:
                ls = ", ".join(str(ln) for ln in v["lines"])
                lines.append(f'| "{v["pattern"]}" | {v["cap"]} | {v["found"]} | {ls} |')
        else:
            lines.append("- (none)")
        lines.append("")

        # Citation ratio
        cr = citation_ratio or {}
        ratio = cr.get("ratio", 1.0)
        total_c = cr.get("total_cites", 0)
        mid_c = cr.get("mid_sentence", 0)
        passed = ratio >= 0.30 or total_c == 0
        lines.append(f"### Mid-Sentence Citation Ratio: {'PASS' if passed else 'FAIL'}")
        lines.append(f"- Total citations: {total_c}")
        lines.append(f"- Mid-sentence citations: {mid_c}")
        lines.append(f"- Ratio: {ratio:.1%} (threshold: ≥30%)")
        lines.append("")

        # Opener diversity
        od = opener_issues or []
        lines.append(f"### Opener Monotony: {len(od)} instance(s)")
        if od:
            lines.append("| Section | Repeated Opener |")
            lines.append("|---------|-----------------|")
            for v in od:
                lines.append(f'| {v["section"]} | "{v["opener"]}" |')
        else:
            lines.append("- (none)")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    """Run anti-AI writing scan on a paper project."""
    parser = argparse.ArgumentParser(
        description="Scan main.tex for common AI writing patterns."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Paper project directory containing main.tex.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode: per-pattern caps, zero-tolerance checks, citation ratio, opener diversity.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        print(f"error: project dir not found: {project_dir}", file=sys.stderr)
        return 1

    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        print(f"error: main.tex not found in {project_dir}", file=sys.stderr)
        return 1

    content = main_tex.read_text(encoding="utf-8", errors="replace")
    findings = scan_content(content)

    # Strict-mode checks
    zero_tolerance: list[dict] = []
    pattern_caps: list[dict] = []
    citation_ratio: dict = {}
    opener_issues: list[dict] = []
    strict_fail = False

    if args.strict:
        zero_tolerance = check_zero_tolerance(content)
        pattern_caps = check_pattern_caps(content)
        citation_ratio = check_mid_sentence_citation_ratio(content)
        opener_issues = check_opener_diversity(content)

        if zero_tolerance:
            strict_fail = True
        if pattern_caps:
            strict_fail = True
        if citation_ratio.get("total_cites", 0) > 0 and citation_ratio.get("ratio", 1.0) < 0.30:
            strict_fail = True
        if len(opener_issues) >= 2:
            strict_fail = True

    timestamp = now_iso()
    report = generate_report(
        findings,
        timestamp,
        strict=args.strict,
        zero_tolerance=zero_tolerance,
        pattern_caps=pattern_caps,
        citation_ratio=citation_ratio,
        opener_issues=opener_issues,
    )

    # Write report
    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    report_path = notes_dir / "anti-ai-report.md"
    report_path.write_text(report, encoding="utf-8")

    total = sum(f["count"] for f in findings)
    severity = severity_label(total)
    print(f"Anti-AI scan complete: {total} patterns found ({severity})")
    if args.strict:
        strict_label = "FAIL" if strict_fail else "PASS"
        print(f"Strict mode: {strict_label}")
    print(f"Report written to: {report_path}")

    if args.strict and strict_fail:
        return 1
    if severity in ("MEDIUM", "HIGH"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
