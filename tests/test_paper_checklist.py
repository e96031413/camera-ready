import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MINIMAL_MAIN_TEX = r"""
\documentclass{article}
\begin{document}
\section{Introduction}
We use a GPU (A100) for training.
\section{Experimental Setup}
Hyperparameters: lr=0.001.
\section{Results}
We report mean +/- stderr over 5 seeds.
\section{Limitations}
This work has limitations.
Code: https://github.com/example/repo
\end{document}
"""


class TestPaperChecklist(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_dir = Path(__file__).resolve().parents[1]
        self.scripts_dir = self.skill_dir / "scripts"
        self.script = self.scripts_dir / "paper_checklist.py"

    def _run(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")

    def _setup_paper(self, project_dir: Path, *, main_tex: str) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "main.tex").write_text(main_tex.rstrip() + "\n", encoding="utf-8")

    # ── --help ────────────────────────────────────────────────────

    def test_help_exits_zero(self) -> None:
        proc = self._run([sys.executable, str(self.script), "--help"], cwd=self.skill_dir)
        self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

    # ── Worksheet generation ─────────────────────────────────────

    def test_generate_writes_worksheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            worksheet_path = project_dir / "notes" / "paper-checklist.md"
            self.assertTrue(worksheet_path.exists(), msg="notes/paper-checklist.md should be created")

            content = worksheet_path.read_text(encoding="utf-8")
            self.assertIn("## 1. Claims", content)
            self.assertIn("## 16. Declaration of LLM Usage", content)

    def test_generate_never_fills_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

            self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )

            content = (project_dir / "notes" / "paper-checklist.md").read_text(encoding="utf-8")
            self.assertNotIn("**Answer:** Yes", content)
            self.assertNotIn("**Answer:** No", content)
            self.assertEqual(content.count("**Answer:** [TODO"), 16)
            self.assertEqual(content.count("**Justification:** [TODO"), 16)

    def test_detects_limitations_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

            self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )

            content = (project_dir / "notes" / "paper-checklist.md").read_text(encoding="utf-8")
            self.assertIn("**Detected signal:** Limitations section found", content)
            self.assertIn("**Detected signal:** Code/data hosting URL found", content)

    def test_no_false_signal_without_evidence(self) -> None:
        bare_tex = "\\documentclass{article}\n\\begin{document}\nHello.\n\\end{document}\n"
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=bare_tex)

            self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )

            content = (project_dir / "notes" / "paper-checklist.md").read_text(encoding="utf-8")
            self.assertNotIn("**Detected signal:**", content)

    # ── --emit-tex ───────────────────────────────────────────────

    def test_emit_tex_writes_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir), "--emit-tex"],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            tex_path = project_dir / "checklist.tex"
            self.assertTrue(tex_path.exists(), msg="checklist.tex should be created")
            content = tex_path.read_text(encoding="utf-8")
            self.assertIn("NeurIPS Paper Checklist", content)
            self.assertIn("SCAFFOLD", content, msg="emitted .tex must warn it is not submission-ready")
            body_lines = [ln for ln in content.splitlines() if not ln.strip().startswith("%")]
            body_text = "\n".join(body_lines)
            self.assertNotIn("\\answerYes{}", body_text, msg="body text must not invoke live answer macros")
            self.assertNotIn("\\answerNo{}", body_text, msg="body text must not invoke live answer macros")
            self.assertNotIn("\\answerNA{}", body_text, msg="body text must not invoke live answer macros")

    def test_emit_tex_compiles_under_plain_article(self) -> None:
        pdflatex = shutil.which("pdflatex")
        if not pdflatex:
            self.skipTest("pdflatex not available")

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

            self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir), "--emit-tex"],
                cwd=self.skill_dir,
            )

            (project_dir / "wrap.tex").write_text(
                "\\documentclass{article}\n\\begin{document}\n\\input{checklist}\n\\end{document}\n",
                encoding="utf-8",
            )
            proc = subprocess.run(
                [pdflatex, "-interaction=nonstopmode", "wrap.tex"],
                cwd=str(project_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(proc.returncode, 0, msg=f"pdflatex failed:\n{proc.stdout[-3000:]}")
            self.assertTrue((project_dir / "wrap.pdf").exists())

    # ── --validate ───────────────────────────────────────────────

    def test_validate_fails_when_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

            self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir), "--validate"],
                cwd=self.skill_dir,
            )
            self.assertNotEqual(proc.returncode, 0, msg="Validation should fail on an unfilled worksheet")
            self.assertIn("FAILED", proc.stdout)

    def test_validate_rejects_non_allowlisted_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

            self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            worksheet_path = project_dir / "notes" / "paper-checklist.md"
            content = worksheet_path.read_text(encoding="utf-8")
            # Adversarial: neither "[TODO" nor starting with yes/no -- must still be rejected.
            content = content.replace("**Answer:** [TODO: Yes/No/NA]", "**Answer:** TBD")
            worksheet_path.write_text(content, encoding="utf-8")

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir), "--validate"],
                cwd=self.skill_dir,
            )
            self.assertNotEqual(proc.returncode, 0, msg="'TBD' must not be accepted as a valid answer")
            self.assertIn("Yes/No/NA", proc.stdout)

    def test_validate_fails_on_missing_justification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

            self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            worksheet_path = project_dir / "notes" / "paper-checklist.md"
            content = worksheet_path.read_text(encoding="utf-8")
            # Answer everything Yes but leave justifications blank.
            content = content.replace("**Answer:** [TODO: Yes/No/NA]", "**Answer:** Yes")
            worksheet_path.write_text(content, encoding="utf-8")

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir), "--validate"],
                cwd=self.skill_dir,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("justification is missing", proc.stdout)

    def test_validate_passes_when_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

            self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir)],
                cwd=self.skill_dir,
            )
            worksheet_path = project_dir / "notes" / "paper-checklist.md"
            content = worksheet_path.read_text(encoding="utf-8")
            content = content.replace("**Answer:** [TODO: Yes/No/NA]", "**Answer:** NA")
            content = content.replace("**Justification:** [TODO]", "**Justification:** n/a")
            worksheet_path.write_text(content, encoding="utf-8")

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir), "--validate"],
                cwd=self.skill_dir,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

    def test_validate_missing_worksheet_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            project_dir.mkdir(parents=True, exist_ok=True)

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir), "--validate"],
                cwd=self.skill_dir,
            )
            self.assertNotEqual(proc.returncode, 0)

    # ── Multi-venue coverage ─────────────────────────────────────

    ALL_VENUES = ("neurips", "icml", "iclr", "acl", "aaai", "cvpr")

    def test_every_venue_checklist_parses_and_generates(self) -> None:
        for venue in self.ALL_VENUES:
            with self.subTest(venue=venue), tempfile.TemporaryDirectory() as tmp:
                project_dir = Path(tmp) / "paper"
                self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

                proc = self._run(
                    [sys.executable, str(self.script), "--project-dir", str(project_dir), "--venue", venue],
                    cwd=self.skill_dir,
                )
                self.assertEqual(proc.returncode, 0, msg=f"{venue}: {proc.stdout} {proc.stderr}")

                content = (project_dir / "notes" / "paper-checklist.md").read_text(encoding="utf-8")
                self.assertIn("## 1. ", content, msg=f"{venue} worksheet has no parsed items")
                self.assertIn("**Question:**", content)
                self.assertIn("**Answer:** [TODO", content)

    def test_every_venue_worksheet_leaves_answers_blank(self) -> None:
        for venue in self.ALL_VENUES:
            with self.subTest(venue=venue), tempfile.TemporaryDirectory() as tmp:
                project_dir = Path(tmp) / "paper"
                self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)
                self._run(
                    [sys.executable, str(self.script), "--project-dir", str(project_dir), "--venue", venue],
                    cwd=self.skill_dir,
                )
                content = (project_dir / "notes" / "paper-checklist.md").read_text(encoding="utf-8")
                self.assertNotIn("**Answer:** Yes", content)
                self.assertNotIn("**Answer:** No", content)
                self.assertEqual(
                    content.count("**Answer:** [TODO"),
                    content.count("**Justification:** [TODO"),
                )

    def test_venue_display_names_are_used(self) -> None:
        expected = {
            "icml": "ICML Paper Checklist Worksheet",
            "iclr": "ICLR Paper Checklist Worksheet",
            "acl": "ACL Paper Checklist Worksheet",
            "aaai": "AAAI Paper Checklist Worksheet",
            "cvpr": "CVPR Paper Checklist Worksheet",
        }
        for venue, heading in expected.items():
            with self.subTest(venue=venue), tempfile.TemporaryDirectory() as tmp:
                project_dir = Path(tmp) / "paper"
                self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)
                self._run(
                    [sys.executable, str(self.script), "--project-dir", str(project_dir), "--venue", venue],
                    cwd=self.skill_dir,
                )
                content = (project_dir / "notes" / "paper-checklist.md").read_text(encoding="utf-8")
                self.assertIn(heading, content)

    def test_signals_attach_by_topic_not_by_item_number(self) -> None:
        """The Limitations hint must land on each venue's own Limitations item."""
        for venue in ("neurips", "icml", "iclr", "acl"):
            with self.subTest(venue=venue), tempfile.TemporaryDirectory() as tmp:
                project_dir = Path(tmp) / "paper"
                self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)
                self._run(
                    [sys.executable, str(self.script), "--project-dir", str(project_dir), "--venue", venue],
                    cwd=self.skill_dir,
                )
                content = (project_dir / "notes" / "paper-checklist.md").read_text(encoding="utf-8")
                blocks = content.split("\n## ")
                limitation_blocks = [b for b in blocks if "imitation" in b.splitlines()[0]]
                self.assertTrue(limitation_blocks, msg=f"{venue} has no Limitations item")
                self.assertIn(
                    "**Detected signal:** Limitations section found",
                    limitation_blocks[0],
                    msg=f"{venue}: the Limitations hint landed on the wrong item",
                )

    def test_emit_tex_works_for_every_venue(self) -> None:
        for venue in self.ALL_VENUES:
            with self.subTest(venue=venue), tempfile.TemporaryDirectory() as tmp:
                project_dir = Path(tmp) / "paper"
                self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)
                proc = self._run(
                    [
                        sys.executable,
                        str(self.script),
                        "--project-dir",
                        str(project_dir),
                        "--venue",
                        venue,
                        "--emit-tex",
                    ],
                    cwd=self.skill_dir,
                )
                self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
                content = (project_dir / "checklist.tex").read_text(encoding="utf-8")
                self.assertIn("SCAFFOLD", content, msg=f"{venue}: must warn it is not submission-ready")

    def test_checklist_assets_are_paraphrase_not_verbatim_latex(self) -> None:
        """Venue checklist blocks must never be committed verbatim.

        The asset files may *mention* the answer macros in prose (inside
        backticks) to tell the author what to fill in. What they must not
        contain is live LaTeX: a pasted \\begin{enumerate} block from a venue
        style file, which most venues forbid redistributing.
        """
        import re

        for path in sorted((self.skill_dir / "assets" / "checklists").glob("*.md")):
            content = path.read_text(encoding="utf-8")
            with self.subTest(checklist=path.name):
                self.assertNotIn("\\begin{enumerate}", content)
                self.assertNotIn("\\item[]", content)
                self.assertIn("paraphras", content.lower())
                # Every mention of an answer macro must be inside inline code.
                for match in re.finditer(r"\\answer(Yes|No|NA)", content):
                    line = content[: match.start()].rsplit("\n", 1)[-1]
                    self.assertEqual(
                        line.count("`") % 2,
                        1,
                        msg=f"{path.name}: {match.group(0)} appears as live LaTeX, not as prose",
                    )

    def test_list_venues(self) -> None:
        proc = self._run([sys.executable, str(self.script), "--list-venues"], cwd=self.skill_dir)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        for venue in self.ALL_VENUES:
            self.assertIn(venue, proc.stdout)

    def test_project_dir_required_without_list_venues(self) -> None:
        proc = self._run([sys.executable, str(self.script)], cwd=self.skill_dir)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--project-dir", proc.stderr)

    # ── Unknown venue ────────────────────────────────────────────

    def test_unknown_venue_errors_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "paper"
            self._setup_paper(project_dir, main_tex=MINIMAL_MAIN_TEX)

            proc = self._run(
                [sys.executable, str(self.script), "--project-dir", str(project_dir), "--venue", "nonexistent"],
                cwd=self.skill_dir,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("no checklist asset", proc.stderr)


if __name__ == "__main__":
    unittest.main()
