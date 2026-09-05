import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestAntiAiScan(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_dir = Path(__file__).resolve().parents[1]
        self.scripts_dir = self.skill_dir / "scripts"
        self.script = self.scripts_dir / "anti_ai_scan.py"

    def _run(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    def _write_main_tex(self, project_dir: Path, content: str) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "main.tex").write_text(content.rstrip() + "\n", encoding="utf-8")

    # ── Clean text ─────────────────────────────────────────────────

    def test_scan_clean_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._write_main_tex(
                project_dir,
                r"""
\documentclass{article}
\begin{document}
\begin{abstract}
We present a method for graph partitioning that achieves state-of-the-art
results on benchmark datasets.
\end{abstract}
\section{Introduction}
Prior work has shown that spectral methods are effective for this problem.
\section{Method}
Our approach uses a novel formulation based on semidefinite programming.
\section{Conclusion}
We demonstrated competitive performance on all benchmarks.
\end{document}
""",
            )

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

    # ── Detects AI patterns ────────────────────────────────────────

    def test_scan_detects_ai_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._write_main_tex(
                project_dir,
                r"""
\documentclass{article}
\begin{document}
\section{Introduction}
Additionally, this delve into the crucial landscape of leveraging
transformative approaches. It is important to note that this
represents a paradigm shift in the realm of cutting-edge methodologies.
Furthermore, it is worth noting that the aforementioned framework
showcases the intricate interplay between various components.
\end{document}
""",
            )

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertNotEqual(proc.returncode, 0, msg="Script should return non-zero for AI-patterned text")

            report_path = project_dir / "notes" / "anti-ai-report.md"
            self.assertTrue(report_path.exists(), msg="anti-ai-report.md should be generated")

    # ── Generates report ───────────────────────────────────────────

    def test_scan_generates_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._write_main_tex(
                project_dir,
                r"""
\documentclass{article}
\begin{document}
\section{Introduction}
It is important to note that delving into the crucial landscape is essential.
\end{document}
""",
            )

            self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )

            report_path = project_dir / "notes" / "anti-ai-report.md"
            self.assertTrue(report_path.exists(), msg="anti-ai-report.md should be created")

            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Summary", report, msg="Report should contain a Summary section")
            self.assertIn("Finding", report, msg="Report should contain a Findings section")

    # ── Ignores LaTeX comments ─────────────────────────────────────

    def test_scan_ignores_latex_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._write_main_tex(
                project_dir,
                r"""
\documentclass{article}
\begin{document}
\section{Introduction}
% Additionally, this delve into the crucial landscape of leveraging
% transformative approaches in the realm of cutting-edge methodologies.
% Furthermore, it is worth noting that the aforementioned framework
We use standard graph methods to solve the problem efficiently.
\end{document}
""",
            )

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(
                proc.returncode,
                0,
                msg=f"AI patterns in comments should be ignored.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
            )

    # ── Missing main.tex ──────────────────────────────────────────

    def test_scan_missing_main_tex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            project_dir.mkdir(parents=True, exist_ok=True)
            # No main.tex created

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            # Should not crash (exit code may be non-zero but should not be a Python traceback)
            self.assertNotIn("Traceback", proc.stderr, msg="Script should handle missing main.tex gracefully")


if __name__ == "__main__":
    unittest.main()
