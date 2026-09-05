"""Tests for scripts/claim_registry.py — the structural pre-pass and claim filter."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import claim_registry as cr  # noqa: E402

PAPER = r"""
\documentclass[conference]{IEEEtran}
\usepackage{tikz}
\definecolor{gateblue}{RGB}{70,130,180}
\begin{document}
\title{A Title With 4 Words}
\begin{abstract}
The suite runs 430 tests in 31 seconds, all passing.
\end{abstract}
\section{Introduction}
The gate refuses 3 of the 4 malformed inputs.
\begin{figure}[t]
\centering
\begin{tikzpicture}
\node[box] (a) at (0,0) {12 phases and 6 venues};
\draw[->] (a) -- (b);
\end{tikzpicture}
\caption{An architecture diagram with 10 boxes.}
\label{fig:x}
\end{figure}
\begin{table}[t]
\caption{Coverage at commit abc1234.}
\begin{tabular}{lc}
\toprule
Axis & Count \\
Disciplines & 8 \\
\bottomrule
\end{tabular}
\end{table}
\section{Method}
\begin{equation}
E = mc^2 + 3
\end{equation}
The engine records 10 phases in one state file.
\bibliography{ref}
\end{document}
"""


class TestStripNonProse:
    def test_preamble_is_dropped(self):
        out = cr.strip_non_prose(PAPER)
        assert "usepackage" not in out
        assert "definecolor" not in out

    def test_tikz_and_float_bodies_are_dropped(self):
        out = cr.strip_non_prose(PAPER)
        assert "tikzpicture" not in out
        assert "12 phases and 6 venues" not in out
        assert "An architecture diagram" not in out

    def test_table_body_is_dropped(self):
        out = cr.strip_non_prose(PAPER)
        assert "Disciplines & 8" not in out
        assert "toprule" not in out

    def test_math_environment_is_dropped(self):
        out = cr.strip_non_prose(PAPER)
        assert "E = mc^2" not in out

    def test_prose_survives(self):
        out = cr.strip_non_prose(PAPER)
        assert "The gate refuses 3 of the 4 malformed inputs." in out
        assert "The engine records 10 phases in one state file." in out
        assert "The suite runs 430 tests" in out

    def test_keep_floats_leaves_float_bodies_in(self):
        out = cr.strip_non_prose(PAPER, keep_floats=True)
        assert "12 phases and 6 venues" in out
        assert "An architecture diagram" in out

    def test_environment_markers_are_never_emitted(self):
        out = cr.strip_non_prose(PAPER, keep_floats=True)
        assert "\\begin{" not in out
        assert "\\end{" not in out


class TestClaimFilter:
    def test_markup_residue_is_not_a_claim(self):
        assert not cr.looks_like_claim(r"\begin{tikzpicture} node at 0,0 with 3 boxes", mode="numeric")

    def test_a_fragment_without_a_verb_is_not_a_claim(self):
        assert not cr.looks_like_claim("Coverage at commit abc1234, 8 disciplines", mode="numeric")

    def test_a_numeric_assertion_is_a_claim(self):
        assert cr.looks_like_claim("The suite runs 430 tests in 31 seconds.", mode="numeric")

    def test_spacing_macros_are_cleaned_not_flagged(self):
        cleaned = cr.clean_sentence(r"The example compiles in 5.8\,s end to end.")
        assert cleaned == "The example compiles in 5.8 s end to end."
        assert cr.looks_like_claim(cleaned, mode="numeric")

    def test_escaped_specials_survive_cleaning(self):
        assert cr.clean_sentence(r"Roadmap \& Guide has 2 parts") == "Roadmap & Guide has 2 parts"


class TestBuildClaims:
    def test_registry_holds_only_prose_claims(self):
        claims = cr.build_claims(PAPER, mode="numeric", max_claims=50)
        texts = [c.text for c in claims]
        assert any("430 tests" in t for t in texts)
        assert any("10 phases in one state file" in t for t in texts)
        assert not any("tikz" in t.lower() for t in texts)
        assert not any("Disciplines" in t for t in texts)

    def test_sections_are_labelled(self):
        claims = cr.build_claims(PAPER, mode="numeric", max_claims=50)
        sections = {c.section for c in claims}
        assert "Introduction" in sections
        assert "Method" in sections
