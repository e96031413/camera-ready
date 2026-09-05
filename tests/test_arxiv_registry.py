"""Tests for scripts/arxiv_registry.py — the fetch-to-BibTeX escaping path."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import arxiv_registry as ar  # noqa: E402

ENTRY = """@misc{kong2026ai,
      title={AI for Auto-Research: Roadmap & User Guide},
      author={Lingdong Kong and Wei Tsang Ooi},
      year={2026},
      eprint={2605.18661},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2605.18661},
}
"""


class TestEscapeBibtexLatex:
    def test_bare_ampersand_in_a_title_is_escaped(self):
        out = ar.escape_bibtex_latex(ENTRY)
        assert r"Roadmap \& User Guide" in out

    def test_url_field_is_left_verbatim(self):
        entry = ENTRY.replace(
            "url={https://arxiv.org/abs/2605.18661}",
            "url={https://example.org/a?x=1&y=2#frag_z}",
        )
        out = ar.escape_bibtex_latex(entry)
        assert "url={https://example.org/a?x=1&y=2#frag_z}" in out

    def test_existing_escapes_are_not_doubled(self):
        entry = ENTRY.replace("Roadmap & User", r"Roadmap \& User")
        out = ar.escape_bibtex_latex(entry)
        assert r"Roadmap \& User" in out
        assert r"\\&" not in out

    def test_math_mode_is_left_alone(self):
        entry = ENTRY.replace("AI for Auto-Research", "Scaling $x_i$ and 50% of $2^n$")
        out = ar.escape_bibtex_latex(entry)
        assert "$x_i$" in out
        assert "$2^n$" in out
        assert r"50\%" in out

    def test_underscore_and_hash_outside_math_are_escaped(self):
        entry = ENTRY.replace("AI for Auto-Research", "The C# and snake_case study")
        out = ar.escape_bibtex_latex(entry)
        assert r"C\#" in out
        assert r"snake\_case" in out

    def test_entry_header_and_closing_brace_are_untouched(self):
        out = ar.escape_bibtex_latex(ENTRY)
        assert out.startswith("@misc{kong2026ai,")
        assert out.rstrip().endswith("}")

    def test_a_clean_entry_is_returned_unchanged(self):
        clean = ENTRY.replace("Roadmap & User Guide", "Roadmap and User Guide")
        assert ar.escape_bibtex_latex(clean) == clean
