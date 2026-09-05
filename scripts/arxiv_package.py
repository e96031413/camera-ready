#!/usr/bin/env python3
"""Build an arXiv submission tarball from a paper project.

arXiv compiles your source on its own machines, with three constraints that
break most working directories:

  1. It does not run BibTeX. A \\bibliography{...} with no .bbl produces a paper
     full of question marks. This script inlines the compiled .bbl.
  2. Its build is flat and case-sensitive. Subdirectories work, but they are a
     common source of "file not found" failures, so this script flattens
     everything to the archive root and rewrites the paths that point at it.
  3. Anything you upload is public source. Comments, \\todo notes, and commented
     -out paragraphs ship with the paper unless you remove them.

This script **only builds a file**. It never uploads anything. Submission is a
manual step you perform yourself, after reading the generated report.

Outputs:
  <out>                             the tarball, default submission.tar.gz
  notes/arxiv-submission-report.md  what went in, what was rewritten, what to check
"""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
import tempfile
from pathlib import Path

# Graphics formats arXiv's pdflatex path accepts.
SAFE_GRAPHICS = {".pdf", ".png", ".jpg", ".jpeg"}
# Accepted only on the legacy latex+dvips path; mixing them with pdflatex fails.
LEGACY_GRAPHICS = {".eps", ".ps"}
# Never compiled by arXiv; convert before submitting.
BAD_GRAPHICS = {".svg", ".gif", ".tif", ".tiff", ".bmp", ".webp", ".psd", ".ai"}

# arXiv's default per-submission limit. Larger submissions need a support request.
SIZE_WARN_BYTES = 10 * 1024 * 1024
SINGLE_FILE_WARN_BYTES = 5 * 1024 * 1024

_INPUT_RE = re.compile(r"\\(input|include)\s*\{([^}]+)\}")
_GRAPHICS_RE = re.compile(r"(\\includegraphics(?:\s*\[[^\]]*\])?\s*\{)([^}]+)(\})")
_BIBLIOGRAPHY_RE = re.compile(r"^[ \t]*\\bibliography\s*\{([^}]+)\}[ \t]*$", re.MULTILINE)
_TODO_RE = re.compile(r"\\(todo|TODO|note|fixme|FIXME)(\s*\[[^\]]*\])?\s*\{")
_ABS_PATH_RE = re.compile(r"\{([A-Za-z]:[\\/]|/(?:home|Users|mnt|media|var|opt)/)[^}]*\}")


class Issue:
    """One packaging problem or note."""

    def __init__(self, level: str, message: str) -> None:
        self.level = level
        self.message = message


def strip_comments(text: str) -> str:
    """Remove LaTeX line comments while preserving escaped percent signs.

    A line that becomes empty only because it was entirely a comment is dropped,
    so the packaged source does not carry a ladder of blank lines.
    """
    out = []
    for line in text.splitlines():
        result = []
        index = 0
        commented = False
        while index < len(line):
            char = line[index]
            if char == "\\" and index + 1 < len(line):
                result.append(line[index : index + 2])
                index += 2
                continue
            if char == "%":
                commented = True
                break
            result.append(char)
            index += 1
        kept = "".join(result)
        if commented and not kept.strip():
            continue
        # A stripped comment leaves a trailing space that LaTeX would now honour.
        out.append(kept.rstrip() if commented else kept)
    return "\n".join(out) + "\n"


def strip_todo_macros(text: str) -> tuple[str, int]:
    """Remove \\todo{...} style macros, matching braces. Returns (text, count)."""
    result = []
    index = 0
    removed = 0
    while index < len(text):
        match = _TODO_RE.search(text, index)
        if not match:
            result.append(text[index:])
            break
        result.append(text[index : match.start()])
        # Walk from the opening brace of the macro argument to its match.
        depth = 0
        cursor = match.end() - 1
        while cursor < len(text):
            char = text[cursor]
            if char == "\\":
                cursor += 2
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    cursor += 1
                    break
            cursor += 1
        removed += 1
        index = cursor
    return "".join(result), removed


