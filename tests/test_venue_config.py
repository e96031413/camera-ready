import subprocess
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from venue_config import (  # noqa: E402
    REQUIRED_FIELDS,
    VALID_COLUMNS,
    VenueConfigError,
    list_venues,
    load_venue,
    parse_simple_yaml,
    validate_venue,
)

EXPECTED_VENUES = {"neurips", "icml", "iclr", "acl", "aaai", "cvpr"}


class TestYamlSubsetParser(unittest.TestCase):
    def test_parses_scalars_lists_and_comments(self) -> None:
        parsed = parse_simple_yaml(
            "\n".join(
                [
                    "# a comment",
                    "venue: neurips",
                    "page_limit_main: 9",
                    "anonymous: true",
                    "checklist_required: false",
                    "empty_list: []",
                    "required_sections:",
                    "  - Broader Impact",
                    "  - Paper Checklist",
                    "",
                ]
            )
        )
        self.assertEqual(parsed["venue"], "neurips")
        self.assertEqual(parsed["page_limit_main"], 9)
        self.assertIs(parsed["anonymous"], True)
        self.assertIs(parsed["checklist_required"], False)
        self.assertEqual(parsed["empty_list"], [])
        self.assertEqual(parsed["required_sections"], ["Broader Impact", "Paper Checklist"])

    def test_keeps_fragment_in_url(self) -> None:
        parsed = parse_simple_yaml("url: https://example.org/guide#formatting")
        self.assertEqual(parsed["url"], "https://example.org/guide#formatting")

    def test_strips_separated_inline_comment(self) -> None:
        parsed = parse_simple_yaml("columns: single # not two")
        self.assertEqual(parsed["columns"], "single")

    def test_rejects_nested_mapping(self) -> None:
        with self.assertRaises(VenueConfigError):
            parse_simple_yaml("checklist:\n  required: true\n")

    def test_rejects_flow_collection(self) -> None:
        with self.assertRaises(VenueConfigError):
            parse_simple_yaml("required_sections: [a, b]\n")

    def test_rejects_duplicate_key(self) -> None:
        with self.assertRaises(VenueConfigError):
            parse_simple_yaml("venue: a\nvenue: b\n")

    def test_rejects_list_item_before_key(self) -> None:
        with self.assertRaises(VenueConfigError):
            parse_simple_yaml("  - orphan\n")


class TestVenueFiles(unittest.TestCase):
    def test_all_expected_venues_exist(self) -> None:
        self.assertEqual(EXPECTED_VENUES, set(list_venues()) & EXPECTED_VENUES)

    def test_every_venue_file_is_valid(self) -> None:
        for slug in list_venues():
            with self.subTest(venue=slug):
                config = load_venue(slug)
                self.assertEqual(config["venue"], slug)

    def test_every_venue_has_all_required_fields(self) -> None:
        for slug in list_venues():
            config = load_venue(slug, validate=False)
            for field in REQUIRED_FIELDS:
                with self.subTest(venue=slug, field=field):
                    self.assertIn(field, config)
                    self.assertIsNotNone(config[field])

    def test_column_values_are_allowed(self) -> None:
        for slug in list_venues():
            with self.subTest(venue=slug):
                self.assertIn(load_venue(slug)["columns"], VALID_COLUMNS)

    def test_page_limits_are_plausible(self) -> None:
        for slug in list_venues():
            with self.subTest(venue=slug):
                limit = load_venue(slug)["page_limit_main"]
                self.assertGreaterEqual(limit, 4)
                self.assertLessEqual(limit, 20)

    def test_urls_are_http(self) -> None:
        for slug in list_venues():
            config = load_venue(slug)
            for field in ("style_file_url", "author_guide_url"):
                with self.subTest(venue=slug, field=field):
                    self.assertTrue(config[field].startswith("https://"))

    def test_checklist_asset_exists_when_required(self) -> None:
        for slug in list_venues():
            config = load_venue(slug)
            if not config["checklist_required"]:
                continue
            asset = SKILL_DIR / "assets" / "checklists" / f"{config['checklist_asset']}.md"
            with self.subTest(venue=slug):
                self.assertTrue(asset.exists(), msg=f"{asset} is missing")

    def test_no_venue_style_file_is_committed(self) -> None:
        """Style files are downloaded at run time, never redistributed."""
        for pattern in ("*.sty", "*.bst"):
            found = list((SKILL_DIR / "assets" / "venues").glob(pattern))
            self.assertEqual(found, [], msg=f"venue style files must not be committed: {found}")

    def test_unknown_venue_raises(self) -> None:
        with self.assertRaises(VenueConfigError):
            load_venue("nonexistent-venue")

    def test_missing_required_field_is_reported(self) -> None:
        problems = validate_venue({"venue": "x"}, path_label="x.yaml")
        self.assertTrue(any("page_limit_main" in problem for problem in problems))

    def test_bool_is_not_accepted_as_int(self) -> None:
        config = load_venue("neurips", validate=False)
        config["page_limit_main"] = True
        problems = validate_venue(config, path_label="neurips.yaml")
        self.assertTrue(any("must be an integer" in problem for problem in problems))


class TestVenueConfigCli(unittest.TestCase):
    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "venue_config.py"), *args],
            cwd=str(SKILL_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )

    def test_help_exits_zero(self) -> None:
        self.assertEqual(self._run(["--help"]).returncode, 0)

    def test_no_args_exits_zero(self) -> None:
        self.assertEqual(self._run([]).returncode, 0)

    def test_validate_all_passes(self) -> None:
        proc = self._run(["--validate-all"])
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)

    def test_list_prints_every_venue(self) -> None:
        proc = self._run(["--list"])
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(EXPECTED_VENUES, set(proc.stdout.split()) & EXPECTED_VENUES)

    def test_unknown_venue_errors(self) -> None:
        proc = self._run(["--venue", "nope"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown venue", proc.stderr)


if __name__ == "__main__":
    unittest.main()
