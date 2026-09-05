import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MINIMAL_MAIN_TEX = r"""
\documentclass{article}
\begin{document}
\begin{abstract}
Test abstract.
\end{abstract}
\section{Introduction}
Some text \cite{smith2024}.
\section{Method}
More text.
\begin{figure}
\caption{A figure}
\end{figure}
\section{Conclusion}
Final text.
\bibliography{ref}
\end{document}
"""

MINIMAL_BIB = r"""
@article{smith2024,
  title={A Great Paper},
  author={Smith, John},
  year={2024},
  journal={Journal of Testing},
}
"""


class TestPaperSelfReview(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_dir = Path(__file__).resolve().parents[1]
        self.scripts_dir = self.skill_dir / "scripts"
        self.script = self.scripts_dir / "paper_self_review.py"

    def _run(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    def _setup_paper(self, project_dir: Path, *, main_tex: str, bib: str | None = None) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "main.tex").write_text(main_tex.rstrip() + "\n", encoding="utf-8")
        if bib is not None:
            (project_dir / "ref.bib").write_text(bib.rstrip() + "\n", encoding="utf-8")

    # ── Basic paper ────────────────────────────────────────────────

    def test_review_basic_paper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX, bib=MINIMAL_BIB)

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            review_path = project_dir / "notes" / "self-review.md"
            self.assertTrue(review_path.exists(), msg="notes/self-review.md should be created")

    # ── Section count ──────────────────────────────────────────────

    def test_review_counts_sections(self) -> None:
        tex = r"""
\documentclass{article}
\begin{document}
\section{Introduction}
Intro.
\section{Background}
Background.
\section{Method}
Method.
\section{Results}
Results.
\section{Conclusion}
Conclusion.
\end{document}
"""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=tex)

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            review = (project_dir / "notes" / "self-review.md").read_text(encoding="utf-8")
            self.assertIn("5", review, msg="Report should show 5 sections")

    # ── Citation count ─────────────────────────────────────────────

    def test_review_counts_citations(self) -> None:
        tex = r"""
\documentclass{article}
\begin{document}
\section{Introduction}
See \cite{a2024} and \cite{b2024,c2024}.
\end{document}
"""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=tex)

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            review = (project_dir / "notes" / "self-review.md").read_text(encoding="utf-8")
            # 3 total citation keys (a2024, b2024, c2024)
            self.assertIn("3", review, msg="Report should show 3 citation keys")

    # ── Figure count ───────────────────────────────────────────────

    def test_review_counts_figures(self) -> None:
        tex = r"""
\documentclass{article}
\begin{document}
\section{Results}
\begin{figure}
\caption{Fig 1}
\end{figure}
\begin{figure}
\caption{Fig 2}
\end{figure}
\end{document}
"""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=tex)

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            review = (project_dir / "notes" / "self-review.md").read_text(encoding="utf-8")
            self.assertIn("2", review, msg="Report should show 2 figures")

    # ── Missing limitations ────────────────────────────────────────

    def test_review_detects_missing_limitations(self) -> None:
        tex = r"""
\documentclass{article}
\begin{document}
\section{Introduction}
Text.
\section{Method}
More text.
\section{Conclusion}
Final.
\end{document}
"""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=tex)

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            # Script may still succeed but should flag the missing section
            review = (project_dir / "notes" / "self-review.md").read_text(encoding="utf-8")
            has_flag = (
                "limitation" in review.lower()
                or "missing" in review.lower()
            )
            self.assertTrue(has_flag, msg="Report should flag missing limitations section")

    # ── Missing main.tex ──────────────────────────────────────────

    def test_review_missing_main_tex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            project_dir.mkdir(parents=True, exist_ok=True)
            # No main.tex

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertNotIn("Traceback", proc.stderr, msg="Script should handle missing main.tex gracefully")

    # ── BibTeX entries with missing fields ─────────────────────────

    def test_review_checks_bib_entries(self) -> None:
        bib = r"""
@article{complete2024,
  title={Complete Entry},
  author={Author, A},
  year={2024},
  journal={Good Journal},
}

@article{noyear,
  title={Missing Year},
  author={Author, B},
  journal={Some Journal},
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX, bib=bib)

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            review_path = project_dir / "notes" / "self-review.md"
            self.assertTrue(review_path.exists(), msg="Review report should be created")

            review = review_path.read_text(encoding="utf-8")
            has_bib_issue = (
                "noyear" in review.lower()
                or "missing" in review.lower()
                or "year" in review.lower()
            )
            self.assertTrue(has_bib_issue, msg="Report should identify bib entries with missing fields")


if __name__ == "__main__":
    unittest.main()
