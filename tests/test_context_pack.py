import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestPaperContextPack(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_dir = Path(__file__).resolve().parents[1]
        self.scripts_dir = self.skill_dir / "scripts"

    def _run(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    def test_context_pack_creates_notes_and_does_not_include_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "demo-paper"
            (project_dir / "issues").mkdir(parents=True, exist_ok=True)

            (project_dir / "main.tex").write_text(
                "\n".join(
                    [
                        r"\documentclass{article}",
                        r"\begin{document}",
                        r"\section{Introduction}",
                        r"Text \cite{foo}.",
                        r"\subsection{Motivation}",
                        r"\end{document}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (project_dir / "ref.bib").write_text(
                "\n".join(
                    [
                        "@article{foo,",
                        "  title={Demo},",
                        "  author={A},",
                        "  year={2024},",
                        "}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (project_dir / "issues" / "2026-03-10_00-00-00-demo.csv").write_text(
                "\n".join(
                    [
                        "ID,Phase,Title,Description,Target_Citations,Visualization,Acceptance,Status,Verified_Citations,Notes",
                        "W1,Writing,Intro,Write intro,1,N/A,Has citation,DONE,1,",
                        "PR1,Review,Review r1,Review,0,N/A,No blockers,TODO,0,",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            proc = self._run(
                [sys.executable, str(self.scripts_dir / "paper_context_pack.py"), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            out_path = project_dir / "notes" / "review-context.md"
            self.assertTrue(out_path.exists(), msg="notes/review-context.md should be created")

            text = out_path.read_text(encoding="utf-8")
            self.assertIn("Review Context Pack", text)
            self.assertIn("Introduction", text)
            self.assertIn("Issues CSV:", text)

            # Do not include absolute paths
            self.assertNotIn(str(project_dir), text)


if __name__ == "__main__":
    unittest.main()

