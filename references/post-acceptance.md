# Post-Acceptance Preparation

Purpose: conference materials after paper acceptance. Covers Beamer presentations, posters, and promotion.

## Beamer Presentation Slides

### Prerequisites
- XeLaTeX installed (never pdflatex for slides)
- Template: `assets/template/beamer-preamble.tex`
- Compile: `python scripts/compile_slides.py --project-dir <paper_dir>/slides/`
- Validate: `python scripts/validate_slides.py --project-dir <paper_dir>/slides/ --duration <minutes>`

### Workflow Summary
The full 5-phase Beamer workflow is in `references/beamer-workflow.md`:
1. **Phase 0**: Material analysis — read paper `main.tex` and extract slide-worthy content
2. **Phase 1**: Needs interview — ask duration, audience level, content-driven questions (**GATE**)
3. **Phase 2**: Structure plan — detailed outline with slide allocation (**GATE — user must approve**)
4. **Phase 3**: Draft — iterative batched writing using telegraphic style
5. **Phase 4**: Figures — TikZ diagrams following `references/beamer-tikz-standards.md`
6. **Phase 5**: Quality loop — compile, self-review, score ≥90, fix (max 3 rounds)

### 14 Hard Rules
See `references/beamer-workflow.md` for the full list. Key rules:
- No overlay commands (`\pause`, `\onslide`, `\only`)
- Max 2 colored boxes per slide
- XeLaTeX only
- References slide second-to-last; backup slides after `\appendix`
- Color contrast ≥ 4.5:1 (WCAG AA)
- Never use `\tiny`

### Time Guidelines
- 15-min talk → 10-15 slides (~1-1.5 min per slide)
- 20-min talk → 15-20 slides
- 5-min spotlight → 5-7 slides (key results only)

### Structure

| Slide(s) | Content | Time |
|----------|---------|------|
| 1 | Title, authors, affiliations | 0.5 min |
| 2-3 | Motivation and problem statement | 2 min |
| 3-5 | Method overview (with Figure 1) | 4 min |
| 6-8 | Key results (tables + plots) | 4 min |
| 9-10 | Ablation / analysis highlights | 2 min |
| 11 | Conclusion and takeaways | 1 min |
| 12 | References | 0 min |
| 13 | Q&A slide (with contact info) | 0.5 min |
| Backup | 3-5 slides for anticipated Q&A | — |

### Design Rules (from Beamer Hard Rules)
- One message per slide — if you need two, split it
- Telegraphic keywords, not full sentences
- Minimum 20pt body font, 24pt headers (Beamer 10pt handles this)
- Consistent semantic colors: `\pos{}` (blue/pros), `\con{}` (orange/cons), `\HL{}` (green/key)
- Dark text on light background for projectors
- ≤ 7 bullets, ≤ 2 equations, ≤ 5 new symbols, ≤ 2 boxes per slide
- Pure text-only slides ≤ 30% of deck

### Quality Scoring
Start at 100; deduct per severity:
- **Critical** (overflow, undefined refs): −10 to −20
- **Major** (sparse slides, TikZ inaccuracy): −3 to −10
- **Minor** (spacing): −1

**Thresholds**: ≥90 Ready | 80–89 Acceptable | <80 Must Fix

### Review Actions
See `references/beamer-review-actions.md` for: review, audit, pedagogy, excellence, validate, visual-check.

### Tips
- Rehearse with timer at least 3 times
- Prepare 3-5 backup slides for anticipated Q&A
- Know your first and last sentences by heart
- Record yourself; watch for filler words and pacing

---

## Academic Poster (HTML Interactive)

The poster is a React-based interactive editor — a single self-contained HTML file with CDN dependencies (React 18, Babel, KaTeX 0.16.9, Nunito font). No build step needed. Full workflow in `references/poster-workflow.md`.

### Prerequisites
- Template: `assets/template/poster/template.html`
- Playwright required for layout optimization (`pip install playwright && playwright install chromium`)
- Pillow recommended for image measurement (`pip install Pillow`)
- poppler-utils for PDF conversion (`pdftoppm`)

### Workflow Summary (6-Phase Pipeline)
1. **Phase PS0**: Material analysis — read paper, extract slide-worthy content, note image aspect ratios
2. **Phase PS1**: Requirements interview — dimensions, orientation, columns, style (**GATE**)
3. **Phase PS2**: Resource collection — convert figures, download logos, generate QR codes
4. **Phase PS3**: Generate poster HTML — populate CARD_REGISTRY, DEFAULT_LAYOUT, header
5. **Phase PS4**: Layout optimization — Playwright whitespace sweep + PDF export
6. **Phase PS5**: Quality loop — validate score ≥85, user iteration via Copy Config (max 3 rounds)

### Setup
```bash
python scripts/poster_generate.py --project-dir <paper_dir> --dimensions A0 --orientation landscape --columns 3
```

### Optimize and Export
```bash
python scripts/poster_optimize.py --project-dir <paper_dir> --sweep --pdf --screenshot
python scripts/poster_validate.py --project-dir <paper_dir>
python scripts/poster_thumbnail.py --poster-pdf <paper_dir>/poster/poster.pdf
```

### 18 Hard Rules (Summary)
See `references/poster-workflow.md` for the full list. Key rules:
- 4-6 feet readable; title ≥72pt
- No paragraphs — bullet points and figures only; ≤40 words per card
- Images: `width:100%; height:100%; object-fit:contain`
- Each column has exactly one `grow:true` card
- Self-contained HTML — no build step
- QR code required; print CSS hides editor UI
- Color contrast ≥ 4.5:1 (WCAG AA)
- Whitespace < 15% (measured by `posterAPI.getWaste()`)
- Aspect-ratio-aware column assignment

### Size Guidelines

| Name | Dimensions (mm) | Typical Use |
|------|-----------------|-------------|
| A0 | 841 × 1189 | Large conference poster |
| A1 | 594 × 841 | Standard conference poster |
| 24×36 in | 610 × 914 | US standard |
| 36×48 in | 914 × 1219 | US large |

### Typography

| Element | Minimum Size |
|---------|-------------|
| Title | 72–96pt |
| Section headers | 36–48pt |
| Body text | 24–32pt |
| Captions | 20–24pt |

### Quality Scoring
Start at 100; deduct per severity:
- **CRITICAL** (broken layout, dimension mismatch): −15
- **MAJOR** (FILL_IN placeholders, missing assets): −5
- **MINOR** (missing QR, font-scale): −1

**Thresholds**: ≥85 Ready | 70–84 Acceptable | <70 Must Fix

---

## Promotion Content

### Twitter/X Thread (5-7 tweets)
1. Hook: surprising result or bold claim
2. Problem: what gap exists
3. Method: how you solve it (with figure)
4. Key result: most impressive number or comparison
5. Implications: why this matters
6. Link to paper + code (if available)
7. Acknowledgments (optional)

### LinkedIn Post
- Professional tone, 200-300 words
- Lead with impact/application angle
- Include 1 figure
- Tag co-authors and institutions

### Blog Post
- 800-1500 words, accessible to non-specialists
- Include 3-5 figures from the paper
- Explain intuition before technical details
- Link to paper, code, and demo

### Audience Targeting
| Platform | Audience | Tone | Length |
|----------|----------|------|--------|
| Twitter/X | Researchers, ML community | Casual, exciting | Short |
| LinkedIn | Industry, hiring managers | Professional | Medium |
| Blog | General technical audience | Educational | Long |
