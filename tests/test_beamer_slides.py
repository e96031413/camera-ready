"""Tests for Beamer slide compilation and validation scripts."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import compile_slides
import validate_slides


# ── Fixtures ─────────────────────────────────────────────────

VALID_BEAMER_TEX = textwrap.dedent(r"""
\documentclass[10pt,aspectratio=169]{beamer}
\usetheme{Madrid}
\definecolor{positive}{RGB}{31,119,180}
\newcommand{\pos}[1]{\textcolor{positive}{#1}}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{tikz}
\usepackage{booktabs}
\usepackage{hyperref}
\title{Test Slides}
\author{Test Author}
\begin{document}

\begin{frame}
\titlepage
\end{frame}

\begin{frame}{Motivation}
Key insight: \pos{this matters}
\end{frame}

\begin{frame}{Method}
\begin{itemize}
\item Step 1
\item Step 2
\end{itemize}
\end{frame}

\begin{frame}{Results}
\begin{tabular}{lcc}
\toprule
Method & Accuracy & Speed \\
\midrule
Ours & \textbf{95\%} & 10ms \\
\bottomrule
\end{tabular}
\end{frame}

\begin{frame}[allowframebreaks]{References}
\bibliography{ref}
\end{frame}

\begin{frame}
\centering
{\Large Thank You}
\end{frame}

\appendix

\begin{frame}{Backup: Additional Results}
Extra content here.
\end{frame}

\end{document}
""").strip()


VIOLATION_BEAMER_TEX = textwrap.dedent(r"""
\documentclass[10pt,aspectratio=169]{beamer}
\usetheme{Madrid}
\begin{document}

\begin{frame}{Bad Slide}
\pause
Content after pause
\end{frame}

\begin{frame}{Too Many Boxes}
\begin{block}{A}x\end{block}
\begin{alertblock}{B}y\end{alertblock}
\begin{exampleblock}{C}z\end{exampleblock}
\end{frame}

\begin{frame}{Tiny Text}
{\tiny This is too small}
\end{frame}

\end{document}
""").strip()


# ── validate_slides tests ────────────────────────────────────

class TestCountFrames:
    def test_counts_main_frames(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VALID_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.count_frames(tex) == 6  # title + 3 content + refs + thankyou

    def test_excludes_backup_frames(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VALID_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.count_backup_frames(tex) == 1

    def test_no_appendix(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        simple = r"""\documentclass{beamer}
\begin{document}
\begin{frame}{A}Content\end{frame}
\begin{frame}{B}More\end{frame}
\end{document}"""
        tex.write_text(simple, encoding="utf-8")
        assert validate_slides.count_frames(tex) == 2
        assert validate_slides.count_backup_frames(tex) == 0


class TestOverlayDetection:
    def test_no_overlays_in_valid(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VALID_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.check_overlay_commands(tex) == 0

    def test_detects_pause(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VIOLATION_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.check_overlay_commands(tex) >= 1


class TestTinyUsage:
    def test_no_tiny_in_valid(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VALID_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.check_tiny_usage(tex) == 0

    def test_detects_tiny(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VIOLATION_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.check_tiny_usage(tex) >= 1


class TestReferencesSlide:
    def test_has_bibliography(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VALID_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.check_references_slide(tex) is True

    def test_missing_bibliography(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VIOLATION_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.check_references_slide(tex) is False


class TestAppendixPresent:
    def test_has_appendix(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VALID_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.check_appendix_present(tex) is True

    def test_missing_appendix(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VIOLATION_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.check_appendix_present(tex) is False


class TestBoxFatigue:
    def test_no_violations_in_valid(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VALID_BEAMER_TEX, encoding="utf-8")
        assert validate_slides.check_box_fatigue(tex) == []

    def test_detects_three_boxes(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VIOLATION_BEAMER_TEX, encoding="utf-8")
        violations = validate_slides.check_box_fatigue(tex)
        assert len(violations) >= 1


class TestFileSize:
    def test_returns_none_for_missing(self, tmp_path: Path):
        assert validate_slides.get_file_size_mb(tmp_path / "missing.pdf") is None

    def test_returns_size(self, tmp_path: Path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"x" * 1024)
        size = validate_slides.get_file_size_mb(pdf)
        assert size is not None
        assert abs(size - 0.001) < 0.01


# ── compile_slides tests ─────────────────────────────────────

class TestLogDiagnostics:
    def test_parses_clean_log(self, tmp_path: Path):
        log = tmp_path / "slides.log"
        log.write_text("Output written on slides.pdf (10 pages)\n", encoding="utf-8")
        diag = compile_slides.parse_log_diagnostics(log)
        assert diag["pages"] == 10
        assert diag["overfull_hbox"] == 0
        assert diag["errors"] == 0

    def test_parses_warnings(self, tmp_path: Path):
        log = tmp_path / "slides.log"
        log.write_text(
            "Overfull \\hbox (10pt too wide)\n"
            "Overfull \\hbox (5pt too wide)\n"
            "LaTeX Warning: Reference `fig:x' undefined\n"
            "LaTeX Warning: Citation `smith2024' undefined\n"
            "Output written on slides.pdf (5 pages)\n"
, encoding="utf-8")
        diag = compile_slides.parse_log_diagnostics(log)
        assert diag["overfull_hbox"] == 2
        assert diag["undefined_refs"] == 1
        assert diag["undefined_citations"] == 1
        assert diag["pages"] == 5

    def test_missing_log(self, tmp_path: Path):
        diag = compile_slides.parse_log_diagnostics(tmp_path / "missing.log")
        assert diag["pages"] is None


class TestSourceViolations:
    def test_clean_source(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VALID_BEAMER_TEX, encoding="utf-8")
        v = compile_slides.check_source_violations(tex)
        assert v["overlays"] == 0
        assert v["tiny_usage"] == 0

    def test_violations_detected(self, tmp_path: Path):
        tex = tmp_path / "slides.tex"
        tex.write_text(VIOLATION_BEAMER_TEX, encoding="utf-8")
        v = compile_slides.check_source_violations(tex)
        assert v["overlays"] >= 1
        assert v["tiny_usage"] >= 1


# ── Template existence test ──────────────────────────────────

class TestTemplate:
    def test_beamer_preamble_exists(self):
        template = Path(__file__).resolve().parents[1] / "assets" / "template" / "beamer-preamble.tex"
        assert template.exists(), "beamer-preamble.tex template missing"

    def test_template_uses_xelatex_compatible_setup(self):
        template = Path(__file__).resolve().parents[1] / "assets" / "template" / "beamer-preamble.tex"
        content = template.read_text(encoding="utf-8")
        assert "aspectratio=169" in content
        assert "10pt" in content
        assert r"\usetheme{Madrid}" in content
        assert "positive" in content
        assert "negative" in content
        assert "emphasis" in content

    def test_template_has_no_overlay_commands(self):
        template = Path(__file__).resolve().parents[1] / "assets" / "template" / "beamer-preamble.tex"
        content = template.read_text(encoding="utf-8")
        assert r"\pause" not in content
        assert r"\onslide" not in content
        assert r"\only" not in content

    def test_template_has_appendix_section(self):
        template = Path(__file__).resolve().parents[1] / "assets" / "template" / "beamer-preamble.tex"
        content = template.read_text(encoding="utf-8")
        assert r"\appendix" in content


# ── Issues CSV slide rows test ───────────────────────────────

class TestIssuesCSV:
    def test_all_templates_have_slide_rows(self):
        assets = Path(__file__).resolve().parents[1] / "assets"
        for csv_name in [
            "paper-issues-template.csv",
            "paper-issues-conference-template.csv",
            "paper-issues-codebase-template.csv",
        ]:
            csv_path = assets / csv_name
            content = csv_path.read_text(encoding="utf-8")
            assert "SL4,Slides" in content, f"{csv_name} missing SL4 slide row"
            assert "SL8,Slides" in content, f"{csv_name} missing SL8 slide row"
            assert "VD1,Video" in content, f"{csv_name} missing VD1 video row"
            assert "VD5,Video" in content, f"{csv_name} missing VD5 video row"
