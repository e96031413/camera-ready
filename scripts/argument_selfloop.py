#!/usr/bin/env python3
"""Verify claim-evidence chains in an academic paper.

Cross-checks the claim registry against main.tex to find:
  - Orphan claims (no evidence and no citation in their section)
  - Unsupported passages (≥3 consecutive sentences without citations)
  - Citation-claim misalignments (listed citation keys not found in main.tex)

Outputs:
  - <project-dir>/notes/argument-selfloop.md

Design goals:
- stdlib-only, deterministic output
- does not print absolute filesystem paths
- exit code 0 = PASS, 1 = FAIL
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from paper_utils import now_iso


# ---------------------------------------------------------------------------
# Regex patterns (matching claim_registry.py conventions)
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"\\section\{([^}]+)\}")
_SUBSECTION_RE = re.compile(r"\\subsection\{([^}]+)\}")
_COMMENT_RE = re.compile(r"(?<!\\)%.*$")
_BIB_STOP_RE = re.compile(r"\\bibliography\{|\\begin\{thebibliography\}", re.IGNORECASE)
_CITE_CMD_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegistryClaim:
    id: str
    section: str
    claim: str
    citations: list[str]
    verdict: str
    notes: str


@dataclass
class OrphanClaim:
    id: str
    section: str
    claim: str


@dataclass
class UnsupportedPassage:
    section: str
    approx_line: int
    consecutive_count: int


@dataclass
class CitationMisalignment:
    claim_id: str
    missing_key: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def strip_comments(line: str) -> str:
    return _COMMENT_RE.sub("", line)


def extract_cite_keys(text: str) -> list[str]:
    """Extract all citation keys from a block of LaTeX text."""
    keys: list[str] = []
    for match in _CITE_CMD_RE.finditer(text):
        for raw in match.group(1).split(","):
            key = raw.strip()
            if key:
                keys.append(key)
    return sorted(set(keys))


def truncate(text: str, max_len: int = 50) -> str:
    """Truncate text for display in tables."""
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def escape_md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


# ---------------------------------------------------------------------------
# Claim registry parsing
# ---------------------------------------------------------------------------

def _parse_citation_field(raw: str) -> list[str]:
    """Parse a citations field into a list of citation keys."""
    keys: list[str] = []
    for part in raw.split(","):
        key = part.strip().strip('"').strip("'")
        if key:
            keys.append(key)
    return keys


def parse_registry_csv(csv_path: Path) -> list[RegistryClaim]:
    """Parse notes/claim-registry.csv into a list of RegistryClaim."""
    claims: list[RegistryClaim] = []
    with csv_path.open("r", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cid = row.get("ID", "").strip()
            if not cid:
                continue
            claims.append(
                RegistryClaim(
                    id=cid,
                    section=row.get("Section", "").strip(),
                    claim=row.get("Claim", "").strip(),
                    citations=_parse_citation_field(row.get("Citations_Evidence", "")),
                    verdict=row.get("Verdict", "").strip(),
                    notes=row.get("Notes", "").strip(),
                )
            )
    return claims


def parse_registry_md(md_path: Path) -> list[RegistryClaim]:
    """Parse notes/claim-registry.md markdown table into a list of RegistryClaim."""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    claims: list[RegistryClaim] = []

    in_table = False
    header_indices: dict[str, int] = {}

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            header_indices = {}
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]

        # Detect separator row (|---|---|...)
        if all(re.fullmatch(r"-+", c.strip()) or c.strip() == "" for c in cells):
            in_table = True
            continue

        # Detect header row
        if not in_table and not header_indices:
            lower_cells = [c.lower() for c in cells]
            col_map = {
                "id": "id",
                "section": "section",
                "claim": "claim",
                "citations / evidence": "citations",
                "citations_evidence": "citations",
                "verdict": "verdict",
                "notes": "notes",
            }
            for idx, lc in enumerate(lower_cells):
                for pattern, name in col_map.items():
                    if pattern in lc:
                        header_indices[name] = idx
                        break
            continue

        if not in_table or not header_indices:
            continue

        def _get(name: str) -> str:
            idx = header_indices.get(name)
            if idx is None or idx >= len(cells):
                return ""
            return cells[idx].strip()

        cid = _get("id")
        if not cid:
            continue

        claims.append(
            RegistryClaim(
                id=cid,
                section=_get("section"),
                claim=_get("claim"),
                citations=_parse_citation_field(_get("citations")),
                verdict=_get("verdict"),
                notes=_get("notes"),
            )
        )

    return claims


def load_registry(notes_dir: Path) -> list[RegistryClaim] | None:
    """Load claim registry from CSV (preferred) or MD fallback.

    Returns None if no registry file exists.
    """
    csv_path = notes_dir / "claim-registry.csv"
    md_path = notes_dir / "claim-registry.md"

    if csv_path.exists():
        return parse_registry_csv(csv_path)
    if md_path.exists():
        return parse_registry_md(md_path)
    return None


# ---------------------------------------------------------------------------
# LaTeX section parsing (section -> text with line tracking)
# ---------------------------------------------------------------------------

@dataclass
class SectionBlock:
    name: str
    lines: list[tuple[int, str]] = field(default_factory=list)  # (line_number, text)


def parse_sections(tex_lines: list[str]) -> list[SectionBlock]:
    """Parse main.tex into section blocks, tracking original line numbers."""
    blocks: list[SectionBlock] = []
    current = SectionBlock(name="(frontmatter)")

    for line_no, raw in enumerate(tex_lines, start=1):
        if _BIB_STOP_RE.search(raw):
            break

        cleaned = strip_comments(raw).rstrip("\n")

        sec = _SECTION_RE.search(cleaned)
        if sec:
            if current.lines:
                blocks.append(current)
            current = SectionBlock(name=sec.group(1).strip())
            continue

        sub = _SUBSECTION_RE.search(cleaned)
        if sub:
            if current.lines:
                blocks.append(current)
            current = SectionBlock(name=f"{current.name.split(' / ')[0]} / {sub.group(1).strip()}")
            continue

        if cleaned.strip():
            current.lines.append((line_no, cleaned))

    if current.lines:
        blocks.append(current)

    return blocks


def collect_all_cite_keys(tex_text: str) -> set[str]:
    """Collect every citation key used anywhere in main.tex."""
    keys: set[str] = set()
    for match in _CITE_CMD_RE.finditer(tex_text):
        for raw in match.group(1).split(","):
            key = raw.strip()
            if key:
                keys.add(key)
    return keys


def section_cite_keys(block: SectionBlock) -> set[str]:
    """Extract all citation keys from a section block."""
    keys: set[str] = set()
    for _, line in block.lines:
        for match in _CITE_CMD_RE.finditer(line):
            for raw in match.group(1).split(","):
                key = raw.strip()
                if key:
                    keys.add(key)
    return keys


# ---------------------------------------------------------------------------
# Cross-check logic
# ---------------------------------------------------------------------------

def _normalize_section_name(name: str) -> str:
    """Normalize a section name for fuzzy matching."""
    return _WHITESPACE_RE.sub(" ", name).strip().lower()


def find_orphan_claims(
    claims: list[RegistryClaim],
    sections: list[SectionBlock],
) -> list[OrphanClaim]:
    """Find claims with no citations that also live in sections without supporting cites."""
    # Build a map of normalized section name -> set of cite keys
    section_cites: dict[str, set[str]] = {}
    for block in sections:
        norm = _normalize_section_name(block.name)
        keys = section_cite_keys(block)
        if norm in section_cites:
            section_cites[norm] |= keys
        else:
            section_cites[norm] = keys

    orphans: list[OrphanClaim] = []
    for claim in claims:
        # Only consider claims with empty citations
        if claim.citations:
            continue

        claim_section_norm = _normalize_section_name(claim.section)

        # Check if any section whose normalized name contains or is contained by
        # the claim's section name has citation support
        has_support = False
        for sec_norm, keys in section_cites.items():
            if claim_section_norm in sec_norm or sec_norm in claim_section_norm:
                if keys:
                    has_support = True
                    break

        if not has_support:
            orphans.append(
                OrphanClaim(
                    id=claim.id,
                    section=claim.section,
                    claim=claim.claim,
                )
            )

    return orphans


def find_unsupported_passages(
    sections: list[SectionBlock],
    *,
    min_consecutive: int = 3,
) -> list[UnsupportedPassage]:
    """Find passages with ≥min_consecutive sentences without any \\cite command."""
    passages: list[UnsupportedPassage] = []

    for block in sections:
        # Join all lines in the section to split into sentences
        full_text = " ".join(text for _, text in block.lines)
        sentences = _SENTENCE_SPLIT_RE.split(full_text)

        # Build a rough line-number map: for each character offset, which source line?
        # We'll approximate by tracking cumulative lengths.
        line_numbers = [ln for ln, _ in block.lines]
        line_texts = [text for _, text in block.lines]
        char_to_line: list[int] = []
        for ln, text in zip(line_numbers, line_texts):
            # +1 for the space we joined with
            char_to_line.extend([ln] * (len(text) + 1))

        consecutive = 0
        first_offset = 0
        current_offset = 0

        for sentence in sentences:
            sentence_stripped = sentence.strip()
            if not sentence_stripped:
                current_offset += len(sentence) + 1
                continue

            has_cite = bool(_CITE_CMD_RE.search(sentence))

            if not has_cite:
                if consecutive == 0:
                    first_offset = current_offset
                consecutive += 1
            else:
                if consecutive >= min_consecutive:
                    # Approximate line number from first_offset
                    approx_line = line_numbers[0] if not char_to_line else (
                        char_to_line[min(first_offset, len(char_to_line) - 1)]
                        if char_to_line
                        else line_numbers[0]
                    )
                    passages.append(
                        UnsupportedPassage(
                            section=block.name,
                            approx_line=approx_line,
                            consecutive_count=consecutive,
                        )
                    )
                consecutive = 0

            current_offset += len(sentence) + 1  # +1 for split whitespace

        # Flush trailing run
        if consecutive >= min_consecutive:
            approx_line = line_numbers[0] if not char_to_line else (
                char_to_line[min(first_offset, len(char_to_line) - 1)]
                if char_to_line
                else line_numbers[0]
            )
            passages.append(
                UnsupportedPassage(
                    section=block.name,
                    approx_line=approx_line,
                    consecutive_count=consecutive,
                )
            )

    return passages


def find_citation_misalignments(
    claims: list[RegistryClaim],
    all_keys: set[str],
) -> list[CitationMisalignment]:
    """For each claim with listed citations, verify those keys appear in main.tex."""
    misalignments: list[CitationMisalignment] = []
    for claim in claims:
        for key in claim.citations:
            if key not in all_keys:
                misalignments.append(
                    CitationMisalignment(claim_id=claim.id, missing_key=key)
                )
    return misalignments


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_report(
    *,
    created_at: str,
    claims: list[RegistryClaim],
    orphans: list[OrphanClaim],
    unsupported: list[UnsupportedPassage],
    misalignments: list[CitationMisalignment],
) -> str:
    is_pass = len(orphans) == 0 and len(unsupported) == 0 and len(misalignments) == 0
    result = "PASS" if is_pass else "FAIL"

    lines: list[str] = [
        "# Argument Selfloop Report",
        f"Generated: {created_at}",
        "",
        "## Summary",
        f"- Total claims checked: {len(claims)}",
        f"- Orphan claims (no evidence): {len(orphans)}",
        f"- Unsupported sections (\u22653 sentences without citation): {len(unsupported)}",
        f"- Citation-claim misalignments: {len(misalignments)}",
        f"- Result: {result}",
        "",
    ]

    # Orphan Claims
    lines.append("## Orphan Claims")
    lines.append("| ID | Section | Claim (truncated) |")
    lines.append("|---|---|---|")
    if orphans:
        for o in orphans:
            lines.append(
                f"| {escape_md_cell(o.id)} "
                f"| {escape_md_cell(o.section)} "
                f"| {escape_md_cell(truncate(o.claim))} |"
            )
    lines.append("")

    # Unsupported Passages
    lines.append("## Unsupported Passages")
    lines.append("| Section | Approximate Line | Consecutive Uncited Sentences |")
    lines.append("|---|---|---|")
    if unsupported:
        for u in unsupported:
            lines.append(
                f"| {escape_md_cell(u.section)} "
                f"| ~Line {u.approx_line} "
                f"| {u.consecutive_count} |"
            )
    lines.append("")

    # Citation-Claim Misalignments
    lines.append("## Citation-Claim Misalignments")
    lines.append("| Claim ID | Missing Citation Key |")
    lines.append("|---|---|")
    if misalignments:
        for m in misalignments:
            lines.append(
                f"| {escape_md_cell(m.claim_id)} "
                f"| {escape_md_cell(m.missing_key)} |"
            )
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify claim-evidence chains in an academic paper."
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

    notes_dir = project_dir / "notes"

    # Load claim registry
    claims = load_registry(notes_dir)
    if claims is None:
        print("warning: no claim registry found (notes/claim-registry.csv or .md); nothing to check.", file=sys.stderr)
        return 0

    # Load main.tex
    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        return fail("main.tex not found in project dir")

    tex_text = main_tex.read_text(encoding="utf-8", errors="replace")
    tex_lines = tex_text.splitlines()

    # Parse sections and collect citation keys
    sections = parse_sections(tex_lines)
    all_keys = collect_all_cite_keys(tex_text)

    # Cross-checks
    orphans = find_orphan_claims(claims, sections)
    unsupported = find_unsupported_passages(sections)
    misalignments = find_citation_misalignments(claims, all_keys)

    # Render and write report
    report = render_report(
        created_at=now_iso(),
        claims=claims,
        orphans=orphans,
        unsupported=unsupported,
        misalignments=misalignments,
    )

    notes_dir.mkdir(parents=True, exist_ok=True)
    out_path = notes_dir / "argument-selfloop.md"
    out_path.write_text(report, encoding="utf-8")

    is_pass = len(orphans) == 0 and len(unsupported) == 0 and len(misalignments) == 0
    result = "PASS" if is_pass else "FAIL"
    print(
        f"Created: notes/argument-selfloop.md "
        f"(claims={len(claims)}, orphans={len(orphans)}, "
        f"unsupported={len(unsupported)}, misalignments={len(misalignments)}, "
        f"result={result})"
    )
    return 0 if is_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
