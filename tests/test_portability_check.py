"""Tests for scripts/portability_check.py — the cross-platform lint gate."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import portability_check as pc  # noqa: E402


def write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def rules(findings) -> list[str]:
    return [f.rule for f in findings]


class TestEncodingRule:
    def test_open_without_encoding_is_flagged(self, tmp_path):
        path = write(tmp_path, "a.py", "with open('x.txt') as f:\n    pass\n")
        assert rules(pc.check_python(path)) == ["ENC001"]

    def test_open_with_encoding_is_clean(self, tmp_path):
        path = write(tmp_path, "a.py", "with open('x.txt', encoding='utf-8') as f:\n    pass\n")
        assert pc.check_python(path) == []

    def test_binary_mode_is_clean(self, tmp_path):
        path = write(tmp_path, "a.py", "with open('x.bin', 'rb') as f:\n    pass\n")
        assert pc.check_python(path) == []

    def test_write_text_without_encoding_is_flagged(self, tmp_path):
        path = write(tmp_path, "a.py", "p.write_text('hi')\n")
        assert rules(pc.check_python(path)) == ["ENC001"]

    def test_tarfile_open_is_not_a_text_open(self, tmp_path):
        path = write(tmp_path, "a.py", "import tarfile\nwith tarfile.open('x.tgz', 'w:gz') as t:\n    pass\n")
        assert pc.check_python(path) == []


class TestSubprocessRules:
    def test_capture_output_without_encoding_is_flagged(self, tmp_path):
        path = write(tmp_path, "a.py", "import subprocess\nsubprocess.run(['ls'], capture_output=True)\n")
        assert rules(pc.check_python(path)) == ["ENC002"]

    def test_explicit_encoding_is_clean(self, tmp_path):
        body = "import subprocess\nsubprocess.run(['ls'], capture_output=True, encoding='utf-8')\n"
        path = write(tmp_path, "a.py", body)
        assert pc.check_python(path) == []

    def test_shell_true_is_flagged(self, tmp_path):
        path = write(tmp_path, "a.py", "import subprocess\nsubprocess.run('ls', shell=True)\n")
        assert "PROC001" in rules(pc.check_python(path))

    def test_binary_subprocess_is_clean(self, tmp_path):
        path = write(tmp_path, "a.py", "import subprocess\nsubprocess.run(['ls'])\n")
        assert pc.check_python(path) == []


class TestPathRule:
    def test_posix_only_literal_is_flagged(self, tmp_path):
        path = write(tmp_path, "a.py", "CACHE = '/tmp/paper-cache'\n")
        assert rules(pc.check_python(path)) == ["PATH001"]

    def test_relative_path_is_clean(self, tmp_path):
        path = write(tmp_path, "a.py", "CACHE = 'notes/cache'\n")
        assert pc.check_python(path) == []


class TestSuppression:
    def test_marker_suppresses_the_line(self, tmp_path):
        path = write(tmp_path, "a.py", "CACHE = '/tmp/paper-cache'  # portability: ignore -- POSIX only\n")
        assert pc.check_python(path) == []


class TestDocRule:
    def test_python3_inside_a_fence_is_flagged(self, tmp_path):
        path = write(tmp_path, "a.md", "text\n\n```bash\npython3 scripts/x.py\n```\n")
        assert rules(pc.check_doc(path)) == ["DOC001"]

    def test_python3_outside_a_fence_is_ignored(self, tmp_path):
        path = write(tmp_path, "a.md", "Prose may say python3 freely.\n")
        assert pc.check_doc(path) == []

    def test_python_is_clean(self, tmp_path):
        path = write(tmp_path, "a.md", "```bash\npython scripts/x.py\n```\n")
        assert pc.check_doc(path) == []


class TestSyntaxError:
    def test_unparseable_file_reports_syn001(self, tmp_path):
        path = write(tmp_path, "a.py", "def broken(\n")
        assert rules(pc.check_python(path)) == ["SYN001"]


class TestRepositoryIsClean:
    """The gate must pass on this repository, or the CI step is meaningless."""

    def test_repository_passes_its_own_lint(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "portability_check.py"), "--docs"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0, result.stdout + result.stderr


class TestCli:
    def test_help_does_not_crash(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "portability_check.py"), "--help"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0
        assert "portability" in result.stdout.lower()
