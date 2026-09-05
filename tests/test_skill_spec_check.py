"""Tests for scripts/skill_spec_check.py — Agent Skills spec conformance."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import skill_spec_check as ssc  # noqa: E402


def write_skill(tmp_path, frontmatter, body="# Body\n"):
    path = tmp_path / "SKILL.md"
    path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")
    return path


def rules(issues):
    return [issue.rule for issue in issues]


class TestFrontmatterParsing:
    def test_scalars_lists_and_folded_blocks(self):
        parsed = ssc.parse_frontmatter(
            "name: demo\n"
            "description: >\n  first line\n  second line\n"
            "allowed-tools:\n  - Read\n  - Grep\n"
            "metadata:\n  homepage: https://example.com\n"
        )
        assert parsed["name"] == "demo"
        assert parsed["description"] == "first line second line"
        assert parsed["allowed-tools"] == ["Read", "Grep"]
        assert parsed["metadata"] == {"homepage": "https://example.com"}

    def test_frontmatter_must_start_on_line_one(self, tmp_path):
        path = tmp_path / "SKILL.md"
        path.write_text("\n---\nname: demo\n---\n", encoding="utf-8")
        assert rules(ssc.check_skill(path)) == ["SPEC007"]


class TestSpecFields:
    def test_a_claude_code_only_field_is_rejected(self, tmp_path):
        path = write_skill(tmp_path, "name: demo\ndescription: d\ndisable-model-invocation: true\n")
        assert "SPEC001" in rules(ssc.check_skill(path))

    def test_all_six_spec_fields_are_accepted(self, tmp_path):
        path = write_skill(
            tmp_path,
            "name: demo\ndescription: d\nlicense: MIT\ncompatibility: Python 3.10+\n"
            "allowed-tools: Read Grep\nmetadata:\n  key: value\n",
        )
        assert ssc.check_skill(path) == []

    def test_missing_name_is_reported(self, tmp_path):
        path = write_skill(tmp_path, "description: d\n")
        assert "SPEC002" in rules(ssc.check_skill(path))

    def test_uppercase_name_is_rejected(self, tmp_path):
        path = write_skill(tmp_path, "name: MySkill\ndescription: d\n")
        assert "SPEC003" in rules(ssc.check_skill(path))

    def test_missing_description_is_reported(self, tmp_path):
        path = write_skill(tmp_path, "name: demo\n")
        assert "SPEC004" in rules(ssc.check_skill(path))

    def test_over_long_description_is_reported(self, tmp_path):
        path = write_skill(tmp_path, f"name: demo\ndescription: {'x' * 1100}\n")
        assert "SPEC004" in rules(ssc.check_skill(path))

    def test_over_long_compatibility_is_reported(self, tmp_path):
        path = write_skill(tmp_path, f"name: demo\ndescription: d\ncompatibility: {'x' * 600}\n")
        assert "SPEC005" in rules(ssc.check_skill(path))

    def test_metadata_must_be_a_mapping(self, tmp_path):
        path = write_skill(tmp_path, "name: demo\ndescription: d\nmetadata:\n  - one\n")
        assert "SPEC006" in rules(ssc.check_skill(path))


class TestStructure:
    def test_a_broken_local_link_is_reported(self, tmp_path):
        path = write_skill(tmp_path, "name: demo\ndescription: d\n", "See [it](references/missing.md).\n")
        assert "STRUCT02" in rules(ssc.check_skill(path))

    def test_an_existing_local_link_is_clean(self, tmp_path):
        (tmp_path / "references").mkdir()
        (tmp_path / "references" / "there.md").write_text("x", encoding="utf-8")
        path = write_skill(tmp_path, "name: demo\ndescription: d\n", "See [it](references/there.md).\n")
        assert ssc.check_skill(path) == []

    def test_external_links_are_ignored(self, tmp_path):
        path = write_skill(tmp_path, "name: demo\ndescription: d\n", "See [it](https://example.com/x).\n")
        assert ssc.check_skill(path) == []

    def test_an_over_long_body_is_a_warning_not_an_error(self, tmp_path):
        path = write_skill(tmp_path, "name: demo\ndescription: d\n", "line\n" * 600)
        issues = ssc.check_skill(path)
        assert rules(issues) == ["STRUCT01"]
        assert issues[0].severity == "warning"


class TestThisRepository:
    def test_the_skill_conforms(self):
        assert ssc.check_skill(ROOT / "SKILL.md") == []

    def test_the_cli_passes_in_strict_mode(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "skill_spec_check.py"), "--strict"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0, result.stdout


class TestCli:
    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "skill_spec_check.py"), "--help"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0

    def test_missing_file_exits_two(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "skill_spec_check.py"), "--skill", str(tmp_path / "nope.md")],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 2
