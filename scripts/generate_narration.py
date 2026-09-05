#!/usr/bin/env python3
"""Parse Beamer slides.tex and generate a narration script JSON for TTS synthesis."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from paper_utils import now_iso


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Match \begin{frame} with optional argument: \begin{frame}{Title}
_FRAME_BEGIN_RE = re.compile(r"\\begin\{frame\}")
_FRAME_END_RE = re.compile(r"\\end\{frame\}")

# Frame title variants
_FRAME_TITLE_INLINE_RE = re.compile(r"\\begin\{frame\}\s*\{([^}]*)\}")
_FRAMETITLE_CMD_RE = re.compile(r"\\frametitle\{([^}]*)\}")

# Speaker notes: \note{...} (may span multiple lines via brace matching)
_NOTE_START_RE = re.compile(r"\\note\{")

# Title-only frames to skip
_TITLE_PAGE_RE = re.compile(r"\\(titlepage|maketitle)\b")

# Appendix marker
_APPENDIX_RE = re.compile(r"\\appendix\b")

# CJK Unicode detection range
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# LaTeX command patterns for stripping
_CMD_WITH_ARG_RE = re.compile(
    r"\\(textbf|textit|texttt|emph|underline|alert|structure|pos|mbox|hbox)"
    r"\{([^}]*)\}"
)
_CITE_RE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*)*\{[^}]*\}")
_REF_RE = re.compile(r"\\(ref|label|eqref|pageref)\{[^}]*\}")
_URL_RE = re.compile(r"\\(url|href)\{[^}]*\}(?:\{[^}]*\})?")
_BEGIN_END_RE = re.compile(r"\\(begin|end)\{[^}]*\}")
_SIZING_RE = re.compile(
    r"\\(tiny|scriptsize|footnotesize|small|normalsize|large|Large|LARGE|huge|Huge)\b"
)
_GENERIC_CMD_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])*(?:\{[^}]*\})?")
_LEFTOVER_BRACES_RE = re.compile(r"[{}]")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{2,}")
_ITEM_RE = re.compile(r"\\item\b\s*")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def fail(msg: str) -> int:
    """Print an error message to stderr and return exit code 1."""
    print(f"error: {msg}", file=sys.stderr)
    return 1


def strip_latex(text: str) -> str:
    """Remove LaTeX commands and return cleaned plain text.

    Transforms like \\textbf{x} -> x, \\cite{...} -> "", \\pos{x} -> x, etc.
    Removes \\begin{...}/\\end{...} lines and collapses whitespace.
    """
    # Replace \item with a bullet-like separator so list items stay distinct
    out = _ITEM_RE.sub("\n", text)

    # Commands that expose their argument text (loop for nested commands)
    prev = None
    while prev != out:
        prev = out
        out = _CMD_WITH_ARG_RE.sub(r"\2", out)

    # Commands to remove entirely (citations, refs, urls)
    out = _CITE_RE.sub("", out)
    out = _REF_RE.sub("", out)
    out = _URL_RE.sub("", out)

    # Remove \begin{...} / \end{...} lines
    out = _BEGIN_END_RE.sub("", out)

    # Remove sizing commands
    out = _SIZING_RE.sub("", out)

    # Remove remaining generic LaTeX commands (best-effort)
    out = _GENERIC_CMD_RE.sub("", out)

    # Clean up leftover braces and tilde
    out = _LEFTOVER_BRACES_RE.sub("", out)
    out = out.replace("~", " ")

    # Collapse whitespace per line, then collapse blank lines
    lines = []
    for line in out.splitlines():
        stripped = _WHITESPACE_RE.sub(" ", line).strip()
        if stripped:
            lines.append(stripped)
    out = "\n".join(lines)
    out = _MULTI_NEWLINE_RE.sub("\n", out).strip()
    return out


def detect_language(text: str) -> str:
    """Return 'Chinese' if text contains CJK characters, else 'English'."""
    if _CJK_RE.search(text):
        return "Chinese"
    return "English"


def _extract_braced(text: str, start: int) -> str:
    """Extract text inside balanced braces starting at position *start*.

    *start* must point to the opening '{'.  Returns the content between
    the matching braces (exclusive).
    """
    if start >= len(text) or text[start] != "{":
        return ""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i]
        i += 1
    # Unbalanced – return what we have
    return text[start + 1 :]


def notes_to_narration(note_text: str) -> str:
    """Clean up speaker note text into narration-ready prose."""
    cleaned = strip_latex(note_text)
    # Collapse multiple whitespace into single spaces, preserve sentence breaks
    cleaned = re.sub(r"\n", " ", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def content_to_narration(frame_content: str, title: str) -> str:
    """Convert telegraphic slide content to narration-ready text.

    Prefixes with 'This slide covers {title}.' then appends the cleaned
    content.
    """
    cleaned = strip_latex(frame_content)
    # Join lines into flowing prose
    cleaned = re.sub(r"\n", " ", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()

    if not cleaned:
        return f"This slide covers {title}."
    return f"This slide covers {title}. {cleaned}"


def _is_title_only_frame(content: str) -> bool:
    """Return True if the frame body only contains \\titlepage or \\maketitle."""
    stripped = content.strip()
    # Remove comments
    lines = []
    for line in stripped.splitlines():
        line = re.sub(r"(?<!\\)%.*$", "", line).strip()
        if line:
            lines.append(line)
    body = " ".join(lines)
    # After removing the frame title command, check if only titlepage/maketitle remains
    body = _FRAMETITLE_CMD_RE.sub("", body).strip()
    if not body:
        # Empty body is NOT a title-only frame; it is just an empty slide
        return False
    return bool(_TITLE_PAGE_RE.fullmatch(body))


def extract_frames(tex_content: str) -> list[dict]:
    """Parse \\begin{frame}...\\end{frame} blocks from Beamer source.

    Returns a list of dicts with keys:
      - title: str
      - narration: str
      - lang: str
      - is_backup: bool
      - _skip: bool  (for internal filtering of title-only frames)
    """
    frames: list[dict] = []
    in_appendix = False

    # We iterate line-by-line to track appendix markers and frame boundaries.
    lines = tex_content.splitlines(keepends=True)
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Check for \appendix
        if _APPENDIX_RE.search(line):
            in_appendix = True
            i += 1
            continue

        # Check for \begin{frame}
        if _FRAME_BEGIN_RE.search(line):
            # Collect everything from this line to the matching \end{frame}
            frame_lines = [line]
            depth = 1
            i += 1
            while i < n and depth > 0:
                cur = lines[i]
                frame_lines.append(cur)
                # Count nested frames (rare but possible)
                depth += len(_FRAME_BEGIN_RE.findall(cur))
                depth -= len(_FRAME_END_RE.findall(cur))
                i += 1

            frame_text = "".join(frame_lines)

            # Extract title
            title = ""
            m_inline = _FRAME_TITLE_INLINE_RE.search(frame_text)
            if m_inline:
                title = m_inline.group(1).strip()
            if not title:
                m_cmd = _FRAMETITLE_CMD_RE.search(frame_text)
                if m_cmd:
                    title = m_cmd.group(1).strip()
            if not title:
                title = "Untitled"

            # Extract the body between \begin{frame}... and \end{frame}
            # Find the end of the \begin{frame}{...} line and the \end{frame} line
            body_start = _FRAME_BEGIN_RE.search(frame_text)
            body_end_match = None
            for m in _FRAME_END_RE.finditer(frame_text):
                body_end_match = m  # last match
            if body_start and body_end_match:
                # Body starts after the \begin{frame}{Title} line
                first_line_end = frame_text.index("\n", body_start.end()) if "\n" in frame_text[body_start.end():] else body_start.end()
                body = frame_text[first_line_end:body_end_match.start()]
            else:
                body = frame_text

            # Check if title-only frame
            skip = _is_title_only_frame(body)

            # Extract speaker notes: \note{...}
            narration = ""
            note_match = _NOTE_START_RE.search(body)
            if note_match:
                brace_pos = body.index("{", note_match.start())
                note_content = _extract_braced(body, brace_pos)
                narration = notes_to_narration(note_content)
                # Remove the note from body for content-based fallback
                note_full_end = brace_pos + len(note_content) + 2  # +2 for { and }
                body_without_note = body[:note_match.start()] + body[note_full_end:]
            else:
                body_without_note = body

            if not narration:
                narration = content_to_narration(body_without_note, title)

            # Detect language from narration text
            lang = detect_language(narration)

            frames.append({
                "title": strip_latex(title),
                "narration": narration,
                "lang": lang,
                "is_backup": in_appendix,
                "_skip": skip,
            })
            continue

        i += 1

    return frames


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse Beamer slides.tex and generate a narration script JSON for TTS synthesis."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Paper project directory (must contain a slides/ subfolder with slides.tex).",
    )
    parser.add_argument(
        "--include-backup",
        action="store_true",
        help="Include backup slides after \\appendix in the output (default: exclude).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing narration-script.json if present.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        return fail(f"project directory not found: {project_dir}")

    slides_dir = project_dir / "slides"
    if not slides_dir.is_dir():
        return fail(f"slides/ subfolder not found in {project_dir}")

    tex_path = slides_dir / "slides.tex"
    if not tex_path.exists():
        return fail(f"slides.tex not found in {slides_dir}")

    # Output path
    video_dir = slides_dir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    out_path = video_dir / "narration-script.json"

    if out_path.exists() and not args.force:
        return fail(
            "narration-script.json already exists (use --force to overwrite)"
        )

    # Read and parse
    tex_content = tex_path.read_text(encoding="utf-8", errors="replace")
    raw_frames = extract_frames(tex_content)

    # Filter out title-only frames
    frames = [f for f in raw_frames if not f["_skip"]]

    # Separate main and backup
    main_frames = [f for f in frames if not f["is_backup"]]
    backup_frames = [f for f in frames if f["is_backup"]]

    if args.include_backup:
        output_frames = frames
    else:
        output_frames = main_frames

    # Build output slides list
    slides: list[dict] = []
    for idx, frame in enumerate(output_frames, start=1):
        slides.append({
            "index": idx,
            "title": frame["title"],
            "narration": frame["narration"],
            "lang": frame["lang"],
            "is_backup": frame["is_backup"],
        })

    result = {
        "generated_at": now_iso(),
        "source": "slides/slides.tex",
        "slides": slides,
    }

    out_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    backup_excluded = len(backup_frames) if not args.include_backup else 0
    print(
        f"Generated narration for {len(slides)} slides "
        f"({backup_excluded} backup excluded)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
