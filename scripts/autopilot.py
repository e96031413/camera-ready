#!/usr/bin/env python3
"""Drive a paper from a topic to a camera-ready submission, one gate at a time.

Version: 2026-09-05-v1

This is the state machine for the end-to-end run: topic -> literature ->
plan -> experiments -> draft -> verification -> review -> revision ->
camera-ready. The agent does the research, the writing and the judgement. This
script decides what comes next, checks the exit condition of the current phase
against files that actually exist, and refuses to advance when the condition is
unmet.

That division matters. A script cannot read a paper and know whether the
argument holds. It can know whether the plan file exists, whether every issue
in the CSV is closed, whether the citation verifier passed, and whether a
reviewer comment was answered rather than ignored. Those are the parts worth
enforcing, and they are the parts that go wrong in an unsupervised run.

Two phases need a human, and the script will not pass them on its own:
  plan          an approving name must be recorded
  camera-ready  submission is always manual

State lives in <project>/notes/autopilot-state.json and is safe to read, edit
by hand, and commit.

Usage:
  python scripts/autopilot.py init --project-dir papers/my-study --topic "..." --discipline medicine
  python scripts/autopilot.py status --project-dir papers/my-study
  python scripts/autopilot.py check --project-dir papers/my-study
  python scripts/autopilot.py advance --project-dir papers/my-study
  python scripts/autopilot.py advance --project-dir papers/my-study --approved-by "Ada Lovelace"
  python scripts/autopilot.py log --project-dir papers/my-study --note "swapped the baseline"
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from discipline_profile import DisciplineError, load_discipline
from paper_utils import enable_utf8_stdout, now_iso

BANNER = "autopilot 2026-09-05-v1"

STATE_FILENAME = "autopilot-state.json"

# Evidence models that have no experiment phase to run.
NON_EXPERIMENTAL_MODELS = {"interpretive", "doctrinal"}


@dataclass
class Phase:
    """One stage of the run, with the condition that lets it close."""

    name: str
    goal: str
    exit_condition: str
    next_actions: list[str] = field(default_factory=list)
    needs_human: bool = False


PHASES: list[Phase] = [
    Phase(
        name="ideate",
        goal="Turn the topic into one answerable research question with a stated scope.",
        exit_condition="notes/research-question.md exists and names the question, the population and what is out of scope",
        next_actions=[
            "Write notes/research-question.md: the question, why it is open, and the boundary of the claim.",
            "python scripts/research_decision.py --help   # if the direction is still open",
        ],
    ),
    Phase(
        name="literature",
        goal="Find what already exists, and fetch every citation from a source.",
        exit_condition="ref.bib has at least --min-citations entries and none carries a PLACEHOLDER_ key",
        next_actions=[
            "python scripts/fetch_bibtex.py --help        # never write BibTeX from memory",
            "python scripts/novelty_check.py --help       # what does this add over what exists?",
            "For a synthesis paper, run scripts/reporting_guideline.py --guideline prisma2020 now, not later.",
        ],
    ),
    Phase(
        name="plan",
        goal="Agree the paper before writing it. This phase needs a human.",
        exit_condition="a plan file exists under plan/ and an approver is recorded in the state file",
        next_actions=[
            "python scripts/create_paper_plan.py --help",
            "Read the plan yourself, then: autopilot.py advance --approved-by \"<your name>\"",
        ],
        needs_human=True,
    ),
    Phase(
        name="issues",
        goal="Break the plan into an auditable list of writing tasks.",
        exit_condition="an issues CSV exists under issues/ with at least one row",
        next_actions=["Create the issues CSV from the approved plan; every row needs an acceptance condition."],
    ),
    Phase(
        name="experiments",
        goal="Run what the claims depend on, and record what actually happened.",
        exit_condition="notes/experiment-results.md exists, or the discipline has no experimental evidence model",
        next_actions=[
            "python scripts/experiment_plan.py --help",
            "Record failures and dead ends too; a result you cannot reproduce is not a result.",
        ],
    ),
    Phase(
        name="draft",
        goal="Write the manuscript, one issue at a time.",
        exit_condition="the manuscript exists and every issues-CSV row is marked DONE",
        next_actions=[
            "Close issues in dependency order; do not start a row whose Depends_On is open.",
            "python scripts/compile_paper.py --help      # it must build before it is reviewed",
        ],
    ),
    Phase(
        name="verify",
        goal="Check the machine-checkable claims: citations, evidence, format, anonymity.",
        exit_condition="notes/verification-report.md exists and records a pass for every gate that applies",
        next_actions=[
            "python scripts/verify_citations.py --help",
            "python scripts/citation_style.py validate <style> --bib ref.bib",
            "python scripts/format_gate.py --help",
            "python scripts/anonymity_check.py --help    # double-blind venues only",
        ],
    ),
    Phase(
        name="review",
        goal="Attack the paper before a reviewer does.",
        exit_condition="notes/review-comments.md exists and lists at least one numbered comment",
        next_actions=[
            "python scripts/paper_self_review.py --help",
            "python scripts/cross_model_review.py --help  # a second model, not a second pass by the same one",
            "Record every comment as a numbered item; unrecorded comments cannot be tracked to a fix.",
        ],
    ),
    Phase(
        name="revise",
        goal="Answer every review comment, or say plainly why not.",
        exit_condition="every numbered comment in notes/review-comments.md has a Resolution line that is not TODO",
        next_actions=[
            "Add 'Resolution:' under each comment, naming the change or the reason for declining it.",
            "Re-run the verify gates after revising; a fix can break a gate that passed.",
        ],
    ),
    Phase(
        name="camera-ready",
        goal="Build the submission package. Submitting is always yours to do.",
        exit_condition="the submission package exists; this phase never closes on its own",
        next_actions=[
            "python scripts/paper_checklist.py --help     # venue checklist, answered by you",
            "python scripts/reporting_guideline.py --guideline <g> --project-dir . --validate",
            "python scripts/arxiv_package.py --help",
            "Upload it yourself. This workflow never submits anything anywhere.",
        ],
        needs_human=True,
    ),
]

PHASE_INDEX = {phase.name: index for index, phase in enumerate(PHASES)}


class AutopilotError(RuntimeError):
    """Raised when a run cannot start or cannot be read."""


def state_path(project_dir: Path) -> Path:
    return project_dir / "notes" / STATE_FILENAME


def load_state(project_dir: Path) -> dict:
    path = state_path(project_dir)
    if not path.is_file():
        raise AutopilotError(f"no run at {path}. Start one with: autopilot.py init --project-dir {project_dir}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(project_dir: Path, state: dict) -> None:
    path = state_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_journal(state: dict, message: str) -> None:
    state.setdefault("journal", []).append({"at": now_iso(), "entry": message})


# --- exit condition checks -------------------------------------------------
#
# Each returns (passed, detail). They read the filesystem and nothing else, so
# a run can be inspected, interrupted and resumed without losing anything.


def find_manuscript(project_dir: Path) -> Path | None:
    for name in ("main.tex", "manuscript.tex", "paper.tex", "main.md", "manuscript.md"):
        candidate = project_dir / name
        if candidate.is_file():
            return candidate
    return None


def check_ideate(project_dir: Path, state: dict) -> tuple[bool, str]:
    path = project_dir / "notes" / "research-question.md"
    if not path.is_file():
        return False, "notes/research-question.md is missing"
    words = len(path.read_text(encoding="utf-8").split())
    if words < 40:
        return False, f"notes/research-question.md has {words} words; that is a title, not a question with a scope"
    return True, f"notes/research-question.md, {words} words"


def check_literature(project_dir: Path, state: dict) -> tuple[bool, str]:
    bib = project_dir / "ref.bib"
    if not bib.is_file():
        return False, "ref.bib is missing"
    text = bib.read_text(encoding="utf-8", errors="replace")
    entries = re.findall(r"@\w+\s*\{\s*([^,]+),", text)
    placeholders = [key for key in entries if key.strip().startswith("PLACEHOLDER_")]
    minimum = int(state.get("min_citations", 8))
    if placeholders:
        return False, f"{len(placeholders)} placeholder entr(ies) still in ref.bib: {', '.join(placeholders[:5])}"
    if len(entries) < minimum:
        return False, f"ref.bib has {len(entries)} entries; the run requires at least {minimum}"
    return True, f"ref.bib has {len(entries)} fetched entries, no placeholders"


def check_plan(project_dir: Path, state: dict) -> tuple[bool, str]:
    plans = sorted((project_dir / "plan").glob("*.md")) if (project_dir / "plan").is_dir() else []
    if not plans:
        return False, "no plan file under plan/"
    approver = state.get("plan_approved_by")
    if not approver:
        return False, f"{plans[-1].name} exists but nobody has approved it; pass --approved-by"
    return True, f"{plans[-1].name}, approved by {approver}"


def read_issue_rows(project_dir: Path) -> tuple[Path | None, list[dict]]:
    directory = project_dir / "issues"
    files = sorted(directory.glob("*.csv")) if directory.is_dir() else []
    if not files:
        return None, []
    latest = files[-1]
    with latest.open(encoding="utf-8", newline="") as handle:
        return latest, list(csv.DictReader(handle))


def check_issues(project_dir: Path, state: dict) -> tuple[bool, str]:
    path, rows = read_issue_rows(project_dir)
    if path is None:
        return False, "no issues CSV under issues/"
    if not rows:
        return False, f"{path.name} has no rows"
    return True, f"{path.name}, {len(rows)} issues"


def check_experiments(project_dir: Path, state: dict) -> tuple[bool, str]:
    if state.get("evidence_model") in NON_EXPERIMENTAL_MODELS:
        return True, f"skipped: the {state.get('discipline')} profile has a {state.get('evidence_model')} evidence model"
    path = project_dir / "notes" / "experiment-results.md"
    if not path.is_file():
        return False, "notes/experiment-results.md is missing; record what was run and what came out"
    return True, "notes/experiment-results.md exists"


def check_draft(project_dir: Path, state: dict) -> tuple[bool, str]:
    manuscript = find_manuscript(project_dir)
    if manuscript is None:
        return False, "no manuscript found (main.tex, manuscript.tex, main.md, ...)"
    path, rows = read_issue_rows(project_dir)
    if path is None:
        return False, "no issues CSV to check against"
    open_rows = [row.get("ID", "?") for row in rows if (row.get("Status") or "").strip().upper() != "DONE"]
    if open_rows:
        return False, f"{len(open_rows)} issue(s) still open: {', '.join(open_rows[:8])}"
    return True, f"{manuscript.name} written, all {len(rows)} issues closed"


def check_verify(project_dir: Path, state: dict) -> tuple[bool, str]:
    path = project_dir / "notes" / "verification-report.md"
    if not path.is_file():
        return False, "notes/verification-report.md is missing; record each gate you ran and its result"
    text = path.read_text(encoding="utf-8", errors="replace")
    failures = re.findall(r"^\s*[-*]?\s*(.+?):\s*FAIL\b", text, re.MULTILINE | re.IGNORECASE)
    if failures:
        return False, f"{len(failures)} gate(s) recorded as FAIL: {', '.join(failures[:5])}"
    passes = len(re.findall(r"\bPASS\b", text, re.IGNORECASE))
    if passes == 0:
        return False, "notes/verification-report.md records no PASS lines"
    return True, f"{passes} gate(s) recorded as PASS, none failing"


COMMENT_PATTERN = re.compile(r"^##+\s*(?:Comment\s*)?(\d+)[.):]?\s*(.*)$", re.MULTILINE | re.IGNORECASE)


def check_review(project_dir: Path, state: dict) -> tuple[bool, str]:
    path = project_dir / "notes" / "review-comments.md"
    if not path.is_file():
        return False, "notes/review-comments.md is missing"
    comments = COMMENT_PATTERN.findall(path.read_text(encoding="utf-8", errors="replace"))
    if not comments:
        return False, "notes/review-comments.md has no numbered comments ('## 1. ...')"
    return True, f"{len(comments)} numbered comment(s) recorded"


def check_revise(project_dir: Path, state: dict) -> tuple[bool, str]:
    path = project_dir / "notes" / "review-comments.md"
    if not path.is_file():
        return False, "notes/review-comments.md is missing"
    text = path.read_text(encoding="utf-8", errors="replace")
    headings = list(COMMENT_PATTERN.finditer(text))
    if not headings:
        return False, "no numbered comments to resolve"

    unresolved: list[str] = []
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        block = text[match.end() : end]
        resolution = re.search(r"\*{0,2}Resolution:?\*{0,2}\s*(.*)", block, re.IGNORECASE)
        answer = resolution.group(1).strip() if resolution else ""
        if not answer or answer.upper().startswith("TODO") or "[TODO" in answer:
            unresolved.append(match.group(1))
    if unresolved:
        return False, f"{len(unresolved)} comment(s) without a Resolution: {', '.join(unresolved[:8])}"
    return True, f"all {len(headings)} comments resolved"


def check_camera_ready(project_dir: Path, state: dict) -> tuple[bool, str]:
    packages = list(project_dir.glob("*.tar.gz")) + list(project_dir.glob("*.zip"))
    packages += list((project_dir / "dist").glob("*")) if (project_dir / "dist").is_dir() else []
    documents = list(project_dir.glob("*.pdf")) + list(project_dir.glob("*.docx"))
    if not packages and not documents:
        return False, "no submission package or rendered document in the project directory"
    built = [p.name for p in (packages + documents)][:5]
    return False, f"built: {', '.join(built)}. Submission is manual; this phase never closes on its own."


CHECKS = {
    "ideate": check_ideate,
    "literature": check_literature,
    "plan": check_plan,
    "issues": check_issues,
    "experiments": check_experiments,
    "draft": check_draft,
    "verify": check_verify,
    "review": check_review,
    "revise": check_revise,
    "camera-ready": check_camera_ready,
}


# --- commands --------------------------------------------------------------


def cmd_init(args) -> int:
    project_dir = Path(args.project_dir)
    if state_path(project_dir).exists() and not args.force:
        print(f"error: a run already exists at {state_path(project_dir)}; pass --force to restart", file=sys.stderr)
        return 2

    discipline_config = None
    if args.discipline:
        try:
            discipline_config = load_discipline(args.discipline)
        except DisciplineError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    for folder in ("notes", "plan", "issues", "figures"):
        (project_dir / folder).mkdir(parents=True, exist_ok=True)

    state = {
        "banner": BANNER,
        "created": now_iso(),
        "topic": args.topic,
        "discipline": args.discipline,
        "evidence_model": discipline_config.get("evidence_model") if discipline_config else None,
        "style": args.style or (discipline_config.get("default_style") if discipline_config else None),
        "format": args.format or (discipline_config.get("default_format") if discipline_config else "latex"),
        "venue": args.venue,
        "min_citations": args.min_citations,
        "phase": PHASES[0].name,
        "plan_approved_by": None,
        "overrides": {},
        "journal": [],
    }
    append_journal(state, f"run created for topic: {args.topic}")
    save_state(project_dir, state)

    print(f"{BANNER}: run created at {state_path(project_dir)}\n")
    print(f"  topic:      {args.topic}")
    print(f"  discipline: {state['discipline'] or '(unset)'}")
    print(f"  style:      {state['style'] or '(unset)'}")
    print(f"  format:     {state['format']}")
    print(f"  venue:      {state['venue'] or '(unset)'}")
    if discipline_config:
        print("\n  Read what this field requires before writing anything:")
        print(f"    python scripts/discipline_profile.py requirements {args.discipline}")
    print()
    print_phase(PHASES[0], project_dir, state)
    return 0


def print_phase(phase: Phase, project_dir: Path, state: dict) -> None:
    index = PHASE_INDEX[phase.name]
    print(f"Phase {index + 1}/{len(PHASES)}: {phase.name}")
    print(f"  Goal:  {phase.goal}")
    print(f"  Exit:  {phase.exit_condition}")
    if phase.needs_human:
        print("  This phase needs a person. It will not close on its own.")
    if phase.next_actions:
        print("  Next:")
        for action in phase.next_actions:
            print(f"    - {action}")


def cmd_status(args) -> int:
    project_dir = Path(args.project_dir)
    state = load_state(project_dir)
    current = state["phase"]
    current_index = PHASE_INDEX[current]

    print(f"{BANNER}")
    print(f"  topic:      {state.get('topic')}")
    print(f"  discipline: {state.get('discipline') or '(unset)'}   style: {state.get('style') or '(unset)'}"
          f"   format: {state.get('format')}")
    print()
    for index, phase in enumerate(PHASES):
        if index < current_index:
            mark = "done"
        elif index == current_index:
            mark = "NOW "
        else:
            mark = "    "
        override = state.get("overrides", {}).get(phase.name)
        suffix = f"   (forced: {override})" if override else ""
        print(f"  [{mark}] {index + 1:>2}. {phase.name}{suffix}")
    print()
    print_phase(PHASES[current_index], project_dir, state)

    passed, detail = CHECKS[current](project_dir, state)
    print()
    print(f"  Exit condition: {'MET' if passed else 'not met'} — {detail}")
    return 0


def cmd_check(args) -> int:
    project_dir = Path(args.project_dir)
    state = load_state(project_dir)
    phase_name = args.phase or state["phase"]
    if phase_name not in CHECKS:
        print(f"error: unknown phase {phase_name!r}; known: {', '.join(CHECKS)}", file=sys.stderr)
        return 2
    passed, detail = CHECKS[phase_name](project_dir, state)
    print(f"{phase_name}: {'MET' if passed else 'NOT MET'} — {detail}")
    return 0 if passed else 1


def cmd_advance(args) -> int:
    project_dir = Path(args.project_dir)
    state = load_state(project_dir)
    current = state["phase"]
    index = PHASE_INDEX[current]
    phase = PHASES[index]

    if args.approved_by:
        state["plan_approved_by"] = args.approved_by
        append_journal(state, f"plan approved by {args.approved_by}")

    passed, detail = CHECKS[current](project_dir, state)

    if not passed and not args.force:
        print(f"{BANNER}: cannot leave '{current}' — {detail}\n")
        print_phase(phase, project_dir, state)
        print("\n  Fix the condition, or record a deliberate override:")
        print(f"    autopilot.py advance --project-dir {project_dir} --force --reason \"<why>\"")
        save_state(project_dir, state)
        return 1

    if not passed and args.force:
        if not args.reason:
            print("error: --force requires --reason, so the override is on the record", file=sys.stderr)
            return 2
        state.setdefault("overrides", {})[current] = args.reason
        append_journal(state, f"forced past '{current}' despite: {detail}. Reason: {args.reason}")
        print(f"Forced past '{current}'. Recorded: {args.reason}")

    if index + 1 >= len(PHASES):
        append_journal(state, "reached the end of the run")
        save_state(project_dir, state)
        print(f"{BANNER}: '{current}' is the last phase. Submission is yours to do.")
        return 0

    next_phase = PHASES[index + 1]
    state["phase"] = next_phase.name
    append_journal(state, f"advanced from '{current}' to '{next_phase.name}' ({detail})")
    save_state(project_dir, state)

    print(f"{BANNER}: left '{current}' — {detail}\n")
    print_phase(next_phase, project_dir, state)
    return 0


def cmd_log(args) -> int:
    project_dir = Path(args.project_dir)
    state = load_state(project_dir)
    append_journal(state, args.note)
    save_state(project_dir, state)
    print(f"Logged against phase '{state['phase']}'.")
    return 0


def cmd_phases(args) -> int:
    print(f"{BANNER}: {len(PHASES)} phases\n")
    for index, phase in enumerate(PHASES):
        human = "  (needs a human)" if phase.needs_human else ""
        print(f"{index + 1:>2}. {phase.name}{human}")
        print(f"    goal: {phase.goal}")
        print(f"    exit: {phase.exit_condition}")
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Drive a paper from a topic to a camera-ready submission.")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="start a run")
    init.add_argument("--project-dir", required=True)
    init.add_argument("--topic", required=True, help="the research topic, in one sentence")
    init.add_argument("--discipline", help="a slug from scripts/discipline_profile.py list")
    init.add_argument("--style", help="a slug from scripts/citation_style.py list")
    init.add_argument("--format", choices=["latex", "docx", "markdown", "typst"])
    init.add_argument("--venue", help="a slug from assets/venues, when there is a target venue")
    init.add_argument("--min-citations", type=int, default=8, help="minimum entries before leaving the literature phase")
    init.add_argument("--force", action="store_true", help="overwrite an existing run")

    status = sub.add_parser("status", help="where the run is and what closes the current phase")
    status.add_argument("--project-dir", required=True)

    check = sub.add_parser("check", help="evaluate one phase's exit condition")
    check.add_argument("--project-dir", required=True)
    check.add_argument("--phase", help="a phase name (default: the current one)")

    advance = sub.add_parser("advance", help="move to the next phase if the exit condition is met")
    advance.add_argument("--project-dir", required=True)
    advance.add_argument("--approved-by", help="record the person approving the plan")
    advance.add_argument("--force", action="store_true", help="advance despite an unmet condition")
    advance.add_argument("--reason", help="why the override is justified; required with --force")

    log = sub.add_parser("log", help="append a note to the run journal")
    log.add_argument("--project-dir", required=True)
    log.add_argument("--note", required=True)

    sub.add_parser("phases", help="print the whole phase list and exit")

    return parser


def main() -> int:
    enable_utf8_stdout()
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        "init": cmd_init,
        "status": cmd_status,
        "check": cmd_check,
        "advance": cmd_advance,
        "log": cmd_log,
        "phases": cmd_phases,
    }
    try:
        return handlers[args.command](args)
    except AutopilotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
