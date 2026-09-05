"""Tests for scripts/reporting_guideline.py and the guideline question sets."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import reporting_guideline as rg  # noqa: E402

EXPECTED = {
    "prisma2020",
    "consort",
    "strobe",
    "care",
    "coreq",
    "srqr",
    "cherries",
    "jars-quant",
    "jars-qual",
}


class TestInstalledGuidelines:
    def test_expected_guidelines_exist(self):
        assert EXPECTED.issubset(set(rg.available_guidelines()))

    def test_venue_checklists_are_not_listed_as_guidelines(self):
        assert not set(rg.available_guidelines()) & rg.VENUE_CHECKLISTS

    @pytest.mark.parametrize("slug", sorted(EXPECTED))
    def test_every_guideline_parses_into_items(self, slug):
        title, items = rg.load_guideline(slug)
        assert title
        assert len(items) >= 13
        for item in items:
            assert item["question"] and item["guidance"]

    @pytest.mark.parametrize("slug", sorted(EXPECTED))
    def test_item_numbers_are_unique(self, slug):
        _, items = rg.load_guideline(slug)
        numbers = [item["number"] for item in items]
        assert len(numbers) == len(set(numbers))

    @pytest.mark.parametrize("slug", sorted(EXPECTED))
    def test_every_question_set_cites_its_source(self, slug):
        text = (ROOT / "assets" / "checklists" / f"{slug}.md").read_text(encoding="utf-8")
        assert "Source:" in text
        assert "http" in text

    def test_lettered_sub_items_parse(self):
        _, items = rg.load_guideline("consort")
        assert any(item["number"] == "1a" for item in items)

    def test_unknown_guideline_raises(self):
        with pytest.raises(FileNotFoundError):
            rg.load_guideline("not-a-guideline")


class TestSignals:
    def test_registry_identifier_is_detected(self):
        _, items = rg.load_guideline("prisma2020")
        signals = rg.detect_signals("The review was registered in PROSPERO.", items)
        assert signals

    def test_a_signal_is_never_an_answer(self, tmp_path):
        _, items = rg.load_guideline("prisma2020")
        signals = rg.detect_signals("Registered in PROSPERO.", items)
        worksheet = rg.generate_worksheet("t", "prisma2020", items, signals)
        assert worksheet.count("**Answer:** [TODO: Yes/No/NA]") == len(items)

    def test_no_signals_on_empty_text(self):
        _, items = rg.load_guideline("coreq")
        assert rg.detect_signals("", items) == {}


class TestWorksheetValidation:
    def _worksheet(self, answer, location):
        return (
            "# W\n\n## 1. Title\n**Question:** Q\n**Guidance:** G\n"
            f"**Answer:** {answer}\n**Location:** {location}\n"
        )

    def test_complete_item_passes(self):
        assert rg.validate_worksheet(self._worksheet("Yes", "Section 2")) == []

    def test_na_still_needs_a_reason(self):
        problems = rg.validate_worksheet(self._worksheet("NA", "[TODO]"))
        assert len(problems) == 1
        assert "Location is empty" in problems[0]

    def test_unanswered_item_is_reported(self):
        problems = rg.validate_worksheet(self._worksheet("[TODO: Yes/No/NA]", "Section 2"))
        assert "must be Yes, No or NA" in problems[0]

    def test_freeform_answer_is_rejected(self):
        problems = rg.validate_worksheet(self._worksheet("mostly", "Section 2"))
        assert len(problems) == 1

    def test_empty_worksheet_is_reported(self):
        assert rg.validate_worksheet("# nothing here") == ["worksheet has no items; regenerate it"]


class TestCli:
    def _run(self, args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "reporting_guideline.py")] + args,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_help_exits_zero(self):
        assert self._run(["--help"]).returncode == 0

    def test_list_names_every_guideline(self):
        result = self._run(["--list"])
        assert result.returncode == 0
        for slug in EXPECTED:
            assert slug in result.stdout

    def test_for_discipline_lists_the_medical_guidelines(self):
        result = self._run(["--for-discipline", "medicine"])
        assert result.returncode == 0
        assert "consort" in result.stdout and "prisma2020" in result.stdout

    def test_for_discipline_says_when_there_are_none(self):
        result = self._run(["--for-discipline", "humanities"])
        assert result.returncode == 0
        assert "no reporting-guideline tradition" in result.stdout

    def test_generate_then_validate_round_trip(self, tmp_path):
        (tmp_path / "notes").mkdir()
        (tmp_path / "main.md").write_text("Registered in PROSPERO. Ethics approval was granted.", encoding="utf-8")

        generated = self._run(["--guideline", "care", "--project-dir", str(tmp_path)])
        assert generated.returncode == 0
        worksheet = tmp_path / "notes" / "reporting-care.md"
        assert worksheet.is_file()

        unfinished = self._run(["--guideline", "care", "--project-dir", str(tmp_path), "--validate"])
        assert unfinished.returncode == 1

        filled = worksheet.read_text(encoding="utf-8")
        filled = filled.replace("**Answer:** [TODO: Yes/No/NA]", "**Answer:** Yes")
        filled = filled.replace("**Location:** [TODO]", "**Location:** Section 1")
        worksheet.write_text(filled, encoding="utf-8")

        finished = self._run(["--guideline", "care", "--project-dir", str(tmp_path), "--validate"])
        assert finished.returncode == 0

    def test_generating_twice_needs_force(self, tmp_path):
        (tmp_path / "notes").mkdir()
        assert self._run(["--guideline", "care", "--project-dir", str(tmp_path)]).returncode == 0
        assert self._run(["--guideline", "care", "--project-dir", str(tmp_path)]).returncode == 2
        assert self._run(["--guideline", "care", "--project-dir", str(tmp_path), "--force"]).returncode == 0

    def test_missing_arguments_exit_two(self):
        assert self._run(["--guideline", "care"]).returncode == 2
