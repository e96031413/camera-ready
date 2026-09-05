#!/usr/bin/env python3
"""Local cache and offline corpus for bibliographic lookups. 2026-09-05-v1.

Why this exists: every citation path in this skill ends at a third-party API.
When DBLP throttles or the machine is offline, a lookup that would have
succeeded yesterday returns nothing, and a verification that passed yesterday
reports "cannot tell". Neither is a fact about the reference.

Two mechanisms, both stdlib-only:

1. A SQLite cache of successful responses, keyed by source and query. Reads are
   served from it when the network fails, and always when --offline is set.
2. An optional local corpus: a JSON Lines file of records carrying at least a
   title, and optionally doi, arxiv_id and bibtex. Point --corpus at an export
   of a bibliographic dataset (S2ORC, DBLP, a group library) and lookups resolve
   without a network at all.

Nothing here invents an entry. A cache miss is a miss, and the caller falls back
to the same [VERIFY] path it would have taken with no cache present.

CLI:
  python scripts/citation_cache.py stats   --cache <path>
  python scripts/citation_cache.py prune   --cache <path> --max-age-days 90
  python scripts/citation_cache.py corpus-check --corpus <path.jsonl>
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

from paper_utils import now_iso

DEFAULT_CACHE_NAME = "citation-cache.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lookups (
  source     TEXT NOT NULL,
  query      TEXT NOT NULL,
  payload    TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  epoch      REAL NOT NULL,
  PRIMARY KEY (source, query)
);
"""

_NORMALISE_RE = re.compile(r"[^a-z0-9]+")


def normalise_query(text: str) -> str:
    """Canonical cache key: case, punctuation and spacing carry no meaning here."""
    return _NORMALISE_RE.sub(" ", (text or "").lower()).strip()


def default_cache_path(project_dir: Path | str | None = None) -> Path:
    """Cache beside the project's notes, so a project carries its own history."""
    if project_dir is None:
        return Path.cwd() / "notes" / DEFAULT_CACHE_NAME
    return Path(project_dir) / "notes" / DEFAULT_CACHE_NAME


def connect(cache_path: Path | str) -> sqlite3.Connection:
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


class CitationCache:
    """Read-through cache for bibliographic lookups.

    Usage is deliberately dumb: `get` returns a payload or None, `put` stores
    one. The caller decides what a payload means.
    """

    def __init__(self, cache_path: Path | str | None = None, *, enabled: bool = True):
        self.enabled = enabled
        self.path = Path(cache_path) if cache_path else None
        self._conn: sqlite3.Connection | None = None

    def _connection(self) -> sqlite3.Connection | None:
        if not self.enabled or self.path is None:
            return None
        if self._conn is None:
            try:
                self._conn = connect(self.path)
            except sqlite3.Error:
                # A broken cache must never break a run.
                self.enabled = False
                return None
        return self._conn

    def get(self, source: str, query: str, *, max_age_s: float | None = None):
        conn = self._connection()
        if conn is None:
            return None
        row = conn.execute(
            "SELECT payload, epoch FROM lookups WHERE source = ? AND query = ?;",
            (source, normalise_query(query)),
        ).fetchone()
        if row is None:
            return None
        if max_age_s is not None and (time.time() - float(row["epoch"])) > max_age_s:
            return None
        try:
            return json.loads(row["payload"])
        except json.JSONDecodeError:
            return None

    def put(self, source: str, query: str, payload) -> None:
        conn = self._connection()
        if conn is None:
            return
        try:
            conn.execute(
                """
                INSERT INTO lookups(source, query, payload, fetched_at, epoch)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(source, query) DO UPDATE SET
                  payload=excluded.payload,
                  fetched_at=excluded.fetched_at,
                  epoch=excluded.epoch;
                """,
                (source, normalise_query(query), json.dumps(payload), now_iso(), time.time()),
            )
            conn.commit()
        except sqlite3.Error:
            self.enabled = False

    def stats(self) -> dict:
        conn = self._connection()
        if conn is None:
            return {"entries": 0, "sources": {}}
        rows = conn.execute("SELECT source, COUNT(*) AS n FROM lookups GROUP BY source;").fetchall()
        total = conn.execute("SELECT COUNT(*) AS n FROM lookups;").fetchone()["n"]
        return {"entries": int(total), "sources": {r["source"]: int(r["n"]) for r in rows}}

    def prune(self, max_age_s: float) -> int:
        conn = self._connection()
        if conn is None:
            return 0
        cutoff = time.time() - max_age_s
        cur = conn.execute("DELETE FROM lookups WHERE epoch < ?;", (cutoff,))
        conn.commit()
        return int(cur.rowcount or 0)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class LocalCorpus:
    """A JSON Lines bibliographic index consulted before any network call.

    Each line is one record. Recognised fields: title (required), doi, arxiv_id,
    bibtex. Anything else is carried through untouched, so an S2ORC or DBLP
    export can be used as-is.
    """

    def __init__(self, path: Path | str | None):
        self.path = Path(path) if path else None
        self._by_title: dict[str, dict] = {}
        self._by_doi: dict[str, dict] = {}
        self._by_arxiv: dict[str, dict] = {}
        self.records = 0
        self.malformed = 0
        if self.path is not None and self.path.is_file():
            self._load()

    def _load(self) -> None:
        assert self.path is not None
        with self.path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    self.malformed += 1
                    continue
                if not isinstance(record, dict) or not record.get("title"):
                    self.malformed += 1
                    continue
                self.records += 1
                self._by_title.setdefault(normalise_query(record["title"]), record)
                if record.get("doi"):
                    self._by_doi.setdefault(normalise_query(record["doi"]), record)
                if record.get("arxiv_id"):
                    self._by_arxiv.setdefault(normalise_query(record["arxiv_id"]), record)

    @property
    def available(self) -> bool:
        return self.records > 0

    def by_title(self, title: str) -> dict | None:
        return self._by_title.get(normalise_query(title))

    def by_doi(self, doi: str) -> dict | None:
        return self._by_doi.get(normalise_query(doi))

    def by_arxiv_id(self, arxiv_id: str) -> dict | None:
        return self._by_arxiv.get(normalise_query(arxiv_id))


