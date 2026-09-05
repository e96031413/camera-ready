"""Tests for poster workflow scripts and integration."""

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestPosterWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_dir = Path(__file__).resolve().parents[1]
        self.scripts_dir = self.skill_dir / "scripts"
        self.assets_dir = self.skill_dir / "assets"
        self.template_path = self.assets_dir / "template" / "poster" / "template.html"

    def _run(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=str(self.skill_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            **kwargs,
        )

    # --- Template Tests ---

    def test_template_exists(self) -> None:
        self.assertTrue(self.template_path.exists(), "poster template.html should exist")

    def test_template_has_customize_markers(self) -> None:
        html = self.template_path.read_text(encoding="utf-8")
        self.assertIn("CUSTOMIZE", html, "template should have CUSTOMIZE markers")

    def test_template_has_fill_in_placeholders(self) -> None:
        html = self.template_path.read_text(encoding="utf-8")
        self.assertIn("FILL_IN", html, "template should have FILL_IN placeholders")

    def test_template_has_react_and_katex(self) -> None:
        html = self.template_path.read_text(encoding="utf-8")
        self.assertIn("react@18", html, "template should include React 18")
        self.assertIn("katex@0.16.9", html, "template should include KaTeX")
        self.assertIn("babel", html, "template should include Babel")

    def test_template_has_poster_api(self) -> None:
        html = self.template_path.read_text(encoding="utf-8")
        self.assertIn("posterAPI", html, "template should expose posterAPI")
        self.assertIn("getWaste", html, "template should have getWaste function")

    def test_template_no_posterskill_branding(self) -> None:
        html = self.template_path.read_text(encoding="utf-8")
        self.assertNotIn("qr-posterskill", html, "template should not have posterskill QR code")
        self.assertNotIn("Poster made with my Claude skill", html, "template should not have posterskill branding")

    def test_template_has_source_attribution(self) -> None:
        html = self.template_path.read_text(encoding="utf-8")
        self.assertIn("ethanweber/posterskill", html, "template should credit original source")

    # --- poster_generate.py Tests ---

    def test_poster_generate_help(self) -> None:
        proc = self._run([sys.executable, str(self.scripts_dir / "poster_generate.py"), "--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--project-dir", proc.stdout)
        self.assertIn("--dimensions", proc.stdout)
        self.assertIn("--orientation", proc.stdout)
        self.assertIn("--columns", proc.stdout)
        self.assertIn("--standalone", proc.stdout)

    def test_poster_generate_creates_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()

            proc = self._run([
                sys.executable, str(self.scripts_dir / "poster_generate.py"),
                "--project-dir", str(project_dir),
                "--standalone",
            ])
            self.assertEqual(proc.returncode, 0, msg=f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")

            poster_dir = project_dir / "poster"
            self.assertTrue(poster_dir.exists(), "poster/ directory should be created")
            self.assertTrue((poster_dir / "index.html").exists(), "poster/index.html should be created")
            self.assertTrue((poster_dir / "logos").is_dir(), "poster/logos/ should be created")

    def test_poster_generate_patches_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()

            proc = self._run([
                sys.executable, str(self.scripts_dir / "poster_generate.py"),
                "--project-dir", str(project_dir),
                "--standalone",
                "--dimensions", "A1",
                "--orientation", "portrait",
            ])
            self.assertEqual(proc.returncode, 0, msg=f"stderr:\n{proc.stderr}")

            html = (project_dir / "poster" / "index.html").read_text(encoding="utf-8")
            self.assertIn("POSTER_W_MM = 594", html)
            self.assertIn("POSTER_H_MM = 841", html)

    # --- poster_convert_figures.py Tests ---

    def test_poster_convert_figures_help(self) -> None:
        proc = self._run([sys.executable, str(self.scripts_dir / "poster_convert_figures.py"), "--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--source-dir", proc.stdout)
        self.assertIn("--output-dir", proc.stdout)

    def test_poster_convert_figures_copies_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "figures"
            source_dir.mkdir()
            output_dir = Path(tmpdir) / "poster"
            output_dir.mkdir()

            # Create a minimal PNG (1x1 pixel)
            import struct
            import zlib
            def make_minimal_png() -> bytes:
                signature = b'\x89PNG\r\n\x1a\n'
                ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
                ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
                ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
                raw = b'\x00\x00\x00\x00'
                compressed = zlib.compress(raw)
                idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
                idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)
                iend_crc = zlib.crc32(b'IEND') & 0xffffffff
                iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
                return signature + ihdr + idat + iend

            (source_dir / "test.png").write_bytes(make_minimal_png())

            proc = self._run([
                sys.executable, str(self.scripts_dir / "poster_convert_figures.py"),
                "--source-dir", str(source_dir),
                "--output-dir", str(output_dir),
            ])
            self.assertEqual(proc.returncode, 0, msg=f"stderr:\n{proc.stderr}")
            self.assertTrue((output_dir / "test.png").exists(), "PNG should be copied to output")
            self.assertTrue((output_dir / "figure-aspects.json").exists(), "aspect ratio report should be generated")

    # --- poster_validate.py Tests ---

    def test_poster_validate_help(self) -> None:
        proc = self._run([sys.executable, str(self.scripts_dir / "poster_validate.py"), "--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--project-dir", proc.stdout)

    def test_poster_validate_reports_fill_in_on_template(self) -> None:
        """Validating the raw template should report FILL_IN placeholders."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()

            # Generate poster from template (standalone)
            self._run([
                sys.executable, str(self.scripts_dir / "poster_generate.py"),
                "--project-dir", str(project_dir),
                "--standalone",
            ])

            proc = self._run([
                sys.executable, str(self.scripts_dir / "poster_validate.py"),
                "--project-dir", str(project_dir),
            ])
            # Should fail because template has FILL_IN placeholders
            self.assertNotEqual(proc.returncode, 0, "raw template should fail validation due to FILL_IN")
            combined = proc.stdout + proc.stderr
            self.assertIn("FILL_IN", combined)

    # --- poster_thumbnail.py Tests ---

    def test_poster_thumbnail_help(self) -> None:
        proc = self._run([sys.executable, str(self.scripts_dir / "poster_thumbnail.py"), "--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--poster-pdf", proc.stdout)

    # --- Issues CSV Template Tests ---

    def test_review_issues_template_has_poster_rows(self) -> None:
        csv_path = self.assets_dir / "paper-issues-template.csv"
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        ids = [row[0] for row in rows[1:]]
        for ps_id in ["PS1", "PS2", "PS3", "PS4", "PS5", "PS6"]:
            self.assertIn(ps_id, ids, f"{ps_id} should be in review issues template")

    def test_conference_issues_template_has_poster_rows(self) -> None:
        csv_path = self.assets_dir / "paper-issues-conference-template.csv"
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        ids = [row[0] for row in rows[1:]]
        for ps_id in ["PS1", "PS2", "PS3", "PS4", "PS5", "PS6"]:
            self.assertIn(ps_id, ids, f"{ps_id} should be in conference issues template")

    def test_codebase_issues_template_has_poster_rows(self) -> None:
        csv_path = self.assets_dir / "paper-issues-codebase-template.csv"
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        ids = [row[0] for row in rows[1:]]
        for ps_id in ["PS1", "PS2", "PS3", "PS4", "PS5", "PS6"]:
            self.assertIn(ps_id, ids, f"{ps_id} should be in codebase issues template")

    def test_issues_templates_validate(self) -> None:
        """All three CSV templates should pass validation with the Poster phase."""
        for template_name in [
            "paper-issues-template.csv",
            "paper-issues-conference-template.csv",
            "paper-issues-codebase-template.csv",
        ]:
            csv_path = self.assets_dir / template_name
            proc = self._run([
                sys.executable, str(self.scripts_dir / "validate_paper_issues.py"),
                str(csv_path),
            ])
            self.assertEqual(
                proc.returncode, 0,
                msg=f"{template_name} validation failed:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
