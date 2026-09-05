"""Tests for scripts/venue_rules_sync.py — venue config against the published guide."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import venue_rules_sync as vrs  # noqa: E402

GUIDE_MATCHING_NEURIPS = """
<html><head><style>.x{color:red}</style></head><body>
<h1>NeurIPS 2025 Style Files</h1>
<p>Submissions are limited to 9 pages of main text, excluding references.</p>
<p>Use 10pt type on letter paper. The style file is neurips_2025.sty.</p>
<p>Reviewing is double-blind.</p>
</body></html>
"""

GUIDE_WITH_NEW_RULES = """
<html><body>
<h1>NeurIPS 2027 Style Files</h1>
<p>Submissions are limited to 10 pages of main text.</p>
<p>Use 11pt type on a4 paper. The style file is neurips_2027.sty.</p>
<p>Reviewing is single-blind this year.</p>
</body></html>
"""


def run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "venue_rules_sync.py")] + args,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
    )


class TestExtraction:
    def test_page_limit_font_style_and_review_model(self):
        rules = vrs.extract_rules(vrs.html_to_text(GUIDE_MATCHING_NEURIPS))
        assert rules["page_limit_main"] == 9
        assert rules["font_size"] == "10pt"
        assert rules["style_file"] == "neurips_2025.sty"
        assert rules["paper_size"] == "letter"
        assert rules["review_model"] == "double-blind"
        assert rules["anonymous"] is True

    def test_scripts_and_tags_are_stripped(self):
        text = vrs.html_to_text(GUIDE_MATCHING_NEURIPS)
        assert "color:red" not in text
        assert "<p>" not in text

    def test_single_blind_flips_anonymity(self):
        rules = vrs.extract_rules(vrs.html_to_text(GUIDE_WITH_NEW_RULES))
        assert rules["review_model"] == "single-blind"
        assert rules["anonymous"] is False

    def test_a_page_that_states_nothing_yields_no_rules(self):
        rules = vrs.extract_rules("Welcome to the conference website.")
        assert [k for k in rules if k != "_evidence"] == []


class TestDiff:
    def test_matching_config_produces_no_differences(self):
        stored = {
            "page_limit_main": 9,
            "font_size": "10pt",
            "paper_size": "letter",
            "style_file": "neurips_2025.sty",
            "review_model": "double-blind",
            "anonymous": True,
            "reference_year": 2025,
        }
        observed = vrs.extract_rules(vrs.html_to_text(GUIDE_MATCHING_NEURIPS))
        assert vrs.diff_rules(stored, observed) == []

    def test_changed_rules_are_reported(self):
        stored = {
            "page_limit_main": 9,
            "font_size": "10pt",
            "style_file": "neurips_2025.sty",
            "review_model": "double-blind",
        }
        observed = vrs.extract_rules(vrs.html_to_text(GUIDE_WITH_NEW_RULES))
        fields = {d.field for d in vrs.diff_rules(stored, observed)}
        assert {"page_limit_main", "font_size", "style_file", "review_model"} <= fields

    def test_a_field_the_page_omits_is_not_a_difference(self):
        stored = {"page_limit_main": 9, "text_area": "5.5in x 9in"}
        observed = vrs.extract_rules("Papers are limited to 9 pages.")
        assert vrs.diff_rules(stored, observed) == []


class TestProposal:
    def test_proposal_keeps_comments_and_edits_only_the_field(self):
        stored_text = "# a comment\nvenue: neurips\npage_limit_main: 9\ncolumns: single\n"
        differences = [vrs.Difference("page_limit_main", 9, 10, "evidence")]
        proposed = vrs.render_proposal(stored_text, differences)
        assert "# a comment" in proposed
        assert "page_limit_main: 10" in proposed
        assert "columns: single" in proposed


class TestCli:
    def test_matching_guide_exits_zero(self, tmp_path):
        guide = tmp_path / "guide.html"
        guide.write_text(GUIDE_MATCHING_NEURIPS, encoding="utf-8")
        result = run(
            ["--venue", "neurips", "--from-file", str(guide), "--out-dir", str(tmp_path)]
        )
        assert result.returncode == 0
        assert (tmp_path / "venue-rule-check-neurips.md").is_file()

    def test_changed_guide_exits_one_and_writes_a_proposal(self, tmp_path):
        guide = tmp_path / "guide.html"
        guide.write_text(GUIDE_WITH_NEW_RULES, encoding="utf-8")
        result = run(
            [
                "--venue",
                "neurips",
                "--from-file",
                str(guide),
                "--out-dir",
                str(tmp_path),
                "--write-proposal",
            ]
        )
        assert result.returncode == 1
        assert "[DIFF] page_limit_main" in result.stdout
        proposal = (tmp_path / "neurips.proposed.yaml").read_text(encoding="utf-8")
        assert "page_limit_main: 10" in proposal

    def test_the_shipped_config_is_never_edited(self, tmp_path):
        config = ROOT / "assets" / "venues" / "neurips.yaml"
        before = config.read_text(encoding="utf-8")
        guide = tmp_path / "guide.html"
        guide.write_text(GUIDE_WITH_NEW_RULES, encoding="utf-8")
        run(
            [
                "--venue",
                "neurips",
                "--from-file",
                str(guide),
                "--out-dir",
                str(tmp_path),
                "--write-proposal",
            ]
        )
        assert config.read_text(encoding="utf-8") == before

    def test_unknown_venue_is_a_usage_error(self, tmp_path):
        result = run(["--venue", "notaconference", "--out-dir", str(tmp_path)])
        assert result.returncode == 2
