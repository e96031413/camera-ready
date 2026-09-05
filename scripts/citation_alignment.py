#!/usr/bin/env python3
"""Citation alignment: does the sentence say what the cited work says? 2026-09-05-v1.

Provenance and alignment are different guarantees. `fetch_bibtex.py` and
`arxiv_registry.py` guarantee that a reference exists, because a service
returned it. Nothing guaranteed that the sentence around the citation describes
that work rather than a neighbouring one, and a misattributed citation is a
real reference used as a false witness.

This tool pairs every citation occurrence with the abstract of the work it
points at, scores the overlap, and ranks the weakest pairs for a person to read.
Sources for the abstract, in order: the project's arXiv registry
(notes/arxiv-registry.sqlite3), the shared lookup cache, then the arXiv API.

The score is a TF-IDF cosine between the citing sentence (plus its paragraph as
context) and the cited title and abstract. It is a triage signal, not a verdict:
a low score means "read this pairing", never "this citation is wrong". The tool
is advisory by default and exits non-zero only with --strict.

Usage:
  python scripts/citation_alignment.py --project-dir <paper_dir>
  python scripts/citation_alignment.py --project-dir <paper_dir> --offline
  python scripts/citation_alignment.py --project-dir <paper_dir> --strict --min-score 0.05
"""

from __future__ import annotations

import argparse
import math
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from citation_cache import (
    CitationCache,
    LocalCorpus,
    add_cache_arguments,
    cache_from_args,
    corpus_from_args,
)
from claim_registry import scan_prose_lines
from paper_utils import now_iso

BANNER = "citation_alignment 2026-09-05-v1"

_CITE_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}")
_BIB_ENTRY_RE = re.compile(r"@\w+\{([^,]+),(.*?)(?=\n@|\Z)", re.DOTALL)
_FIELD_RE = r"{field}\s*=\s*\{{(.*?)\}},?\s*\n"
_WORD_RE = re.compile(r"[a-z]{4,}")
_WHITESPACE_RE = re.compile(r"\s+")

_STOP_WORDS = frozenset(
    """that this with from have been were which their these those also than they will each
    more such when into over only very about some most other does what used using based
    between under where before after through while both same well then many much even here
    there would could should being given shown proposed paper section figure table method
    results result approach model models work works study studies show shows""".split()
)


@dataclass
class Occurrence:
    key: str
    line: int
    sentence: str
    context: str


@dataclass
class Alignment:
    key: str
    line: int
    score: float
    verdict: str
    sentence: str
    reason: str


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def _tokens(text: str) -> dict[str, int]:
    plain = _CITE_RE.sub(" ", text)
    plain = re.sub(r"\\[a-zA-Z]+", " ", plain)
    plain = plain.replace("{", " ").replace("}", " ").replace("~", " ").lower()
    counts: dict[str, int] = {}
    for word in _WORD_RE.findall(plain):
        if word in _STOP_WORDS:
            continue
        counts[word] = counts.get(word, 0) + 1
    return counts


def cosine(a: dict[str, int], b: dict[str, int], idf: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    va = {t: c * idf.get(t, 1.0) for t, c in a.items()}
    vb = {t: c * idf.get(t, 1.0) for t, c in b.items()}
    na = math.sqrt(sum(v * v for v in va.values()))
    nb = math.sqrt(sum(v * v for v in vb.values()))
    if na == 0 or nb == 0:
        return 0.0
    return sum(va[t] * vb[t] for t in set(va) & set(vb)) / (na * nb)


def build_idf(documents: list[dict[str, int]]) -> dict[str, float]:
    total = len(documents)
    if total == 0:
        return {}
    freq: dict[str, int] = {}
    for doc in documents:
        for term in doc:
            freq[term] = freq.get(term, 0) + 1
    return {term: math.log((total + 1) / (n + 1)) + 1.0 for term, n in freq.items()}


def split_sentences(text: str) -> list[str]:
    flat = _WHITESPACE_RE.sub(" ", text).strip()
    if not flat:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", flat) if s.strip()]


def find_occurrences(tex_text: str) -> list[Occurrence]:
    """Every citation occurrence, with the sentence and paragraph around it.

    The scan runs over line-preserving prose, so the reported line is the line in
    main.tex where the paragraph starts.
    """
    prose_lines = scan_prose_lines(tex_text)
    occurrences: list[Occurrence] = []
    buffer: list[str] = []
    start_line = 0

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        paragraph = "\n".join(buffer)
        buffer = []
        if "\\cite" not in paragraph:
            return
        context = _WHITESPACE_RE.sub(" ", paragraph).strip()
        for sentence in split_sentences(paragraph):
            for match in _CITE_RE.finditer(sentence):
                for raw in match.group(1).split(","):
                    key = raw.strip()
                    if key:
                        occurrences.append(
                            Occurrence(key=key, line=start_line, sentence=sentence, context=context)
                        )

    for index, line in enumerate(prose_lines, start=1):
        if not line.strip():
            flush()
            continue
        if not buffer:
            start_line = index
        buffer.append(line)
    flush()
    return occurrences


def parse_bib(bib_text: str) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for match in _BIB_ENTRY_RE.finditer(bib_text):
        key = match.group(1).strip()
        body = match.group(2)
        entry: dict = {}
        for field in ("title", "eprint", "doi", "abstract", "author", "year"):
            found = re.search(_FIELD_RE.format(field=field), body, re.IGNORECASE | re.DOTALL)
            if found:
                entry[field] = _WHITESPACE_RE.sub(" ", found.group(1)).strip()
        entries[key] = entry
    return entries


def abstract_from_registry(db_path: Path, arxiv_id: str) -> str | None:
    if not db_path.is_file() or not arxiv_id:
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT title, summary FROM works WHERE arxiv_id = ?;", (arxiv_id,)
        ).fetchone()
        conn.close()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    return " ".join(part for part in (row["title"], row["summary"]) if part)


