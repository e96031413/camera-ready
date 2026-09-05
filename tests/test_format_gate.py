import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "format_gate.py"

MAIN_TEX = r"""
\documentclass{article}
\usepackage{neurips_2025}
\begin{document}
\section{Introduction}
Text.
\section{Broader Impact}
Text.
\section*{NeurIPS Paper Checklist}
Text.
\end{document}
"""


def make_log(pages: int) -> str:
    return f"Output written on main.pdf ({pages} pages, 123456 bytes).\n"


def make_aux(label: str, page: int) -> str:
    return "\\newlabel{%s}{{1}{%d}{}{}{}}\n" % (label, page)


class TestFormatGate(unittest.TestCase):
    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=str(SKILL_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )

    def _project(self, tmp: str, *, main_tex: str = MAIN_TEX, style: bool = True) -> Path:
        project_dir = Path(tmp) / "paper"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "main.tex").write_text(main_tex.strip() + "\n", encoding="utf-8")
        if style:
            (project_dir / "neurips_2025.sty").write_text("% stub\n", encoding="utf-8")
        return project_dir

    # ── CLI surface ───────────────────────────────────────────────

    def test_help_exits_zero(self) -> None:
        self.assertEqual(self._run(["--help"]).returncode, 0)

    def test_list_venues(self) -> None:
        proc = self._run(["--list-venues"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("neurips", proc.stdout)

    def test_missing_args_errors(self) -> None:
        proc = self._run([])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("required", proc.stderr)

    def test_unknown_venue_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            proc = self._run(["--project-dir", str(project_dir), "--venue", "nope"])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("unknown venue", proc.stderr)

    def test_missing_main_tex_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty"
            empty.mkdir()
            proc = self._run(["--project-dir", str(empty), "--venue", "neurips"])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("no main.tex", proc.stderr)

    # ── Page limit ────────────────────────────────────────────────

    def test_page_limit_skipped_without_compile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[SKIP] Page limit", proc.stdout)
            self.assertIn("compile the paper first", proc.stdout)

    def test_page_limit_passes_within_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            (project_dir / "main.log").write_text(make_log(14), encoding="utf-8")
            (project_dir / "main.aux").write_text(make_aux("sec:bib", 10), encoding="utf-8")
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[PASS] Page limit", proc.stdout)
            self.assertIn("9 main-text pages", proc.stdout)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout)

    def test_page_limit_fails_when_over(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            (project_dir / "main.log").write_text(make_log(18), encoding="utf-8")
            (project_dir / "main.aux").write_text(make_aux("sec:bib", 13), encoding="utf-8")
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[FAIL] Page limit", proc.stdout)
            self.assertIn("3 over the limit", proc.stdout)
            self.assertNotEqual(proc.returncode, 0)

    def test_page_limit_respects_tighter_venue(self) -> None:
        """The same paper that passes NeurIPS (9) fails AAAI (7)."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            (project_dir / "main.log").write_text(make_log(14), encoding="utf-8")
            (project_dir / "main.aux").write_text(make_aux("sec:bib", 10), encoding="utf-8")
            proc = self._run(["--project-dir", str(project_dir), "--venue", "aaai"])
            self.assertIn("[FAIL] Page limit", proc.stdout)

    def test_custom_bib_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            (project_dir / "main.log").write_text(make_log(12), encoding="utf-8")
            (project_dir / "main.aux").write_text(make_aux("bibstart", 8), encoding="utf-8")
            proc = self._run(
                ["--project-dir", str(project_dir), "--venue", "neurips", "--bib-label", "bibstart"]
            )
            self.assertIn("7 main-text pages", proc.stdout)

    def test_missing_label_warns_when_over_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            (project_dir / "main.log").write_text(make_log(20), encoding="utf-8")
            (project_dir / "main.aux").write_text("% no labels\n", encoding="utf-8")
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[WARN] Page limit", proc.stdout)

    # ── Required sections ─────────────────────────────────────────

    def test_required_sections_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[PASS] Required section: Broader Impact", proc.stdout)
            self.assertIn("[PASS] Required section: Paper Checklist", proc.stdout)

    def test_missing_required_section_fails(self) -> None:
        tex = MAIN_TEX.replace(r"\section{Broader Impact}", r"\section{Discussion}")
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, main_tex=tex)
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[FAIL] Required section: Broader Impact", proc.stdout)
            self.assertNotEqual(proc.returncode, 0)

    def test_acl_limitations_required(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{acl}
\begin{document}
\section{Introduction}
Text.
\end{document}
"""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, main_tex=tex, style=False)
            (project_dir / "acl.sty").write_text("% stub\n", encoding="utf-8")
            proc = self._run(["--project-dir", str(project_dir), "--venue", "acl"])
            self.assertIn("[FAIL] Required section: Limitations", proc.stdout)

    def test_section_found_in_included_file(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{neurips_2025}
\begin{document}
\input{sections/impact}
\section*{NeurIPS Paper Checklist}
\end{document}
"""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, main_tex=tex)
            (project_dir / "sections").mkdir()
            (project_dir / "sections" / "impact.tex").write_text(
                "\\section{Broader Impact}\nText.\n", encoding="utf-8"
            )
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[PASS] Required section: Broader Impact", proc.stdout)

    def test_commented_out_section_does_not_count(self) -> None:
        tex = MAIN_TEX.replace(r"\section{Broader Impact}", r"% \section{Broader Impact}")
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, main_tex=tex)
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[FAIL] Required section: Broader Impact", proc.stdout)

    def test_cvpr_has_no_required_sections(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{cvpr}
\begin{document}
\section{Introduction}
\end{document}
"""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, main_tex=tex, style=False)
            (project_dir / "cvpr.sty").write_text("% stub\n", encoding="utf-8")
            proc = self._run(["--project-dir", str(project_dir), "--venue", "cvpr"])
            self.assertIn("[PASS] Required sections", proc.stdout)

    # ── Style file ────────────────────────────────────────────────

    def test_style_file_present_and_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[PASS] Venue style file", proc.stdout)

    def test_style_file_missing_fails_with_setup_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, style=False)
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[FAIL] Venue style file", proc.stdout)
            self.assertIn("venue_setup.py", proc.stdout)

    def test_style_file_present_but_not_loaded_fails(self) -> None:
        tex = MAIN_TEX.replace(r"\usepackage{neurips_2025}", "")
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, main_tex=tex)
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[FAIL] Venue style file", proc.stdout)
            self.assertIn("does not load it", proc.stdout)

    def test_style_file_year_mismatch_still_matches_family(self) -> None:
        """A 2026 style file must satisfy a config written against 2025."""
        tex = MAIN_TEX.replace("neurips_2025", "neurips_2026")
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, main_tex=tex, style=False)
            (project_dir / "neurips_2026.sty").write_text("% stub\n", encoding="utf-8")
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[PASS] Venue style file", proc.stdout)

    # ── Anonymity + strict ────────────────────────────────────────

    def test_anonymity_warns_and_points_at_the_scanner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            proc = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            self.assertIn("[WARN] Anonymity", proc.stdout)
            self.assertIn("anonymity_check.py", proc.stdout)

    def test_strict_turns_warnings_into_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            (project_dir / "main.log").write_text(make_log(14), encoding="utf-8")
            (project_dir / "main.aux").write_text(make_aux("sec:bib", 10), encoding="utf-8")
            lenient = self._run(["--project-dir", str(project_dir), "--venue", "neurips"])
            strict = self._run(["--project-dir", str(project_dir), "--venue", "neurips", "--strict"])
            self.assertEqual(lenient.returncode, 0, msg=lenient.stdout)
            self.assertNotEqual(strict.returncode, 0, msg=strict.stdout)


if __name__ == "__main__":
    unittest.main()
