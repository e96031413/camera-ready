"""Tests for scripts/discipline_profile.py and the assets/disciplines profiles."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import citation_style as cs  # noqa: E402
import discipline_profile as dp  # noqa: E402

EXPECTED = {
    "computer-science",
    "psychology",
    "medicine",
    "humanities",
    "law",
    "education",
    "business",
    "social-science",
}


class TestInstalledProfiles:
    def test_expected_disciplines_exist(self):
        assert EXPECTED.issubset(set(dp.list_disciplines()))

    @pytest.mark.parametrize("slug", sorted(EXPECTED))
    def test_every_profile_validates(self, slug):
        config = dp.load_discipline(slug)
        assert dp.validate_discipline(config, path_label=slug) == []

    @pytest.mark.parametrize("slug", sorted(EXPECTED))
    def test_default_style_is_installed_and_allowed(self, slug):
        config = dp.load_discipline(slug)
        assert config["default_style"] in cs.list_styles()
        assert config["default_style"] in config["allowed_styles"]

    @pytest.mark.parametrize("slug", sorted(EXPECTED))
    def test_every_reporting_guideline_has_a_question_set(self, slug):
        config = dp.load_discipline(slug)
        for guideline in config["reporting_guidelines"]:
            assert (ROOT / "assets" / "checklists" / f"{guideline}.md").is_file()

    def test_unknown_discipline_raises(self):
        with pytest.raises(dp.DisciplineError):
            dp.load_discipline("astrology")


class TestFieldSpecificExpectations:
    """The profiles exist to encode differences; assert the differences are real."""

    def test_medicine_uses_vancouver_and_requires_ethics(self):
        config = dp.load_discipline("medicine")
        assert config["default_style"] == "vancouver"
        assert config["ethics_approval_required"] is True
        assert "consort" in config["reporting_guidelines"]

    def test_humanities_has_no_reporting_guideline_and_no_data_statement(self):
        config = dp.load_discipline("humanities")
        assert config["reporting_guidelines"] == []
        assert config["data_availability_required"] is False
        assert config["evidence_model"] == "interpretive"

    def test_law_is_doctrinal_and_uses_chicago_notes(self):
        config = dp.load_discipline("law")
        assert config["evidence_model"] == "doctrinal"
        assert config["default_style"] == "chicago-notes"

    def test_computer_science_is_the_only_latex_default(self):
        formats = {slug: dp.load_discipline(slug)["default_format"] for slug in EXPECTED}
        assert formats["computer-science"] == "latex"
        assert all(value == "docx" for slug, value in formats.items() if slug != "computer-science")

    def test_qualitative_guidelines_reach_the_social_fields(self):
        for slug in ("education", "social-science"):
            guidelines = dp.load_discipline(slug)["reporting_guidelines"]
            assert "coreq" in guidelines or "srqr" in guidelines


class TestRequiredStatements:
    def test_medicine_wants_ethics_funding_and_conflicts(self):
        statements = dp.required_statements(dp.load_discipline("medicine"))
        joined = " ".join(statements)
        assert "Ethics" in joined and "Funding" in joined and "Conflict" in joined

    def test_computer_science_wants_no_ethics_statement(self):
        statements = dp.required_statements(dp.load_discipline("computer-science"))
        assert not any("Ethics" in item for item in statements)


class TestRequirementsReport:
    def test_report_names_the_style_and_the_guidelines(self):
        report = dp.requirements_report(dp.load_discipline("medicine"))
        assert "Vancouver" in report
        assert "consort" in report
        assert "Ethics approval" in report

    def test_report_says_when_a_field_has_no_guidelines(self):
        report = dp.requirements_report(dp.load_discipline("humanities"))
        assert "no reporting-guideline tradition" in report


class TestValidation:
    def test_style_not_in_allowed_list_is_reported(self):
        config = dict(dp.load_discipline("medicine"))
        config["default_style"] = "ieee"
        problems = dp.validate_discipline(config, path_label="x")
        assert any("not listed in allowed_styles" in p for p in problems)

    def test_missing_guideline_question_set_is_reported(self):
        config = dict(dp.load_discipline("medicine"))
        config["reporting_guidelines"] = ["not-a-guideline"]
        problems = dp.validate_discipline(config, path_label="x")
        assert any("has no question set" in p for p in problems)

    def test_unknown_format_is_reported(self):
        config = dict(dp.load_discipline("humanities"))
        config["default_format"] = "pdf"
        problems = dp.validate_discipline(config, path_label="x")
        assert any("default_format" in p for p in problems)


class TestCli:
    def _run(self, args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "discipline_profile.py")] + args,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_help_exits_zero(self):
        assert self._run(["--help"]).returncode == 0

    def test_list_names_every_discipline(self):
        result = self._run(["list"])
        assert result.returncode == 0
        for slug in EXPECTED:
            assert slug in result.stdout

    def test_requirements_writes_to_a_file(self, tmp_path):
        out = tmp_path / "req.md"
        result = self._run(["requirements", "psychology", "--out", str(out)])
        assert result.returncode == 0
        assert "APA" in out.read_text(encoding="utf-8")

    def test_unknown_discipline_exits_two(self):
        result = self._run(["show", "astrology"])
        assert result.returncode == 2
