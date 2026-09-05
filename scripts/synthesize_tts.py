#!/usr/bin/env python3
"""Synthesize TTS audio for each slide using Qwen3-TTS."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paper_utils import now_iso


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fail(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


def _wav_duration(wav_path: Path) -> float:
    """Return duration in seconds for a WAV file."""
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate == 0:
            return 0.0
        return frames / rate


def _mp3_duration_ffprobe(mp3_path: Path) -> float | None:
    """Return duration in seconds using ffprobe, or None on failure."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        result = subprocess.run(
            [
                ffprobe, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(mp3_path),
            ],
            capture_output=True, encoding="utf-8", errors="replace",
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (ValueError, OSError):
        pass
    return None


def _wav_to_mp3(wav_path: Path, mp3_path: Path) -> int:
    """Convert WAV to MP3 using ffmpeg. Returns process exit code."""
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(wav_path),
            "-codec:a", "libmp3lame", "-qscale:a", "2",
            str(mp3_path),
        ],
        capture_output=True, encoding="utf-8", errors="replace",
        text=True,
    )
    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr.strip()}", file=sys.stderr)
    return result.returncode


def _detect_language(text: str) -> str:
    """Heuristic: if >30% of characters are CJK, assume Chinese."""
    cjk = 0
    total = 0
    for ch in text:
        cp = ord(ch)
        if cp > 127:
            cjk += 1
        if not ch.isspace():
            total += 1
    if total == 0:
        return "English"
    return "Chinese" if (cjk / total) > 0.30 else "English"


# ---------------------------------------------------------------------------
# Synthesis backends
# ---------------------------------------------------------------------------

def _synthesize_local(
    text: str,
    lang: str,
    speaker: str,
    instruct: str,
    wav_path: Path,
    *,
    model: object,
    sample_rate_holder: list[int],
) -> float:
    """Synthesize one slide with a local Qwen3-TTS model.

    Returns duration in seconds.
    """
    import torch  # noqa: F811 – already guarded at top level

    wavs, sr = model.generate_custom_voice(  # type: ignore[union-attr]
        text=text,
        language=lang,
        speaker=speaker,
        instruct=instruct,
    )
    sample_rate_holder.clear()
    sample_rate_holder.append(sr)

    # wavs is a list of tensors; concatenate if needed
    if isinstance(wavs, list):
        audio = torch.cat(wavs, dim=-1) if len(wavs) > 1 else wavs[0]
    else:
        audio = wavs

    # Ensure 1-D numpy
    if hasattr(audio, "cpu"):
        audio_np = audio.cpu().float().numpy()
    else:
        audio_np = audio  # already numpy

    if audio_np.ndim > 1:
        audio_np = audio_np.squeeze()

    import soundfile as sf  # noqa: F811

    sf.write(str(wav_path), audio_np, sr, subtype="PCM_16")

    duration = len(audio_np) / sr
    return float(duration)


