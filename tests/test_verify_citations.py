"""Tests for scripts/verify_citations.py — 4-layer citation verification and strict gate mode."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import verify_citations as vc  # noqa: E402


def run_vc(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_citations.py")] + args,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def test_parse_bib_entries():
    bib_text = """
    @article{smith2024,
      title = {A Great Study},
      author = {Smith, John},
      doi = {10.1234/example},
      year = {2024}
    }
    @misc{jones2023,
      title = {Another Study},
      author = {Jones, Alice},
      eprint = {2301.00001}
    }
    """
    entries = vc.parse_bib_entries(bib_text)
    assert len(entries) == 2
    assert entries[0]["key"] == "smith2024"
    assert entries[0]["title"] == "A Great Study"
    assert entries[0]["doi"] == "10.1234/example"
    assert entries[1]["key"] == "jones2023"
    assert entries[1]["eprint"] == "2301.00001"


def test_classify_entry_detects_placeholders():
    placeholder_entry = {
        "key": "PLACEHOLDER_novelty",
        "title": "Novel Approach to X",
        "author": "Unknown",
        "raw": "@misc{PLACEHOLDER_novelty,\n  title = {Novel Approach to X},\n  note = {[VERIFY]},\n}\n",
    }
    classification, layers = vc.classify_entry(placeholder_entry, offline=True)
    assert classification == "HALLUCINATED"
    assert layers[0]["status"] == "placeholder"

    verify_suffix_entry = {
        "key": "novelty_verify",
        "title": "Novel Approach to X",
        "author": "Unknown",
        "raw": "@misc{novelty_verify,\n  title = {Novel Approach to X},\n  note = {[VERIFY]},\n}\n",
    }
    classification, layers = vc.classify_entry(verify_suffix_entry, offline=True)
    assert classification == "HALLUCINATED"


def test_strict_mode_rejects_placeholders(tmp_path):
    bib = tmp_path / "ref.bib"
    bib.write_text(
        "@misc{PLACEHOLDER_deepseek,\n"
        "  title = {DeepSeek R1},\n"
        "  author = {DeepSeek-AI},\n"
        "  note = {[VERIFY]},\n"
        "}\n",
        encoding="utf-8",
    )

    # In strict mode, must fail with exit code 1
    res = run_vc(["--bib-file", str(bib), "--strict", "--offline"])
    assert res.returncode == 1
    assert "strict gate failed" in res.stderr
    assert "HALLUCINATED" in res.stderr or "placeholder" in res.stderr

    # In advisory mode without --strict, exits 0
    res_advisory = run_vc(["--bib-file", str(bib), "--offline"])
    assert res_advisory.returncode == 0


def test_strict_mode_rejects_truncated_max_entries(tmp_path):
    bib = tmp_path / "ref.bib"
    entries = "\n".join(
        f"@misc{{paper{i},\n  title = {{Paper {i}}},\n  author = {{Author {i}}},\n}}\n"
        for i in range(5)
    )
    bib.write_text(entries, encoding="utf-8")

    res = run_vc(["--bib-file", str(bib), "--strict", "--max-entries", "3", "--offline"])
    assert res.returncode == 1
    assert "strict gate mode requires verifying all citations" in res.stderr
    assert "3" in res.stderr and "5" in res.stderr


def test_strict_mode_passes_when_all_verified(tmp_path):
    bib = tmp_path / "ref.bib"
    bib.write_text(
        "@misc{smith2024,\n"
        "  title = {Verified Paper},\n"
        "  author = {Smith, John},\n"
        "  eprint = {2401.00001},\n"
        "}\n",
        encoding="utf-8",
    )

    # Prime citation cache
    cache = vc.CitationCache(tmp_path / "notes" / "citation-cache.sqlite3")
    cache.put("verify", "2401.00001", "VERIFIED")

    res = run_vc(["--bib-file", str(bib), "--strict", "--offline"])
    assert res.returncode == 0
    assert "VERIFIED:      1" in res.stdout
