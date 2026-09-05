#!/usr/bin/env python3
"""Export a manuscript to Word, ODT, Markdown, Typst or HTML through pandoc.

Version: 2026-09-05-v2

Most disciplines outside computer science submit Word files. This script is the
non-LaTeX output path: it converts a LaTeX or Markdown manuscript, resolves the
citations with citeproc, and applies the CSL file for the citation style the
discipline expects.

The citation style comes from assets/styles/<style>.yaml, so APA, MLA, Chicago
and Vancouver all work through the same command; the profile supplies the CSL
identifier and the URL to fetch the CSL file from.

What this script does not do: it does not guarantee that a LaTeX manuscript
with heavy custom macros survives the conversion. Check the output. Complex
tables, TikZ figures and custom environments are the usual casualties, and the
script reports what pandoc warned about rather than hiding it.

Usage:
  python scripts/export_document.py --input main.tex --style apa7
  python scripts/export_document.py --input main.md --style vancouver --to odt
  python scripts/export_document.py --input main.tex --style mla9 --reference-doc house.docx
  python scripts/export_document.py --fetch-csl apa7
  python scripts/export_document.py --check
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from citation_style import StyleError, load_style
from paper_utils import enable_utf8_stdout, get_assets_dir

BANNER = "export_document 2026-09-05-v2"

# Output format -> (pandoc writer name, file extension)
FORMATS = {
    "docx": ("docx", ".docx"),
    "odt": ("odt", ".odt"),
    "markdown": ("markdown", ".md"),
    "typst": ("typst", ".typ"),
    "html": ("html", ".html"),
}

# Input extension -> pandoc reader name
READERS = {
    ".tex": "latex",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".org": "org",
}

CSL_TIMEOUT = 20


def csl_dir() -> Path:
    return get_assets_dir() / "csl"


def pandoc_version() -> str | None:
    """Return the installed pandoc version, or None when pandoc is missing."""
    if shutil.which("pandoc") is None:
        return None
    try:
        result = subprocess.run(
            ["pandoc", "--version"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.splitlines()[0].strip() if result.stdout else "pandoc"


def fetch_csl(style_slug: str, *, force: bool = False) -> Path:
    """Download the CSL file for a style into assets/csl/. Returns its path."""
    config = load_style(style_slug)
    csl_id = config["csl_id"]
    url = config.get("csl_url")
    target = csl_dir() / f"{csl_id}.csl"

    if target.is_file() and not force:
        return target
    if not url:
        raise StyleError(f"style {style_slug!r} has no csl_url to fetch from")

    request = urllib.request.Request(url, headers={"User-Agent": "camera-ready/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=CSL_TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise StyleError(f"could not fetch the CSL file for {style_slug!r} from {url}: {exc}") from exc

    if "<style" not in body:
        raise StyleError(f"{url} did not return a CSL file; download {csl_id}.csl by hand into {csl_dir()}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


def resolve_csl(style_slug: str, *, allow_fetch: bool) -> Path | None:
    """Return the local CSL path for a style, fetching it when allowed."""
    config = load_style(style_slug)
    target = csl_dir() / f"{config['csl_id']}.csl"
    if target.is_file():
        return target
    if not allow_fetch:
        return None
    return fetch_csl(style_slug)


def build_command(
    *,
    input_path: Path,
    output_path: Path,
    reader: str,
    writer: str,
    bibliography: Path | None,
    csl_path: Path | None,
    reference_doc: Path | None,
    resource_path: Path,
) -> list[str]:
    """Assemble the pandoc invocation. Kept separate so tests can inspect it."""
    command = [
        "pandoc",
        str(input_path),
        "--from",
        reader,
        "--to",
        writer,
        "--output",
        str(output_path),
        "--standalone",
        "--resource-path",
        str(resource_path),
    ]
    if bibliography is not None:
        command += ["--citeproc", "--bibliography", str(bibliography)]
    if csl_path is not None:
        command += ["--csl", str(csl_path)]
    if reference_doc is not None:
        command += ["--reference-doc", str(reference_doc)]
    return command


def cmd_check() -> int:
    """Report whether the non-LaTeX output path is usable on this machine."""
    version = pandoc_version()
    print(f"{BANNER}")
    if version is None:
        print("  pandoc:      NOT FOUND")
        print("               Install it from https://pandoc.org/installing.html")
        print("               Windows: winget install --id JohnMacFarlane.Pandoc")
        print("               macOS:   brew install pandoc")
        print("               Linux:   your package manager, or the .deb from the site")
        return 1
    print(f"  pandoc:      {version}")

    directory = csl_dir()
    local = sorted(p.name for p in directory.glob("*.csl")) if directory.is_dir() else []
    print(f"  CSL files:   {', '.join(local) if local else 'none cached yet'}")
    print(f"  cache dir:   {directory}")
    print("\n  Fetch one with: python scripts/export_document.py --fetch-csl apa7")
    return 0


def main() -> int:
    enable_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="Export a manuscript to Word, ODT, Markdown, Typst or HTML through pandoc."
    )
    parser.add_argument("--input", help="the manuscript to convert (.tex or .md)")
    parser.add_argument("--output", help="output file (default: the input name with the new extension)")
    parser.add_argument("--to", default="docx", choices=sorted(FORMATS), help="output format (default: docx)")
    parser.add_argument("--style", help="citation style slug from assets/styles, e.g. apa7")
    parser.add_argument("--bib", help="bibliography file (default: ref.bib beside the input)")
    parser.add_argument("--reference-doc", help="a .docx or .odt whose styles the output should adopt")
    parser.add_argument("--no-fetch", action="store_true", help="fail rather than download a missing CSL file")
    parser.add_argument("--fetch-csl", metavar="STYLE", help="download the CSL file for a style and exit")
    parser.add_argument("--check", action="store_true", help="report whether pandoc and the CSL cache are ready")
    args = parser.parse_args()

    if args.check:
        return cmd_check()

    if args.fetch_csl:
        try:
            path = fetch_csl(args.fetch_csl, force=True)
        except StyleError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"Wrote {path}")
        return 0

    if not args.input:
        parser.print_help()
        print("\nerror: --input is required", file=sys.stderr)
        return 2

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"error: no such file: {input_path}", file=sys.stderr)
        return 2

    reader = READERS.get(input_path.suffix.lower())
    if reader is None:
        print(
            f"error: cannot convert {input_path.suffix!r}; supported inputs are "
            f"{', '.join(sorted(READERS))}",
            file=sys.stderr,
        )
        return 2

    if pandoc_version() is None:
        print("error: pandoc is not installed; run --check for install instructions", file=sys.stderr)
        return 2

    writer, extension = FORMATS[args.to]
    output_path = Path(args.output) if args.output else input_path.with_suffix(extension)

    bibliography = Path(args.bib) if args.bib else input_path.parent / "ref.bib"
    if not bibliography.is_file():
        print(f"warning: no bibliography at {bibliography}; citations will stay unresolved")
        bibliography = None

    csl_path = None
    if args.style:
        try:
            csl_path = resolve_csl(args.style, allow_fetch=not args.no_fetch)
        except StyleError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if csl_path is None:
            print(
                f"error: no cached CSL file for {args.style!r} and --no-fetch was given; "
                f"run --fetch-csl {args.style}",
                file=sys.stderr,
            )
            return 2

    reference_doc = Path(args.reference_doc) if args.reference_doc else None
    if reference_doc is not None and not reference_doc.is_file():
        print(f"error: no such reference document: {reference_doc}", file=sys.stderr)
        return 2

    command = build_command(
        input_path=input_path,
        output_path=output_path,
        reader=reader,
        writer=writer,
        bibliography=bibliography,
        csl_path=csl_path,
        reference_doc=reference_doc,
        resource_path=input_path.parent,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace")

    if result.stderr.strip():
        print("pandoc reported:")
        for line in result.stderr.strip().splitlines():
            print(f"  {line}")

    if result.returncode != 0:
        print(f"\n{BANNER}: conversion FAILED (pandoc exit {result.returncode})", file=sys.stderr)
        return 1

    size = output_path.stat().st_size if output_path.exists() else 0
    print(f"\nWrote {output_path} ({size:,} bytes)")
    if csl_path is not None:
        print(f"  Citation style: {args.style} via {csl_path.name}")
    print("  Open the file and check tables, figures and equations; pandoc does not")
    print("  translate every LaTeX construct, and it fails quietly when it cannot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
