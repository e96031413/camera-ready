# Post-Acceptance Materials (Phase 4)

After paper acceptance (or when slides/poster/video are requested), prepare conference materials.

## 4a. Beamer Presentation Slides
Create slides using the full Beamer workflow (see `references/beamer-workflow.md`):
1. **Phase 0**: Read paper `main.tex` and extract slide-worthy content.
2. **Phase 1**: Needs interview -- ask duration, audience level, content scope (**GATE**).
3. **Phase 2**: Structure plan -- detailed outline with slide allocation (**GATE -- user must approve**).
4. **Phase 3**: Draft in batches using telegraphic style + semantic colors (`\pos{}`, `\con{}`, `\HL{}`).
5. **Phase 4**: TikZ figures following `references/beamer-tikz-standards.md`.
6. **Phase 5**: Quality loop -- compile + self-review + score >=90 (max 3 rounds).

**Setup:**
```bash
mkdir -p <paper_dir>/slides
cp assets/template/beamer-preamble.tex <paper_dir>/slides/slides.tex
```

**Compile and validate:**
```bash
python scripts/compile_slides.py --project-dir <paper_dir>/slides/
python scripts/validate_slides.py --project-dir <paper_dir>/slides/ --duration <minutes>
```

**14 Hard Rules** (non-negotiable; see `references/beamer-workflow.md`):
- No overlays (`\pause`/`\onslide`/`\only`) -- use separate slides
- Max 2 colored boxes per slide; XeLaTeX only; never `\tiny`
- References slide second-to-last; 3-5 backup slides after `\appendix`
- Color contrast >= 4.5:1 (WCAG AA); telegraphic style

**Review actions** (see `references/beamer-review-actions.md`):
- `review`: grammar, typos, consistency, overflow
- `audit`: visual layout, spacing-first fixes
- `pedagogy`: 13 pedagogical patterns validation
- `excellence`: parallel multi-dimensional review
- `validate`: quantitative checks via `validate_slides.py`
- `visual-check`: PDF-based slide-by-slide inspection

**Quality target**: Score >= 90 (start at 100; deduct -10/-20 for critical, -3/-10 for major, -1 for minor).

## 4b. Narrated Presentation Video (Optional)
Convert approved Beamer slides into a narrated MP4 video using Qwen3-TTS and Remotion.

**Prerequisites**: Completed slides (Phase 4a, score >= 90), Qwen3-TTS (`pip install qwen-tts` + CUDA GPU >= 6GB VRAM), Node.js 18+, poppler-utils (`pdftoppm`), ffmpeg.

**Pipeline** (see `references/video-workflow.md`):
1. **VD1 -- Generate narration script**: `python scripts/generate_narration.py --project-dir <paper_dir>`
2. **VD2 -- Synthesize TTS audio**: `python scripts/synthesize_tts.py --project-dir <paper_dir>`
3. **VD3 -- Scaffold Remotion project**: `python scripts/scaffold_video.py --project-dir <paper_dir>`
4. **VD4 -- Render video**: `python scripts/render_video.py --project-dir <paper_dir>`
5. **VD5 -- Validate video**: `python scripts/validate_video.py --project-dir <paper_dir>`

## 4c. Academic Poster (HTML Interactive)
Generate conference posters as self-contained HTML with React interactive editor.

**6-Phase Pipeline:**
1. **PS0 -- Material Analysis**: Read paper, extract key content.
2. **PS1 -- Requirements Interview** (**GATE**): Confirm dimensions/orientation/columns/style.
3. **PS2 -- Resource Collection**: Convert figures, download logos, generate QR codes.
4. **PS3 -- Generate Poster HTML**: Populate template with paper content.
5. **PS4 -- Layout Optimization**: Playwright whitespace sweep + PDF export.
6. **PS5 -- Quality Loop**: Validate score >=85 (max 3 rounds).

**Setup:**
```bash
python scripts/poster_generate.py --project-dir <paper_dir> --dimensions A0 --orientation landscape --columns 3
python scripts/poster_convert_figures.py --source-dir <paper_dir>/figures --output-dir <paper_dir>/poster
```

**Optimize and validate:**
```bash
python scripts/poster_optimize.py --project-dir <paper_dir> --sweep --pdf --screenshot
python scripts/poster_validate.py --project-dir <paper_dir>
```

**18 Hard Rules** (see `references/poster-workflow.md`): 4-6 feet readable; title >=72pt; body >=24pt; no paragraphs; self-contained HTML; WCAG AA contrast.

**Quality target**: Score >= 85.

## 4d. Promotion Content
Twitter thread (5-7 tweets), LinkedIn post, blog post. See `references/post-acceptance.md`.

## 4e. PowerPoint (.pptx) Slides
Generate presentation slides as native PowerPoint using PptxGenJS + OMML math.

**5-Phase Pipeline:**
1. **Material Analysis** -- Read paper/source material, extract key points, identify formulas & diagrams.
2. **Requirements Interview** -- Confirm audience, duration, theme (5 themes: `academic_light`, `midnight`, `ocean`, `forest`, `sandwich`), emphasis areas.
3. **Structure Plan** -- Outline slide deck. Map content to 9 layout types (see `references/pptx-pptxgenjs-reference.md`).
4. **Formula & Diagram Prep** (see `references/pptx-formula-rendering.md` and `references/pptx-diagram-rendering.md`):
   - `python scripts/pptx_render_latex.py formulas.json pptx/images/formulas/ [--theme <name>]` -- renders LaTeX formulas from JSON to transparent PNG/SVG images.
   - `python scripts/pptx_render_diagrams.py diagrams.json pptx/images/diagrams/ [--theme <name>]` -- renders diagrams from JSON, routing to Graphviz, Mermaid, TikZ, or PDF figure extraction as needed.
5. **Generate & QA Loop:**
   - Write `pptx/generate_slides.js` using PptxGenJS API.
   - Run: `cd pptx && node generate_slides.js`
   - Inject OMML: `python scripts/pptx_inject_omml.py pptx/output.pptx formulas.json pptx/output_final.pptx` -- converts LaTeX to OMML via pandoc and replaces `{{MATH:id}}` placeholders with native PowerPoint math elements.
   - Check overlaps: `python scripts/pptx_check_overlaps.py pptx/output_final.pptx`
   - Generate thumbnails: `python scripts/pptx_thumbnail.py pptx/output_final.pptx pptx/thumbnails`

**29 Hard Rules** govern content density, layout, typography. See `references/pptx-themes.md`.
