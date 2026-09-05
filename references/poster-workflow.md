# Poster Creation Workflow (Phase PS0–PS5)

Purpose: full lifecycle for academic HTML conference posters, from material analysis to print-ready PDF.

Adapted from [ethanweber/posterskill](https://github.com/ethanweber/posterskill). The poster is a React-based interactive editor — a single self-contained HTML file. No build step needed (React 18/Babel/KaTeX loaded via CDN).

## 18 Hard Rules (Non-Negotiable)

1. **4-6 feet readable** — title ≥72pt; body ≥24pt at print size
2. **No paragraphs** — bullet points and figures only; each card ≤40 words
3. **Images: width:100% + height:100% + object-fit:contain** — prevents upscaling gaps
4. **Each column has exactly one grow:true card** — fills remaining vertical space
5. **Self-contained HTML** — no build step, no npm, no server; single file with CDN deps
6. **Assets use relative paths** — all figures/logos alongside index.html
7. **Must have QR code** — linking to paper/project page
8. **Print CSS hides editor UI** — `@media print` removes toolbar, dividers, swap handles
9. **Color contrast ≥ 4.5:1** (WCAG AA) — dark text on light background
10. **Each column ≤ 6 cards** — prevent vertical cramming
11. **Each card ≤ 40 words** — posters are visual, not textual
12. **Figure captions include bold title** — `<b>Figure X.</b> Description`
13. **Header contains conference badge** — year and venue name
14. **Logo auto-invert** — CSS `filter:brightness(0) invert(1)` for white-on-gradient header
15. **@page size matches body dimensions** — prevents PDF scaling artifacts
16. **Font scaling via --font-scale CSS variable** — A-/A+ buttons adjust globally
17. **Whitespace < 15%** — measured by `posterAPI.getWaste()`
18. **Aspect-ratio-aware column assignment** — wide images → widest column; portrait → narrowest

---

## Phase PS0: Material Analysis

When source papers/materials are provided:
- Read the full paper `main.tex` and any `\input{}` files
- Extract: title, authors, affiliations, core contribution, key figures, main results
- Identify 1-2 key equations (poster-appropriate subset)
- Note image aspect ratios for column assignment planning
- Check `references/` folder for style reference posters

**Do NOT generate anything yet — proceed to PS1.**

---

## Phase PS1: Requirements Interview (GATE)

### Minimum required questions (always ask):
1. **Dimensions**: A0, A1, 24×36, 36×48, or custom WxH (mm)?
2. **Orientation**: portrait or landscape?
3. **Number of columns**: 2, 3, or 4?
4. **Conference/venue name**: for the header badge
5. **Style preferences**: color scheme, reference posters to match?

### Optional questions:
- Institutional logos to include?
- Project page URL for QR code?
- Specific figures to highlight?

**Do NOT proceed until user confirms.**

---

## Phase PS2: Resource Collection

1. **Convert figures** (PDF→PNG, cross-platform):
   ```bash
   python scripts/poster_convert_figures.py --source-dir <paper_dir>/figures --output-dir <paper_dir>/poster
   ```
   This measures aspect ratios and generates `figure-aspects.json` for column assignment.

2. **Download logos** to `poster/logos/` (auto-inverted in header via CSS).

3. **Generate QR codes**:
   ```bash
   curl -sL -o poster/qr.png "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=PROJECT_URL"
   ```

---

## Phase PS3: Generate Poster HTML

```bash
python scripts/poster_generate.py --project-dir <paper_dir> --dimensions A0 --orientation landscape --columns 3
```

Then customize `poster/index.html`:
1. Update `CARD_REGISTRY` with paper content (one card per poster section)
2. Update `DEFAULT_LAYOUT` with aspect-ratio-optimized column assignments
3. Update `DEFAULT_LOGOS` with institutional logos
4. Update header (title, authors, affiliations, conference badge)
5. Replace all `FILL_IN` placeholders

### Card Content Patterns
- **Figure**: `<div className="fig"><div className="fig-wrap"><img src="file.png" alt="..." /></div><div className="cap"><b>Title.</b> Desc.</div></div>`
- **Text**: `<div className="hl"><p>Highlight</p></div><ul><li>Point 1</li></ul>`
- **Table**: `<table>...</table>` with `className="best"` on winning cells
- **Equation**: `<div className="eq">{'$LaTeX$'}</div>` (escape backslashes)

---

## Phase PS4: Layout Optimization (Playwright)

```bash
# Sweep column widths + export PDF
python scripts/poster_optimize.py --project-dir <paper_dir> --sweep --pdf --screenshot
```

This:
1. Opens poster in Chromium headless
2. Measures baseline whitespace via `posterAPI.getWaste()`
3. Sweeps column width combinations to minimize waste
4. Exports print-ready PDF at exact poster dimensions
5. Saves screenshot preview and optimization report

### Manual Optimization
Open `poster/index.html` in browser:
- **Drag column dividers** to resize columns
- **Drag row dividers** to resize cards within columns
- **Click-to-swap**: click one card's ✥ handle, then another's
- **Move/insert**: click a card's handle, then click a drop zone
- **A-/A+**: adjust font scale globally
- **Copy Config**: copies layout JSON to clipboard → paste to Claude

---

## Phase PS5: Quality Loop + User Iteration

```bash
python scripts/poster_validate.py --project-dir <paper_dir>
```

### Quality Scoring Rubric
Start at 100; deduct per severity:
- **CRITICAL** (broken layout, missing index.html, dimension mismatch): −15 each
- **MAJOR** (FILL_IN placeholders, missing assets, no grow cards): −5 each
- **MINOR** (missing QR, font-scale): −1 each

**Thresholds**: ≥85 Ready | 70–84 Acceptable | <70 Must Fix

### User Iteration Workflow
1. User opens poster in browser and adjusts layout
2. User clicks **Copy Config** → pastes JSON to Claude
3. Claude updates `DEFAULT_LAYOUT`, `DEFAULT_CARD_HEIGHTS`, `DEFAULT_FONT_SCALE`, `DEFAULT_LOGOS` in `index.html`
4. Claude writes config to `poster-config.json`
5. User refreshes and clicks **Reset** to load new defaults
6. Repeat until satisfied (max 3 rounds)

### Final Export
```bash
# Generate thumbnail
python scripts/poster_thumbnail.py --poster-pdf poster/poster.pdf

# Re-validate
python scripts/poster_validate.py --project-dir <paper_dir>
```

---

## Size Guidelines

| Name | Dimensions (mm) | Typical Use |
|------|-----------------|-------------|
| A0 | 841 × 1189 | Large conference poster |
| A1 | 594 × 841 | Standard conference poster |
| 24×36 in | 610 × 914 | US standard |
| 36×48 in | 914 × 1219 | US large |

## Typography

| Element | Minimum Size |
|---------|-------------|
| Title | 72–96pt |
| Section headers | 36–48pt |
| Body text | 24–32pt |
| Captions | 20–24pt |

Font sizes scale via `--font-scale` CSS variable. Default: 1.3.

---

## Programmatic API (window.posterAPI)

Available in browser console or via Playwright:
- `swapCards(id1, id2)` — swap two cards
- `moveCard(cardId, colId, position)` — move card to position
- `setColumnWidth(colId, widthMm)` — set column width (null for flex)
- `setCardHeight(cardId, heightMm)` — set explicit card height
- `setFontScale(scale)` — set global font scale
- `getWaste()` — measure whitespace in figure containers
- `getLayout()` — get current rendered layout
- `getConfig()` — get serializable config
- `resetLayout()` / `saveConfig()` / `copyConfig()`

---

## Known Limitations

- **KaTeX** does not support all LaTeX commands (e.g., `\DeclareMathOperator`, some AMS environments). Keep equations simple.
- **CDN dependencies** require internet access. Future: `--offline` flag to inline JS.
- **Playwright headless** on Linux may need `--no-sandbox` (handled by scripts).
- **SVG figures** require manual conversion to PNG before use.
