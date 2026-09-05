import csv
import unittest
from pathlib import Path


class TestConferenceTemplates(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_dir = Path(__file__).resolve().parents[1]
        self.assets_dir = self.skill_dir / "assets"

    # ── Plan template ──────────────────────────────────────────────

    def test_conference_plan_template_exists(self) -> None:
        path = self.assets_dir / "paper-plan-conference-template.md"
        self.assertTrue(path.exists(), msg=f"{path} should exist")

    def test_conference_plan_has_venue_placeholder(self) -> None:
        path = self.assets_dir / "paper-plan-conference-template.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("<venue>", text, msg="Conference plan template must contain a <venue> placeholder")

    def test_conference_plan_has_kickoff_gate(self) -> None:
        path = self.assets_dir / "paper-plan-conference-template.md"
        text = path.read_text(encoding="utf-8")
        # Kickoff gate is typically a checkbox line mentioning "kickoff"
        has_kickoff = any(
            "kickoff" in line.lower() and ("- [" in line or "- [ ]" in line or "- [x]" in line)
            for line in text.splitlines()
        )
        self.assertTrue(has_kickoff, msg="Conference plan template must have a kickoff gate checkbox")

    # ── Issues template ────────────────────────────────────────────

    def test_conference_issues_template_exists(self) -> None:
        path = self.assets_dir / "paper-issues-conference-template.csv"
        self.assertTrue(path.exists(), msg=f"{path} should exist")

    def test_conference_issues_valid_csv(self) -> None:
        path = self.assets_dir / "paper-issues-conference-template.csv"
        expected_header = [
            "ID", "Phase", "Title", "Description", "Target_Citations",
            "Visualization", "Acceptance", "Status", "Verified_Citations", "Notes",
            "Depends_On", "Owner",
        ]
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        self.assertEqual(header, expected_header, msg="CSV header must match the expected 12-column schema")

    def test_conference_issues_has_required_phases(self) -> None:
        path = self.assets_dir / "paper-issues-conference-template.csv"
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            phases = {row["Phase"] for row in reader}

        required = {"Research", "Writing", "Integrity", "Review", "QA", "Video"}
        missing = required - phases
        self.assertFalse(missing, msg=f"Conference issues template missing phases: {missing}")

    def test_conference_issues_has_anti_ai_issue(self) -> None:
        path = self.assets_dir / "paper-issues-conference-template.csv"
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        found = any(
            "anti-ai" in (row.get("Title", "") + row.get("Description", "")).lower()
            or "ai pattern" in (row.get("Title", "") + row.get("Description", "")).lower()
            for row in rows
        )
        self.assertTrue(found, msg="At least one issue must mention anti-AI or AI pattern")

    def test_conference_issues_has_self_review_issue(self) -> None:
        path = self.assets_dir / "paper-issues-conference-template.csv"
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        found = any(
            "self-review" in (row.get("Title", "") + row.get("Description", "")).lower()
            or "self review" in (row.get("Title", "") + row.get("Description", "")).lower()
            for row in rows
        )
        self.assertTrue(found, msg="At least one issue must mention self-review")

    def test_conference_issues_no_empty_ids(self) -> None:
        path = self.assets_dir / "paper-issues-conference-template.csv"
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                self.assertTrue(
                    row["ID"].strip(),
                    msg=f"Row {i} has an empty ID cell",
                )

    def test_conference_issues_valid_statuses(self) -> None:
        path = self.assets_dir / "paper-issues-conference-template.csv"
        valid_statuses = {"TODO", "DOING", "DONE", "SKIP"}
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                status = row["Status"].strip()
                self.assertIn(
                    status,
                    valid_statuses,
                    msg=f"Row {i} has invalid status '{status}'; expected one of {valid_statuses}",
                )


if __name__ == "__main__":
    unittest.main()
