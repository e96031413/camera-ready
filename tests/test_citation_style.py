"""Tests for scripts/citation_style.py and the assets/styles profiles."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import citation_style as cs  # noqa: E402

EXPECTED_STYLES = {"apa7", "mla9", "chicago-author-date", "chicago-notes", "vancouver", "ieee"}


class TestInstalledProfiles:
    def test_expected_styles_exist(self):
        assert EXPECTED_STYLES.issubset(set(cs.list_styles()))

    @pytest.mark.parametrize("slug", sorted(EXPECTED_STYLES))
    def test_every_profile_validates(self, slug):
        config = cs.load_style(slug)
        assert cs.validate_style(config, path_label=slug) == []

    @pytest.mark.parametrize("slug", sorted(EXPECTED_STYLES))
    def test_every_profile_declares_misc_requirements(self, slug):
        config = cs.load_style(slug)
        assert config.get("required_fields_misc"), f"{slug} must say what a @misc entry needs"

    def test_unknown_style_raises(self):
        with pytest.raises(cs.StyleError):
            cs.load_style("harvard-does-not-exist")

    def test_ieee_is_the_only_bibtex_backend(self):
        processors = {slug: cs.load_style(slug)["bib_processor"] for slug in EXPECTED_STYLES}
        assert processors["ieee"] == "bibtex"
        assert all(value == "biber" for slug, value in processors.items() if slug != "ieee")


class TestPreamble:
    def test_biblatex_style_adds_a_bib_resource(self):
        text = cs.render_preamble(cs.load_style("apa7"))
        assert "\\addbibresource{ref.bib}" in text
        assert "style=apa" in text

    def test_bst_style_emits_a_bibliographystyle(self):
        text = cs.render_preamble(cs.load_style("ieee"))
        assert "\\bibliographystyle{IEEEtran}" in text
        assert "\\addbibresource" not in text

    def test_chicago_loads_its_own_package_not_biblatex(self):
        text = cs.render_preamble(cs.load_style("chicago-notes"))
        assert "{biblatex-chicago}" in text

    def test_mla_bibliography_is_titled_works_cited(self):
        config = cs.load_style("mla9")
        assert "Works Cited" in config["latex_bibliography_line"]


class TestBibParsing:
    def test_reads_type_key_and_fields(self):
        text = "@article{smith2020,\n  author = {S},\n  title = {T},\n  year = {2020}\n}\n"
        entries = cs.parse_bib_entries(text)
        assert entries == [("article", "smith2020", {"author", "title", "year"})]

    def test_ignores_an_unknown_entry_type(self):
        config = cs.load_style("apa7")
        assert cs.validate_bib(config, "@patent{p1,\n  title = {T}\n}\n") == []


class TestBibValidation:
    def test_missing_field_is_reported(self):
        config = cs.load_style("apa7")
        text = "@misc{broken,\n  title = {A Paper},\n  year = {2024}\n}\n"
        problems = cs.validate_bib(config, text)
        assert len(problems) == 1
        assert "author" in problems[0]

    def test_alternation_is_satisfied_by_either_field(self):
        config = cs.load_style("apa7")
        with_doi = "@misc{a,\n  author = {A},\n  title = {T},\n  year = {2024},\n  doi = {10.1/x}\n}\n"
        with_url = "@misc{a,\n  author = {A},\n  title = {T},\n  year = {2024},\n  url = {https://x}\n}\n"
        assert cs.validate_bib(config, with_doi) == []
        assert cs.validate_bib(config, with_url) == []

    def test_field_names_are_case_insensitive(self):
        config = cs.load_style("ieee")
        text = "@inproceedings{a,\n  AUTHOR = {A},\n  Title = {T},\n  BookTitle = {B},\n  YEAR = {2024}\n}\n"
        assert cs.validate_bib(config, text) == []

    def test_ieee_wants_journal_and_apa_wants_journaltitle(self):
        bibtex_style = "@article{a,\n  author={A},\n  title={T},\n  journal={J},\n  year={2020}\n}\n"
        assert cs.validate_bib(cs.load_style("ieee"), bibtex_style) == []
        assert cs.validate_bib(cs.load_style("apa7"), bibtex_style) != []

    def test_example_bibliography_passes_every_style(self):
        text = (ROOT / "examples" / "minimal-review-paper" / "ref.bib").read_text(encoding="utf-8")
        for slug in sorted(EXPECTED_STYLES):
            assert cs.validate_bib(cs.load_style(slug), text) == [], slug


class TestCli:
    def _run(self, args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "citation_style.py")] + args,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_help_exits_zero(self):
        assert self._run(["--help"]).returncode == 0

    def test_bare_invocation_prints_help(self):
        result = self._run([])
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()

    def test_list_names_every_style(self):
        result = self._run(["list"])
        assert result.returncode == 0
        for slug in EXPECTED_STYLES:
            assert slug in result.stdout

    def test_unknown_style_exits_two(self):
        result = self._run(["show", "not-a-style"])
        assert result.returncode == 2
        assert "unknown citation style" in result.stderr

    def test_validate_fails_on_a_broken_entry(self, tmp_path):
        bib = tmp_path / "ref.bib"
        bib.write_text("@misc{broken,\n  title = {T}\n}\n", encoding="utf-8")
        result = self._run(["validate", "apa7", "--bib", str(bib)])
        assert result.returncode == 1
        assert "FAIL" in result.stdout
