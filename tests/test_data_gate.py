"""Tests for scripts/data_gate.py — data-to-prose reconciliation."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import data_gate as dg  # noqa: E402

PAPER = r"""
\documentclass{article}
\begin{document}
\section{Results}
Prose mentioning 999 outside any float.
\begin{table}[t]
\centering
\caption{Accuracy by split.}
\label{tab:results}
\renewcommand{\arraystretch}{1.2}
\begin{tabular}{lc}
\toprule
Split & Accuracy \\
\midrule
train & 0.94 \\
test & 0.88 \\
\bottomrule
\end{tabular}
\end{table}
\end{document}
"""


def run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "data_gate.py")] + args,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def make_project(tmp_path, results, paper=PAPER, tolerance=0.005, command=""):
    (tmp_path / "main.tex").write_text(paper, encoding="utf-8")
    (tmp_path / "notes").mkdir(exist_ok=True)
    (tmp_path / "results.json").write_text(json.dumps(results), encoding="utf-8")
    manifest = {
        "bindings": [
            {
                "label": "tab:results",
                "produces": "results.json",
                "tolerance": tolerance,
                "command": command,
            }
        ]
    }
    (tmp_path / "notes" / "data-bindings.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return tmp_path


class TestFloatExtraction:
    def test_finds_the_float_carrying_the_label(self):
        body = dg.find_float_body(PAPER, "tab:results")
        assert body is not None
        assert "Accuracy by split" in body

    def test_unknown_label_returns_none(self):
        assert dg.find_float_body(PAPER, "tab:missing") is None

    def test_layout_digits_are_not_data(self):
        body = dg.find_float_body(PAPER, "tab:results")
        values = dg.numbers_in_float(body)
        assert 0.94 in values
        assert 0.88 in values
        assert 1.2 not in values  # \arraystretch
        assert 999 not in values  # outside the float


class TestDataFiles:
    def test_json_numbers_are_walked(self, tmp_path):
        path = tmp_path / "r.json"
        path.write_text(json.dumps({"a": [0.94, {"b": "0.88 pct"}], "ok": True}), encoding="utf-8")
        values = dg.numbers_in_data_file(path)
        assert 0.94 in values and 0.88 in values
        assert 1.0 not in values  # booleans are not measurements

    def test_csv_numbers_are_read(self, tmp_path):
        path = tmp_path / "r.csv"
        path.write_text("split,acc\ntrain,0.94\ntest,0.88\n", encoding="utf-8")
        values = dg.numbers_in_data_file(path)
        assert values == [0.94, 0.88]


class TestMatching:
    def test_exact_and_tolerant_matches(self):
        assert dg.matches_any(0.94, [0.94], 0.0)
        assert dg.matches_any(0.94, [0.9405], 0.01)
        assert not dg.matches_any(0.94, [0.80], 0.01)


class TestCli:
    def test_reconciling_numbers_pass(self, tmp_path):
        project = make_project(tmp_path, {"train": 0.94, "test": 0.88})
        result = run(["--project-dir", str(project), "--no-run"])
        assert result.returncode == 0
        assert "1/1 binding(s) reconcile" in result.stdout

    def test_a_number_absent_from_the_data_fails(self, tmp_path):
        project = make_project(tmp_path, {"train": 0.94, "test": 0.71})
        result = run(["--project-dir", str(project), "--no-run"])
        assert result.returncode == 1
        assert "0.88" in result.stdout
        report = (project / "notes" / "data-gate.md").read_text(encoding="utf-8")
        assert "0.88" in report

    def test_missing_output_file_fails(self, tmp_path):
        project = make_project(tmp_path, {"train": 0.94, "test": 0.88})
        (project / "results.json").unlink()
        result = run(["--project-dir", str(project), "--no-run"])
        assert result.returncode == 1
        assert "missing output" in result.stdout

    def test_a_failing_command_fails_the_gate(self, tmp_path):
        project = make_project(
            tmp_path,
            {"train": 0.94, "test": 0.88},
            command=f'"{sys.executable}" -c "raise SystemExit(3)"',
        )
        result = run(["--project-dir", str(project)])
        assert result.returncode == 1
        assert "exited 3" in result.stdout

    def test_command_output_is_what_gets_compared(self, tmp_path):
        project = make_project(
            tmp_path,
            {"train": 0.0, "test": 0.0},
            command=(
                f'"{sys.executable}" -c '
                '"import json,pathlib; pathlib.Path(\'results.json\').write_text(json.dumps([0.94,0.88]))"'
            ),
        )
        result = run(["--project-dir", str(project)])
        assert result.returncode == 0

    def test_no_manifest_is_not_a_failure(self, tmp_path):
        (tmp_path / "main.tex").write_text(PAPER, encoding="utf-8")
        result = run(["--project-dir", str(tmp_path), "--no-run"])
        assert result.returncode == 0
        assert "nothing is bound to data" in result.stdout

    def test_init_writes_a_skeleton(self, tmp_path):
        (tmp_path / "main.tex").write_text(PAPER, encoding="utf-8")
        result = run(["--project-dir", str(tmp_path), "--init"])
        assert result.returncode == 0
        manifest = json.loads((tmp_path / "notes" / "data-bindings.json").read_text(encoding="utf-8"))
        assert manifest["bindings"][0]["label"] == "tab:results"

    def test_unknown_label_is_reported(self, tmp_path):
        project = make_project(tmp_path, {"train": 0.94, "test": 0.88})
        manifest = json.loads((project / "notes" / "data-bindings.json").read_text(encoding="utf-8"))
        manifest["bindings"][0]["label"] = "tab:nope"
        (project / "notes" / "data-bindings.json").write_text(json.dumps(manifest), encoding="utf-8")
        result = run(["--project-dir", str(project), "--no-run"])
        assert result.returncode == 1
        assert "no float carries" in result.stdout
