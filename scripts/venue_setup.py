#!/usr/bin/env python3
"""Set up a paper project for a target venue.

Writes notes/venue.md (the requirements summary the author works against) and
attempts to download the venue's official style file into the project.

Style files are NOT bundled with this repository. Several conferences forbid
redistribution, and every one of them revises its template between editions, so
a bundled copy would be both a licensing risk and a source of silent format
errors. See THIRD_PARTY_NOTICES.md.

When the download does not produce a usable file -- the URL serves an HTML
landing page, the network is unavailable, the site blocks the request -- the
script prints the official URL and exits 0 with a clear manual step. A failed
download is not a failed setup: the notes file is still written, and the author
downloads the template by hand.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

from venue_config import VenueConfigError, list_venues, load_venue

USER_AGENT = "CameraReady/0.1 (paper tooling; +https://github.com/e96031413/camera-ready)"
DOWNLOAD_TIMEOUT = 30
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024

# Extensions we are willing to save from a venue URL.
ARCHIVE_SUFFIXES = (".zip", ".tar.gz", ".tgz", ".tar")
STYLE_SUFFIXES = (".sty", ".cls", ".bst")


def looks_like_html(payload: bytes) -> bool:
    """Return True when the payload is an HTML page rather than a template file."""
    head = payload[:1024].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<head" in head[:200]


def download(url: str) -> tuple[bytes | None, str]:
    """Fetch a URL. Returns (payload, message); payload is None on failure."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
            payload = response.read(MAX_DOWNLOAD_BYTES + 1)
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code} {exc.reason}"
    except urllib.error.URLError as exc:
        return None, f"network error: {exc.reason}"
    except OSError as exc:
        return None, f"network error: {exc}"

    if len(payload) > MAX_DOWNLOAD_BYTES:
        return None, f"response exceeds {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB limit"
    if not payload:
        return None, "empty response"
    return payload, "ok"


def target_filename(url: str) -> str | None:
    """Return the filename to save a download as, or None if the URL is a web page."""
    name = url.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]
    lowered = name.lower()
    if lowered.endswith(ARCHIVE_SUFFIXES) or lowered.endswith(STYLE_SUFFIXES):
        return name
    return None


