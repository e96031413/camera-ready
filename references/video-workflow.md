# Video Workflow (Phase 4d)

## Purpose
Convert Beamer presentation slides into a narrated MP4 video with TTS voiceover, suitable for conference talks, online presentations, or social media promotion.

## Prerequisites
- Completed Beamer slides (Phase 4a) with score ≥ 90
- System requirements:
  - **Qwen3-TTS**: `pip install qwen-tts` + NVIDIA GPU with ≥6GB VRAM (or use API server mode)
  - **Remotion**: Node.js 18+ and npm
  - **PDF conversion**: poppler-utils (`sudo apt install poppler-utils` for `pdftoppm`)
  - **Audio conversion**: ffmpeg (`sudo apt install ffmpeg`)
  - **Video validation**: ffprobe (included with ffmpeg)

## Pipeline Overview
```
slides.tex → generate_narration.py → narration-script.json
                                           ↓
                                    synthesize_tts.py (Qwen3-TTS)
                                           ↓
slides.pdf → scaffold_video.py → remotion/ project
                                    (frames/ + audio/ + props.json)
                                           ↓
                                    render_video.py (npx remotion render)
                                           ↓
                                    presentation.mp4
                                           ↓
                                    validate_video.py ✓
```

## Step-by-Step

### VD1: Generate Narration Script
```bash
python scripts/generate_narration.py --project-dir <paper_dir>
```
- Parses `slides/slides.tex` frame by frame
- Extracts `\note{}` content as narration (falls back to frame content)
- Detects language per slide (Chinese/English)
- Output: `slides/video/narration-script.json`

### VD2: Synthesize TTS Audio
```bash
# Local model (requires GPU)
python scripts/synthesize_tts.py --project-dir <paper_dir>

# Or via API server (if running groxaxo/Qwen3-TTS-Openai-Fastapi)
python scripts/synthesize_tts.py --project-dir <paper_dir> --api-url http://localhost:8880/v1
```
- Uses Qwen3-TTS CustomVoice model (1.7B)
- Default speakers: Ryan (English), Vivian (Chinese)
- Output: `slides/video/audio/slide-{N}.mp3` + `slides/video/manifest.json`

### VD3: Scaffold Video Project
```bash
python scripts/scaffold_video.py --project-dir <paper_dir>
```
- Converts `slides.pdf` → PNG images via `pdftoppm`
- Copies Remotion template, generates `props.json`
- Runs `npm install`
- Output: `slides/video/remotion/` (ready to render)

### VD4: Render Video
```bash
python scripts/render_video.py --project-dir <paper_dir>

# Speed up with higher concurrency (default: half of CPU cores)
python scripts/render_video.py --project-dir <paper_dir> --concurrency 16
```
- Runs `npx remotion render` with `--props=./public/props.json`
- Default: H.264, CRF 18, 1920×1080, 30fps
- Output: `slides/video/output/presentation.mp4`

**Performance tuning**: Remotion renders frames in parallel via Chrome headless instances. The `--concurrency` flag controls how many frames are rendered simultaneously. Higher values use more RAM but render significantly faster:
- `--concurrency 2`: ~20 min for 15-min video (low RAM usage)
- `--concurrency 8`: ~8 min (balanced)
- `--concurrency 16`: ~5 min (recommended for ≥32GB RAM)

> **Note**: Remotion's `--gl` GPU acceleration does **not** work in headless mode (`--headless=old` disables GPU). Increasing `--concurrency` is the most effective way to speed up rendering. For Linux, also add `--enable-multiprocess-on-linux` (automatically included by `render_video.py`).

### VD5: Validate Video
```bash
python scripts/validate_video.py --project-dir <paper_dir>
```
- Checks resolution, audio track, duration, file size
- Output: `notes/video-validation.md`

## Qwen3-TTS Configuration

### Available Speakers
| Speaker | Language | Profile |
|---------|----------|---------|
| Ryan | English | Dynamic male, strong rhythmic drive |
| Aiden | English | Sunny American male, clear midrange |
| Vivian | Chinese | Bright, slightly edgy young female |
| Serena | Chinese | Warm, gentle young female |
| Uncle_Fu | Chinese | Seasoned male, low mellow timbre |

### Prosody Control
Qwen3-TTS uses natural language instructions instead of SSML:
```bash
# Professional academic tone (default)
--instruct "Speak in a clear, professional academic presentation tone."

# Enthusiastic
--instruct "Speak with enthusiasm and energy, as if presenting exciting research findings."

# Slow and deliberate
--instruct "Speak slowly and clearly, emphasizing key terms."
```

### API Server Mode
For machines without GPU, run the API server on a GPU machine:
```bash
# On GPU machine: start OpenAI-compatible server
pip install qwen-tts[api]
python -m api.main  # http://0.0.0.0:8880

# On any machine: use API
python scripts/synthesize_tts.py --project-dir <paper_dir> --api-url http://gpu-machine:8880/v1
```

## Remotion Template

The template uses:
- `<TransitionSeries>` with fade transitions (0.5s default)
- `<Img>` for slide images (cover fit, subtle Ken Burns zoom)
- `<Audio>` for TTS narration
- `calculateMetadata` for dynamic duration

## Customization

### Transition Style
Edit `--transition-duration` in scaffold_video.py (default 0.5s).

### Video Quality
- `--crf 18` (default): High quality, ~50MB for 10min
- `--crf 23`: Medium quality, ~25MB for 10min
- `--crf 28`: Lower quality, ~12MB for 10min

### Resolution
Default 1920×1080. For 4K: modify the Remotion composition in Root.tsx.

## Output Structure
```
slides/video/
├── narration-script.json    (VD1)
├── audio/                   (VD2)
│   ├── slide-001.mp3
│   ├── slide-002.mp3
│   └── ...
├── manifest.json            (VD2)
├── frames/                  (VD3)
│   ├── slide-001.png
│   ├── slide-002.png
│   └── ...
├── remotion/                (VD3)
│   ├── package.json
│   ├── src/
│   ├── public/
│   │   ├── props.json
│   │   ├── frames/ → ../../frames/
│   │   └── audio/ → ../../audio/
│   └── node_modules/
└── output/                  (VD4)
    └── presentation.mp4
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `qwen_tts` import error | `pip install qwen-tts` (requires Python 3.12+) |
| CUDA out of memory | Use 0.6B model: `--model Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` |
| pdftoppm not found | `sudo apt install poppler-utils` |
| ffmpeg not found | `sudo apt install ffmpeg` |
| npm/node not found | Install Node.js 18+ from nodejs.org |
| Remotion render fails | Check `npm install` ran successfully in remotion/ |
| Audio-video sync off | Re-run scaffold_video.py to regenerate props.json |
| "No available ports found" | IPv6 timeout issue — patch `port-config.js` to return `['127.0.0.1', '0.0.0.0']` only (see below) |
| Video renders only 1 frame | `--props` flag missing — `render_video.py` handles this automatically |
| `fade is not a function` | Import `fade` from `@remotion/transitions/fade` (not `@remotion/transitions`) |
| `null was passed to staticFile()` | Slides without narration have `audioPath: null` — guard with conditional render |
| Render too slow | Increase `--concurrency` (e.g., 16); GPU mode is not available in headless Chrome |

### IPv6 Port Workaround
On systems where IPv6 loopback (`::1`) is detected but not functional, Remotion's port scanner times out on all ports. Fix by editing `node_modules/@remotion/renderer/dist/port-config.js`:
```javascript
const getHostsToTry = (flattened) => {
    // Force IPv4-only to avoid IPv6 timeout issues
    return ['127.0.0.1', '0.0.0.0'];
};
```
