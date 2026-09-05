#!/usr/bin/env python3
"""PROCEED / REFINE / PIVOT decision framework for research loops.

After analyzing experiment results, determines whether to:
  PROCEED: Results support claims → continue to paper writing
  REFINE: Partial support → tweak experiments/params → re-run
  PIVOT: Fundamental failure → discard hypothesis → new direction

Tracks decision history with artifact versioning (v0, v1, v2).

Concept adapted from AutoResearchClaw (aiming-lab/AutoResearchClaw).

Usage:
  python3 scripts/research_decision.py --project-dir <paper_dir> evaluate
  python3 scripts/research_decision.py --project-dir <paper_dir> status
  python3 scripts/research_decision.py --project-dir <paper_dir> record --decision PROCEED --reason "claims supported"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import now_iso


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


DECISION_FILE = "notes/research-decisions.json"
MAX_PIVOTS = 2
MAX_REFINES = 3


def _load_decisions(project_dir: Path) -> list[dict]:
    path = project_dir / DECISION_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_decisions(project_dir: Path, decisions: list[dict]) -> None:
    path = project_dir / DECISION_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(decisions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def record_decision(
    project_dir: Path,
    decision: str,
    reason: str,
    evidence: str = "",
    version: int | None = None,
) -> dict:
    """Record a research decision."""
    decisions = _load_decisions(project_dir)

    pivot_count = sum(1 for d in decisions if d["decision"] == "PIVOT")
    refine_count = sum(1 for d in decisions if d["decision"] == "REFINE")

    if decision == "PIVOT" and pivot_count >= MAX_PIVOTS:
        print(f"warning: max pivots ({MAX_PIVOTS}) reached. Consider manual review.", file=sys.stderr)

    if decision == "REFINE" and refine_count >= MAX_REFINES:
        print(f"warning: max refines ({MAX_REFINES}) reached. Consider PROCEED or PIVOT.", file=sys.stderr)

    if version is None:
        version = len(decisions)

    entry = {
        "version": version,
        "decision": decision.upper(),
        "reason": reason,
        "evidence": evidence,
        "timestamp": now_iso(),
        "pivot_count": pivot_count + (1 if decision == "PIVOT" else 0),
        "refine_count": refine_count + (1 if decision == "REFINE" else 0),
    }

    decisions.append(entry)
    _save_decisions(project_dir, decisions)
    print(f"Decision recorded: {decision} (v{version})")
    return entry


def evaluate_readiness(project_dir: Path) -> int:
    """Evaluate current readiness and suggest a decision."""
    decisions = _load_decisions(project_dir)
    pivot_count = sum(1 for d in decisions if d["decision"] == "PIVOT")
    refine_count = sum(1 for d in decisions if d["decision"] == "REFINE")

    print("=== Research Decision Evaluation ===")
    print()

    # Check existing artifacts
    claim_registry = project_dir / "notes" / "claim-registry.md"
    experiment_plan = project_dir / "notes" / "experiment-plan.md"
    review_state = project_dir / "REVIEW_STATE.json"
    novelty_check = project_dir / "notes" / "novelty-check.md"

    checks = {
        "Claim registry": claim_registry.exists(),
        "Experiment plan": experiment_plan.exists(),
        "Review state": review_state.exists(),
        "Novelty check": novelty_check.exists(),
    }

    print("Artifact checklist:")
    for name, exists in checks.items():
        print(f"  {'[x]' if exists else '[ ]'} {name}")

    print()
    print(f"Decision history: {len(decisions)} decision(s)")
    print(f"  Pivots: {pivot_count}/{MAX_PIVOTS}")
    print(f"  Refines: {refine_count}/{MAX_REFINES}")

    if decisions:
        last = decisions[-1]
        print(f"  Last: {last['decision']} (v{last['version']}) — {last['reason'][:60]}")

    # Suggest decision
    print()
    print("--- Decision Framework ---")
    print()
    print("PROCEED if:")
    print("  - Core claims are supported by experimental evidence")
    print("  - Cross-model review score >= 6/10")
    print("  - No critical weaknesses remaining")
    print()
    print("REFINE if:")
    print("  - Partial support: some claims work, others need tweaking")
    print("  - Reviewer suggests specific fixable experiments")
    print("  - Results are promising but not convincing")
    print(f"  (remaining: {MAX_REFINES - refine_count} refines)")
    print()
    print("PIVOT if:")
    print("  - Core hypothesis falsified by experiments")
    print("  - Key claim cannot be reproduced")
    print("  - Fundamental flaw discovered in method")
    print(f"  (remaining: {MAX_PIVOTS - pivot_count} pivots)")
    print()
    print("Record: python3 scripts/research_decision.py --project-dir . record --decision PROCEED --reason '...'")

    return 0


def show_status(project_dir: Path) -> int:
    """Show decision history."""
    decisions = _load_decisions(project_dir)
    if not decisions:
        print("No decisions recorded yet.")
        return 0

    print("=== Decision History ===")
    for d in decisions:
        print(f"  v{d['version']} [{d['decision']}] {d['reason'][:60]} ({d['timestamp'][:10]})")

    last = decisions[-1]
    print(f"\nCurrent state: {last['decision']} at v{last['version']}")
    print(f"  Pivots: {last.get('pivot_count', 0)}/{MAX_PIVOTS}")
    print(f"  Refines: {last.get('refine_count', 0)}/{MAX_REFINES}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PROCEED/REFINE/PIVOT decision framework for research loops."
    )
    parser.add_argument("--project-dir", required=True, help="Paper/project root directory")
    parser.add_argument("command", choices=["evaluate", "status", "record"],
                        help="Command: evaluate, status, record")
    parser.add_argument("--decision", choices=["PROCEED", "REFINE", "PIVOT"], help="Decision (for record)")
    parser.add_argument("--reason", default="", help="Reason for decision (for record)")
    parser.add_argument("--evidence", default="", help="Supporting evidence (for record)")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)

    if args.command == "evaluate":
        return evaluate_readiness(project_dir)
    elif args.command == "status":
        return show_status(project_dir)
    elif args.command == "record":
        if not args.decision:
            return fail("--decision required for record command")
        record_decision(project_dir, args.decision, args.reason, args.evidence)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
