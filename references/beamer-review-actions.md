# Beamer Slide Review Actions

Purpose: definitions for review, audit, pedagogy, excellence, validate, and visual-check actions on Beamer slides.

---

## `review` (Proofreading)

Read-only report, no file edits.

### 5 Check Categories

| Category | What to check |
|----------|---------------|
| Grammar | Subject-verb, articles, prepositions, tense consistency |
| Typos | Misspellings, duplicated words, unreplaced placeholders (`[TODO]`, `[XXX]`) |
| Overflow | Long equations without `\resizebox`, too many items per slide |
| Consistency | Citation format, notation, terminology, box usage, denominator consistency |
| Academic quality | Informal abbreviations, claims without citations, ambiguous abbreviations |

### Report Format
```
### Issue N: [Brief description]
- **Location:** [slide title or line number]
- **Current:** "[exact text]"
- **Proposed:** "[fix]"
- **Category / Severity:** [Category] / [High|Medium|Low]
```

---

## `audit` (Visual Layout)

### Check Dimensions
- **Overflow:** Content exceeding boundaries, wide tables/equations
- **Font consistency:** Inline size overrides, inconsistent sizes
- **Box fatigue:** 2+ boxes per slide, wrong box types
- **Spacing:** `\vspace` overuse, structural issues
- **Layout:** Missing transitions, missing framing sentences

### Spacing-First Fix Principle (priority order)
1. Reduce vertical spacing (structural changes)
2. Consolidate lists
3. Move displayed equations inline
4. Reduce image/table size with `\resizebox`
5. **Last resort:** `\footnotesize` (never `\tiny`)

---

## `pedagogy` (Pedagogical Validation)

### 13 Patterns to Validate

| # | Pattern | Red flag |
|---|---------|----------|
| 1 | Motivation before formalism | Definition without context |
| 2 | Incremental notation | 5+ new symbols on one slide |
| 3 | Worked example after definition | 2 consecutive definitions, no example |
| 4 | Progressive complexity | Advanced concept before prerequisite |
| 5 | Fragment reveals (problem→solution) | Dense theorem revealed all at once |
| 6 | Standout slides at pivots | Abrupt topic jump, no transition |
| 7 | Two-slide strategy for dense theorems | Complex theorem crammed in 1 slide |
| 8 | Semantic color usage | Binary contrasts in same color |
| 9 | Box hierarchy | Wrong box type for content |
| 10 | Box fatigue | 3+ boxes on one slide |
| 11 | Socratic embedding | Zero questions in entire deck |
| 12 | Visual-first for complex concepts | Notation before visualization |
| 13 | Side-by-side for comparisons | Sequential slides for related definitions |

### Deck-Level Checks
- Narrative arc
- Pacing (max 3–4 theory slides before example)
- Visual rhythm (section dividers every 5–8 slides)
- Notation consistency
- Student prerequisite assumptions

---

## `excellence` (Multi-Dimensional Review)

### Parallel Dispatch (5 concurrent checks)
1. **Visual audit** — overflow, font consistency, box fatigue, spacing, transitions
2. **Pedagogical review** — 13 patterns + deck-level checks
3. **Proofreading** — grammar, typos, citation consistency, academic quality
4. **TikZ review** (if applicable) — label overlaps, geometric accuracy, visual semantics
5. **Domain review** (optional) — assumption stress test, derivation verification, citation fidelity

### Combined Report Format
```markdown
# Slide Excellence Review: [Filename]

## Overall Quality Score: [EXCELLENT / GOOD / NEEDS WORK / POOR]

| Dimension | Critical | Major | Minor |
|-----------|----------|-------|-------|
| Visual/Layout | | | |
| Pedagogical | | | |
| Proofreading | | | |
| TikZ (if any) | | | |

### Critical Issues (Immediate Action Required)
### Major Issues (Next Revision)
### Recommended Next Steps
```

### Quality Score Rubric

| Score | Critical | Medium | Meaning |
|-------|----------|--------|---------|
| Excellent | 0–2 | 0–5 | Ready to present |
| Good | 3–5 | 6–15 | Minor refinements |
| Needs Work | 6–10 | 16–30 | Significant revision |
| Poor | 11+ | 31+ | Major restructuring |

---

## `validate` (Quantitative Checks)

### Checks Performed
1. **Slide count vs. duration** — compare against timing allocation table
2. **Aspect ratio** — expected 16:9 (364.19 × 272.65 pts at 10pt)
3. **File size** — >50 MB warning, >100 MB critical
4. **Compilation health** (from .log): overfull hbox, undefined refs, multiply defined labels
5. **Source code static checks** (from .tex):
   - `\pause` / `\onslide` / `\only` usage → must be 0 (Hard Rule 1)
   - Slides with >2 colored boxes → flag (Hard Rule 2)
   - `\tiny` usage → must be 0 (Hard Rule 13)
   - Missing `\begin{thebibliography}` → warn (Hard Rule 11)

### Report Format
```
# Validation Report: [Filename]

| Check | Result | Status |
|-------|--------|--------|
| Slide count | N slides / Xmin duration | OK / WARNING |
| Aspect ratio | 16:9 | OK |
| File size | X.X MB | OK / WARNING |
| Overfull hbox | N warnings | OK / CRITICAL |
| Undefined references | N | OK / CRITICAL |
| Overlay commands | N found | OK / VIOLATION |
| Box fatigue violations | N slides | OK / WARNING |
| References slide | Present / Missing | OK / WARNING |

Overall: PASS / PASS WITH WARNINGS / FAIL
```

---

## `visual-check` (PDF-Based Inspection)

### Workflow
1. Compile (if not already compiled)
2. Convert PDF to images (PyMuPDF or read PDF directly)
3. Per-slide inspection:
   - [ ] No text overflow at any edge
   - [ ] No content overflowing inside colored boxes
   - [ ] All text legible
   - [ ] Tables and equations fit within slide width
   - [ ] TikZ labels not overlapping
   - [ ] Consistent font sizes
   - [ ] Adequate contrast
   - [ ] No visual clutter
4. Report per issue with slide number, description, severity, fix recommendation
