"""Tests for scripts/rebuttal_gate.py — review comments as tracked work."""

import csv
import io
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rebuttal_gate as rg  # noqa: E402

COMMENTS = """# Review Comments

## Reviewer 1

### 1. The abstract overclaims

The abstract says the gates prevent every failure.
Resolution: softened the abstract wording.

### 2. No baseline comparison

An ungated agent would make the comparison concrete.
Resolution: declined, running one is out of scope for this paper.

## Area Chair

### 3. Evaluation section needs the environment stated

Say which machine and which Python version produced the timings.
Resolution: added the environment paragraph.
"""

HEADER = "ID,Phase,Title,Description,Target_Citations,Visualization,Acceptance,Status,Verified_Citations,Notes,Depends_On,Owner\n"


def run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "rebuttal_gate.py")] + args,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def make_project(tmp_path, rows="", comments=COMMENTS):
    (tmp_path / "notes").mkdir(exist_ok=True)
    (tmp_path / "issues").mkdir(exist_ok=True)
    (tmp_path / "notes" / "review-comments.md").write_text(comments, encoding="utf-8")
    (tmp_path / "issues" / "i.csv").write_text(HEADER + rows, encoding="utf-8")
    return tmp_path


class TestParsing:
    def test_comments_carry_their_role_and_resolution(self):
        comments = rg.parse_comments(COMMENTS)
        assert [c.number for c in comments] == [1, 2, 3]
        assert comments[0].role == "Reviewer 1"
        assert comments[2].role == "Area Chair"
        assert comments[0].resolution.startswith("softened")

    def test_a_declined_resolution_is_recognised(self):
        comments = rg.parse_comments(COMMENTS)
        verdicts = rg.judge(comments, [])
        by_number = {v.comment.number: v.status for v in verdicts}
        assert by_number[2] == "DECLINED"

    def test_a_promise_with_no_row_is_untracked(self):
        comments = rg.parse_comments(COMMENTS)
        verdicts = rg.judge(comments, [])
        by_number = {v.comment.number: v.status for v in verdicts}
        assert by_number[1] == "UNTRACKED"
        assert by_number[3] == "UNTRACKED"


class TestTracking:
    def test_a_row_naming_the_comment_tracks_it(self):
        rows = list(csv.DictReader(io.StringIO(HEADER + "W9,Writing,Fix abstract,,,,,DONE,,answers RC1,,\n")))
        comments = rg.parse_comments(COMMENTS)
        assert rg.comment_is_tracked(comments[0], rows) == "W9"

    def test_a_similar_number_does_not_count(self):
        rows = list(csv.DictReader(io.StringIO(HEADER + "W9,Writing,Fix,,,,,DONE,,relates to RC11,,\n")))
        comments = rg.parse_comments(COMMENTS)
        assert rg.comment_is_tracked(comments[0], rows) is None


class TestCli:
    def test_untracked_comments_fail_the_gate(self, tmp_path):
        project = make_project(tmp_path)
        result = run(["--project-dir", str(project)])
        assert result.returncode == 1
        assert "UNTRACKED" in result.stdout

    def test_tracked_and_declined_comments_pass(self, tmp_path):
        rows = (
            "W9,Writing,Abstract rewrite,,,,,DONE,,answers RC1,,\n"
            "W10,Writing,Environment paragraph,,,,,DONE,,answers RC3,,\n"
        )
        project = make_project(tmp_path, rows=rows)
        result = run(["--project-dir", str(project)])
        assert result.returncode == 0
        report = (project / "notes" / "rebuttal-gate.md").read_text(encoding="utf-8")
        assert "Verdict: PASS" in report

    def test_emit_issues_creates_one_row_per_untracked_comment(self, tmp_path):
        project = make_project(tmp_path)
        result = run(["--project-dir", str(project), "--emit-issues"])
        assert result.returncode == 0
        text = (project / "issues" / "i.csv").read_text(encoding="utf-8")
        rows = list(csv.DictReader(io.StringIO(text)))
        ids = {r["ID"] for r in rows}
        assert {"RC1", "RC3"} <= ids
        assert all(r["Status"] == "TODO" for r in rows if r["ID"] in {"RC1", "RC3"})
        # The declined comment gets no row.
        assert "RC2" not in ids

    def test_emitted_rows_use_a_phase_the_schema_allows(self, tmp_path):
        project = make_project(tmp_path)
        run(["--project-dir", str(project), "--emit-issues"])
        text = (project / "issues" / "i.csv").read_text(encoding="utf-8")
        rows = {r["ID"]: r for r in csv.DictReader(io.StringIO(text))}
        assert rows["RC1"]["Phase"] == "Review"

    def test_emitted_rows_keep_the_header_shape(self, tmp_path):
        project = make_project(tmp_path)
        run(["--project-dir", str(project), "--emit-issues"])
        text = (project / "issues" / "i.csv").read_text(encoding="utf-8")
        assert text.splitlines()[0] == HEADER.strip()

    def test_scaffold_writes_role_sections(self, tmp_path):
        (tmp_path / "notes").mkdir()
        result = run(["--project-dir", str(tmp_path), "--scaffold"])
        assert result.returncode == 0
        text = (tmp_path / "notes" / "review-comments.md").read_text(encoding="utf-8")
        assert "## Reviewer 1" in text and "## Area Chair" in text

    def test_scaffold_refuses_to_overwrite(self, tmp_path):
        project = make_project(tmp_path)
        result = run(["--project-dir", str(project), "--scaffold"])
        assert result.returncode == 2

    def test_missing_issues_csv_is_a_usage_error(self, tmp_path):
        (tmp_path / "notes").mkdir()
        (tmp_path / "notes" / "review-comments.md").write_text(COMMENTS, encoding="utf-8")
        result = run(["--project-dir", str(tmp_path)])
        assert result.returncode == 2
