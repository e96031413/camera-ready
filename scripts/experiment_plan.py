#!/usr/bin/env python3
"""Generate a claim-driven experiment plan from paper claims.

Creates a structured experiment roadmap mapping claims → evidence → runs,
with 5-stage milestone structure and compute budget estimation.

Concept adapted from ARIS (Auto-claude-code-research-in-sleep).

Usage:
  python3 scripts/experiment_plan.py --project-dir <paper_dir>
  python3 scripts/experiment_plan.py --project-dir <paper_dir> --claims-file notes/claim-registry.md
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


MAX_PRIMARY_CLAIMS = 2
MAX_CORE_BLOCKS = 5
MAX_BASELINE_FAMILIES = 3
DEFAULT_SEEDS = 3


def extract_claims_from_registry(project_dir: Path) -> list[dict]:
    """Extract claims from claim-registry.md or claim-registry.csv."""
    claims: list[dict] = []

    # Try CSV first
    csv_path = project_dir / "notes" / "claim-registry.csv"
    if csv_path.exists():
        import csv
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                claim_text = row.get("Claim", row.get("claim", ""))
                if claim_text:
                    claims.append({
                        "text": claim_text,
                        "type": row.get("Type", row.get("type", "empirical")),
                        "section": row.get("Section", row.get("section", "")),
                    })
        return claims[:MAX_PRIMARY_CLAIMS + 3]

    # Try markdown
    md_path = project_dir / "notes" / "claim-registry.md"
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8", errors="replace")
        # Extract claims from table rows or bullet points
        for match in re.finditer(r"\|\s*(.+?)\s*\|\s*(empirical|theoretical|methodological)\s*\|", text, re.IGNORECASE):
            claims.append({"text": match.group(1).strip(), "type": match.group(2).strip(), "section": ""})
        if not claims:
            for match in re.finditer(r"[-*]\s+(.+)", text):
                line = match.group(1).strip()
                if len(line) > 20 and not line.startswith("#"):
                    claims.append({"text": line[:200], "type": "empirical", "section": ""})

    return claims[:MAX_PRIMARY_CLAIMS + 3]


def extract_claims_from_tex(project_dir: Path) -> list[dict]:
    """Extract claims from main.tex contributions section."""
    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        return []

    text = main_tex.read_text(encoding="utf-8", errors="replace")
    claims: list[dict] = []

    # Look for contribution items
    for match in re.finditer(r"\\item\s+(.+?)(?=\\item|\\end)", text, re.DOTALL):
        raw = match.group(1).strip()
        clean = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", raw)
        clean = re.sub(r"\\[a-zA-Z]+", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        if len(clean) > 20:
            claims.append({"text": clean[:200], "type": "empirical", "section": "introduction"})

    return claims[:MAX_PRIMARY_CLAIMS + 3]


def generate_plan(project_dir: Path, claims: list[dict], output_path: Path) -> None:
    """Generate experiment plan markdown."""
    plan = [
        "# Experiment Plan",
        "",
        f"**Project**: {project_dir.name}",
        f"**Date**: {now_iso()}",
        f"**Max primary claims**: {MAX_PRIMARY_CLAIMS}",
        f"**Default seeds**: {DEFAULT_SEEDS}",
        "",
        "---",
        "",
        "## Claim Map",
        "",
        "| # | Claim | Type | Min. Convincing Evidence | Linked Blocks |",
        "|---|-------|------|------------------------|---------------|",
    ]

    for i, c in enumerate(claims, 1):
        label = "C" + str(i)
        plan.append(f"| {label} | {c['text'][:80]} | {c['type']} | `TODO` | `TODO` |")

    plan.extend([
        "",
        "### Anti-Claims to Rule Out",
        "- `TODO`: e.g., 'gain comes only from more parameters'",
        "- `TODO`: e.g., 'modern component is decorative, not functional'",
        "",
        "---",
        "",
        "## Paper Storyline",
        "",
        "- **Main paper must prove**:",
        "  - `TODO`",
        "- **Appendix can support**:",
        "  - `TODO`",
        "- **Experiments intentionally cut**:",
        "  - `TODO`",
        "",
        "---",
        "",
        "## Experiment Blocks",
        "",
    ])

    block_templates = [
        ("Main Anchor Result", "Does the method solve the actual bottleneck?"),
        ("Novelty Isolation", "Does the dominant contribution itself matter? (ablation)"),
        ("Simplicity / Elegance Check", "Can a bigger or more fragmented version be avoided?"),
        ("Failure Analysis", "What does the method still miss? (qualitative diagnosis)"),
    ]

    for i, (name, why) in enumerate(block_templates, 1):
        plan.extend([
            f"### Block {i}: {name}",
            f"- **Claim tested**: `TODO`",
            f"- **Why this block exists**: {why}",
            f"- **Dataset / split / task**: `TODO`",
            f"- **Compared systems**: `TODO` (max {MAX_BASELINE_FAMILIES} baseline families)",
            f"- **Metrics**: `TODO` (decisive first, secondary second)",
            f"- **Setup**: backbone, key hyperparameters, seeds={DEFAULT_SEEDS}",
            f"- **Success criterion**: `TODO`",
            f"- **Failure interpretation**: `TODO`",
            f"- **Table / figure target**: `TODO`",
            f"- **Priority**: MUST-RUN / NICE-TO-HAVE",
            "",
        ])

    plan.extend([
        "---",
        "",
        "## Run Order and Milestones",
        "",
        "| Milestone | Goal | Runs | Decision Gate | Est. Cost | Risk |",
        "|-----------|------|------|---------------|-----------|------|",
        "| M0: Sanity | Data pipeline + metric correctness | 1 quick run | Pass/fail | 0.5 GPU-hr | Low |",
        "| M1: Baseline | Reproduce strongest baseline | 1-2 runs | Numbers match paper | 2-4 GPU-hr | Medium |",
        "| M2: Main Method | Run final method on primary setting | 1-2 runs | Beats baseline? | 2-4 GPU-hr | High |",
        "| M3: Decision | Decisive ablations (novelty, simplicity) | 3-5 runs | Claims supported? | 4-8 GPU-hr | High |",
        "| M4: Polish | Robustness, qualitative, appendix | 2-4 runs | Nice-to-have | 2-4 GPU-hr | Low |",
        "",
        "---",
        "",
        "## Compute and Data Budget",
        "",
        "- **Total estimated GPU-hours**: `TODO`",
        "- **Data preparation needs**: `TODO`",
        "- **Human evaluation needs**: `TODO` (if applicable)",
        "- **Biggest bottleneck**: `TODO`",
        "",
        "## Risks and Mitigations",
        "",
        "| Risk | Likelihood | Impact | Mitigation |",
        "|------|-----------|--------|------------|",
        "| `TODO` | `TODO` | `TODO` | `TODO` |",
        "",
        "---",
        "",
        "## Final Checklist",
        "",
        "- [ ] Main paper tables are covered by experiment blocks",
        "- [ ] Novelty is isolated (ablation exists)",
        "- [ ] Simplicity is defended (no unnecessary complexity)",
        "- [ ] Anti-claims are addressed",
        "- [ ] Nice-to-have runs are separated from must-run",
        "- [ ] Compute budget is realistic",
        "",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(plan), encoding="utf-8")


def generate_tracker(output_path: Path) -> None:
    """Generate experiment tracker markdown."""
    tracker = [
        "# Experiment Tracker",
        "",
        f"**Created**: {now_iso()}",
        "",
        "| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |",
        "|--------|-----------|---------|------------------|-------|---------|----------|--------|-------|",
        "| R001 | M0 | Sanity check | — | dev | — | MUST | TODO | — |",
        "| R002 | M1 | Baseline reproduction | — | test | — | MUST | TODO | — |",
        "| R003 | M2 | Main method | Ours | test | — | MUST | TODO | — |",
        "| R004 | M3 | Ablation: novelty | Ours w/o X | test | — | MUST | TODO | — |",
        "| R005 | M4 | Robustness check | Ours | dev+test | — | NICE | TODO | — |",
        "",
        "**Status**: TODO → RUNNING → DONE → FAILED",
        "",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(tracker), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a claim-driven experiment plan."
    )
    parser.add_argument("--project-dir", required=True, help="Paper/project root directory")
    parser.add_argument("--claims-file", default=None, help="Path to claims file (default: auto-detect)")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: <project-dir>/notes)")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    if not project_dir.is_dir():
        return fail(f"project directory not found: {project_dir}")

    # Extract claims
    claims: list[dict] = []
    if args.claims_file:
        cf = Path(args.claims_file)
        if cf.exists():
            text = cf.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and len(line) > 20:
                    claims.append({"text": line[:200], "type": "empirical", "section": ""})

    if not claims:
        claims = extract_claims_from_registry(project_dir)
    if not claims:
        claims = extract_claims_from_tex(project_dir)
    if not claims:
        claims = [{"text": "[Define your primary claim here]", "type": "empirical", "section": ""}]

    output_dir = Path(args.output_dir) if args.output_dir else project_dir / "notes"
    plan_path = output_dir / "experiment-plan.md"
    tracker_path = output_dir / "experiment-tracker.md"

    generate_plan(project_dir, claims, plan_path)
    generate_tracker(tracker_path)

    print(f"Experiment plan: {plan_path}")
    print(f"Experiment tracker: {tracker_path}")
    print(f"  Claims found: {len(claims)}")
    for i, c in enumerate(claims, 1):
        print(f"  C{i}: {c['text'][:80]}...")
    print(f"\nNext: Fill in TODO fields, then execute milestones M0→M4.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
