import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "arxiv_package.py"

MAIN_TEX = r"""
\documentclass{article}
\usepackage{graphicx}
% private note: reviewer 2 hated this framing
\begin{document}
\input{sections/intro}
\bibliographystyle{plain}
\bibliography{ref}
\end{document}
"""

INTRO_TEX = r"""
\section{Introduction}
\todo{tighten this}The method works. % fix wording later
\begin{figure}
\includegraphics[width=\columnwidth]{figures/plot}
\end{figure}
"""

BBL = r"""
\begin{thebibliography}{1}
\bibitem{smith2023} J. Smith. A paper. 2023.
\end{thebibliography}
"""

# A tiny but structurally valid PDF, used as a figure fixture.
FAKE_PDF = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\ntrailer\n<< >>\n%%EOF\n"


class TestArxivPackage(unittest.TestCase):
    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=str(SKILL_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )

    def _project(
        self,
        tmp: str,
        *,
        main_tex: str = MAIN_TEX,
        intro_tex: str = INTRO_TEX,
        bbl: str | None = BBL,
        figure_name: str = "plot.pdf",
    ) -> Path:
        project_dir = Path(tmp) / "paper"
        (project_dir / "sections").mkdir(parents=True)
        (project_dir / "figures").mkdir(parents=True)
        (project_dir / "main.tex").write_text(main_tex.strip() + "\n", encoding="utf-8")
        (project_dir / "sections" / "intro.tex").write_text(intro_tex.strip() + "\n", encoding="utf-8")
        (project_dir / "figures" / figure_name).write_bytes(FAKE_PDF)
        (project_dir / "ref.bib").write_text("@misc{smith2023, title={A paper}}\n", encoding="utf-8")
        if bbl is not None:
            (project_dir / "main.bbl").write_text(bbl.strip() + "\n", encoding="utf-8")
        return project_dir

    def _members(self, tarball: Path) -> list[str]:
        with tarfile.open(tarball) as tar:
            return sorted(tar.getnames())

    def _read(self, tarball: Path, name: str) -> str:
        with tarfile.open(tarball) as tar:
            return tar.extractfile(name).read().decode("utf-8")

    # ── CLI surface ───────────────────────────────────────────────

    def test_help_exits_zero(self) -> None:
        self.assertEqual(self._run(["--help"]).returncode, 0)

    def test_missing_project_dir_errors(self) -> None:
        proc = self._run(["--project-dir", str(SKILL_DIR / "does-not-exist")])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("not found", proc.stderr)

    def test_missing_main_tex_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty"
            empty.mkdir()
            proc = self._run(["--project-dir", str(empty)])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("entry point not found", proc.stderr)

    # ── Tarball contents ──────────────────────────────────────────

    def test_builds_tarball(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertTrue((project_dir / "submission.tar.gz").exists())

    def test_directory_structure_is_flattened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            self._run(["--project-dir", str(project_dir)])
            members = self._members(project_dir / "submission.tar.gz")
            self.assertEqual(members, ["intro.tex", "main.tex", "plot.pdf"])
            for name in members:
                self.assertNotIn("/", name, msg="arXiv submissions are packaged flat")

    def test_paths_are_rewritten_to_match_the_flattening(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            self._run(["--project-dir", str(project_dir)])
            tarball = project_dir / "submission.tar.gz"
            self.assertIn(r"\input{intro}", self._read(tarball, "main.tex"))
            self.assertIn("{plot}", self._read(tarball, "intro.tex"))
            self.assertNotIn("figures/", self._read(tarball, "intro.tex"))

    def test_bbl_is_inlined_and_bibliography_macro_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            self._run(["--project-dir", str(project_dir)])
            main = self._read(project_dir / "submission.tar.gz", "main.tex")
            self.assertIn(r"\begin{thebibliography}", main)
            self.assertIn("smith2023", main)
            self.assertNotIn(r"\bibliography{ref}", main)

    def test_missing_bbl_is_a_blocking_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, bbl=None)
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("does not run", proc.stdout)

    def test_comments_are_stripped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            self._run(["--project-dir", str(project_dir)])
            tarball = project_dir / "submission.tar.gz"
            self.assertNotIn("reviewer 2", self._read(tarball, "main.tex"))
            self.assertNotIn("fix wording later", self._read(tarball, "intro.tex"))

    def test_keep_comments_preserves_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            self._run(["--project-dir", str(project_dir), "--keep-comments"])
            main = self._read(project_dir / "submission.tar.gz", "main.tex")
            self.assertIn("reviewer 2", main)

    def test_todo_macros_are_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            self._run(["--project-dir", str(project_dir)])
            intro = self._read(project_dir / "submission.tar.gz", "intro.tex")
            self.assertNotIn("tighten this", intro)
            self.assertIn("The method works.", intro)

    def test_style_files_are_included(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            (project_dir / "neurips_2025.sty").write_text("% stub\n", encoding="utf-8")
            self._run(["--project-dir", str(project_dir)])
            self.assertIn("neurips_2025.sty", self._members(project_dir / "submission.tar.gz"))

    def test_filename_collision_is_resolved(self) -> None:
        tex = INTRO_TEX + "\n\\includegraphics{extra/plot}\n"
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, intro_tex=tex)
            (project_dir / "extra").mkdir()
            (project_dir / "extra" / "plot.pdf").write_bytes(FAKE_PDF)
            self._run(["--project-dir", str(project_dir)])
            members = self._members(project_dir / "submission.tar.gz")
            self.assertIn("plot.pdf", members)
            self.assertIn("extra-plot.pdf", members)

    # ── Problem detection ─────────────────────────────────────────

    def test_missing_figure_is_a_blocking_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            (project_dir / "figures" / "plot.pdf").unlink()
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("includegraphics", proc.stdout)

    def test_unsupported_graphics_format_is_a_blocking_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, figure_name="plot.svg")
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(".svg", proc.stdout)

    def test_eps_is_a_warning_not_a_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, figure_name="plot.eps")
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertEqual(proc.returncode, 0, msg=proc.stdout)
            self.assertIn("[WARN]", proc.stdout)

    def test_absolute_path_is_a_blocking_error(self) -> None:
        tex = MAIN_TEX.replace(r"\input{sections/intro}", "\\input{sections/intro}\n\\input{/home/jane/extra}")
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, main_tex=tex)
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("absolute path", proc.stdout)

    def test_missing_input_file_is_a_blocking_error(self) -> None:
        tex = MAIN_TEX.replace(r"\input{sections/intro}", r"\input{sections/nowhere}")
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, main_tex=tex)
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("does not resolve", proc.stdout)

    # ── Report and safety ─────────────────────────────────────────

    def test_report_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            self._run(["--project-dir", str(project_dir)])
            report = project_dir / "notes" / "arxiv-submission-report.md"
            self.assertTrue(report.exists())
            content = report.read_text(encoding="utf-8")
            self.assertIn("Nothing has been uploaded", content)
            self.assertIn("main.tex", content)

    def test_report_is_written_even_when_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, bbl=None)
            self._run(["--project-dir", str(project_dir)])
            self.assertTrue((project_dir / "notes" / "arxiv-submission-report.md").exists())

    def test_never_claims_to_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertIn("does not upload", proc.stdout)

    def test_dry_run_writes_no_tarball(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            proc = self._run(["--project-dir", str(project_dir), "--dry-run"])
            self.assertEqual(proc.returncode, 0, msg=proc.stdout)
            self.assertFalse((project_dir / "submission.tar.gz").exists())
            self.assertTrue((project_dir / "notes" / "arxiv-submission-report.md").exists())

    def test_custom_out_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp)
            out = Path(tmp) / "dist" / "upload.tar.gz"
            proc = self._run(["--project-dir", str(project_dir), "--out", str(out)])
            self.assertEqual(proc.returncode, 0, msg=proc.stdout)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