def render_notes(config: dict) -> str:
    """Render notes/venue.md from a venue configuration."""
    sections = config.get("required_sections") or []
    lines = [
        f"# Target venue: {config['display_name']} ({config['full_name']})",
        "",
        f"Config: `assets/venues/{config['_slug']}.yaml`, written against the "
        f"{config['reference_year']} edition.",
        "",
        "**Verify every number below against the official author guide before you "
        "submit.** Page limits and required sections change between editions, and a "
        "wrong page limit is a desk reject, not a review comment.",
        "",
        "## Hard constraints",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Main-text page limit | {config['page_limit_main']} |",
        f"| References / appendix | {config.get('page_limit_note', 'see author guide')} |",
        f"| Columns | {config['columns']} |",
        f"| Base font size | {config['font_size']} |",
        f"| Paper size | {config.get('paper_size', 'see author guide')} |",
        f"| Text area | {config.get('text_area', 'set by the style file')} |",
        f"| Review model | {config.get('review_model', 'see author guide')} |",
        f"| Style file | `{config['style_file']}` |",
        "",
        "## Required sections",
        "",
    ]
    if sections:
        lines.extend(f"- {section}" for section in sections)
    else:
        lines.append("- None beyond the standard structure. Check the author guide anyway.")

    lines += [
        "",
        "## Checklist",
        "",
    ]
    if config.get("checklist_required"):
        lines += [
            "This venue requires a paper checklist. Generate the worksheet with:",
            "",
            "```bash",
            f"python scripts/paper_checklist.py --project-dir <paper_dir> --venue {config['_slug']}",
            "```",
            "",
            "Fill in every `Answer:` and `Justification:` yourself, then validate with",
            "`--validate`. Before submission, replace the generated `checklist.tex`",
            "scaffold with the verbatim checklist block from the style file.",
        ]
    else:
        lines += [
            "This venue does not require a paper checklist. "
            f"`assets/checklists/{config.get('checklist_asset')}.md` is available as a "
            "self-review worksheet, but nothing is submitted to the conference.",
        ]
    if config.get("checklist_guide_url"):
        lines += ["", f"Checklist guide: {config['checklist_guide_url']}"]

    if config.get("anonymous"):
        lines += [
            "",
            "## Anonymity",
            "",
            "This venue reviews anonymously. Before submitting:",
            "",
            "```bash",
            "python scripts/anonymity_check.py --project-dir <paper_dir>",
            "```",
            "",
            "A tool pass is evidence, not proof. Read every flagged line, and check the",
            "PDF metadata and any repository link you include.",
        ]

    rejections = config.get("common_rejections") or []
    if rejections:
        lines += ["", "## Common reasons for rejection at this venue", ""]
        lines.extend(f"- {item}" for item in rejections)

    lines += [
        "",
        "## Official sources",
        "",
        f"- Author guide: {config['author_guide_url']}",
        f"- Style files: {config['style_file_url']}",
        "",
        "## Format gate",
        "",
        "```bash",
        f"python scripts/format_gate.py --project-dir <paper_dir> --venue {config['_slug']}",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write venue requirements into a paper project and fetch the official style file."
    )
    parser.add_argument("--venue", help="Venue slug, e.g. neurips, icml, iclr, acl, aaai, cvpr.")
    parser.add_argument("--project-dir", help="Paper project directory.")
    parser.add_argument(
        "--list-venues", action="store_true", help="Print the available venue slugs, then exit."
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Write notes/venue.md only; do not contact the venue website.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing style file in the project directory.",
    )
    args = parser.parse_args()

    if args.list_venues:
        for slug in list_venues():
            try:
                config = load_venue(slug)
            except VenueConfigError as exc:
                print(f"{slug:10} (invalid: {exc})")
                continue
            print(f"{slug:10} {config['display_name']:8} {config['page_limit_main']} pages, {config['columns']}-column")
        return 0

    if not args.venue or not args.project_dir:
        print("error: --venue and --project-dir are required (or use --list-venues)", file=sys.stderr)
        return 1

    try:
        config = load_venue(args.venue)
    except VenueConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"error: project dir not found: {project_dir}", file=sys.stderr)
        return 1

    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    notes_path = notes_dir / "venue.md"
    notes_path.write_text(render_notes(config), encoding="utf-8")
    print(f"Venue requirements written to: {notes_path}")

    style_url = config["style_file_url"]
    if args.no_download:
        print(f"Skipped download (--no-download). Style files: {style_url}")
        return 0

    filename = target_filename(style_url)
    if filename is None:
        print()
        print("MANUAL STEP -- the style file URL is a web page, not a direct file link.")
        print(f"  Download the {config['display_name']} template yourself from:")
        print(f"    {style_url}")
        print(f"  Then unpack it into: {project_dir}")
        print(f"  You need at least: {config['style_file']}")
        return 0

    destination = project_dir / filename
    if destination.exists() and not args.force:
        print(f"Style file already present, left untouched: {destination} (use --force to replace)")
        return 0

    payload, message = download(style_url)
    if payload is None or looks_like_html(payload):
        reason = message if payload is None else "the server returned an HTML page"
        print()
        print(f"MANUAL STEP -- automatic download failed ({reason}).")
        print(f"  Download the {config['display_name']} template yourself from:")
        print(f"    {style_url}")
        print(f"  Then unpack it into: {project_dir}")
        print(f"  You need at least: {config['style_file']}")
        return 0

    destination.write_bytes(payload)
    print(f"Downloaded {len(payload)} bytes to: {destination}")
    if filename.lower().endswith(ARCHIVE_SUFFIXES):
        print("  This is an archive. Unpack it in the project directory before compiling.")
    print()
    print(f"The downloaded file is licensed by {config['display_name']}, not by this project.")
    print("Do not commit it to a public repository unless the venue permits redistribution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