def resolve_tex(project_dir: Path, raw: str) -> Path | None:
    """Resolve an \\input/\\include argument to a file in the project."""
    raw = raw.strip()
    for candidate in (project_dir / raw, project_dir / f"{raw}.tex"):
        if candidate.is_file():
            return candidate
    return None


def resolve_graphic(project_dir: Path, raw: str) -> Path | None:
    """Resolve an \\includegraphics argument, which usually omits the extension."""
    raw = raw.strip()
    direct = project_dir / raw
    if direct.is_file():
        return direct
    for suffix in list(SAFE_GRAPHICS) + list(LEGACY_GRAPHICS) + list(BAD_GRAPHICS):
        candidate = project_dir / f"{raw}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def flat_name(path: Path, project_dir: Path, taken: set[str]) -> str:
    """Return a unique flat archive name for a project file."""
    relative = path.relative_to(project_dir)
    name = relative.name
    if name not in taken:
        taken.add(name)
        return name
    # Collision: fold the directory into the name rather than silently
    # overwriting a figure with a same-named one from another folder.
    folded = "-".join(relative.parts)
    counter = 1
    candidate = folded
    while candidate in taken:
        counter += 1
        candidate = f"{relative.stem}-{counter}{relative.suffix}"
    taken.add(candidate)
    return candidate


def collect(project_dir: Path, main_tex: Path) -> tuple[dict[Path, str], list[Issue], dict[str, str]]:
    """Walk the project from main.tex. Returns (file->flat name, issues, path rewrites)."""
    issues: list[Issue] = []
    taken: set[str] = set()
    mapping: dict[Path, str] = {}
    rewrites: dict[str, str] = {}

    mapping[main_tex] = flat_name(main_tex, project_dir, taken)

    pending = [main_tex]
    seen = {main_tex.resolve()}
    while pending:
        current = pending.pop()
        text = current.read_text(encoding="utf-8", errors="replace")

        for _, raw in _INPUT_RE.findall(text):
            resolved = resolve_tex(project_dir, raw)
            if resolved is None:
                issues.append(
                    Issue("ERROR", f"{current.name}: \\input{{{raw}}} does not resolve to a file in the project")
                )
                continue
            if resolved.resolve() in seen:
                continue
            seen.add(resolved.resolve())
            mapping[resolved] = flat_name(resolved, project_dir, taken)
            rewrites[raw.strip()] = Path(mapping[resolved]).stem
            pending.append(resolved)

        for _, raw, _ in _GRAPHICS_RE.findall(text):
            resolved = resolve_graphic(project_dir, raw)
            if resolved is None:
                issues.append(
                    Issue(
                        "ERROR",
                        f"{current.name}: \\includegraphics{{{raw}}} does not resolve to a file. "
                        "arXiv will fail to compile.",
                    )
                )
                continue
            if resolved not in mapping:
                mapping[resolved] = flat_name(resolved, project_dir, taken)
            # \includegraphics conventionally omits the extension; keep it that way.
            flat = mapping[resolved]
            rewrites[raw.strip()] = flat if Path(raw).suffix else Path(flat).stem

        for match in _ABS_PATH_RE.finditer(text):
            issues.append(
                Issue(
                    "ERROR",
                    f"{current.name}: absolute path {match.group(0)[:80]} — "
                    "it does not exist on arXiv's build machine.",
                )
            )

    # Class and style files the paper needs. These are not discoverable from
    # \usepackage alone (most packages come from arXiv's TeX Live), so ship
    # every local one and let the report say what was included.
    for pattern in ("*.cls", "*.sty", "*.bst", "*.clo"):
        for path in sorted(project_dir.glob(pattern)):
            if path not in mapping:
                mapping[path] = flat_name(path, project_dir, taken)

    return mapping, issues, rewrites


def rewrite_tex(text: str, rewrites: dict[str, str]) -> str:
    """Rewrite \\input and \\includegraphics arguments to their flattened names."""

    def sub_input(match: re.Match) -> str:
        macro, raw = match.group(1), match.group(2).strip()
        return f"\\{macro}{{{rewrites.get(raw, raw)}}}"

    def sub_graphics(match: re.Match) -> str:
        prefix, raw, suffix = match.group(1), match.group(2).strip(), match.group(3)
        return f"{prefix}{rewrites.get(raw, raw)}{suffix}"

    text = _INPUT_RE.sub(sub_input, text)
    return _GRAPHICS_RE.sub(sub_graphics, text)


