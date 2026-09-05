"""Tests for scripts/benchmark_compare.py — measuring arms the same way."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import benchmark_compare as bc  # noqa: E402

TEX = r"""
\begin{document}
\begin{abstract}
An abstract.
\end{abstract}
\section{Introduction}
A claim~\cite{real2024}.
\section{Related Work}
Another~\cite{real2024}.
\section{Method}
\section{Experiments}
\section{Limitations}
\section{Conclusion}
\end{document}
"""

BIB_GOOD = """
@misc{real2024,
  title = {A Real Paper},
  eprint = {2401.00001},
  year = {2024}
}
"""

BIB_BAD = """
@misc{PLACEHOLDER_guess2024,
  title = {A Guessed Paper},
  year = {2024}
}

@article{ghost2023,
  title = {Another Guess},
  journal = {Journal},
  year = {2023}
}
"""


def run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "benchmark_compare.py")] + args,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
    )


def make_arm(tmp_path, name, bib, *, tex=TEX, verification=None, registry=None, log=None):
    project = tmp_path / name
    (project / "notes").mkdir(parents=True)
    (project / "main.tex").write_text(tex, encoding="utf-8")
    (project / "ref.bib").write_text(bib, encoding="utf-8")
    if verification:
        (project / "notes" / "citation-verification.md").write_text(verification, encoding="utf-8")
    if registry:
        (project / "notes" / "claim-registry.csv").write_text(registry, encoding="utf-8")
    if log:
        (project / "main.log").write_text(log, encoding="utf-8")
    return project


class TestMetrics:
    def test_identifier_share_and_placeholders(self, tmp_path):
        good = make_arm(tmp_path, "good", BIB_GOOD)
        bad = make_arm(tmp_path, "bad", BIB_BAD, tex=TEX.replace("real2024", "ghost2023"))
        m_good = bc.measure("good", good, None)
        m_bad = bc.measure("bad", bad, None)
        assert m_good.values["identified"] == 1.0
        assert m_bad.values["identified"] == 0.0
        assert m_bad.values["placeholders"] == 1

    def test_cited_but_missing_is_counted(self, tmp_path):
        arm = make_arm(tmp_path, "a", BIB_GOOD, tex=TEX.replace("real2024", "nowhere2024"))
        metrics = bc.measure("a", arm, None)
        assert metrics.values["cited_but_missing"] == 1
        assert metrics.values["entries_uncited"] == 1

    def test_required_sections_use_the_discipline_profile(self, tmp_path):
        arm = make_arm(tmp_path, "a", BIB_GOOD)
        metrics = bc.measure("a", arm, "computer-science")
        assert metrics.values["required_sections"] == 1.0

    def test_verification_counts_are_read_from_the_report(self, tmp_path):
        report = (
            "| Status | Count |\n|---|---|\n"
            "| VERIFIED | 8 |\n| SUSPICIOUS | 0 |\n| HALLUCINATED | 2 |\n| SKIPPED | 0 |\n"
        )
        arm = make_arm(tmp_path, "a", BIB_GOOD, verification=report)
        metrics = bc.measure("a", arm, None)
        assert metrics.values["verified"] == 0.8
        assert metrics.values["hallucinated"] == 2

    def test_missing_artifacts_are_notes_not_zeros(self, tmp_path):
        arm = make_arm(tmp_path, "a", BIB_GOOD)
        metrics = bc.measure("a", arm, None)
        assert "verified" not in metrics.values
        assert any("citation-verification" in note for note in metrics.notes)

    def test_page_count_comes_from_the_log(self, tmp_path):
        arm = make_arm(tmp_path, "a", BIB_GOOD, log="Output written on main.pdf (7 pages, 1 bytes).")
        assert bc.measure("a", arm, None).values["pages"] == 7

    def test_claim_verdict_share(self, tmp_path):
        registry = "ID,Section,Claim,Citations_Evidence,Verdict,Notes\nC1,S,x,,VERIFIED,\nC2,S,y,,,\n"
        arm = make_arm(tmp_path, "a", BIB_GOOD, registry=registry)
        assert bc.measure("a", arm, None).values["claims_with_verdicts"] == 0.5


class TestCli:
    def test_two_arms_are_tabulated(self, tmp_path):
        good = make_arm(tmp_path, "good", BIB_GOOD)
        bad = make_arm(tmp_path, "bad", BIB_BAD, tex=TEX.replace("real2024", "ghost2023"))
        out = tmp_path / "benchmark.md"
        result = run(
            [
                "--arm",
                f"gated={good}",
                "--arm",
                f"ungated={bad}",
                "--discipline",
                "computer-science",
                "--out",
                str(out),
            ]
        )
        assert result.returncode == 0
        report = out.read_text(encoding="utf-8")
        assert "| `identified` |" in report
        assert "gated" in report and "ungated" in report

    def test_json_output_carries_the_raw_metrics(self, tmp_path):
        arm = make_arm(tmp_path, "a", BIB_GOOD)
        out = tmp_path / "b.md"
        js = tmp_path / "b.json"
        result = run(["--arm", f"a={arm}", "--out", str(out), "--json-out", str(js)])
        assert result.returncode == 0
        data = json.loads(js.read_text(encoding="utf-8"))
        assert data["arms"][0]["metrics"]["references"] == 1

    def test_malformed_arm_is_a_usage_error(self, tmp_path):
        result = run(["--arm", "justapath"])
        assert result.returncode == 2

    def test_no_arm_is_a_usage_error(self):
        assert run([]).returncode == 2
