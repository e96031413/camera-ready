"""Tests for scripts/logic_selfloop.py — TF-IDF linkage and parallel-series awareness."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import logic_selfloop as ls  # noqa: E402


def section_from(text: str, title: str = "S") -> ls.Section:
    section = ls.Section(title=title, start_line=1)
    for i, line in enumerate(text.splitlines(), start=1):
        section.raw_lines.append((i, line))
    return section


LABELLED = """
\\textbf{P1: state lives outside the model.} The run position is a file on disk.
It survives a truncated conversation and a different model entirely.

\\textbf{P2: refuse by default.} Every gate script exits non-zero on failure.
Advancing needs the condition to hold, or a journaled override.

\\textbf{P3: source or nothing.} No code path writes a reference from memory.
A lookup that fails returns a marker, never an entry.
"""

LINKED = """
The gate engine reads the project directory before any phase closes.
It compares the exit condition against files rather than against assertions.

The engine then records the transition in a journal beside the state file.
That journal is what a later reader consults to see how the project advanced.
"""


class TestCosine:
    def test_identical_bags_are_one(self):
        counts = {"gate": 2, "engine": 1}
        idf = {"gate": 1.5, "engine": 2.0}
        assert ls.cosine_similarity(counts, counts, idf) == pytest.approx(1.0)

    def test_disjoint_bags_are_zero(self):
        idf = {"gate": 1.5, "poster": 2.0}
        assert ls.cosine_similarity({"gate": 1}, {"poster": 1}, idf) == 0.0

    def test_empty_side_is_zero(self):
        assert ls.cosine_similarity({}, {"gate": 1}, {"gate": 1.0}) == 0.0

    def test_rare_terms_weigh_more_than_common_ones(self):
        idf = {"rare": 4.0, "common": 1.0}
        shared_rare = ls.cosine_similarity({"rare": 1, "x": 1}, {"rare": 1, "y": 1}, idf | {"x": 1.0, "y": 1.0})
        shared_common = ls.cosine_similarity({"common": 1, "x": 1}, {"common": 1, "y": 1}, idf | {"x": 1.0, "y": 1.0})
        assert shared_rare > shared_common


class TestLabelledSeries:
    def test_bold_lead_in_is_labelled(self):
        assert ls._is_labelled(r"\textbf{P2: refuse by default.} Every gate script exits.")

    def test_alphanumeric_label_is_labelled(self):
        assert ls._is_labelled("F1: fabricated references. The model emits BibTeX.")

    def test_ordinary_prose_is_not_labelled(self):
        assert not ls._is_labelled("The gate engine reads the project directory.")

    def test_a_parallel_series_is_not_reported_as_islands(self):
        findings = ls.analyze_section(section_from(LABELLED))
        assert [f for f in findings if f.kind == "island"] == []


class TestLinkage:
    def test_linked_paragraphs_produce_no_island(self):
        findings = ls.analyze_section(section_from(LINKED))
        assert [f for f in findings if f.kind == "island"] == []

    def test_baseline_is_the_median_of_adjacent_pairs(self):
        assert ls.baseline_similarity([0.0, 0.2, 0.4]) == 0.2
        assert ls.baseline_similarity([0.0, 0.4]) == 0.2
        assert ls.baseline_similarity([]) == 0.0


class TestSuffixTerms:
    def test_a_term_reused_in_a_later_section_is_not_dangling(self):
        first = section_from(
            "The registry stores every fetched entry with a key.\n"
            "The registry is consulted before any export runs.\n",
            title="One",
        )
        second = section_from(
            "The registry is exported into the bibliography file.\n"
            "Export assigns a stable key to every entry it writes.\n",
            title="Two",
        )
        lookup = ls.suffix_terms([first, second])
        first_para = ls.split_paragraphs(first)[0]
        assert "registry" in lookup[first_para.start_line]


class TestFloatsAreExcluded:
    def test_a_tikz_body_is_not_a_paragraph(self):
        tex = (
            "\\begin{document}\n"
            "\\section{Method}\n"
            "The engine reads the project directory before a phase closes.\n"
            "It compares the condition against files rather than assertions.\n"
            "\n"
            "\\begin{figure}\n"
            "\\begin{tikzpicture}\n"
            "\\node (a) at (0,0) {alpha beta gamma delta};\n"
            "\\draw (a) -- (b);\n"
            "\\end{tikzpicture}\n"
            "\\end{figure}\n"
            "\n"
            "The engine then records the transition in a journal on disk.\n"
            "That journal is what a later reader consults about the project.\n"
        )
        sections = ls.parse_sections(tex)
        paragraphs = ls.split_paragraphs(sections[0])
        assert len(paragraphs) == 2
        assert all("tikz" not in " ".join(p.lines) for p in paragraphs)
