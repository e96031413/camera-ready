#!/usr/bin/env python3
"""Check a venue config against the venue's own author guide. 2026-09-05-v1.

Venue rules change every year: page limits move, style files are renamed, a
review model flips. A stale `assets/venues/<venue>.yaml` is worse than no
config, because `format_gate.py` then enforces last year's rules confidently.

This tool fetches the venue's author guide, extracts the rules a page states in
prose, and diffs them against the stored config. It never edits the config: it
writes a proposal for a person to apply, because a scraped page is evidence, not
authority, and a marketing sentence can look exactly like a rule.

Exit codes: 0 config agrees with the page (or nothing extractable); 1 a
difference worth a human decision; 2 usage error.

Usage:
  python scripts/venue_rules_sync.py --venue neurips
  python scripts/venue_rules_sync.py --venue icml --write-proposal --out-dir notes/proposals
  python scripts/venue_rules_sync.py --venue acl --from-file saved-guide.html   # offline
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import now_iso
from venue_config import VenueConfigError, list_venues, load_venue, venues_dir

BANNER = "venue_rules_sync 2026-09-05-v1"

_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

_PAGE_LIMIT_RES = (
    re.compile(r"(?:limited to|maximum of|up to|at most)\s+(\d{1,2})\s+pages", re.IGNORECASE),
    re.compile(r"(\d{1,2})\s*(?:-|\s)?page\s+limit", re.IGNORECASE),
    re.compile(r"(\d{1,2})\s+pages?\s+of\s+(?:main\s+)?(?:text|content|body)", re.IGNORECASE),
)
_FONT_RE = re.compile(r"\b(9|10|11|12)\s*(?:pt|point)\b", re.IGNORECASE)
_STYLE_FILE_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_\-]*\d{4}[A-Za-z0-9_\-]*\.sty)\b")
_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_DOUBLE_BLIND_RE = re.compile(r"double[-\s]?blind", re.IGNORECASE)
_SINGLE_BLIND_RE = re.compile(r"single[-\s]?blind", re.IGNORECASE)
_PAPER_SIZE_RE = re.compile(r"\b(letter|a4)\b", re.IGNORECASE)


@dataclass
class Difference:
    field: str
    stored: object
    observed: object
    evidence: str


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def html_to_text(raw: str) -> str:
    text = _TAG_RE.sub(" ", raw)
    text = _ANY_TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", html.unescape(text)).strip()


def fetch_page(url: str, timeout_s: float) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "camera-ready/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        print(f"  warning: could not fetch {url[:70]}: {exc}", file=sys.stderr)
        return None


def _context(text: str, match: re.Match, width: int = 90) -> str:
    start = max(0, match.start() - width // 2)
    end = min(len(text), match.end() + width // 2)
    return text[start:end].strip()


def extract_rules(text: str) -> dict:
    """Rules a page states in prose. Absent keys mean "the page did not say"."""
    observed: dict = {}
    evidence: dict[str, str] = {}

    for pattern in _PAGE_LIMIT_RES:
        match = pattern.search(text)
        if match:
            observed["page_limit_main"] = int(match.group(1))
            evidence["page_limit_main"] = _context(text, match)
            break

    match = _FONT_RE.search(text)
    if match:
        observed["font_size"] = f"{match.group(1)}pt"
        evidence["font_size"] = _context(text, match)

    match = _STYLE_FILE_RE.search(text)
    if match:
        observed["style_file"] = match.group(1)
        evidence["style_file"] = _context(text, match)

    match = _PAPER_SIZE_RE.search(text)
    if match:
        observed["paper_size"] = match.group(1).lower()
        evidence["paper_size"] = _context(text, match)

    if _DOUBLE_BLIND_RE.search(text):
        match = _DOUBLE_BLIND_RE.search(text)
        observed["review_model"] = "double-blind"
        observed["anonymous"] = True
        evidence["review_model"] = _context(text, match)
    elif _SINGLE_BLIND_RE.search(text):
        match = _SINGLE_BLIND_RE.search(text)
        observed["review_model"] = "single-blind"
        observed["anonymous"] = False
        evidence["review_model"] = _context(text, match)

    years = [int(y) for y in _YEAR_RE.findall(text)]
    if years:
        observed["reference_year"] = max(years)
        evidence["reference_year"] = f"latest year mentioned on the page: {max(years)}"

    observed["_evidence"] = evidence
    return observed


COMPARED_FIELDS = (
    "page_limit_main",
    "font_size",
    "paper_size",
    "style_file",
    "review_model",
    "anonymous",
    "reference_year",
)


def diff_rules(stored: dict, observed: dict) -> list[Difference]:
    evidence = observed.get("_evidence", {})
    differences: list[Difference] = []
    for field in COMPARED_FIELDS:
        if field not in observed:
            continue
        if field not in stored:
            continue
        if str(stored[field]).strip().lower() == str(observed[field]).strip().lower():
            continue
        differences.append(
            Difference(
                field=field,
                stored=stored[field],
                observed=observed[field],
                evidence=evidence.get(field, ""),
            )
        )
    return differences


def render_proposal(stored_text: str, differences: list[Difference]) -> str:
    """The stored YAML with differing scalars replaced, comments preserved."""
    lines = stored_text.splitlines()
    changes = {d.field: d.observed for d in differences}
    out: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if ":" in stripped and not stripped.startswith("#") and not stripped.startswith("- "):
            key = stripped.split(":", 1)[0].strip()
            if key in changes:
                value = changes[key]
                rendered = "true" if value is True else "false" if value is False else value
                out.append(f"{key}: {rendered}  # proposed by {BANNER}")
                continue
        out.append(line)
    return "\n".join(out) + "\n"


def write_report(path: Path, venue: str, url: str, differences: list[Difference], observed: dict) -> None:
    lines = [
        f"# Venue Rule Check: {venue}",
        "",
        f"- Created at: {now_iso()}",
        f"- Source page: {url}",
        f"- Fields the page stated: {', '.join(k for k in observed if k != '_evidence') or 'none'}",
        f"- Differences: {len(differences)}",
        "",
    ]
    if differences:
        lines += ["| Field | Stored | On the page | Evidence |", "|---|---|---|---|"]
        for d in differences:
            evidence = d.evidence.replace("|", "\\|")
            if len(evidence) > 120:
                evidence = evidence[:117] + "..."
            lines.append(f"| `{d.field}` | {d.stored} | {d.observed} | {evidence} |")
    else:
        lines.append("The stored config agrees with everything the page states.")
    lines += [
        "",
        "A scraped page is evidence, not authority. Read the guide before you",
        "apply a proposal: prose that looks like a rule may describe a workshop,",
        "a previous edition, or an exception.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diff a venue config against the venue's published author guide."
    )
    parser.add_argument("--venue", required=True, help=f"Venue slug ({', '.join(list_venues())}).")
    parser.add_argument(
        "--from-file",
        default=None,
        help="Read the guide from a local HTML/text file instead of the network.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory for the report and proposal (default: ./notes).",
    )
    parser.add_argument(
        "--write-proposal",
        action="store_true",
        help="Write a proposed YAML beside the report. It is never applied automatically.",
    )
    parser.add_argument("--timeout-s", type=float, default=20.0, help="Network timeout (default: 20).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    slug = args.venue.strip().lower()
    try:
        stored = load_venue(slug)
    except VenueConfigError as exc:
        return fail(str(exc))

    url = str(stored.get("author_guide_url") or stored.get("style_file_url") or "")
    if args.from_file:
        source = Path(args.from_file)
        if not source.is_file():
            return fail(f"file not found: {source}")
        raw = source.read_text(encoding="utf-8", errors="replace")
        url = f"file://{source.name}"
    else:
        if not url:
            return fail(f"{slug}.yaml has no author_guide_url to check against")
        raw = fetch_page(url, args.timeout_s) or ""

    if not raw.strip():
        print(f"{BANNER}: no page content retrieved; nothing to compare.")
        return 0

    text = html_to_text(raw)
    observed = extract_rules(text)
    differences = diff_rules(stored, observed)

    out_dir = Path(args.out_dir) if args.out_dir else Path("notes")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"venue-rule-check-{slug}.md"
    write_report(report_path, slug, url, differences, observed)

    if differences:
        for d in differences:
            print(f"  [DIFF] {d.field}: stored={d.stored!r} page={d.observed!r}")
    else:
        print(f"{BANNER}: {slug} config agrees with the page.")

    if args.write_proposal and differences:
        stored_text = (venues_dir() / f"{slug}.yaml").read_text(encoding="utf-8")
        proposal_path = out_dir / f"{slug}.proposed.yaml"
        proposal_path.write_text(render_proposal(stored_text, differences), encoding="utf-8")
        print(f"Proposal: {proposal_path.as_posix()} (review it, then copy it over the config yourself)")

    print(f"Report: {report_path.as_posix()}")
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main())