def inline_bbl(text: str, project_dir: Path, issues: list[Issue]) -> str:
    """Replace \\bibliography{...} with the compiled .bbl contents."""
    match = _BIBLIOGRAPHY_RE.search(text)
    if not match:
        return text

    bbl = project_dir / "main.bbl"
    if not bbl.is_file():
        candidates = sorted(project_dir.glob("*.bbl"))
        bbl = candidates[0] if candidates else bbl

    if not bbl.is_file():
        issues.append(
            Issue(
                "ERROR",
                "\\bibliography{...} is present but no .bbl file was found. arXiv does not run "
                "BibTeX, so every citation would render as [?]. Compile the paper first: "
                "python scripts/compile_paper.py --project-dir <paper_dir>",
            )
        )
        return text

    contents = bbl.read_text(encoding="utf-8", errors="replace").rstrip()
    replacement = (
        "% Bibliography inlined from " + bbl.name + " by scripts/arxiv_package.py.\n"
        "% arXiv does not run BibTeX; the .bbl must be embedded.\n" + contents
    )
    issues.append(Issue("INFO", f"Inlined {bbl.name} ({len(contents)} chars) in place of \\bibliography{{...}}"))
    return _BIBLIOGRAPHY_RE.sub(lambda _: replacement, text, count=1)


def audit_assets(mapping: dict[Path, str], issues: list[Issue]) -> None:
    """Flag graphics formats and file sizes that arXiv will reject or throttle."""
    total = 0
    for path in mapping:
        size = path.stat().st_size
        total += size
        suffix = path.suffix.lower()

        if suffix in BAD_GRAPHICS:
            issues.append(
                Issue(
                    "ERROR",
                    f"{path.name}: arXiv does not compile {suffix} graphics. "
                    "Convert it to PDF (vector) or PNG (raster) and update the \\includegraphics.",
                )
            )
        elif suffix in LEGACY_GRAPHICS:
            issues.append(
                Issue(
                    "WARN",
                    f"{path.name}: {suffix} works only on arXiv's legacy latex+dvips path. "
                    "If the paper is built with pdflatex, convert it to PDF.",
                )
            )

        if size > SINGLE_FILE_WARN_BYTES:
            issues.append(
                Issue(
                    "WARN",
                    f"{path.name}: {size / (1024 * 1024):.1f} MB. Large raster figures slow the "
                    "build and often indicate an un-downsampled screenshot.",
                )
            )

    if total > SIZE_WARN_BYTES:
        issues.append(
            Issue(
                "WARN",
                f"Total source size is {total / (1024 * 1024):.1f} MB, above arXiv's usual "
                f"{SIZE_WARN_BYTES // (1024 * 1024)} MB limit. You will need to shrink figures "
                "or request an exception.",
            )
        )


