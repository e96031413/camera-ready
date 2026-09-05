import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestCodebasePaperWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_dir = Path(__file__).resolve().parents[1]
        self.scripts_dir = self.skill_dir / "scripts"
        self.fixture_codebase = self.skill_dir / "assets" / "fixtures" / "mini_codebase"
        if not self.fixture_codebase.exists():
            raise RuntimeError(f"Fixture missing: {self.fixture_codebase}")

    def _run(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    def test_codebase_snapshot_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            project_dir.mkdir(parents=True, exist_ok=True)

            proc = self._run(
                [
                    sys.executable,
                    str(self.scripts_dir / "codebase_snapshot.py"),
                    "--codebase-dir",
                    str(self.fixture_codebase),
                    "--project-dir",
                    str(project_dir),
                ],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            md_path = project_dir / "notes" / "codebase-snapshot.md"
            json_path = project_dir / "notes" / "codebase-snapshot.json"
            self.assertTrue(md_path.exists(), msg="codebase-snapshot.md should be created")
            self.assertTrue(json_path.exists(), msg="codebase-snapshot.json should be created")

            md = md_path.read_text(encoding="utf-8")
            self.assertIn("- Codebase: mini_codebase", md)
            self.assertIn("Top-level areas", md)
            self.assertIn("Languages / file types", md)
            self.assertNotIn(str(self.fixture_codebase), md, msg="snapshot should not include absolute codebase paths")
            self.assertNotIn("ignored.txt", md, msg="node_modules should be ignored")

            raw_json = json_path.read_text(encoding="utf-8")
            self.assertNotIn(str(self.fixture_codebase), raw_json, msg="snapshot json should not include absolute codebase paths")

    def test_codebase_snapshot_redacts_urls_and_absolute_paths_in_readme_excerpt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codebase_dir = Path(tmp) / "codebase"
            codebase_dir.mkdir(parents=True, exist_ok=True)
            (codebase_dir / "README.md").write_text(
                "\n".join(
                    [
                        "# Demo",
                        "Internal link: https://example.internal.local/path?a=b",
                        "Absolute path: /home/user/secret.txt",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            project_dir = Path(tmp) / "paper"
            project_dir.mkdir(parents=True, exist_ok=True)

            proc = self._run(
                [
                    sys.executable,
                    str(self.scripts_dir / "codebase_snapshot.py"),
                    "--codebase-dir",
                    str(codebase_dir),
                    "--project-dir",
                    str(project_dir),
                ],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            md_path = project_dir / "notes" / "codebase-snapshot.md"
            md = md_path.read_text(encoding="utf-8")
            self.assertIn("<URL_REDACTED>", md)
            self.assertIn("<PATH_REDACTED>", md)
            self.assertNotIn("https://example.internal.local", md)
            self.assertNotIn("/home/user/secret.txt", md) # portability: ignore -- POSIX path fixture for the privacy scanner

    def test_bootstrap_codebase_kickoff_uses_codebase_template_and_writes_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)

            proc = self._run(
                [
                    sys.executable,
                    str(self.scripts_dir / "bootstrap_ieee_review_paper.py"),
                    "--stage",
                    "kickoff",
                    "--paper-type",
                    "codebase",
                    "--codebase-dir",
                    str(self.fixture_codebase),
                    "--topic",
                    "Mini codebase paper",
                    "--name",
                    "mini-codebase-paper",
                    "--out",
                    str(out_dir),
                ],
                cwd=self.scripts_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            project_dir = out_dir / "mini-codebase-paper"
            main_tex = project_dir / "main.tex"
            snapshot_md = project_dir / "notes" / "codebase-snapshot.md"
            self.assertTrue(main_tex.exists(), msg="main.tex should exist")
            self.assertTrue(snapshot_md.exists(), msg="codebase snapshot should exist in notes/")

            tex = main_tex.read_text(encoding="utf-8")
            self.assertIn(r"\section{System Overview}", tex)
            self.assertNotIn(r"\section{Background and Preliminaries}", tex)

            plan_dir = project_dir / "plan"
            self.assertTrue(plan_dir.exists(), msg="plan/ should exist")
            plan_files = sorted(plan_dir.glob("*.md"))
            self.assertTrue(plan_files, msg="plan/*.md should be created")
            plan_text = plan_files[-1].read_text(encoding="utf-8")
            self.assertIn("codebase_name: mini_codebase", plan_text)
            self.assertNotIn(str(self.fixture_codebase), plan_text, msg="plan should not include absolute codebase paths")

    def test_bootstrap_review_kickoff_uses_review_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)

            proc = self._run(
                [
                    sys.executable,
                    str(self.scripts_dir / "bootstrap_ieee_review_paper.py"),
                    "--stage",
                    "kickoff",
                    "--topic",
                    "Review test paper",
                    "--name",
                    "review-paper",
                    "--out",
                    str(out_dir),
                ],
                cwd=self.scripts_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            project_dir = out_dir / "review-paper"
            main_tex = project_dir / "main.tex"
            self.assertTrue(main_tex.exists(), msg="main.tex should exist")

            tex = main_tex.read_text(encoding="utf-8")
            self.assertIn(r"\section{Background and Preliminaries}", tex)
            self.assertNotIn(r"\section{System Overview}", tex)

            snapshot_md = project_dir / "notes" / "codebase-snapshot.md"
            self.assertFalse(snapshot_md.exists(), msg="review kickoff should not create codebase snapshot")


if __name__ == "__main__":
    unittest.main()
