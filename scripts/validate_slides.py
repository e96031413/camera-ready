#!/usr/bin/env python3
"""Validate Beamer slides against quantitative checks and Hard Rules."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Slide count ranges per duration (minutes)
TIMING_TABLE: dict[int, tuple[int, int]] = {
    5: (5, 7),
    10: (8, 12),
    15: (10, 15),
    20: (13, 18),
    45: (22, 30),
    90: (45, 60),
}


def count_frames(tex_path: Path) -> int:
    """Count \\begin{frame} occurrences (excludes \\appendix backup slides)."""
    if not tex_path.exists():
        return 0
    text = tex_path.read_text(encoding="utf-8", errors="replace")

    # Split at \appendix; only count frames before it
    parts = re.split(r"\\appendix\b", text, maxsplit=1)
    main_text = parts[0]

    return len(re.findall(r"\\begin\{frame\}", main_text))


def count_backup_frames(tex_path: Path) -> int:
    """Count frames after \\appendix."""
    if not tex_path.exists():
        return 0
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"\\appendix\b", text, maxsplit=1)
    if len(parts) < 2:
        return 0
    return len(re.findall(r"\\begin\{frame\}", parts[1]))


def check_overlay_commands(tex_path: Path) -> int:
    """Count overlay command violations (Hard Rule 1)."""
    if not tex_path.exists():
        return 0
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    return len(re.findall(r"\\(pause|onslide|only)\b", text))


def check_tiny_usage(tex_path: Path) -> int:
    """Count \\tiny usage (Hard Rule 13)."""
    if not tex_path.exists():
        return 0
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    return len(re.findall(r"\\tiny\b", text))


def check_references_slide(tex_path: Path) -> bool:
    """Check for references/bibliography slide (Hard Rule 11)."""
    if not tex_path.exists():
        return False
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(r"\\begin\{thebibliography\}|\\bibliography\{", text))


def check_appendix_present(tex_path: Path) -> bool:
    """Check for \\appendix command (Hard Rule 14)."""
    if not tex_path.exists():
        return False
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(r"\\appendix\b", text))


def check_box_fatigue(tex_path: Path) -> list[str]:
    """Find frames with >2 colored boxes (Hard Rule 2)."""
    if not tex_path.exists():
        return []
    text = tex_path.read_text(encoding="utf-8", errors="replace")

    violations = []
    # Split by frame
    frames = re.split(r"\\begin\{frame\}", text)
    for i, frame in enumerate(frames[1:], start=1):
        frame_end = frame.find("\\end{frame}")
        if frame_end != -1:
            frame = frame[:frame_end]

        box_count = len(re.findall(
            r"\\begin\{(block|alertblock|exampleblock)\}", frame
        ))
        if box_count > 2:
            # Try to find frame title
            title_match = re.search(r"\{([^}]+)\}", frame)
            title = title_match.group(1) if title_match else f"Frame {i}"
            violations.append(f"{title} ({box_count} boxes)")

    return violations


def parse_log_diagnostics(log_path: Path) -> dict:
    """Parse XeLaTeX log for warnings."""
    if not log_path.exists():
        return {"overfull_hbox": 0, "undefined_refs": 0, "undefined_citations": 0}

    text = log_path.read_text(encoding="utf-8", errors="replace")
    return {
        "overfull_hbox": len(re.findall(r"Overfull \\hbox", text)),
        "undefined_refs": len(re.findall(r"LaTeX Warning: Reference .* undefined", text)),
        "undefined_citations": len(re.findall(r"LaTeX Warning: Citation .* undefined", text)),
    }


def get_file_size_mb(pdf_path: Path) -> float | None:
    """Get PDF file size in MB."""
    if not pdf_path.exists():
        return None
    return pdf_path.stat().st_size / (1024 * 1024)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Beamer slides against Hard Rules and quantitative checks."
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Directory containing the slides .tex file.",
    )
    parser.add_argument(
        "--tex-file",
        default="slides.tex",
        help="Name of the .tex file to validate (default: slides.tex).",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Presentation duration in minutes (for slide count check).",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    tex_path = project_dir / args.tex_file
    stem = tex_path.stem
    log_path = project_dir / f"{stem}.log"
    pdf_path = project_dir / f"{stem}.pdf"

    if not tex_path.exists():
        print(f"error: {args.tex_file} not found in {project_dir}", file=sys.stderr)
        return 1

    results: list[tuple[str, str, str]] = []  # (check, result, status)
    overall_pass = True

    # 1. Slide count
    frame_count = count_frames(tex_path)
    backup_count = count_backup_frames(tex_path)
    if args.duration and args.duration in TIMING_TABLE:
        low, high = TIMING_TABLE[args.duration]
        if low <= frame_count <= high:
            status = "OK"
        else:
            status = "WARNING"
        results.append(("Slide count", f"{frame_count} slides / {args.duration}min (expected {low}-{high})", status))
    else:
        results.append(("Slide count", f"{frame_count} main + {backup_count} backup", "INFO"))

    # 2. File size
    size_mb = get_file_size_mb(pdf_path)
    if size_mb is not None:
        if size_mb > 100:
            results.append(("File size", f"{size_mb:.1f} MB", "CRITICAL"))
            overall_pass = False
        elif size_mb > 50:
            results.append(("File size", f"{size_mb:.1f} MB", "WARNING"))
        else:
            results.append(("File size", f"{size_mb:.1f} MB", "OK"))
    else:
        results.append(("File size", "PDF not found", "WARNING"))

    # 3. Log diagnostics
    diag = parse_log_diagnostics(log_path)
    if diag["overfull_hbox"] > 0:
        results.append(("Overfull hbox", f"{diag['overfull_hbox']} warnings", "CRITICAL"))
        overall_pass = False
    else:
        results.append(("Overfull hbox", "0", "OK"))

    if diag["undefined_refs"] > 0:
        results.append(("Undefined references", str(diag["undefined_refs"]), "CRITICAL"))
        overall_pass = False
    else:
        results.append(("Undefined references", "0", "OK"))

    if diag["undefined_citations"] > 0:
        results.append(("Undefined citations", str(diag["undefined_citations"]), "CRITICAL"))
        overall_pass = False
    else:
        results.append(("Undefined citations", "0", "OK"))

    # 4. Hard Rule checks
    overlays = check_overlay_commands(tex_path)
    if overlays > 0:
        results.append(("Overlay commands (Rule 1)", f"{overlays} found", "VIOLATION"))
        overall_pass = False
    else:
        results.append(("Overlay commands (Rule 1)", "0", "OK"))

    box_violations = check_box_fatigue(tex_path)
    if box_violations:
        results.append(("Box fatigue (Rule 2)", f"{len(box_violations)} slides: {'; '.join(box_violations)}", "WARNING"))
    else:
        results.append(("Box fatigue (Rule 2)", "0 violations", "OK"))

    has_refs = check_references_slide(tex_path)
    results.append(("References slide (Rule 11)", "Present" if has_refs else "Missing", "OK" if has_refs else "WARNING"))

    tiny = check_tiny_usage(tex_path)
    if tiny > 0:
        results.append(("\\tiny usage (Rule 13)", f"{tiny} found", "VIOLATION"))
        overall_pass = False
    else:
        results.append(("\\tiny usage (Rule 13)", "0", "OK"))

    has_appendix = check_appendix_present(tex_path)
    results.append(("Backup slides (Rule 14)", "Present" if has_appendix else "Missing", "OK" if has_appendix else "WARNING"))

    # Print report
    print(f"# Validation Report: {args.tex_file}\n")
    print(f"| {'Check':<30} | {'Result':<50} | {'Status':<10} |")
    print(f"|{'-'*32}|{'-'*52}|{'-'*12}|")
    for check, result, status in results:
        print(f"| {check:<30} | {result:<50} | {status:<10} |")

    has_violations = any(s == "VIOLATION" for _, _, s in results)
    has_warnings = any(s in ("WARNING", "CRITICAL") for _, _, s in results)

    if has_violations:
        print("\nOverall: FAIL (Hard Rule violations)")
    elif not overall_pass:
        print("\nOverall: FAIL")
    elif has_warnings:
        print("\nOverall: PASS WITH WARNINGS")
    else:
        print("\nOverall: PASS")

    return 0 if overall_pass and not has_violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
