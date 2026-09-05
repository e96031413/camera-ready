#!/usr/bin/env python3
"""Cross-model adversarial review with state persistence.

Orchestrates an autonomous review loop where Claude executes fixes and an
external LLM (via Codex MCP or any OpenAI-compatible API) acts as reviewer.
Supports state recovery from context compaction via REVIEW_STATE.json.

Concept adapted from ARIS (Auto-claude-code-research-in-sleep).

This script manages the STATE FILE only. The actual MCP calls and fix
implementation are done by the LLM agent following the workflow in
references/autonomous-research.md.

Usage:
  python3 scripts/cross_model_review.py --project-dir <paper_dir> init
  python3 scripts/cross_model_review.py --project-dir <paper_dir> status
  python3 scripts/cross_model_review.py --project-dir <paper_dir> update --round 2 --score 6.5 --verdict "almost ready"
  python3 scripts/cross_model_review.py --project-dir <paper_dir> complete
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import now_iso


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


STATE_FILE = "REVIEW_STATE.json"
REVIEW_DOC = "notes/cross-model-review.md"
MAX_ROUNDS = 4
STALE_HOURS = 24
POSITIVE_THRESHOLD = 6.0


def _state_path(project_dir: Path) -> Path:
    return project_dir / STATE_FILE


def _review_path(project_dir: Path) -> Path:
    return project_dir / REVIEW_DOC


def load_state(project_dir: Path) -> dict | None:
    """Load review state, returning None if absent or stale."""
    path = _state_path(project_dir)
    if not path.exists():
        return None

    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    # Check if completed
    if state.get("status") == "completed":
        return None  # Fresh start

    # Check staleness
    ts = state.get("timestamp", "")
    try:
        saved_time = datetime.fromisoformat(ts)
        if datetime.now(timezone.utc) - saved_time > timedelta(hours=STALE_HOURS):
            print(f"warning: state file older than {STALE_HOURS}h, starting fresh", file=sys.stderr)
            return None
    except (ValueError, TypeError):
        return None

    return state


def save_state(project_dir: Path, state: dict) -> None:
    """Save review state to JSON."""
    state["timestamp"] = now_iso()
    path = _state_path(project_dir)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"State saved: {path}")


def init_state(project_dir: Path, topic: str = "") -> dict:
    """Initialize a fresh review state."""
    state = {
        "round": 0,
        "max_rounds": MAX_ROUNDS,
        "status": "in_progress",
        "topic": topic,
        "scores": [],
        "verdicts": [],
        "thread_id": None,
        "pending_fixes": [],
        "timestamp": now_iso(),
    }
    save_state(project_dir, state)

    # Initialize review doc
    review_path = _review_path(project_dir)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    if not review_path.exists():
        review_path.write_text(
            f"# Cross-Model Review Log\n\n"
            f"**Topic**: {topic}\n"
            f"**Started**: {now_iso()}\n"
            f"**Max rounds**: {MAX_ROUNDS}\n"
            f"**Positive threshold**: {POSITIVE_THRESHOLD}/10\n\n"
            f"---\n\n",
            encoding="utf-8",
        )
        print(f"Review doc created: {review_path}")

    return state


def update_round(
    project_dir: Path,
    round_num: int,
    score: float,
    verdict: str,
    thread_id: str | None = None,
    action_items: list[str] | None = None,
    actions_taken: list[str] | None = None,
) -> dict:
    """Update state after a review round."""
    state = load_state(project_dir)
    if state is None:
        state = init_state(project_dir)

    state["round"] = round_num
    state["scores"].append(score)
    state["verdicts"].append(verdict)
    if thread_id:
        state["thread_id"] = thread_id
    state["pending_fixes"] = action_items or []

    # Check stop condition
    if score >= POSITIVE_THRESHOLD and any(
        kw in verdict.lower() for kw in ["ready", "accept", "almost", "sufficient"]
    ):
        state["status"] = "positive_assessment"
    elif round_num >= MAX_ROUNDS:
        state["status"] = "max_rounds_reached"

    save_state(project_dir, state)

    # Append to review doc
    review_path = _review_path(project_dir)
    entry = (
        f"## Round {round_num} ({now_iso()})\n\n"
        f"### Assessment\n"
        f"- **Score**: {score}/10\n"
        f"- **Verdict**: {verdict}\n"
    )
    if action_items:
        entry += f"\n### Action Items\n"
        for i, item in enumerate(action_items, 1):
            entry += f"{i}. {item}\n"
    if actions_taken:
        entry += f"\n### Actions Taken\n"
        for action in actions_taken:
            entry += f"- {action}\n"
    entry += f"\n### Status\n- {'Continuing' if state['status'] == 'in_progress' else state['status']}\n\n---\n\n"

    with review_path.open("a", encoding="utf-8") as f:
        f.write(entry)

    return state


def complete_review(project_dir: Path) -> dict:
    """Mark review as completed."""
    state = load_state(project_dir)
    if state is None:
        return fail("no active review state found")

    state["status"] = "completed"
    save_state(project_dir, state)

    # Write final summary
    review_path = _review_path(project_dir)
    scores = state.get("scores", [])
    summary = (
        f"## Final Summary\n\n"
        f"- **Rounds completed**: {state['round']}\n"
        f"- **Score progression**: {' → '.join(str(s) for s in scores)}\n"
        f"- **Final verdict**: {state['verdicts'][-1] if state['verdicts'] else 'N/A'}\n"
        f"- **Status**: {state['status']}\n"
        f"- **Completed**: {now_iso()}\n"
    )
    with review_path.open("a", encoding="utf-8") as f:
        f.write(summary)

    print(f"Review completed. Score progression: {' → '.join(str(s) for s in scores)}")
    return state


def show_status(project_dir: Path) -> int:
    """Show current review status."""
    state = load_state(project_dir)
    if state is None:
        path = _state_path(project_dir)
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("status") == "completed":
                scores = raw.get("scores", [])
                print(f"Review COMPLETED. Score: {' → '.join(str(s) for s in scores)}")
                return 0
        print("No active review. Use 'init' to start.")
        return 1

    scores = state.get("scores", [])
    print(f"Review in progress")
    print(f"  Round: {state['round']}/{state['max_rounds']}")
    print(f"  Status: {state['status']}")
    if scores:
        print(f"  Scores: {' → '.join(str(s) for s in scores)}")
        print(f"  Last verdict: {state['verdicts'][-1]}")
    if state.get("thread_id"):
        print(f"  Thread ID: {state['thread_id']}")
    if state.get("pending_fixes"):
        print(f"  Pending fixes: {len(state['pending_fixes'])}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross-model adversarial review state management."
    )
    parser.add_argument("--project-dir", required=True, help="Paper/project root directory")
    parser.add_argument("command", choices=["init", "status", "update", "complete"],
                        help="Command: init, status, update, complete")
    parser.add_argument("--topic", default="", help="Research topic (for init)")
    parser.add_argument("--round", type=int, default=1, help="Round number (for update)")
    parser.add_argument("--score", type=float, default=0.0, help="Review score (for update)")
    parser.add_argument("--verdict", default="", help="Reviewer verdict (for update)")
    parser.add_argument("--thread-id", default=None, help="Codex thread ID (for update)")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    if not project_dir.is_dir():
        return fail(f"project directory not found: {project_dir}")

    if args.command == "init":
        init_state(project_dir, args.topic)
        print(f"Review initialized (max {MAX_ROUNDS} rounds, threshold {POSITIVE_THRESHOLD}/10)")
        return 0
    elif args.command == "status":
        return show_status(project_dir)
    elif args.command == "update":
        update_round(project_dir, args.round, args.score, args.verdict, args.thread_id)
        return 0
    elif args.command == "complete":
        result = complete_review(project_dir)
        return 0 if isinstance(result, dict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
