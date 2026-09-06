#!/usr/bin/env python3
"""4-layer citation verification to detect hallucinated references.

Verification chain:
  Layer 1: arXiv ID lookup (direct API if eprint field present)
  Layer 2: DOI resolution (CrossRef/DataCite HTTP HEAD)
  Layer 3: Title search (Semantic Scholar + arXiv by title, >0.80 similarity)
  Layer 4: LLM relevance scoring (optional, via external reviewer)

Classifications:
  VERIFIED: Found + metadata matches (≥0.80 similarity)
  SUSPICIOUS: Found but metadata diverges (0.50-0.80 similarity)
  HALLUCINATED: Not found or similarity < 0.50
  SKIPPED: No title or all APIs unreachable

Concept adapted from AutoResearchClaw (aiming-lab/AutoResearchClaw).

Usage:
  python3 scripts/verify_citations.py --bib-file ref.bib [--output notes/citation-verification.md]
  python3 scripts/verify_citations.py --bib-file ref.bib --remove-hallucinated --out-bib ref.clean.bib
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from citation_cache import (
    CitationCache,
    LocalCorpus,
    add_cache_arguments,
    cache_from_args,
    corpus_from_args,
)
from paper_utils import now_iso


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _http_get(url: str, accept: str = "application/json", timeout: int = 10) -> str | None:
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "camera-ready/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None


def _title_similarity(a: str, b: str) -> float:
    """Fuzzy title match (case-insensitive, stripped)."""
    a_clean = re.sub(r"[^a-z0-9\s]", "", a.lower()).strip()
    b_clean = re.sub(r"[^a-z0-9\s]", "", b.lower()).strip()
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def parse_bib_entries(bib_text: str) -> list[dict]:
    """Parse .bib file into list of entries with key, title, author, doi, eprint."""
    entries: list[dict] = []
    # Split on @ entries
    for match in re.finditer(
        r"@\w+\{([^,]+),\s*(.*?)(?=\n\s*@|\Z)", bib_text, re.DOTALL
    ):
        key = match.group(1).strip()
        body = match.group(2)
        entry: dict = {"key": key, "raw": match.group(0)}

        for field in ["title", "author", "doi", "eprint", "year", "journal", "booktitle"]:
            field_match = re.search(
                rf"{field}\s*=\s*\{{([^}}]*)\}}", body, re.IGNORECASE
            )
            if field_match:
                entry[field] = field_match.group(1).strip()

        entries.append(entry)

    return entries


# --- Layer 1: arXiv ID lookup ---
def verify_arxiv(eprint: str) -> dict:
    """Verify via arXiv API."""
    if not eprint:
        return {"layer": 1, "status": "skipped", "detail": "no eprint"}

    clean_id = re.sub(r"^arxiv:", "", eprint, flags=re.IGNORECASE).strip()
    url = f"http://export.arxiv.org/api/query?id_list={clean_id}&max_results=1"
    body = _http_get(url)
    if not body:
        return {"layer": 1, "status": "api_error", "detail": "arXiv API unreachable"}

    # 2026-09-05-v2: read the title inside <entry>, not the feed <title>. The Atom
    # feed opens with "arXiv Query: ...", so matching the first <title> compared the
    # entry against the query string and drove every real arXiv paper to layer 3.
    entry_match = re.search(r"<entry>(.*?)</entry>", body, re.DOTALL)
    if entry_match:
        title_match = re.search(r"<title>(.*?)</title>", entry_match.group(1), re.DOTALL)
        if title_match:
            title = re.sub(r"\s+", " ", title_match.group(1)).strip()
            return {"layer": 1, "status": "found", "title": title}

    return {"layer": 1, "status": "not_found", "detail": f"arXiv ID {clean_id} not found"}


# --- Layer 2: DOI resolution ---
def verify_doi(doi: str) -> dict:
    """Verify via DOI resolution (CrossRef/DataCite)."""
    if not doi:
        return {"layer": 2, "status": "skipped", "detail": "no doi"}

    url = f"https://doi.org/{doi}"
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "camera-ready/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status < 400:
                return {"layer": 2, "status": "found", "detail": f"DOI resolves (HTTP {resp.status})"}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        if hasattr(e, "code") and e.code == 302:
            return {"layer": 2, "status": "found", "detail": "DOI redirects (valid)"}
        return {"layer": 2, "status": "api_error", "detail": str(e)[:80]}

    return {"layer": 2, "status": "not_found", "detail": "DOI does not resolve"}


# --- Layer 3: Title search ---
def verify_title_semantic_scholar(title: str) -> dict:
    """Search Semantic Scholar by title."""
    if not title:
        return {"layer": 3, "status": "skipped", "detail": "no title"}

    encoded = urllib.parse.quote(title[:200])
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={encoded}&limit=3&fields=title"
    body = _http_get(url)
    if not body:
        return {"layer": 3, "status": "api_error", "detail": "Semantic Scholar unreachable"}

    try:
        import json
        data = json.loads(body)
        papers = data.get("data", [])
        for paper in papers:
            found_title = paper.get("title", "")
            sim = _title_similarity(title, found_title)
            if sim >= 0.80:
                return {"layer": 3, "status": "found", "similarity": round(sim, 3), "found_title": found_title}
            elif sim >= 0.50:
                return {"layer": 3, "status": "suspicious", "similarity": round(sim, 3), "found_title": found_title}
    except Exception:
        pass

    return {"layer": 3, "status": "not_found", "detail": "no matching title in Semantic Scholar"}


def classify_entry(
    entry: dict,
    *,
    cache: CitationCache | None = None,
    corpus: LocalCorpus | None = None,
    offline: bool = False,
) -> tuple[str, list[dict]]:
    """Run 4-layer verification and return (classification, layer_results).

    2026-09-05-v2: a local corpus answers first, then a verdict this cache
    recorded from a live source in an earlier run. Both are evidence that a
    source once returned this work; neither can turn an unknown entry into a
    verified one. Under --offline with no local evidence the entry is SKIPPED,
    never HALLUCINATED: a network nobody asked is not a source that denied it.
    """
    results: list[dict] = []
    identity = entry.get("eprint") or entry.get("doi") or entry.get("title") or entry["key"]

    # Explicit check for unverified placeholders:
    # A placeholder emitted on unresolved lookup cannot be considered verified or merely skipped.
    is_placeholder = (
        entry["key"].startswith("PLACEHOLDER_")
        or entry["key"].endswith("_verify")
        or "_verify" in entry["key"]
        or bool(re.search(r"note\s*=\s*\{?\s*\[VERIFY\]", entry.get("raw", ""), re.IGNORECASE))
    )
    if is_placeholder:
        results.append({"layer": 0, "status": "placeholder", "detail": "unresolved placeholder marked for manual verification"})
        return "HALLUCINATED", results

    # Layer 0a: local corpus.
    if corpus is not None and corpus.available:
        record = None
        if entry.get("eprint"):
            record = corpus.by_arxiv_id(entry["eprint"])
        if record is None and entry.get("doi"):
            record = corpus.by_doi(entry["doi"])
        if record is None and entry.get("title"):
            record = corpus.by_title(entry["title"])
        if record is not None:
            results.append({"layer": 0, "status": "found", "detail": "local corpus"})
            return "VERIFIED", results

    # Layer 0b: cached verdict.
    if cache is not None:
        cached = cache.get("verify", identity)
        if cached in ("VERIFIED", "SUSPICIOUS"):
            results.append({"layer": 0, "status": "found", "detail": "cached verdict"})
            return str(cached), results

    if offline:
        results.append({"layer": 0, "status": "skipped", "detail": "offline, no local evidence"})
        return "SKIPPED", results

    # Layer 1: arXiv
    if entry.get("eprint"):
        r1 = verify_arxiv(entry["eprint"])
        results.append(r1)
        if r1["status"] == "found":
            if entry.get("title"):
                sim = _title_similarity(entry["title"], r1.get("title", ""))
                if sim >= 0.80:
                    return "VERIFIED", results
                elif sim >= 0.50:
                    return "SUSPICIOUS", results
            else:
                return "VERIFIED", results
        time.sleep(3.0)  # arXiv asks for 1 request per 3 seconds

    # Layer 2: DOI
    if entry.get("doi"):
        r2 = verify_doi(entry["doi"])
        results.append(r2)
        if r2["status"] == "found":
            return "VERIFIED", results
        time.sleep(0.3)

    # Layer 3: Title search
    if entry.get("title"):
        r3 = verify_title_semantic_scholar(entry["title"])
        results.append(r3)
        if r3["status"] == "found":
            return "VERIFIED", results
        elif r3["status"] == "suspicious":
            return "SUSPICIOUS", results
        time.sleep(0.3)

    # No verification succeeded
    if not results or all(r["status"] in ("skipped", "api_error") for r in results):
        return "SKIPPED", results

    return "HALLUCINATED", results


def main() -> int:
    parser = argparse.ArgumentParser(description="4-layer citation verification.")
    parser.add_argument("--bib-file", required=True, help="Path to .bib file")
    parser.add_argument("--output", default=None, help="Output report path (default: notes/citation-verification.md)")
    parser.add_argument("--remove-hallucinated", action="store_true", help="Remove HALLUCINATED entries")
    parser.add_argument("--out-bib", default=None, help="Write cleaned .bib file (requires --remove-hallucinated)")
    parser.add_argument("--max-entries", type=int, default=None, help="Max entries to verify (default: 60 in advisory mode, all in strict mode)")
    parser.add_argument(
        "--strict",
        "--gate",
        dest="strict",
        action="store_true",
        help="Gate mode: verify all citations, reject placeholders/hallucinations with exit code 1",
    )
    add_cache_arguments(parser)
    args = parser.parse_args()

    bib_path = Path(args.bib_file)
    if not bib_path.exists():
        return fail(f"bib file not found: {bib_path}")

    bib_text = bib_path.read_text(encoding="utf-8", errors="replace")
    entries = parse_bib_entries(bib_text)

    if not entries:
        return fail("no BibTeX entries found")

    # In strict/gate mode, verify all citations; fail if max_entries prematurely truncates
    if args.strict and args.max_entries is not None and args.max_entries < len(entries):
        return fail(
            f"strict gate mode requires verifying all citations, but max-entries ({args.max_entries}) < total citations ({len(entries)})"
        )

    limit = args.max_entries if args.max_entries is not None else (len(entries) if args.strict else min(len(entries), 60))

    cache = cache_from_args(args, bib_path.parent)
    corpus = corpus_from_args(args)
    mode = " [offline]" if args.offline else ""
    strict_tag = " [strict/gate]" if args.strict else ""
    print(f"Verifying {min(len(entries), limit)} of {len(entries)} citations...{mode}{strict_tag}")

    results: dict[str, list] = {"VERIFIED": [], "SUSPICIOUS": [], "HALLUCINATED": [], "SKIPPED": []}
    entry_classifications: list[tuple[dict, str, list]] = []

    for i, entry in enumerate(entries[:limit]):
        title_short = entry.get("title", entry["key"])[:60]
        print(f"  [{i + 1}/{min(len(entries), limit)}] {title_short}...", end=" ")

        classification, layers = classify_entry(
            entry, cache=cache, corpus=corpus, offline=args.offline
        )
        # Record only verdicts a live source supported, so the cache cannot
        # harden a transient failure into a permanent answer.
        if classification in ("VERIFIED", "SUSPICIOUS"):
            identity = entry.get("eprint") or entry.get("doi") or entry.get("title") or entry["key"]
            cache.put("verify", identity, classification)
        results[classification].append(entry["key"])
        entry_classifications.append((entry, classification, layers))
        print(classification)

    # Summary
    total = sum(len(v) for v in results.values())
    print(f"\n--- Verification Summary ---")
    print(f"  VERIFIED:      {len(results['VERIFIED'])}")
    print(f"  SUSPICIOUS:    {len(results['SUSPICIOUS'])}")
    print(f"  HALLUCINATED:  {len(results['HALLUCINATED'])}")
    print(f"  SKIPPED:       {len(results['SKIPPED'])}")
    if total > 0:
        integrity = len(results["VERIFIED"]) / max(1, total - len(results["SKIPPED"]))
        print(f"  Integrity:     {integrity:.0%}")

    # Generate report
    output_path = Path(args.output) if args.output else bib_path.parent / "notes" / "citation-verification.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = [
        "# Citation Verification Report",
        "",
        f"**Source**: `{bib_path.name}`",
        f"**Verified**: {now_iso()}",
        f"**Entries checked**: {total} of {len(entries)}",
        f"**Mode**: {'Strict Gate' if args.strict else 'Advisory'}",
        "",
        "## Summary",
        "",
        f"| Status | Count |",
        f"|--------|-------|",
        f"| VERIFIED | {len(results['VERIFIED'])} |",
        f"| SUSPICIOUS | {len(results['SUSPICIOUS'])} |",
        f"| HALLUCINATED | {len(results['HALLUCINATED'])} |",
        f"| SKIPPED | {len(results['SKIPPED'])} |",
        "",
    ]

    if results["HALLUCINATED"]:
        report.extend([
            "## Hallucinated Citations (REMOVE)",
            "",
            "| Key | Title |",
            "|-----|-------|",
        ])
        for entry, cls, _ in entry_classifications:
            if cls == "HALLUCINATED":
                report.append(f"| `{entry['key']}` | {entry.get('title', 'N/A')[:80]} |")
        report.append("")

    if results["SUSPICIOUS"]:
        report.extend([
            "## Suspicious Citations (VERIFY MANUALLY)",
            "",
            "| Key | Title | Issue |",
            "|-----|-------|-------|",
        ])
        for entry, cls, layers in entry_classifications:
            if cls == "SUSPICIOUS":
                issue = next((l.get("detail", f"similarity={l.get('similarity', '?')}") for l in layers if l["status"] == "suspicious"), "metadata divergence")
                report.append(f"| `{entry['key']}` | {entry.get('title', 'N/A')[:60]} | {issue} |")
        report.append("")

    report.extend([
        "## Verification Protocol",
        "- Layer 1: arXiv ID lookup (direct API)",
        "- Layer 2: DOI resolution (CrossRef/DataCite)",
        "- Layer 3: Title search (Semantic Scholar, >0.80 similarity)",
        "- Layer 4: LLM relevance scoring (manual, via cross-model review)",
        "",
    ])

    output_path.write_text("\n".join(report), encoding="utf-8")
    print(f"\nReport: {output_path}")

    # Remove hallucinated entries
    if args.remove_hallucinated and args.out_bib and results["HALLUCINATED"]:
        hallu_keys = set(results["HALLUCINATED"])
        cleaned_entries = [e for e in entries if e["key"] not in hallu_keys]
        # Rebuild bib from raw entries
        cleaned_bib = "\n\n".join(e["raw"] for e in cleaned_entries)
        out_path = Path(args.out_bib)
        out_path.write_text(cleaned_bib + "\n", encoding="utf-8")
        print(f"Cleaned bib: {out_path} (removed {len(hallu_keys)} hallucinated entries)")

    if args.strict:
        if results["HALLUCINATED"]:
            return fail(f"strict gate failed: {len(results['HALLUCINATED'])} citation(s) classified as HALLUCINATED: {', '.join(results['HALLUCINATED'][:5])}")
        if total < len(entries):
            return fail(f"strict gate failed: only {total} of {len(entries)} citations were verified")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
