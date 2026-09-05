"""Tests for scripts/quick_start.py — the five-minute path."""

import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import citation_style as cs  # noqa: E402
import discipline_profile as dp  # noqa: E402
import quick_start as qs  # noqa: E402


def run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "quick_start.py")] + args,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


class TestLatexSkeleton:
    def _build(self, style_slug, discipline_slug="computer-science"):
        discipline = dp.load_discipline(discipline_slug)
        style = cs.load_style(style_slug)
        return qs.build_latex(
            "A Title",
            discipline["required_sections"],
            style,
            dp.required_statements(discipline),
        )

    def test_document_is_well_formed(self):
        text = self._build("ieee")
        assert text.count("\\begin{document}") == 1
        assert text.count("\\end{document}") == 1
        assert text.index("\\begin{document}") < text.index("\\end{document}")

    def test_bst_backend_ends_with_a_bibliography_command(self):
        text = self._build("ieee")
        assert "\\bibliographystyle{IEEEtran}" in text
        assert "\\bibliography{ref}" in text

    def test_biblatex_backend_ends_with_printbibliography(self):
        text = self._build("apa7", "psychology")
        assert "\\addbibresource{ref.bib}" in text
        assert "\\printbibliography" in text
        assert "\\bibliography{ref}" not in text

    def test_every_section_becomes_a_stub(self):
        discipline = dp.load_discipline("computer-science")
        text = self._build("ieee")
        for section in discipline["required_sections"]:
            if section in {"Abstract", "References"}:
                continue
            assert f"\\section{{{section}}}" in text

    def test_no_prose_is_invented(self):
        """Every stub is a comment; the skeleton must assert nothing."""
        text = self._build("ieee")
        body = text.split("\\begin{document}", 1)[1].split("\\end{document}", 1)[0]
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            assert stripped.startswith(("%", "\\")), f"unexpected prose: {stripped!r}"


class TestMarkdownSkeleton:
    def test_front_matter_names_the_bibliography_and_style(self):
        discipline = dp.load_discipline("psychology")
        style = cs.load_style("apa7")
        text = qs.build_markdown("A Title", discipline["required_sections"], style, [])
        assert "bibliography: ref.bib" in text
        assert "csl-id: apa" in text

    def test_required_statements_become_a_declarations_section(self):
        discipline = dp.load_discipline("medicine")
        style = cs.load_style("vancouver")
        text = qs.build_markdown("T", discipline["required_sections"], style,
                                 dp.required_statements(discipline))
        assert "# Declarations" in text
        assert "Ethics approval" in text


class TestBibliographyStub:
    def test_stub_is_empty_of_entries_but_names_the_fetch_command(self):
        text = qs.build_bib(cs.load_style("vancouver"))
        assert "@" not in text
        assert "fetch_bibtex.py" in text
        assert "citation_style.py validate vancouver" in text


class TestIssues:
    def test_research_comes_first_and_writing_depends_on_evidence(self):
        rows = qs.build_issues(["Introduction", "Method", "Results"])
        by_id = {row["ID"]: row for row in rows}
        assert by_id["R1"]["Depends_On"] == ""
        assert by_id["E1"]["Depends_On"] == "R1"
        assert by_id["W1"]["Depends_On"] == "E1"

    def test_every_row_starts_open(self):
        rows = qs.build_issues(["Introduction"])
        assert {row["Status"] for row in rows} == {"TODO"}

    def test_reference_sections_do_not_become_writing_issues(self):
        titles = {row["Title"] for row in qs.build_issues(["Introduction", "References", "Works Cited"])}
        assert "References" not in titles and "Works Cited" not in titles


class TestEndToEnd:
    def test_psychology_produces_a_markdown_project(self, tmp_path):
        target = tmp_path / "p"
        result = run(["--title", "Sleep and recall", "--discipline", "psychology", "--project-dir", str(target)])
        assert result.returncode == 0, result.stderr
        assert (target / "main.md").is_file()
        assert not (target / "main.tex").exists()
        assert (target / "ref.bib").is_file()
        assert (target / "notes" / "autopilot-state.json").is_file()
        assert list((target / "plan").glob("*.md"))
        assert list((target / "issues").glob("*.csv"))

    def test_computer_science_produces_a_latex_project(self, tmp_path):
        target = tmp_path / "p"
        result = run(["--title", "Scaling laws", "--discipline", "computer-science", "--project-dir", str(target)])
        assert result.returncode == 0, result.stderr
        assert (target / "main.tex").is_file()

    def test_generated_issues_csv_is_readable(self, tmp_path):
        target = tmp_path / "p"
        run(["--title", "T", "--discipline", "humanities", "--project-dir", str(target)])
        path = next((target / "issues").glob("*.csv"))
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows and rows[0]["ID"] == "R1"

    def test_the_generated_bibliography_passes_its_own_style_gate(self, tmp_path):
        target = tmp_path / "p"
        run(["--title", "T", "--discipline", "medicine", "--project-dir", str(target)])
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "citation_style.py"),
                "validate",
                "vancouver",
                "--bib",
                str(target / "ref.bib"),
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0

    def test_a_style_the_field_does_not_use_warns_but_proceeds(self, tmp_path):
        target = tmp_path / "p"
        result = run(
            ["--title", "T", "--discipline", "medicine", "--style", "ieee", "--project-dir", str(target)]
        )
        assert result.returncode == 0
        assert "warning" in result.stdout

    def test_existing_non_empty_directory_needs_force(self, tmp_path):
        target = tmp_path / "p"
        target.mkdir()
        (target / "keep.txt").write_text("x", encoding="utf-8")
        assert run(["--title", "T", "--discipline", "law", "--project-dir", str(target)]).returncode == 2
        assert run(
            ["--title", "T", "--discipline", "law", "--project-dir", str(target), "--force"]
        ).returncode == 0


class TestCli:
    def test_help_exits_zero(self):
        assert run(["--help"]).returncode == 0

    def test_list_shows_the_disciplines(self):
        result = run(["--list"])
        assert result.returncode == 0
        assert "medicine" in result.stdout

    def test_missing_arguments_exit_two(self):
        assert run(["--title", "T"]).returncode == 2

    def test_unknown_discipline_exits_two(self, tmp_path):
        assert run(["--title", "T", "--discipline", "astrology", "--project-dir", str(tmp_path)]).returncode == 2
