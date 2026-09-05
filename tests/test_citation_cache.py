"""Tests for scripts/citation_cache.py and the offline paths it gives the citation tools."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import citation_cache as cc  # noqa: E402
import fetch_bibtex as fb  # noqa: E402
import verify_citations as vc  # noqa: E402

BIBTEX = "@article{doe2024x,\n  title = {A Real Paper},\n  author = {Doe, Jane},\n  year = {2024}\n}"


class TestCache:
    def test_roundtrip(self, tmp_path):
        cache = cc.CitationCache(tmp_path / "c.sqlite3")
        cache.put("bibtex", "A Real Paper", BIBTEX)
        assert cache.get("bibtex", "A Real Paper") == BIBTEX

    def test_key_is_normalised(self, tmp_path):
        cache = cc.CitationCache(tmp_path / "c.sqlite3")
        cache.put("bibtex", "A Real Paper", BIBTEX)
        assert cache.get("bibtex", "  a  real,  paper ") == BIBTEX

    def test_miss_returns_none(self, tmp_path):
        cache = cc.CitationCache(tmp_path / "c.sqlite3")
        assert cache.get("bibtex", "Nothing Here") is None

    def test_expired_entry_is_a_miss(self, tmp_path):
        cache = cc.CitationCache(tmp_path / "c.sqlite3")
        cache.put("bibtex", "A Real Paper", BIBTEX)
        assert cache.get("bibtex", "A Real Paper", max_age_s=-1) is None

    def test_disabled_cache_stores_nothing(self, tmp_path):
        cache = cc.CitationCache(tmp_path / "c.sqlite3", enabled=False)
        cache.put("bibtex", "A Real Paper", BIBTEX)
        assert cache.get("bibtex", "A Real Paper") is None

    def test_prune_removes_old_entries(self, tmp_path):
        cache = cc.CitationCache(tmp_path / "c.sqlite3")
        cache.put("bibtex", "A Real Paper", BIBTEX)
        assert cache.prune(-1) == 1
        assert cache.stats()["entries"] == 0

    def test_stats_counts_by_source(self, tmp_path):
        cache = cc.CitationCache(tmp_path / "c.sqlite3")
        cache.put("bibtex", "one", BIBTEX)
        cache.put("verify", "two", "VERIFIED")
        stats = cache.stats()
        assert stats["entries"] == 2
        assert stats["sources"] == {"bibtex": 1, "verify": 1}


def write_corpus(tmp_path, records):
    path = tmp_path / "corpus.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return path


class TestLocalCorpus:
    def test_lookup_by_title_doi_and_arxiv(self, tmp_path):
        path = write_corpus(
            tmp_path,
            [{"title": "A Real Paper", "doi": "10.1/abc", "arxiv_id": "2401.00001", "bibtex": BIBTEX}],
        )
        corpus = cc.LocalCorpus(path)
        assert corpus.available
        assert corpus.by_title("a real paper")["doi"] == "10.1/abc"
        assert corpus.by_doi("10.1/ABC")["title"] == "A Real Paper"
        assert corpus.by_arxiv_id("2401.00001")["title"] == "A Real Paper"

    def test_malformed_lines_are_counted_not_fatal(self, tmp_path):
        path = tmp_path / "corpus.jsonl"
        path.write_text('{"title": "Good"}\nnot json\n{"no_title": 1}\n', encoding="utf-8")
        corpus = cc.LocalCorpus(path)
        assert corpus.records == 1
        assert corpus.malformed == 2

    def test_absent_corpus_is_unavailable(self, tmp_path):
        corpus = cc.LocalCorpus(tmp_path / "missing.jsonl")
        assert not corpus.available
        assert corpus.by_title("anything") is None


class TestFetchOffline:
    def test_offline_never_calls_the_network(self, tmp_path, monkeypatch):
        def explode(*args, **kwargs):
            raise AssertionError("network call in offline mode")

        monkeypatch.setattr(fb, "_http_get", explode)
        bib, source = fb.fetch_bibtex("Anything At All", offline=True)
        assert bib is None
        assert source == "verify"

    def test_corpus_answers_before_the_network(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fb, "_http_get", lambda *a, **k: None)
        corpus = cc.LocalCorpus(write_corpus(tmp_path, [{"title": "A Real Paper", "bibtex": BIBTEX}]))
        bib, source = fb.fetch_bibtex("A Real Paper", corpus=corpus, offline=True)
        assert source == "corpus"
        assert bib == BIBTEX

    def test_cache_answers_when_the_network_is_down(self, tmp_path, monkeypatch):
        cache = cc.CitationCache(tmp_path / "c.sqlite3")
        cache.put("bibtex", "A Real Paper", BIBTEX)
        monkeypatch.setattr(fb, "_http_get", lambda *a, **k: None)
        bib, source = fb.fetch_bibtex("A Real Paper", cache=cache)
        assert source == "cache"
        assert bib == BIBTEX

    def test_a_successful_fetch_is_cached(self, tmp_path, monkeypatch):
        cache = cc.CitationCache(tmp_path / "c.sqlite3")
        monkeypatch.setattr(fb, "fetch_from_dblp", lambda *a, **k: BIBTEX)
        bib, source = fb.fetch_bibtex("A Real Paper", cache=cache)
        assert source == "dblp"
        assert cache.get("bibtex", "A Real Paper") == BIBTEX


class TestVerifyOffline:
    def test_offline_entry_is_skipped_not_hallucinated(self, monkeypatch):
        def explode(*args, **kwargs):
            raise AssertionError("network call in offline mode")

        monkeypatch.setattr(vc, "_http_get", explode)
        classification, _ = vc.classify_entry(
            {"key": "x", "title": "Some Paper", "eprint": "2401.00001"}, offline=True
        )
        assert classification == "SKIPPED"

    def test_corpus_verifies_an_entry_offline(self, tmp_path):
        corpus = cc.LocalCorpus(
            write_corpus(tmp_path, [{"title": "Some Paper", "arxiv_id": "2401.00001"}])
        )
        classification, layers = vc.classify_entry(
            {"key": "x", "title": "Some Paper", "eprint": "2401.00001"},
            corpus=corpus,
            offline=True,
        )
        assert classification == "VERIFIED"
        assert layers[0]["detail"] == "local corpus"

    def test_cached_verdict_survives_an_api_outage(self, tmp_path, monkeypatch):
        cache = cc.CitationCache(tmp_path / "c.sqlite3")
        cache.put("verify", "2401.00001", "VERIFIED")
        monkeypatch.setattr(vc, "_http_get", lambda *a, **k: None)
        classification, _ = vc.classify_entry(
            {"key": "x", "title": "Some Paper", "eprint": "2401.00001"}, cache=cache
        )
        assert classification == "VERIFIED"

    def test_a_hallucinated_verdict_is_never_cached_back_as_verified(self, tmp_path, monkeypatch):
        cache = cc.CitationCache(tmp_path / "c.sqlite3")
        cache.put("verify", "2401.00001", "HALLUCINATED")
        monkeypatch.setattr(vc, "_http_get", lambda *a, **k: None)
        classification, _ = vc.classify_entry(
            {"key": "x", "title": "Some Paper", "eprint": "2401.00001"}, cache=cache
        )
        assert classification != "VERIFIED"