def render_report(
    project_dir: Path,
    out_path: Path,
    mapping: dict[Path, str],
    issues: list[Issue],
    todo_removed: int,
) -> str:
    """Render notes/arxiv-submission-report.md."""
    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level == "WARN"]
    notes = [i for i in issues if i.level == "INFO"]

    lines = [
        "# arXiv Submission Report",
        "",
        f"- Project: `{project_dir}`",
        f"- Tarball: `{out_path}`",
        f"- Files packaged: {len(mapping)}",
        f"- Blocking problems: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
        "**This report describes a file on disk. Nothing has been uploaded.** "
        "Submission to arXiv is a manual step you perform yourself.",
        "",
    ]

    if errors:
        lines += ["## Blocking problems", "", "Fix these before uploading. arXiv will fail to compile.", ""]
        lines.extend(f"- {issue.message}" for issue in errors)
        lines.append("")

    if warnings:
        lines += ["## Warnings", "", "These compile, but they are the usual causes of a rejected or malformed submission.", ""]
        lines.extend(f"- {issue.message}" for issue in warnings)
        lines.append("")

    lines += ["## Transformations applied", ""]
    lines.append("- LaTeX comments stripped from every packaged `.tex` file. Uploaded source is public.")
    lines.append(
        f"- `\\todo`/`\\note`/`\\fixme` macros removed: {todo_removed}."
        if todo_removed
        else "- No `\\todo`/`\\note`/`\\fixme` macros found."
    )
    lines.append("- Directory structure flattened; `\\input` and `\\includegraphics` paths rewritten to match.")
    for issue in notes:
        lines.append(f"- {issue.message}")
    lines.append("")

    lines += ["## Packaged files", "", "| Archive name | Source | Size |", "|---|---|---|"]
    for path, name in sorted(mapping.items(), key=lambda item: item[1]):
        relative = path.relative_to(project_dir).as_posix()
        size = path.stat().st_size
        lines.append(f"| `{name}` | `{relative}` | {size:,} B |")
    lines.append("")

    lines += [
        "## Before you upload",
        "",
        "1. Unpack the tarball into an empty directory and compile it there. A build that "
        "works in your project directory can still fail on arXiv, because your directory "
        "contains files the tarball does not.",
        "2. Check the bibliography renders — no `[?]` markers.",
        "3. Run `python scripts/anonymity_check.py --project-dir <paper_dir>` if the arXiv "
        "posting must stay anonymous for a concurrent double-blind submission. Check your "
        "target venue's policy on preprints first; some forbid posting during review.",
        "4. Confirm the license you select on arXiv matches what you intend. It cannot be "
        "made more restrictive later.",
        "5. Upload it yourself at <https://arxiv.org/submit>.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an arXiv submission tarball from a paper project. Never uploads."
    )
    parser.add_argument("--project-dir", required=True, help="Paper project directory containing main.tex.")
    parser.add_argument(
        "--out",
        help="Tarball path (default: <project-dir>/submission.tar.gz).",
    )
    parser.add_argument(
        "--main", default="main.tex", help="Entry-point .tex file (default: main.tex)."
    )
    parser.add_argument(
        "--keep-comments",
        action="store_true",
        help="Do not strip LaTeX comments. Uploaded arXiv source is public; think before using this.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be packaged without writing the tarball.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"error: project dir not found: {project_dir}", file=sys.stderr)
        return 1

    main_tex = project_dir / args.main
    if not main_tex.is_file():
        print(f"error: entry point not found: {main_tex}", file=sys.stderr)
        return 1

    out_path = Path(args.out).expanduser().resolve() if args.out else project_dir / "submission.tar.gz"

    mapping, issues, rewrites = collect(project_dir, main_tex)
    audit_assets(mapping, issues)

    # Transform the .tex sources into a staging directory.
    todo_removed = 0
    staged: dict[str, bytes] = {}
    for path, name in mapping.items():
        if path.suffix.lower() != ".tex":
            staged[name] = path.read_bytes()
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not args.keep_comments:
            text = strip_comments(text)
        text, removed = strip_todo_macros(text)
        todo_removed += removed
        text = rewrite_tex(text, rewrites)
        if path == main_tex:
            text = inline_bbl(text, project_dir, issues)
        staged[name] = text.encode("utf-8")

    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    report_path = notes_dir / "arxiv-submission-report.md"
    report_path.write_text(
        render_report(project_dir, out_path, mapping, issues, todo_removed), encoding="utf-8"
    )

    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level == "WARN"]

    if args.dry_run:
        print(f"Dry run: {len(staged)} file(s) would be packaged into {out_path}")
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp)
            for name, payload in staged.items():
                (staging / name).write_bytes(payload)
            with tarfile.open(out_path, "w:gz") as tar:
                for name in sorted(staged):
                    tar.add(staging / name, arcname=name)
        print(f"Wrote {out_path} ({out_path.stat().st_size:,} bytes, {len(staged)} files)")

    print(f"Report: {report_path}")
    for issue in errors:
        print(f"  [ERROR] {issue.message}")
    for issue in warnings:
        print(f"  [WARN]  {issue.message}")

    print()
    if errors:
        print(f"{len(errors)} blocking problem(s). Fix them and rebuild before uploading.")
    else:
        print("No blocking problems. Unpack the tarball into an empty directory and compile it "
              "there before uploading.")
    print("This script does not upload. Submit it yourself at https://arxiv.org/submit")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
