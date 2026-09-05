import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "anonymity_check.py"

# A deliberately non-anonymous fixture paper. Every line here is a violation
# the tool is expected to catch.
DEANONYMIZED_TEX = r"""
\documentclass{article}
\author{Jane Q. Researcher\thanks{Supported by NSF grant 1234567.}}
\affiliation{Institute of Examples}
\begin{document}
% TODO(jane.researcher@example.edu): tighten the abstract
Correspondence: jane.researcher@example.edu
Our code is at https://github.com/janeresearcher/anon-paper
See also https://cs.example.edu/~jane/project
ORCID: https://orcid.org/0000-0002-1825-0097
In our previous work \cite{jane2023} we showed that this holds.
We proposed \cite{jane2022} an earlier variant.
As we have shown, the effect is robust.
\section{Acknowledgements}
We thank our colleagues.
\end{document}
"""

ANONYMOUS_TEX = r"""
\documentclass{article}
\begin{document}
\section{Introduction}
Prior work \cite{smith2023} showed that this holds.
An anonymized mirror is available at https://anonymous.4open.science/r/paper-1234
\section{Limitations}
The method assumes independent samples.
\end{document}
"""


class TestAnonymityCheck(unittest.TestCase):
    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=str(SKILL_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )

    def _project(self, tmp: str, tex: str, *, name: str = "main.tex") -> Path:
        project_dir = Path(tmp) / "paper"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / name).write_text(tex.strip() + "\n", encoding="utf-8")
        return project_dir

    # ── CLI surface ───────────────────────────────────────────────

    def test_help_exits_zero(self) -> None:
        self.assertEqual(self._run(["--help"]).returncode, 0)

    def test_missing_project_dir_errors(self) -> None:
        proc = self._run(["--project-dir", str(SKILL_DIR / "does-not-exist")])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("not found", proc.stderr)

    def test_empty_project_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty"
            empty.mkdir()
            proc = self._run(["--project-dir", str(empty)])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("no LaTeX", proc.stderr)

    # ── Blockers ──────────────────────────────────────────────────

    def test_deanonymized_paper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, DEANONYMIZED_TEX)
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertNotEqual(proc.returncode, 0, msg=proc.stdout)
            self.assertIn("Do not submit until every BLOCKER is resolved", proc.stdout)

    def test_detects_author_macro(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, DEANONYMIZED_TEX)
            self.assertIn("author macro", self._run(["--project-dir", str(project_dir)]).stdout)

    def test_detects_thanks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, DEANONYMIZED_TEX)
            self.assertIn("thanks/footnote", self._run(["--project-dir", str(project_dir)]).stdout)

    def test_detects_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, DEANONYMIZED_TEX)
            self.assertIn("email address", self._run(["--project-dir", str(project_dir)]).stdout)

    def test_detects_named_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, DEANONYMIZED_TEX)
            self.assertIn("named code repository", self._run(["--project-dir", str(project_dir)]).stdout)

    def test_detects_acknowledgements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, DEANONYMIZED_TEX)
            self.assertIn("acknowledgements", self._run(["--project-dir", str(project_dir)]).stdout)

    # ── Warnings ──────────────────────────────────────────────────

    def test_detects_first_person_self_citation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, DEANONYMIZED_TEX)
            out = self._run(["--project-dir", str(project_dir)]).stdout
            self.assertIn("first-person self-citation", out)
            self.assertIn("first-person reference to a citation", out)

    def test_detects_orcid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, DEANONYMIZED_TEX)
            self.assertIn("ORCID", self._run(["--project-dir", str(project_dir)]).stdout)

    def test_detects_identity_in_comment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, DEANONYMIZED_TEX)
            self.assertIn("identity in a LaTeX comment", self._run(["--project-dir", str(project_dir)]).stdout)

    def test_reports_line_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, DEANONYMIZED_TEX)
            self.assertIn("main.tex:2", self._run(["--project-dir", str(project_dir)]).stdout)

    # ── Clean paper ───────────────────────────────────────────────

    def test_anonymous_paper_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, ANONYMOUS_TEX)
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertEqual(proc.returncode, 0, msg=proc.stdout)

    def test_anonymous_mirror_is_info_not_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, ANONYMOUS_TEX)
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertIn("anonymous repository link", proc.stdout)
            self.assertEqual(proc.returncode, 0)

    def test_clean_run_states_it_is_not_proof(self) -> None:
        tex = "\\documentclass{article}\n\\begin{document}\nHello.\n\\end{document}\n"
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, tex)
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertEqual(proc.returncode, 0)
            self.assertIn("evidence, not proof", proc.stdout)

    def test_third_person_self_reference_is_clean(self) -> None:
        tex = r"""
\documentclass{article}
\begin{document}
Prior work \cite{smith2023} showed the effect. We propose a refinement.
\end{document}
"""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, tex)
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertEqual(proc.returncode, 0, msg=proc.stdout)

    # ── Scope and options ─────────────────────────────────────────

    def test_scans_bib_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, ANONYMOUS_TEX)
            (project_dir / "ref.bib").write_text(
                "@misc{x, note = {see https://github.com/janeresearcher/repo}}\n", encoding="utf-8"
            )
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertIn("ref.bib", proc.stdout)
            self.assertNotEqual(proc.returncode, 0)

    def test_scans_included_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, ANONYMOUS_TEX)
            (project_dir / "sections").mkdir()
            (project_dir / "sections" / "intro.tex").write_text(
                "Contact jane@example.org.\n", encoding="utf-8"
            )
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertIn("sections/intro.tex", proc.stdout)

    def test_class_files_are_not_scanned(self) -> None:
        """A .cls defines \\author and \\thanks; flagging it would be pure noise."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, ANONYMOUS_TEX)
            (project_dir / "IEEEtran.cls").write_text(
                "\\def\\author#1{}\n\\def\\thanks#1{}\n", encoding="utf-8"
            )
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertEqual(proc.returncode, 0, msg=proc.stdout)
            self.assertIn("style files not scanned", proc.stdout)
            self.assertNotIn("IEEEtran.cls:", proc.stdout)

    def test_strict_makes_warnings_blocking(self) -> None:
        tex = r"""
