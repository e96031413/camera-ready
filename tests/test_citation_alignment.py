"""Tests for scripts/citation_alignment.py — citing sentence against cited abstract."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import citation_alignment as ca  # noqa: E402

PAPER = r"""
\documentclass{article}
\begin{document}
\section{Related Work}
Retrieval grounding reduces invented content in structured
generation~\cite{grounding2024}.

Sorting networks of fixed depth admit an optimal construction for eight
inputs~\cite{sorting1968}.
\begin{figure}
\begin{tikzpicture}
\node {citation-free markup with 3 nodes};
\end{tikzpicture}
\end{figure}
\end{document}
"""

BIB = """
@misc{grounding2024,
  title = {Reducing hallucination in structured outputs via retrieval augmented generation},
  abstract = {We show that retrieval grounding reduces invented content when a model produces structured outputs.},
  year = {2024}
}

@misc{sorting1968,
  title = {Optimal sorting networks},
  abstract = {We give an optimal depth construction for sorting networks on eight inputs.},
  year = {1968}
}
"""


def run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "citation_alignment.py")] + args,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def make_project(tmp_path, paper=PAPER, bib=BIB):
    (tmp_path / "main.tex").write_text(paper, encoding="utf-8")
    (tmp_path / "ref.bib").write_text(bib, encoding="utf-8")
    return tmp_path


class TestOccurrences:
    def test_every_key_in_a_multi_key_cite_is_one_occurrence(self):
        tex = "\\begin{document}\n\\section{S}\nA claim~\\cite{a,b}.\n\\end{document}\n"
        keys = [o.key for o in ca.find_occurrences(tex)]
        assert keys == ["a", "b"]

    def test_markup_bodies_contribute_no_occurrences(self):
        occurrences = ca.find_occurrences(PAPER)
        assert all("tikz" not in o.context for o in occurrences)
        assert {o.key for o in occurrences} == {"grounding2024", "sorting1968"}

    def test_line_numbers_point_into_the_source(self):
        occurrences = ca.find_occurrences(PAPER)
        lines = PAPER.splitlines()
        for occurrence in occurrences:
            assert 1 <= occurrence.line <= len(lines)


class TestBibParsing:
    def test_abstract_and_title_are_read(self):
        entries = ca.parse_bib(BIB)
        assert "grounding2024" in entries
        assert entries["grounding2024"]["abstract"].startswith("We show that retrieval")


class TestScoring:
    def test_a_matching_pair_scores_above_a_mismatched_one(self):
        entries = ca.parse_bib(BIB)
        occurrences = {o.key: o for o in ca.find_occurrences(PAPER)}
        docs = [ca._tokens(o.context) for o in occurrences.values()]
        docs += [ca._tokens(e["abstract"]) for e in entries.values()]
        idf = ca.build_idf(docs)

        aligned = ca.cosine(
            ca._tokens(occurrences["grounding2024"].sentence),
            ca._tokens(entries["grounding2024"]["abstract"]),
            idf,
        )
        crossed = ca.cosine(
            ca._tokens(occurrences["grounding2024"].sentence),
            ca._tokens(entries["sorting1968"]["abstract"]),
            idf,
        )
        assert aligned > crossed

    def test_classification_bands(self):
        assert ca.classify(0.20, 0.04) == "ALIGNED"
        assert ca.classify(0.05, 0.04) == "WEAK"
        assert ca.classify(0.01, 0.04) == "REVIEW"


class TestCli:
    def test_offline_run_writes_a_report(self, tmp_path):
        project = make_project(tmp_path)
        result = run(["--project-dir", str(project), "--offline", "--no-cache"])
        assert result.returncode == 0
        report = (project / "notes" / "citation-alignment.md").read_text(encoding="utf-8")
        assert "Citation Alignment Report" in report
        assert "grounding2024" in report

    def test_a_key_absent_from_the_bibliography_is_flagged(self, tmp_path):
        project = make_project(
            tmp_path,
            paper=PAPER.replace("grounding2024", "ghost2024"),
        )
        result = run(["--project-dir", str(project), "--offline", "--no-cache"])
        assert result.returncode == 0
        assert "ghost2024" in result.stdout

    def test_strict_fails_when_a_pairing_is_flagged(self, tmp_path):
        project = make_project(
            tmp_path,
            paper=PAPER.replace("grounding2024", "ghost2024"),
        )
        result = run(["--project-dir", str(project), "--offline", "--no-cache", "--strict"])
        assert result.returncode == 1

    def test_missing_bibliography_is_a_usage_error(self, tmp_path):
        (tmp_path / "main.tex").write_text(PAPER, encoding="utf-8")
        result = run(["--project-dir", str(tmp_path), "--offline"])
        assert result.returncode == 2
