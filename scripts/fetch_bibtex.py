#!/usr/bin/env python3
"""Fetch verified BibTeX from DBLP and CrossRef.

Three-step fallback chain to eliminate hallucinated citations:
  1. DBLP (best quality — full venue, pages, editors)
  2. CrossRef DOI (fallback — works for arXiv preprints)
  3. Mark [VERIFY] (last resort)

Concept adapted from ARIS (Auto-claude-code-research-in-sleep).

Usage:
  python3 scripts/fetch_bibtex.py --title "Attention Is All You Need" --author "Vaswani"
  python3 scripts/fetch_bibtex.py --doi "10.48550/arXiv.1706.03762"
  python3 scripts/fetch_bibtex.py --scan-tex main.tex --out-bib ref.bib
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from citation_cache import (
    CitationCache,
    LocalCorpus,
    add_cache_arguments,
    cache_from_args,
    corpus_from_args,
)


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _http_get(url: str, accept: str = "application/json", timeout: int = 15) -> str | None:
    """Simple HTTP GET with error handling."""
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "camera-ready/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        print(f"  warning: HTTP request failed for {url[:80]}: {e}", file=sys.stderr)
        return None


def fetch_from_dblp(title: str, author: str = "") -> str | None:
    """Search DBLP by title+author and return BibTeX."""
    query = title
    if author:
        query = f"{title} {author}"
    encoded = urllib.parse.quote(query)
    url = f"https://dblp.org/search/publ/api?q={encoded}&format=json&h=3"

    body = _http_get(url)
    if not body:
        return None

    try:
        data = json.loads(body)
        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        if not hits:
            return None

        # Get the first hit's DBLP key
        info = hits[0].get("info", {})
        dblp_key = info.get("key", "")
        if not dblp_key:
            return None

        # Fetch BibTeX
        bib_url = f"https://dblp.org/rec/{dblp_key}.bib"
        bib = _http_get(bib_url, accept="text/plain")
        if bib and "@" in bib:
            return bib.strip()
    except (json.JSONDecodeError, KeyError, IndexError):
        pass

    return None


def fetch_from_crossref(doi: str) -> str | None:
    """Fetch BibTeX from CrossRef via DOI."""
    if not doi:
        return None

    # Normalize DOI
    doi = doi.strip()
    if doi.startswith("http"):
        # Extract DOI from URL
        match = re.search(r"(10\.\d{4,}/\S+)", doi)
        if match:
            doi = match.group(1)

    url = f"https://doi.org/{doi}"
    bib = _http_get(url, accept="application/x-bibtex")
    if bib and "@" in bib:
        return bib.strip()
    return None


def fetch_bibtex(
    title: str,
    author: str = "",
    doi: str = "",
    *,
    cache: CitationCache | None = None,
    corpus: LocalCorpus | None = None,
    offline: bool = False,
) -> tuple[str | None, str]:
    """Fetch BibTeX using the fallback chain.

    2026-09-05-v2: a local corpus and a lookup cache sit in front of the network,
    and the cache also answers when the network is unavailable. Neither can
    invent an entry: a miss still returns (None, "verify").

    Returns (bibtex_string, source) where source is 'corpus', 'cache', 'dblp',
    'crossref' or 'verify'.
    """
    query = title or doi

    # Step 0a: local corpus, when one was supplied.
    if corpus is not None and corpus.available:
        record = corpus.by_doi(doi) if doi else None
        if record is None and title:
            record = corpus.by_title(title)
        if record and record.get("bibtex"):
            return str(record["bibtex"]), "corpus"

    # Step 0b: an earlier successful lookup for the same query.
    if cache is not None and query:
        cached = cache.get("bibtex", query)
        if cached:
            return str(cached), "cache"

    if offline:
        return None, "verify"

    # Step A: DBLP
    bib = fetch_from_dblp(title, author)
    if bib:
        if cache is not None and query:
            cache.put("bibtex", query, bib)
        return bib, "dblp"

    # Brief pause to be polite to APIs
    time.sleep(0.3)

    # Step B: CrossRef
    if doi:
        bib = fetch_from_crossref(doi)
        if bib:
            if cache is not None and query:
                cache.put("bibtex", query, bib)
            return bib, "crossref"

    # Step B alt: Try arXiv DOI if title contains arXiv ID
    arxiv_match = re.search(r"(\d{4}\.\d{4,5})", title)
    if arxiv_match:
        arxiv_doi = f"10.48550/arXiv.{arxiv_match.group(1)}"
        bib = fetch_from_crossref(arxiv_doi)
        if bib:
            if cache is not None and query:
                cache.put("bibtex", query, bib)
            return bib, "crossref"

    # Step C: Mark [VERIFY]
    return None, "verify"


def scan_tex_citations(tex_path: Path) -> list[str]:
    """Extract citation keys from a LaTeX file."""
    if not tex_path.exists():
        return []

    text = tex_path.read_text(encoding="utf-8", errors="replace")
    # Match \citep{...}, \citet{...}, \cite{...}
    raw_keys: list[str] = []
    for match in re.finditer(r"\\cite[tp]?\{([^}]+)\}", text):
        keys = match.group(1).split(",")
        raw_keys.extend(k.strip() for k in keys if k.strip())

    return sorted(set(raw_keys))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch verified BibTeX from DBLP/CrossRef."
    )
    parser.add_argument("--title", default="", help="Paper title to search")
    parser.add_argument("--author", default="", help="First author name")
    parser.add_argument("--doi", default="", help="DOI for CrossRef lookup")
    parser.add_argument("--scan-tex", default=None, help="Scan .tex file for citation keys")
    parser.add_argument("--out-bib", default=None, help="Append found BibTeX to this .bib file")
    add_cache_arguments(parser)
    args = parser.parse_args()

    if args.scan_tex:
        # Scan mode: list citation keys
        tex_path = Path(args.scan_tex)
        keys = scan_tex_citations(tex_path)
        print(f"Found {len(keys)} unique citation key(s) in {tex_path.name}:")
        for key in keys:
            print(f"  {key}")
        return 0

    if not args.title and not args.doi:
        return fail("provide --title and/or --doi")

    cache = cache_from_args(args)
    corpus = corpus_from_args(args)
    if corpus.path is not None and not corpus.available:
        print(f"  warning: corpus has no usable records: {corpus.path.name}", file=sys.stderr)

    print(f"Searching: {args.title[:80]}" + (" [offline]" if args.offline else ""))
    bib, source = fetch_bibtex(
        args.title,
        args.author,
        args.doi,
        cache=cache,
        corpus=corpus,
        offline=args.offline,
    )
    cache.close()

    if bib:
        print(f"  Source: {source}")
        print(f"  Found BibTeX ({len(bib)} chars)")
        print()
        print(bib)

        if args.out_bib:
            out_path = Path(args.out_bib)
            with out_path.open("a", encoding="utf-8") as f:
                f.write(f"\n% Fetched from {source}\n{bib}\n")
            print(f"\nAppended to: {out_path}")
    else:
        reason = "offline and not in cache or corpus" if args.offline else "not found in DBLP or CrossRef"
        print(f"  Source: [VERIFY] — {reason}")
        print(f"  Manually verify this citation before including in paper")

        if args.out_bib:
            out_path = Path(args.out_bib)
            key = re.sub(r"\W+", "", args.title.split()[0].lower() if args.title else "unknown")
            placeholder = (
                f"\n% [VERIFY] — not found in DBLP/CrossRef, needs manual verification\n"
                f"@misc{{{key}_verify,\n"
                f"  title = {{{args.title}}},\n"
                f"  author = {{{args.author}}},\n"
                f"  note = {{[VERIFY]}},\n"
                f"}}\n"
            )
            with out_path.open("a", encoding="utf-8") as f:
                f.write(placeholder)
            print(f"\nPlaceholder appended to: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
