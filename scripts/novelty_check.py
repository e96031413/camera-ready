#!/usr/bin/env python3
"""Structured novelty verification for research ideas.

Extracts core claims from a method description, searches multiple sources,
and produces a structured novelty report with HIGH/MEDIUM/LOW ratings.

Concept adapted from ARIS (Auto-claude-code-research-in-sleep).

Usage:
  python3 scripts/novelty_check.py --project-dir <paper_dir> [--method-file <path>]
  python3 scripts/novelty_check.py --project-dir <paper_dir> --method "description of method"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import now_iso


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def extract_claims_from_tex(project_dir: Path) -> list[str]:
    """Extract potential novelty claims from paper main.tex."""
    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        return []

    text = main_tex.read_text(encoding="utf-8", errors="replace")
    claims: list[str] = []

    # Extract from contribution lists
    # Look for \item within contribution-like environments
    contrib_pattern = re.findall(
        r"\\(?:item|textbf\{Contribution)\s*(.*?)(?=\\item|\\end)", text, re.DOTALL
    )
    for c in contrib_pattern:
        clean = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", c)
        clean = re.sub(r"\\[a-zA-Z]+", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        if len(clean) > 20:
            claims.append(clean[:200])

    # Extract from abstract
    abstract_match = re.search(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.DOTALL
    )
    if abstract_match:
        abstract = abstract_match.group(1).strip()
        # Split into sentences, take those with "we propose/introduce/present"
        sentences = re.split(r"(?<=[.!?])\s+", abstract)
        for sent in sentences:
            if any(kw in sent.lower() for kw in ["we propose", "we introduce", "we present", "our method", "novel"]):
                clean = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", sent)
                clean = re.sub(r"\\[a-zA-Z]+", "", clean).strip()
                if clean and clean not in claims:
                    claims.append(clean[:200])

    return claims[:5]  # Max 5 claims


def generate_search_queries(claim: str) -> list[str]:
    """Generate 3 search query formulations per claim."""
    # Remove common filler
    clean = re.sub(r"\b(we|our|this paper|in this work)\b", "", claim, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()

    queries = []
    # Direct query
    queries.append(clean[:100])

    # Keywords-only query
    words = [w for w in clean.split() if len(w) > 3 and w.lower() not in {"that", "with", "from", "into", "also", "which", "have", "been", "more", "than"}]
    if words:
        queries.append(" ".join(words[:8]))

    # ArXiv-style query
    queries.append(f"arxiv {clean[:60]}")

    return queries


def generate_report_template(
    method_desc: str,
    claims: list[str],
    output_path: Path,
) -> None:
    """Generate a novelty check report template."""
    report = [
        "# Novelty Check Report",
        "",
        f"**Generated**: {now_iso()}",
        "",
        "## Proposed Method",
        method_desc[:500] if method_desc else "[Extract from paper]",
        "",
        "## Core Claims to Verify",
        "",
    ]

    for i, claim in enumerate(claims, 1):
        report.extend([
            f"### Claim {i}",
            f"> {claim}",
            "",
            f"- **Novelty**: `TODO` (HIGH / MEDIUM / LOW)",
            f"- **Closest prior work**: `TODO`",
            f"- **Key difference**: `TODO`",
            "",
            "#### Search Queries",
        ])
        for q in generate_search_queries(claim):
            report.append(f"- `{q}`")
        report.extend([
            "",
            "#### Found Papers",
            "| Paper | Year | Venue | Overlap | Key Difference |",
            "|-------|------|-------|---------|----------------|",
            "| TODO  | —    | —     | —       | —              |",
            "",
        ])

    report.extend([
        "## Overall Novelty Assessment",
        "",
        "- **Score**: `TODO` /10",
        "- **Recommendation**: `TODO` (PROCEED / PROCEED WITH CAUTION / PIVOT)",
        "- **Key differentiator**: `TODO`",
        "- **Reviewer risk**: `TODO` (what a reviewer would cite as prior work)",
        "",
        "## Suggested Positioning",
        "",
        "`TODO`: How to frame the contribution to maximize novelty perception.",
        "",
        "---",
        "",
        "## Verification Protocol",
        "",
        "1. For EACH claim above, execute the search queries via web search",
        "2. Read abstracts of top-5 results for each query",
        "3. If cross-model review available (Codex MCP), send method + found papers for verification",
        "4. Update novelty ratings based on findings",
        "",
        "### Important Rules",
        "- Be BRUTALLY honest — false novelty claims waste months of research",
        "- 'Applying X to Y' is NOT novel unless the application reveals surprising insights",
        "- Check both the METHOD and the EXPERIMENTAL SETTING for novelty",
        "- If the method is not novel but the FINDING would be, say so explicitly",
        "- Always check the most recent 6 months of arXiv — the field moves fast",
        "",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Structured novelty verification for research ideas."
    )
    parser.add_argument("--project-dir", required=True, help="Paper/project root directory")
    parser.add_argument("--method", default="", help="Method description text")
    parser.add_argument("--method-file", default=None, help="File containing method description")
    parser.add_argument("--output", default=None, help="Output report path")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)

    # Get method description
    method_desc = args.method
    if args.method_file:
        mf = Path(args.method_file)
        if mf.exists():
            method_desc = mf.read_text(encoding="utf-8", errors="replace")[:2000]

    # Extract claims
    claims = extract_claims_from_tex(project_dir)
    if not claims and not method_desc:
        print("No claims extracted from main.tex and no --method provided.")
        print("Generating empty template with instructions.")
        claims = ["[Claim 1: describe your main contribution]"]

    if method_desc and not claims:
        # Generate claims from method description
        sentences = re.split(r"(?<=[.!?])\s+", method_desc)
        claims = [s[:200] for s in sentences[:5] if len(s) > 20]

    # Output path
    output_path = Path(args.output) if args.output else project_dir / "notes" / "novelty-check.md"

    generate_report_template(method_desc, claims, output_path)
    print(f"Novelty check report: {output_path}")
    print(f"  Claims to verify: {len(claims)}")
    for i, c in enumerate(claims, 1):
        print(f"  {i}. {c[:80]}...")
    print(f"\nNext: Execute search queries and fill in the report.")
    print(f"  For cross-model verification, use Codex MCP with xhigh reasoning.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
