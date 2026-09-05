#!/usr/bin/env python3
"""Validate rendered presentation video quality.

Uses ffprobe to inspect video properties and generates a validation report
at notes/video-validation.md.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_utils import now_iso


def fail(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_file_size_mb(path: Path) -> float:
    """Return file size in megabytes."""
    return path.stat().st_size / (1024 * 1024)


def run_ffprobe(video_path: Path) -> dict:
    """Run ffprobe and return parsed JSON metadata.

    Raises
    ------
    RuntimeError
        If ffprobe is not found or returns a non-zero exit code.
    """
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found on PATH (install FFmpeg)")

    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    result = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", text=True)
    if result.returncode != 0:
        stderr_msg = result.stderr.strip() if result.stderr else "(no output)"
        raise RuntimeError(f"ffprobe failed (exit {result.returncode}): {stderr_msg}")

    return json.loads(result.stdout)


def check_video(
    probe_data: dict,
    file_size_mb: float,
    expected_duration: float | None,
    max_size_mb: float,
) -> list[str]:
    """Check video properties and return a list of failure messages.

    Returns an empty list when all checks pass.
    """
    failures: list[str] = []
    streams = probe_data.get("streams", [])

    # Categorise streams
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    # Has video stream
    if not video_streams:
        failures.append("No video stream found")

    # Has audio stream
    if not audio_streams:
        failures.append("No audio stream found")

    # Resolution check (1920x1080)
    if video_streams:
        vs = video_streams[0]
        width = vs.get("width", 0)
        height = vs.get("height", 0)
        if width != 1920 or height != 1080:
            failures.append(
                f"Resolution is {width}x{height}, expected 1920x1080"
            )

    # Duration
    fmt = probe_data.get("format", {})
    duration_str = fmt.get("duration")
    duration: float | None = None
    if duration_str:
        try:
            duration = float(duration_str)
        except (ValueError, TypeError):
            duration = None

    if duration is None or duration <= 0:
        failures.append("Duration is missing or zero")
    elif expected_duration is not None:
        threshold = expected_duration * 0.9
        if duration < threshold:
            failures.append(
                f"Duration {duration:.1f}s is below 90% of expected "
                f"{expected_duration:.1f}s (threshold: {threshold:.1f}s)"
            )

    # File size
    if file_size_mb > max_size_mb:
        failures.append(
            f"File size {file_size_mb:.1f} MB exceeds maximum {max_size_mb:.1f} MB"
        )

    return failures


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _extract_property(
    probe_data: dict,
) -> dict:
    """Extract display-friendly properties from probe data."""
    streams = probe_data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    fmt = probe_data.get("format", {})

    # Resolution
    width: int | None = None
    height: int | None = None
    codec_name: str | None = None
    fps: str | None = None
    if video_streams:
        vs = video_streams[0]
        width = vs.get("width")
        height = vs.get("height")
        codec_name = vs.get("codec_name")
        r_frame_rate = vs.get("r_frame_rate", "")
        if r_frame_rate and "/" in r_frame_rate:
            parts = r_frame_rate.split("/")
            try:
                fps_val = int(parts[0]) / int(parts[1]) if int(parts[1]) != 0 else 0
                fps = f"{fps_val:g}"
            except (ValueError, ZeroDivisionError):
                fps = r_frame_rate
        else:
            fps = r_frame_rate or None

    duration_str = fmt.get("duration")
    duration: float | None = None
    if duration_str:
        try:
            duration = float(duration_str)
        except (ValueError, TypeError):
            pass

    return {
        "width": width,
        "height": height,
        "has_video": len(video_streams) > 0,
        "has_audio": len(audio_streams) > 0,
        "duration": duration,
        "codec": codec_name,
        "fps": fps,
    }


def generate_report(
    *,
    timestamp: str,
    passed: bool,
    props: dict,
    file_size_mb: float,
    expected_duration: float | None,
    max_size_mb: float,
    failures: list[str],
) -> str:
    """Render the video-validation.md report content."""
    result_str = "PASS" if passed else "FAIL"

    # Resolution display
    if props["width"] is not None and props["height"] is not None:
        resolution = f"{props['width']}x{props['height']}"
        # Use multiplication sign for display
        resolution_display = f"{props['width']}×{props['height']}"
    else:
        resolution = "N/A"
        resolution_display = "N/A"

    resolution_ok = (props["width"] == 1920 and props["height"] == 1080)

    # Duration display
    duration_display = f"{props['duration']:.1f}s" if props["duration"] else "N/A"
    duration_ok = props["duration"] is not None and props["duration"] > 0
    if duration_ok and expected_duration is not None:
        duration_ok = props["duration"] >= expected_duration * 0.9

    # File size check
    size_ok = file_size_mb <= max_size_mb

    def _mark(ok: bool) -> str:
        return "\u2713" if ok else "\u2717"

    lines: list[str] = [
        "# Video Validation Report",
        f"Generated: {timestamp}",
        "",
        f"## Result: {result_str}",
        "",
        "## Properties",
        "| Property | Value | Check |",
        "|----------|-------|-------|",
        f"| Resolution | {resolution_display} | {_mark(resolution_ok)} |",
        f"| Has video track | {'Yes' if props['has_video'] else 'No'} | {_mark(props['has_video'])} |",
        f"| Has audio track | {'Yes' if props['has_audio'] else 'No'} | {_mark(props['has_audio'])} |",
        f"| Duration | {duration_display} | {_mark(duration_ok)} |",
        f"| File size | {file_size_mb:.1f} MB | {_mark(size_ok)} |",
        f"| Codec | {props['codec'] or 'N/A'} | \u2014 |",
        f"| FPS | {props['fps'] or 'N/A'} | \u2014 |",
        "",
        "## Failures",
    ]

    if failures:
        for f in failures:
            lines.append(f"- {f}")
    else:
        lines.append("- None")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate rendered presentation video quality."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Paper project directory.",
    )
    parser.add_argument(
        "--video",
        default=None,
        help="Video path (default: slides/video/output/presentation.mp4).",
    )
    parser.add_argument(
        "--expected-duration",
        type=float,
        default=None,
        help="Expected duration in seconds (optional).",
    )
    parser.add_argument(
        "--max-size-mb",
        type=float,
        default=500,
        help="Maximum file size in MB (default: 500).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        return fail(f"project dir not found: {project_dir}")

    # ---- Determine video path ---------------------------------------------
    if args.video:
        video_path = Path(args.video).expanduser().resolve()
    else:
        video_path = project_dir / "slides" / "video" / "output" / "presentation.mp4"

    if not video_path.exists():
        return fail(f"video file not found: {video_path}")

    # ---- Auto-load expected duration from manifest.json -------------------
    expected_duration = args.expected_duration
    if expected_duration is None:
        manifest_path = project_dir / "slides" / "video" / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(
                    manifest_path.read_text(encoding="utf-8", errors="replace")
                )
                raw = manifest.get("total_duration_seconds")
                if raw is not None:
                    expected_duration = float(raw)
                    print(
                        f"Loaded expected duration from manifest.json: {expected_duration:.1f}s"
                    )
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                print(
                    f"warning: failed to read manifest.json: {exc}",
                    file=sys.stderr,
                )

    # ---- Run ffprobe ------------------------------------------------------
    try:
        probe_data = run_ffprobe(video_path)
    except RuntimeError as exc:
        return fail(str(exc))

    # ---- Analyse properties -----------------------------------------------
    file_size_mb = get_file_size_mb(video_path)
    failures = check_video(
        probe_data,
        file_size_mb=file_size_mb,
        expected_duration=expected_duration,
        max_size_mb=args.max_size_mb,
    )
    passed = len(failures) == 0
    props = _extract_property(probe_data)

    # ---- Generate report --------------------------------------------------
    timestamp = now_iso()
    report = generate_report(
        timestamp=timestamp,
        passed=passed,
        props=props,
        file_size_mb=file_size_mb,
        expected_duration=expected_duration,
        max_size_mb=args.max_size_mb,
        failures=failures,
    )

    # ---- Write report -----------------------------------------------------
    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    report_path = notes_dir / "video-validation.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Report written: notes/video-validation.md")

    # ---- Print summary ----------------------------------------------------
    if passed:
        print("Validation: PASS")
    else:
        print("Validation: FAIL")
        for f in failures:
            print(f"  - {f}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
