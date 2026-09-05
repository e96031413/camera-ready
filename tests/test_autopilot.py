"""Tests for scripts/autopilot.py — the topic-to-camera-ready state machine."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import autopilot as ap  # noqa: E402


def run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "autopilot.py")] + args,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


@pytest.fixture
def project(tmp_path):
    """A started run in an empty project directory."""
    result = run(
        [
            "init",
            "--project-dir",
            str(tmp_path),
            "--topic",
            "Does X reduce Y in Z?",
            "--discipline",
            "medicine",
        ]
    )
    assert result.returncode == 0, result.stderr
    return tmp_path


def state_of(project_dir):
    return json.loads((project_dir / "notes" / "autopilot-state.json").read_text(encoding="utf-8"))


class TestPhaseTable:
    def test_phases_are_uniquely_named(self):
        names = [phase.name for phase in ap.PHASES]
        assert len(names) == len(set(names))

    def test_every_phase_has_a_check(self):
        assert set(ap.CHECKS) == {phase.name for phase in ap.PHASES}

    def test_the_run_starts_at_ideate_and_ends_at_camera_ready(self):
        assert ap.PHASES[0].name == "ideate"
        assert ap.PHASES[-1].name == "camera-ready"

    def test_plan_and_camera_ready_need_a_human(self):
        needs_human = {phase.name for phase in ap.PHASES if phase.needs_human}
        assert needs_human == {"plan", "camera-ready"}


class TestInit:
    def test_state_records_the_discipline_defaults(self, project):
        state = state_of(project)
        assert state["discipline"] == "medicine"
        assert state["style"] == "vancouver"
        assert state["format"] == "docx"
        assert state["evidence_model"] == "clinical"
        assert state["phase"] == "ideate"

    def test_scaffold_directories_are_created(self, project):
        for folder in ("notes", "plan", "issues", "figures"):
            assert (project / folder).is_dir()

    def test_second_init_needs_force(self, project):
        assert run(["init", "--project-dir", str(project), "--topic", "t"]).returncode == 2
        assert run(["init", "--project-dir", str(project), "--topic", "t", "--force"]).returncode == 0

    def test_unknown_discipline_exits_two(self, tmp_path):
        result = run(["init", "--project-dir", str(tmp_path), "--topic", "t", "--discipline", "astrology"])
        assert result.returncode == 2

    def test_status_on_a_directory_with_no_run_exits_two(self, tmp_path):
        assert run(["status", "--project-dir", str(tmp_path)]).returncode == 2


class TestGates:
    def test_advance_is_blocked_while_the_condition_is_unmet(self, project):
        result = run(["advance", "--project-dir", str(project)])
        assert result.returncode == 1
        assert state_of(project)["phase"] == "ideate"

    def test_a_too_short_research_question_does_not_pass(self, project):
        (project / "notes" / "research-question.md").write_text("Does X work?", encoding="utf-8")
        assert run(["advance", "--project-dir", str(project)]).returncode == 1

    def test_a_complete_research_question_passes(self, project):
        (project / "notes" / "research-question.md").write_text(" ".join(["word"] * 60), encoding="utf-8")
        assert run(["advance", "--project-dir", str(project)]).returncode == 0
        assert state_of(project)["phase"] == "literature"

    def test_force_without_a_reason_is_refused(self, project):
        result = run(["advance", "--project-dir", str(project), "--force"])
        assert result.returncode == 2
        assert "--reason" in result.stderr

    def test_force_with_a_reason_records_the_override(self, project):
        result = run(["advance", "--project-dir", str(project), "--force", "--reason", "question is in the plan"])
        assert result.returncode == 0
        state = state_of(project)
        assert state["overrides"]["ideate"] == "question is in the plan"
        assert state["phase"] == "literature"


class TestLiteratureCheck:
    def test_placeholder_entries_block_the_phase(self, project):
        state = state_of(project)
        (project / "ref.bib").write_text("@misc{PLACEHOLDER_x,\n  title={T}\n}\n", encoding="utf-8")
        passed, detail = ap.check_literature(project, state)
        assert not passed
        assert "placeholder" in detail

    def test_too_few_entries_block_the_phase(self, project):
        state = state_of(project)
        (project / "ref.bib").write_text("@misc{a,\n  title={T}\n}\n", encoding="utf-8")
        passed, detail = ap.check_literature(project, state)
        assert not passed
        assert "at least 8" in detail

    def test_enough_clean_entries_pass(self, project):
        state = state_of(project)
        entries = "".join(f"@misc{{k{index},\n  title={{T}}\n}}\n" for index in range(8))
        (project / "ref.bib").write_text(entries, encoding="utf-8")
        passed, _ = ap.check_literature(project, state)
        assert passed


class TestPlanCheck:
    def test_a_plan_without_an_approver_does_not_pass(self, project):
        (project / "plan" / "p.md").write_text("plan", encoding="utf-8")
        passed, detail = ap.check_plan(project, state_of(project))
        assert not passed
        assert "approved" in detail

    def test_approved_by_records_the_name_and_unblocks(self, project):
        (project / "plan" / "p.md").write_text("plan", encoding="utf-8")
        state = state_of(project)
        state["phase"] = "plan"
        (project / "notes" / "autopilot-state.json").write_text(json.dumps(state), encoding="utf-8")

        result = run(["advance", "--project-dir", str(project), "--approved-by", "Ada Lovelace"])
        assert result.returncode == 0
        assert state_of(project)["plan_approved_by"] == "Ada Lovelace"


class TestDraftAndReviewChecks:
    def test_open_issues_block_the_draft_phase(self, project):
        (project / "main.md").write_text("text", encoding="utf-8")
        (project / "issues" / "i.csv").write_text("ID,Status\nW1,DONE\nW2,TODO\n", encoding="utf-8")
        passed, detail = ap.check_draft(project, state_of(project))
        assert not passed
        assert "W2" in detail

    def test_all_issues_done_passes(self, project):
        (project / "main.md").write_text("text", encoding="utf-8")
        (project / "issues" / "i.csv").write_text("ID,Status\nW1,DONE\nW2,done\n", encoding="utf-8")
        passed, _ = ap.check_draft(project, state_of(project))
        assert passed

    def test_a_failing_gate_blocks_verification(self, project):
        (project / "notes" / "verification-report.md").write_text(
            "- citations: PASS\n- format: FAIL\n", encoding="utf-8"
        )
        passed, detail = ap.check_verify(project, state_of(project))
        assert not passed
        assert "format" in detail

    def test_unresolved_comments_block_revision(self, project):
        (project / "notes" / "review-comments.md").write_text(
            "## 1. Weak baseline\nResolution: added a second baseline\n\n"
            "## 2. No error bars\nResolution: TODO\n",
            encoding="utf-8",
        )
        passed, detail = ap.check_revise(project, state_of(project))
        assert not passed
        assert "2" in detail

    def test_all_comments_resolved_passes(self, project):
        (project / "notes" / "review-comments.md").write_text(
            "## 1. Weak baseline\nResolution: added one\n\n## 2. No error bars\nResolution: added seeds\n",
            encoding="utf-8",
        )
        passed, _ = ap.check_revise(project, state_of(project))
        assert passed


class TestExperimentSkip:
    def test_an_interpretive_field_skips_the_experiment_phase(self, tmp_path):
        run(["init", "--project-dir", str(tmp_path), "--topic", "t", "--discipline", "humanities"])
        passed, detail = ap.check_experiments(tmp_path, state_of(tmp_path))
        assert passed
        assert "skipped" in detail

    def test_a_clinical_field_does_not_skip(self, project):
        passed, _ = ap.check_experiments(project, state_of(project))
        assert not passed


class TestCameraReadyNeverCloses:
    def test_it_reports_the_built_artifacts_but_stays_open(self, project):
        (project / "main.pdf").write_bytes(b"%PDF-1.4")
        passed, detail = ap.check_camera_ready(project, state_of(project))
        assert not passed
        assert "Submission is manual" in detail


class TestJournal:
    def test_log_appends_an_entry(self, project):
        assert run(["log", "--project-dir", str(project), "--note", "swapped the baseline"]).returncode == 0
        entries = [item["entry"] for item in state_of(project)["journal"]]
        assert "swapped the baseline" in entries


class TestCli:
    def test_help_exits_zero(self):
        assert run(["--help"]).returncode == 0

    def test_bare_invocation_prints_help(self):
        result = run([])
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()

    def test_phases_lists_every_phase(self):
        result = run(["phases"])
        assert result.returncode == 0
        for phase in ap.PHASES:
            assert phase.name in result.stdout

    def test_check_exits_one_when_the_condition_is_unmet(self, project):
        assert run(["check", "--project-dir", str(project)]).returncode == 1

    def test_check_rejects_an_unknown_phase(self, project):
        assert run(["check", "--project-dir", str(project), "--phase", "nope"]).returncode == 2