def _synthesize_api(
    text: str,
    speaker: str,
    mp3_path: Path,
    *,
    api_url: str,
    model_name: str,
) -> float | None:
    """Synthesize one slide via an OpenAI-compatible TTS API.

    Returns duration in seconds (via ffprobe), or None if duration cannot be
    determined.
    """
    url = api_url.rstrip("/") + "/audio/speech"
    payload = json.dumps({
        "model": model_name,
        "voice": speaker,
        "input": text,
        "response_format": "mp3",
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            mp3_path.write_bytes(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"  API error ({exc.code}): {body}", file=sys.stderr)
        raise
    except urllib.error.URLError as exc:
        print(f"  API connection error: {exc.reason}", file=sys.stderr)
        raise

    return _mp3_duration_ffprobe(mp3_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_EN_SPEAKERS = ["Ryan", "Aiden"]
_ZH_SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"]
# Current TTS model default — override with --model for a different HuggingFace model,
# or use --api-url with any OpenAI-compatible TTS server.
_DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
_DEFAULT_INSTRUCT = "Speak in a clear, professional academic presentation tone."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synthesize TTS audio for each slide using Qwen3-TTS."
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Paper project directory.",
    )
    parser.add_argument(
        "--model",
        default=_DEFAULT_MODEL,
        help=f"Qwen model name (default: {_DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--speaker-en",
        default="Ryan",
        choices=_EN_SPEAKERS,
        help="English speaker voice (default: Ryan).",
    )
    parser.add_argument(
        "--speaker-zh",
        default="Vivian",
        choices=_ZH_SPEAKERS,
        help="Chinese speaker voice (default: Vivian).",
    )
    parser.add_argument(
        "--instruct",
        default=_DEFAULT_INSTRUCT,
        help=f"Natural language prosody instruction (default: \"{_DEFAULT_INSTRUCT}\").",
    )
    parser.add_argument(
        "--device",
        default="cuda:0",
        help="CUDA device for local model (default: cuda:0).",
    )
    parser.add_argument(
        "--keep-wav",
        action="store_true",
        help="Keep intermediate WAV files after MP3 conversion.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing audio files.",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="OpenAI-compatible API URL (e.g., http://localhost:8880/v1). "
             "If provided, use HTTP API instead of local model loading.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        return fail("project dir not found")
    if not project_dir.is_dir():
        return fail("project dir is not a directory")

    narration_path = project_dir / "slides" / "video" / "narration-script.json"
    if not narration_path.exists():
        return fail(f"narration script not found: slides/video/narration-script.json")

    # Load narration script
    try:
        narration = json.loads(narration_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return fail(f"failed to read narration script: {exc}")

    slides = narration.get("slides")
    if not slides:
        return fail("narration script contains no slides")

    use_api = args.api_url is not None

    # Check ffmpeg availability (needed for both modes; local uses wav->mp3,
    # API mode needs ffprobe for duration)
    if not shutil.which("ffmpeg"):
        return fail("ffmpeg not found on PATH (required for WAV-to-MP3 conversion)")

    # --- Load local model if needed -----------------------------------------
    model = None
    if not use_api:
        try:
            import torch
            from qwen_tts import Qwen3TTSModel
        except ImportError:
            return fail(
                "qwen_tts and torch are required for local synthesis. "
                "Install them or use --api-url for remote synthesis."
            )

        if not torch.cuda.is_available():
            return fail(
                f"CUDA is not available (device={args.device}). "
                "A GPU is required for local Qwen3-TTS inference."
            )

        print(f"Loading model {args.model} on {args.device} ...")
        model = Qwen3TTSModel.from_pretrained(
            args.model,
            device_map=args.device,
            dtype=torch.bfloat16,
        )
        print("Model loaded.")

    # --- Prepare output directory -------------------------------------------
    audio_dir = project_dir / "slides" / "video" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    total_slides = len(slides)
    manifest_slides: list[dict] = []
    total_duration = 0.0
    sample_rate_holder: list[int] = []

    for i, slide in enumerate(slides):
        idx = slide.get("index", i + 1)
        title = slide.get("title", f"Slide {idx}")
        text = slide.get("narration", "")
        if not text.strip():
            print(f"Skipping slide {idx}/{total_slides}: {title} (empty narration)")
            continue

        mp3_name = f"slide-{idx:03d}.mp3"
        mp3_path = audio_dir / mp3_name

        if mp3_path.exists() and not args.force:
            print(f"Skipping slide {idx}/{total_slides}: {title} (already exists, use --force)")
            # Still try to include existing file in manifest
            dur = _mp3_duration_ffprobe(mp3_path)
            lang = _detect_language(text)
            speaker = args.speaker_zh if lang == "Chinese" else args.speaker_en
            manifest_slides.append({
                "index": idx,
                "audio_path": f"audio/{mp3_name}",
                "duration_seconds": round(dur, 2) if dur else 0.0,
                "speaker": speaker,
                "lang": lang,
            })
            if dur:
                total_duration += dur
            continue

        lang = _detect_language(text)
        speaker = args.speaker_zh if lang == "Chinese" else args.speaker_en

        print(f"Synthesizing slide {idx}/{total_slides}: {title}...")

        duration = 0.0

        if use_api:
            # Mode B: API synthesis (produces MP3 directly)
            try:
                dur = _synthesize_api(
                    text=text,
                    speaker=speaker,
                    mp3_path=mp3_path,
                    api_url=args.api_url,  # type: ignore[arg-type]
                    model_name=args.model,
                )
                duration = dur if dur else 0.0
            except (urllib.error.HTTPError, urllib.error.URLError):
                return fail(f"API synthesis failed for slide {idx}")
        else:
            # Mode A: Local model synthesis (produces WAV, then convert)
            wav_name = f"slide-{idx:03d}.wav"
            wav_path = audio_dir / wav_name

            try:
                duration = _synthesize_local(
                    text=text,
                    lang=lang,
                    speaker=speaker,
                    instruct=args.instruct,
                    wav_path=wav_path,
                    model=model,
                    sample_rate_holder=sample_rate_holder,
                )
            except Exception as exc:
                return fail(f"synthesis failed for slide {idx}: {exc}")

            # Convert WAV -> MP3
            rc = _wav_to_mp3(wav_path, mp3_path)
            if rc != 0:
                return fail(f"ffmpeg conversion failed for slide {idx}")

            # Remove WAV unless --keep-wav
            if not args.keep_wav and wav_path.exists():
                wav_path.unlink()

        total_duration += duration
        manifest_slides.append({
            "index": idx,
            "audio_path": f"audio/{mp3_name}",
            "duration_seconds": round(duration, 2),
            "speaker": speaker,
            "lang": lang,
        })
        print(f"  -> {mp3_name}  ({duration:.1f}s)")

    # --- Write manifest.json ------------------------------------------------
    manifest = {
        "generated_at": now_iso(),
        "model": args.model,
        "total_duration_seconds": round(total_duration, 1),
        "slides": manifest_slides,
    }

    manifest_path = project_dir / "slides" / "video" / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"\nDone. {len(manifest_slides)} audio files, total {total_duration:.1f}s")
    print(f"Manifest written to slides/video/manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
