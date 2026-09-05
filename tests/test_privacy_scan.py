import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestPaperPrivacyScan(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_dir = Path(__file__).resolve().parents[1]
        self.scripts_dir = self.skill_dir / "scripts"

    def _run(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    def _write_min_paper(self, project_dir: Path, *, main_tex: str) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "main.tex").write_text(main_tex.rstrip() + "\n", encoding="utf-8")

    def test_privacy_scan_passes_on_public_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._write_min_paper(
                project_dir,
                main_tex=r"""
\documentclass{article}
\begin{document}
Public link: https://arxiv.org/abs/1706.03762
\end{document}
""",
            )

            proc = self._run(
                [sys.executable, str(self.scripts_dir / "paper_privacy_scan.py"), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
            self.assertNotIn("privacy scan failed", proc.stderr)

    def test_privacy_scan_fails_on_internal_url_without_leaking_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            internal_url = "https://example.internal.local/path?a=b"
            self._write_min_paper(
                project_dir,
                main_tex=f"""
\\documentclass{{article}}
\\begin{{document}}
Internal link: {internal_url}
\\end{{document}}
""",
            )

            proc = self._run(
                [sys.executable, str(self.scripts_dir / "paper_privacy_scan.py"), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 1, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
            self.assertNotIn(internal_url, proc.stderr, msg="scanner should not print the matched internal URL")

    def test_privacy_scan_fails_on_absolute_paths_and_secret_assignments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            abs_path = "/home/user/secret.txt" # portability: ignore -- POSIX path fixture for the privacy scanner
            secret_line = "OPENAI_API_KEY=sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            self._write_min_paper(
                project_dir,
                main_tex=f"""
\\documentclass{{article}}
\\begin{{document}}
Abs path: {abs_path}
Secret: {secret_line}
\\end{{document}}
""",
            )

            proc = self._run(
                [sys.executable, str(self.scripts_dir / "paper_privacy_scan.py"), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 1, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
            self.assertNotIn(abs_path, proc.stderr, msg="scanner should not print the matched absolute path")
            self.assertNotIn("sk-aaaaaaaa", proc.stderr, msg="scanner should not print the matched secret token")


if __name__ == "__main__":
    unittest.main()

