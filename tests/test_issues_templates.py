import subprocess
import sys
import unittest
from pathlib import Path


class TestIssuesTemplates(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_dir = Path(__file__).resolve().parents[1]
        self.scripts_dir = self.skill_dir / "scripts"
        self.assets_dir = self.skill_dir / "assets"

    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=str(self.skill_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )

    def test_review_issues_template_is_valid_csv(self) -> None:
        proc = self._run(
            [
                sys.executable,
                str(self.scripts_dir / "validate_paper_issues.py"),
                str(self.assets_dir / "paper-issues-template.csv"),
            ]
        )
        self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

    def test_codebase_issues_template_is_valid_csv(self) -> None:
        proc = self._run(
            [
                sys.executable,
                str(self.scripts_dir / "validate_paper_issues.py"),
                str(self.assets_dir / "paper-issues-codebase-template.csv"),
            ]
        )
        self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")


if __name__ == "__main__":
    unittest.main()
