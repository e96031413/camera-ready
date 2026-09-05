#!/usr/bin/env python3
"""Generate a claim registry from a LaTeX paper project (integrity helper).

Outputs (under <project-dir>/notes/):
  - claim-registry.md
  - claim-registry.csv (optional)

Design goals:
- Deterministic and lightweight (stdlib-only).
- Privacy-safe: do not print absolute filesystem paths.
- Heuristic extraction: identifies *candidate* claims for verification.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from paper_utils import now_iso, check_refined_guard


_SECTION_RE = re.compile(r"\\section\{([^}]+)\}")
_SUBSECTION_RE = re.compile(r"\\subsection\{([^}]+)\}")
_COMMENT_RE = re.compile(r"(?<!\\)%.*$")
_BIB_STOP_RE = re.compile(r"\\bibliography\{|\\begin\{thebibliography\}", re.IGNORECASE)

# \cite, \citet, \citep, \citeauthor, etc. (optional args supported)
_CITE_CMD_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}")
_CITE_PLACEHOLDER_RE = re.compile(r"\[\[CITE:([^\]]+)\]\]")

_WHITESPACE_RE = re.compile(r"\s+")

# Minimal “broad claim” keywords: keep short to avoid over-flagging.
_BROAD_CLAIM_RE = re.compile(
    r"(?i)\b("
    r"first|largest|smallest|most|least|state[-\s]?of[-\s]?the[-\s]?art|sota|"
    r"outperform|improv|increase|decrease|declin|grow|shrink|"
    r"cause|causal|lead to|results? in|drives?"
    r")\b"
)


@dataclass(frozen=True)
class Claim:
    section: str
    text: str
    citations: list[str]


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def strip_comments(line: str) -> str:
    return _COMMENT_RE.sub("", line)


def replace_cites(text: str) -> str:
    def _repl(match: re.Match) -> str:
        keys = match.group(1).strip()
        return f"[[CITE:{keys}]]" if keys else ""

    return _CITE_CMD_RE.sub(_repl, text)


def extract_citations(sentence: str) -> list[str]:
    keys: list[str] = []
    for match in _CITE_PLACEHOLDER_RE.findall(sentence):
        for raw in match.split(","):
            key = raw.strip()
            if key:
                keys.append(key)
    # Stable, de-duplicated, deterministic ordering
    return sorted(set(keys))


def clean_sentence(sentence: str) -> str:
    # Remove cite placeholders from display text
    s = _CITE_PLACEHOLDER_RE.sub("", sentence)
    # Lightweight LaTeX cleanup: keep text content, remove common noise tokens.
    s = s.replace("~", " ").replace("\\%", "%")
    s = re.sub(r"\\label\{[^}]*\}", "", s)
    s = re.sub(r"\\ref\{[^}]*\}", "REF", s)
    s = re.sub(r"\\url\{[^}]*\}", "URL", s)
    s = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\(emph|textit|textbf|texttt|underline)\{([^}]*)\}", r"\2", s)
    s = s.replace("{", "").replace("}", "")
    s = _WHITESPACE_RE.sub(" ", s).strip()
    return s


def split_sentences(text: str) -> list[str]:
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if not text:
        return []
    # Heuristic sentence splitting; good enough for claim triage.
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def looks_like_claim(sentence: str, *, mode: str) -> bool:
    if len(sentence.strip()) < 20:
        return False
    if re.search(r"\d", sentence) or "%" in sentence or "p<" in sentence.lower():
        return True
    if mode == "broad":
        return _BROAD_CLAIM_RE.search(sentence) is not None
    return False


def iter_segments(tex_lines: list[str]) -> list[tuple[str, str]]:
    segments: list[tuple[str, str]] = []
    current_section: str | None = None
    current_subsection: str | None = None
    buf: list[str] = []

    def _flush() -> None:
        nonlocal buf
        if not buf:
            return
        label = current_section or "(frontmatter)"
        if current_subsection:
            label = f"{label} / {current_subsection}"
        segments.append((label, "\n".join(buf)))
        buf = []

    for raw in tex_lines:
        if _BIB_STOP_RE.search(raw):
            break

        line = strip_comments(raw).rstrip("\n")
        if not line.strip():
            continue

        sec = _SECTION_RE.search(line)
        if sec:
            _flush()
            current_section = sec.group(1).strip()
            current_subsection = None
            continue

        sub = _SUBSECTION_RE.search(line)
        if sub:
            _flush()
            current_subsection = sub.group(1).strip()
            continue

        buf.append(line)

    _flush()
    return segments


def build_claims(tex_text: str, *, mode: str, max_claims: int) -> list[Claim]:
    lines = tex_text.splitlines()
    segments = iter_segments(lines)

    claims: list[Claim] = []
    for label, seg_text in segments:
        flat = replace_cites(seg_text)
        flat = flat.replace("\n", " ")
        for sentence in split_sentences(flat):
            citations = extract_citations(sentence)
            cleaned = clean_sentence(sentence)
            if not cleaned:
                continue
            if not looks_like_claim(cleaned, mode=mode):
                continue
            claims.append(Claim(section=label, text=cleaned, citations=citations))
            if len(claims) >= max_claims:
                return claims
    return claims


def escape_md_cell(text: str) -> str:
    # Keep markdown tables intact.
    return text.replace("|", "\\|").replace("\n", " ").strip()


def write_markdown(out_path: Path, *, mode: str, claims: list[Claim]) -> None:
    lines: list[str] = [
        "# Claim Registry",
        "",
        f"- Created at: {now_iso()}",
        f"- Mode: {mode}",
        "- Source: main.tex (paper claims)",
        "",
        "Purpose: track the paper’s verifiable claims and record per-claim verification outcomes.",
        "",
        "## Claims",
        "",
        "| ID | Section | Claim | Citations / Evidence | Verdict | Notes |",
        "|---|---|---|---|---|---|",
    ]

    if not claims:
        lines.append("| C1 |  |  |  |  |  |")
    else:
        for idx, claim in enumerate(claims, start=1):
            cite = ", ".join(claim.citations)
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"C{idx}",
                        escape_md_cell(claim.section),
                        escape_md_cell(claim.text),
                        escape_md_cell(cite),
                        "",
                        "",
                    ]
                )
                + " |"
            )

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_csv(out_path: Path, *, claims: list[Claim]) -> None:
    fieldnames = ["ID", "Section", "Claim", "Citations_Evidence", "Verdict", "Notes"]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        if not claims:
            writer.writerow(
                {"ID": "C1", "Section": "", "Claim": "", "Citations_Evidence": "", "Verdict": "", "Notes": ""}
            )
            return
        for idx, claim in enumerate(claims, start=1):
            writer.writerow(
                {
                    "ID": f"C{idx}",
                    "Section": claim.section,
                    "Claim": claim.text,
                    "Citations_Evidence": ", ".join(claim.citations),
                    "Verdict": "",
                    "Notes": "",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate notes/claim-registry.md for a paper project.")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Paper project directory containing main.tex (default: .).",
    )
    parser.add_argument(
        "--mode",
        default="numeric",
        choices=["numeric", "broad"],
        help="Extraction mode: numeric (default) or broad (adds superlatives/causal/trend keywords).",
    )
    parser.add_argument(
        "--max-claims",
        type=int,
        default=160,
        help="Maximum number of claims to emit (default: 160).",
    )
    parser.add_argument(
        "--write-csv",
        action="store_true",
        help="Also write notes/claim-registry.csv",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing registry files if present.",
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

    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    out_md = notes_dir / "claim-registry.md"
    out_csv = notes_dir / "claim-registry.csv"

    if not args.overwrite and out_md.exists():
        return fail("notes/claim-registry.md already exists (use --overwrite to replace)")
    if args.write_csv and (not args.overwrite) and out_csv.exists():
        return fail("notes/claim-registry.csv already exists (use --overwrite to replace)")

    # Refinement marker guard
    if not check_refined_guard(out_md, force=args.overwrite):
        return 1
    if args.write_csv and not check_refined_guard(out_csv, force=args.overwrite):
        return 1

    tex_text = main_tex.read_text(encoding="utf-8", errors="replace")
    claims = build_claims(tex_text, mode=args.mode, max_claims=max(0, int(args.max_claims)))

    write_markdown(out_md, mode=args.mode, claims=claims)
    if args.write_csv:
        write_csv(out_csv, claims=claims)

    created = ["notes/claim-registry.md"]
    if args.write_csv:
        created.append("notes/claim-registry.csv")
    print(f"Created: {', '.join(created)} ({len(claims)} claim(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