def add_cache_arguments(parser: argparse.ArgumentParser) -> None:
    """Standard cache/offline flags, so every citation tool spells them the same."""
    parser.add_argument(
        "--cache",
        default=None,
        help="SQLite cache of bibliographic lookups (default: notes/citation-cache.sqlite3).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not read or write the lookup cache.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Never call the network: answer from the cache and --corpus only.",
    )
    parser.add_argument(
        "--corpus",
        default=None,
        help="JSON Lines bibliographic index consulted before the network (title/doi/arxiv_id/bibtex).",
    )


def cache_from_args(args: argparse.Namespace, project_dir: Path | str | None = None) -> CitationCache:
    path = Path(args.cache) if getattr(args, "cache", None) else default_cache_path(project_dir)
    return CitationCache(path, enabled=not getattr(args, "no_cache", False))


def corpus_from_args(args: argparse.Namespace) -> LocalCorpus:
    return LocalCorpus(getattr(args, "corpus", None))


def _cmd_stats(args: argparse.Namespace) -> int:
    cache = CitationCache(args.cache or default_cache_path())
    stats = cache.stats()
    print(f"citation_cache 2026-09-05-v1: {stats['entries']} cached lookup(s)")
    for source, count in sorted(stats["sources"].items()):
        print(f"  {source}: {count}")
    cache.close()
    return 0


def _cmd_prune(args: argparse.Namespace) -> int:
    cache = CitationCache(args.cache or default_cache_path())
    removed = cache.prune(args.max_age_days * 86400.0)
    print(f"citation_cache 2026-09-05-v1: pruned {removed} entr(ies) older than {args.max_age_days} day(s)")
    cache.close()
    return 0


def _cmd_corpus_check(args: argparse.Namespace) -> int:
    corpus = LocalCorpus(args.corpus)
    if corpus.path is None or not corpus.path.is_file():
        print(f"error: corpus not found: {args.corpus}", file=sys.stderr)
        return 1
    print(
        f"citation_cache 2026-09-05-v1: {corpus.records} usable record(s), "
        f"{corpus.malformed} skipped"
    )
    return 0 if corpus.records else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the bibliographic lookup cache.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_stats = sub.add_parser("stats", help="Show cache size by source.")
    p_stats.add_argument("--cache", default=None)
    p_stats.set_defaults(fn=_cmd_stats)

    p_prune = sub.add_parser("prune", help="Delete entries older than a cutoff.")
    p_prune.add_argument("--cache", default=None)
    p_prune.add_argument("--max-age-days", type=float, default=90.0)
    p_prune.set_defaults(fn=_cmd_prune)

    p_corpus = sub.add_parser("corpus-check", help="Validate a JSON Lines corpus file.")
    p_corpus.add_argument("--corpus", required=True)
    p_corpus.set_defaults(fn=_cmd_corpus_check)

    args = parser.parse_args()
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
