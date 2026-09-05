"""Tests for scripts/export_document.py — the pandoc output path.

Conversion tests are skipped when pandoc is absent, so the suite stays green on
a machine that only builds LaTeX. Everything that does not need pandoc runs
everywhere.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import export_document as ed  # noqa: E402

HAS_PANDOC = ed.pandoc_version() is not None
needs_pandoc = pytest.mark.skipif(not HAS_PANDOC, reason="pandoc is not installed")


def run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "export_document.py")] + args,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


class TestFormatTables:
    def test_word_and_typst_are_both_reachable(self):
        assert "docx" in ed.FORMATS and "typst" in ed.FORMATS

    def test_latex_and_markdown_are_both_readable(self):
        assert ed.READERS[".tex"] == "latex"
        assert ed.READERS[".md"] == "markdown"


class TestCommandAssembly:
    def _command(self, **overrides):
        defaults = dict(
            input_path=Path("main.md"),
            output_path=Path("main.docx"),
            reader="markdown",
            writer="docx",
            bibliography=Path("ref.bib"),
            csl_path=Path("apa.csl"),
            reference_doc=None,
            resource_path=Path("."),
        )
        defaults.update(overrides)
        return ed.build_command(**defaults)

    def test_a_bibliography_turns_on_citeproc(self):
        assert "--citeproc" in self._command()

    def test_no_bibliography_means_no_citeproc(self):
        assert "--citeproc" not in self._command(bibliography=None)

    def test_the_csl_file_is_passed_through(self):
        command = self._command()
        assert command[command.index("--csl") + 1] == "apa.csl"

    def test_a_reference_document_is_passed_through(self):
        command = self._command(reference_doc=Path("house.docx"))
        assert command[command.index("--reference-doc") + 1] == "house.docx"

    def test_the_resource_path_lets_pandoc_find_figures(self):
        command = self._command(resource_path=Path("papers/x"))
        assert command[command.index("--resource-path") + 1] == str(Path("papers/x"))


class TestGuards:
    def test_an_unsupported_input_extension_is_refused(self, tmp_path):
        source = tmp_path / "notes.txt"
        source.write_text("x", encoding="utf-8")
        result = run(["--input", str(source)])
        assert result.returncode == 2
        assert "cannot convert" in result.stderr

    def test_a_missing_input_is_refused(self, tmp_path):
        result = run(["--input", str(tmp_path / "nope.md")])
        assert result.returncode == 2

    def test_no_input_prints_help_and_exits_two(self):
        result = run([])
        assert result.returncode == 2

    def test_help_exits_zero(self):
        assert run(["--help"]).returncode == 0


class TestCheck:
    def test_check_reports_the_environment(self):
        result = run(["--check"])
        assert "pandoc" in result.stdout
        assert result.returncode == (0 if HAS_PANDOC else 1)


class TestConversion:
    @needs_pandoc
    def test_markdown_converts_to_docx(self, tmp_path):
        source = tmp_path / "main.md"
        source.write_text("---\ntitle: T\n---\n\n# Introduction\n\nText.\n", encoding="utf-8")
        result = run(["--input", str(source), "--to", "docx"])
        assert result.returncode == 0, result.stdout + result.stderr
        assert (tmp_path / "main.docx").stat().st_size > 0

    @needs_pandoc
    def test_markdown_converts_to_typst(self, tmp_path):
        source = tmp_path / "main.md"
        source.write_text("# Introduction\n\nText.\n", encoding="utf-8")
        assert run(["--input", str(source), "--to", "typst"]).returncode == 0
        assert (tmp_path / "main.typ").is_file()

    @needs_pandoc
    def test_a_missing_bibliography_warns_but_still_converts(self, tmp_path):
        source = tmp_path / "main.md"
        source.write_text("# Introduction\n\nText.\n", encoding="utf-8")
        result = run(["--input", str(source), "--to", "html"])
        assert result.returncode == 0
        assert "no bibliography" in result.stdout

    @needs_pandoc
    def test_no_fetch_without_a_cached_csl_is_refused(self, tmp_path):
        source = tmp_path / "main.md"
        source.write_text("# T\n", encoding="utf-8")
        cached = ed.csl_dir() / "modern-language-association.csl"
        if cached.exists():
            pytest.skip("the MLA CSL file is already cached on this machine")
        result = run(["--input", str(source), "--style", "mla9", "--no-fetch"])
        assert result.returncode == 2
        assert "--fetch-csl" in result.stderr
