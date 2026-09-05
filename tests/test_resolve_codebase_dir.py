import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestResolveCodebaseDir(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_dir = Path(__file__).resolve().parents[1]
        self.scripts_dir = self.skill_dir / "scripts"

    def _run(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    def test_resolve_by_name_with_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir(parents=True, exist_ok=True)
            (root / "src" / "ai_shorts_agent").mkdir(parents=True, exist_ok=True)

            proc = self._run(
                [
                    sys.executable,
                    str(self.scripts_dir / "resolve_codebase_dir.py"),
                    "--codebase",
                    "ai_shorts_agent",
                    "--roots",
                    str(root),
                ],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
            resolved = proc.stdout.strip()
            self.assertTrue(resolved.endswith(str(Path("src") / "ai_shorts_agent")))

    def test_resolve_errors_on_multiple_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir(parents=True, exist_ok=True)
            (root / "ai_shorts_agent").mkdir(parents=True, exist_ok=True)
            (root / "src" / "ai_shorts_agent").mkdir(parents=True, exist_ok=True)

            proc = self._run(
                [
                    sys.executable,
                    str(self.scripts_dir / "resolve_codebase_dir.py"),
                    "--codebase",
                    "ai_shorts_agent",
                    "--roots",
                    str(root),
                ],
                cwd=self.skill_dir,
            )
            self.assertNotEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
            self.assertIn("multiple matches", proc.stderr)


if __name__ == "__main__":
    unittest.main()