def abstract_from_arxiv(arxiv_id: str, timeout_s: float) -> str | None:
    url = (
        "https://export.arxiv.org/api/query?id_list="
        f"{urllib.parse.quote(arxiv_id)}&max_results=1"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "camera-ready/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None
    entry = re.search(r"<entry>(.*?)</entry>", body, re.DOTALL)
    if entry is None:
        return None
    title = re.search(r"<title>(.*?)</title>", entry.group(1), re.DOTALL)
    summary = re.search(r"<summary>(.*?)</summary>", entry.group(1), re.DOTALL)
    parts = [
        _WHITESPACE_RE.sub(" ", m.group(1)).strip() for m in (title, summary) if m is not None
    ]
    return " ".join(parts) if parts else None


def resolve_abstract(
    key: str,
    entry: dict,
    *,
    registry: Path,
    cache: CitationCache | None,
    corpus: LocalCorpus | None,
    offline: bool,
    timeout_s: float,
    sleep_s: float,
) -> tuple[str | None, str]:
    """Abstract text for one reference, and where it came from."""
    arxiv_id = (entry.get("eprint") or "").strip()

    if entry.get("abstract"):
        return f"{entry.get('title', '')} {entry['abstract']}", "bib"

    if corpus is not None and corpus.available:
        record = None
        if arxiv_id:
            record = corpus.by_arxiv_id(arxiv_id)
        if record is None and entry.get("doi"):
            record = corpus.by_doi(entry["doi"])
        if record is None and entry.get("title"):
            record = corpus.by_title(entry["title"])
        if record and (record.get("abstract") or record.get("title")):
            return f"{record.get('title', '')} {record.get('abstract', '')}", "corpus"

    if arxiv_id:
        text = abstract_from_registry(registry, arxiv_id)
        if text:
            return text, "registry"

    if cache is not None:
        cached = cache.get("abstract", arxiv_id or entry.get("title", key))
        if cached:
            return str(cached), "cache"

    if offline or not arxiv_id:
        # Title alone is thin evidence, but it is evidence the bibliography holds.
        return (entry.get("title") or None), "title-only"

    text = abstract_from_arxiv(arxiv_id, timeout_s)
    if sleep_s:
        time.sleep(sleep_s)
    if text:
        if cache is not None:
            cache.put("abstract", arxiv_id, text)
        return text, "arxiv"
    return (entry.get("title") or None), "title-only"


def classify(score: float, min_score: float) -> str:
    if score >= min_score * 3:
        return "ALIGNED"
    if score >= min_score:
        return "WEAK"
    return "REVIEW"


def write_report(path: Path, alignments: list[Alignment], *, min_score: float, sources: dict) -> None:
    review = [a for a in alignments if a.verdict == "REVIEW"]
    weak = [a for a in alignments if a.verdict == "WEAK"]
    lines = [
        "# Citation Alignment Report",
        "",
        f"- Created at: {now_iso()}",
        f"- Citation occurrences scored: {len(alignments)}",
        f"- Threshold: {min_score:.3f}",
        f"- ALIGNED: {len(alignments) - len(review) - len(weak)}  WEAK: {len(weak)}  REVIEW: {len(review)}",
        "- Abstract sources: " + ", ".join(f"{k}={v}" for k, v in sorted(sources.items())),
        "",
        "The score is a TF-IDF cosine between the citing sentence, with its",
        "paragraph as context, and the cited work's title and abstract. It ranks",
        "pairings for reading. It does not decide whether a citation is correct:",
        "a paper cited for a method it never names scores low and is right, and a",
        "paper cited for the wrong claim in shared vocabulary scores high and is",
        "wrong. Read the flagged pairs against the source.",
        "",
        "## Lowest-scoring pairings",
        "",
        "| Score | Key | Line | Citing sentence |",
        "|---|---|---|---|",
    ]
    for item in sorted(alignments, key=lambda a: a.score)[:25]:
        sentence = item.sentence.replace("|", "\\|")
        if len(sentence) > 140:
            sentence = sentence[:137] + "..."
        lines.append(f"| {item.score:.3f} | `{item.key}` | {item.line} | {sentence} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score how well each citing sentence matches the work it cites."
    )
    parser.add_argument("--project-dir", default=".", help="Paper project directory (default: .).")
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.04,
        help="Below this cosine a pairing is flagged for review (default: 0.04).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any pairing falls below the threshold.",
    )
    parser.add_argument("--timeout-s", type=float, default=20.0, help="Network timeout (default: 20).")
    parser.add_argument("--sleep-s", type=float, default=3.0, help="Pause between arXiv calls (default: 3).")
    add_cache_arguments(parser)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        return fail("project dir not found")

    main_tex = project_dir / "main.tex"
    ref_bib = project_dir / "ref.bib"
    if not main_tex.is_file():
        return fail("main.tex not found in project dir")
    if not ref_bib.is_file():
        return fail("ref.bib not found in project dir")

    occurrences = find_occurrences(main_tex.read_text(encoding="utf-8", errors="replace"))
    entries = parse_bib(ref_bib.read_text(encoding="utf-8", errors="replace"))
    if not occurrences:
        print(f"{BANNER}: no citation occurrences found in prose.")
        return 0

    cache = cache_from_args(args, project_dir)
    corpus = corpus_from_args(args)
    registry = project_dir / "notes" / "arxiv-registry.sqlite3"

    abstracts: dict[str, str | None] = {}
    sources: dict[str, int] = {}
    for key in sorted({o.key for o in occurrences}):
        entry = entries.get(key)
        if entry is None:
            abstracts[key] = None
            sources["missing-from-bib"] = sources.get("missing-from-bib", 0) + 1
            continue
        text, source = resolve_abstract(
            key,
            entry,
            registry=registry,
            cache=cache,
            corpus=corpus,
            offline=args.offline,
            timeout_s=args.timeout_s,
            sleep_s=args.sleep_s,
        )
        abstracts[key] = text
        sources[source] = sources.get(source, 0) + 1
    cache.close()

    documents = [_tokens(o.context) for o in occurrences]
    documents += [_tokens(t) for t in abstracts.values() if t]
    idf = build_idf(documents)

    alignments: list[Alignment] = []
    for occurrence in occurrences:
        reference_text = abstracts.get(occurrence.key)
        if not reference_text:
            alignments.append(
                Alignment(
                    key=occurrence.key,
                    line=occurrence.line,
                    score=0.0,
                    verdict="REVIEW",
                    sentence=occurrence.sentence,
                    reason="no abstract or title available for this key",
                )
            )
            continue
        sentence_tokens = _tokens(occurrence.sentence)
        context_tokens = _tokens(occurrence.context)
        reference_tokens = _tokens(reference_text)
        score = max(
            cosine(sentence_tokens, reference_tokens, idf),
            cosine(context_tokens, reference_tokens, idf) * 0.8,
        )
        alignments.append(
            Alignment(
                key=occurrence.key,
                line=occurrence.line,
                score=score,
                verdict=classify(score, args.min_score),
                sentence=occurrence.sentence,
                reason="",
            )
        )

    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    write_report(notes_dir / "citation-alignment.md", alignments, min_score=args.min_score, sources=sources)

    review = [a for a in alignments if a.verdict == "REVIEW"]
    weak = [a for a in alignments if a.verdict == "WEAK"]
    print(
        f"{BANNER}: {len(alignments)} occurrence(s); "
        f"{len(alignments) - len(review) - len(weak)} aligned, {len(weak)} weak, {len(review)} to review"
    )
    for item in sorted(review, key=lambda a: a.score)[:10]:
        print(f"  [{item.score:.3f}] {item.key} (line ~{item.line})")
    print("Report: notes/citation-alignment.md")
    print("A low score marks a pairing to read, not a citation to delete.")

    if args.strict and review:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