\documentclass{article}
\begin{document}
In our previous work \cite{x} we showed this.
\end{document}
"""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, tex)
            lenient = self._run(["--project-dir", str(project_dir)])
            strict = self._run(["--project-dir", str(project_dir), "--strict"])
            self.assertEqual(lenient.returncode, 0, msg=lenient.stdout)
            self.assertNotEqual(strict.returncode, 0, msg=strict.stdout)

    def test_pdf_author_metadata_is_a_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, ANONYMOUS_TEX)
            (project_dir / "main.pdf").write_bytes(
                b"%PDF-1.5\n<< /Author (Jane Q. Researcher) /Producer (pdfTeX) >>\n%%EOF\n"
            )
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertIn("PDF author metadata", proc.stdout)
            self.assertNotEqual(proc.returncode, 0)

    def test_no_pdf_flag_skips_metadata_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, ANONYMOUS_TEX)
            (project_dir / "main.pdf").write_bytes(
                b"%PDF-1.5\n<< /Author (Jane Q. Researcher) >>\n%%EOF\n"
            )
            proc = self._run(["--project-dir", str(project_dir), "--no-pdf"])
            self.assertNotIn("PDF author metadata", proc.stdout)
            self.assertEqual(proc.returncode, 0)

    def test_empty_pdf_author_is_not_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self._project(tmp, ANONYMOUS_TEX)
            (project_dir / "main.pdf").write_bytes(b"%PDF-1.5\n<< /Author () /Producer (pdfTeX) >>\n%%EOF\n")
            proc = self._run(["--project-dir", str(project_dir)])
            self.assertNotIn("PDF author metadata", proc.stdout)
            self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
