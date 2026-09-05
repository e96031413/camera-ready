# Beamer Slide Creation Workflow (Phase 0–5)

Purpose: full lifecycle for academic Beamer presentations, from material analysis to quality-assured delivery.

## 14 Hard Rules (Non-Negotiable)

1. **No overlays** — no `\pause`, `\onslide`, `\only`; use separate slides instead
2. **Max 2 colored boxes per slide** — preserve emphasis
3. **Motivation before formalism** — always explain "why" before "what"
4. **Worked example within 2 slides** of every definition
5. **XeLaTeX only** — never pdflatex
6. **Beamer .tex is single source of truth** — all content originates here
7. **Verify after every task** — compile, check warnings, open PDF
8. **Telegraphic style** — keyword phrases, not full sentences
9. **Every slide earns its place** — at least one substantive element
10. **Box-interior overflow guard** — limit box content; visually verify every box
11. **References slide** — second-to-last slide before Thank You
12. **Color contrast ≥ 4.5:1** (WCAG AA); avoid red+green binary contrasts
13. **Never use `\tiny`** for user-facing content
14. **Backup slides** — 3–5 slides after Thank You using `\appendix`

---

## Phase 0: Material Analysis

When source papers/materials are provided:
- Read the full paper/materials thoroughly
- Extract: core contribution, key techniques, main theorems, comparison with prior work
- Map notation conventions
- Identify logical structure and which parts are slide-worthy
- Note: prerequisite knowledge, natural section boundaries, what could be skipped or expanded

For paper-grounded slides: use `notes/codebase-snapshot.md` or the paper's `main.tex` as source material.

**Do NOT present results or ask questions yet — proceed to Phase 1.**

---

## Phase 1: Needs Interview (MANDATORY)

### Minimum required questions (always ask):
1. **Duration**: How long is the presentation?
2. **Audience level**: Who are the listeners?

### Content-driven questions (derive from Phase 0):
- **Prerequisite knowledge**: List concrete technical dependencies
- **Content scope**: Which sections to emphasize, skip, or briefly mention
- **Depth vs. breadth**: Intuitive overview or detailed constructions
- **Paper-specific decisions**: e.g., present both constructions equally or focus on one

### Slide Count Heuristic

| Duration | Total slides | Intro/Motivation | Methods/Background | Core content | Summary |
|----------|-------------|------------------|-------------------|-------------|---------|
| 5min (lightning) | 5–7 | 1–2 | 0–1 | 2–3 | 1 |
| 10min (short) | 8–12 | 2 | 1–2 | 4–5 | 1 |
| 15min (conference) | 10–15 | 2–3 | 2–3 | 5–7 | 1–2 |
| 20min (seminar) | 13–18 | 3 | 2–3 | 6–9 | 2 |
| 45min (keynote) | 22–30 | 4–5 | 5–7 | 10–14 | 2–3 |
| 90min (lecture) | 45–60 | 5–6 | 8–12 | 25–35 | 3–4 |

### Talk-Type Tips

| Talk type | Key emphasis | Common mistake |
|-----------|-------------|----------------|
| Lightning (5min) | One core message, no background review | Cramming a full talk into 5 minutes |
| Conference (10–20min) | 1–2 key results, fast methods overview | Too much technical detail, no big picture |
| Seminar (45min) | Deep dive OK, but need visual rhythm | Wall-to-wall formulas without examples |
| Defense/Thesis | Demonstrate mastery, systematic coverage | Skipping motivation, rushing results |
| Journal club | Critical analysis, facilitate discussion | Summarizing without evaluating |
| Grant pitch | Significance → feasibility → impact | Too technical, not enough "why it matters" |

**Time distribution**: 40–50% on core content. Max 3–4 consecutive theory-heavy slides before a worked example or visual break.

---

## Phase 1.5: Academic Talk Narrative Arc (Recommended Default)

The narrative arc below is the **default structure template** for academic research presentations. It builds audience understanding progressively: from *why this research direction matters* → *what challenges exist* → *how we solve them* → *what we achieved*.

### 9-Step Narrative Structure

```
┌─ Act I: Context & Motivation ────────────────────────────┐
│  1. Research Objective   — one-sentence problem statement │
│  2. Application Scenario — real-world relevance           │
│  3. Related Work Chain   — storytelling through RW        │
│     3a. RW₁ + its limitations                            │
│     3b. RW₂ solves RW₁'s gaps → new limitations          │
│     3c. Challenge Summary — what THIS talk solves         │
│  4. Talk Overview        — contributions roadmap          │
├─ Act II: Contributions (repeat per contribution) ────────┤
│  5. Contribution k                                        │
│     5a. Task Setting    — what are we trying to do?       │
│     5b. Challenge       — why is it hard?                 │
│     5c. Core Idea       — key insight (1–2 sentences)     │
│     5d. Method          — how it works (diagram + math)   │
│     5e. Results         — evidence it works (table/plot)  │
│  6. Contribution k+1 … (same pattern)                    │
├─ Act III: Closure ───────────────────────────────────────┤
│  7. Conclusion          — recap key results               │
│  8. Future Work         — open questions, next steps      │
│  9. References + Q&A                                      │
└──────────────────────────────────────────────────────────┘
```

### Narrative Arc Slide Budget (by duration)

| Duration | Act I (Context) | Act II (Contributions) | Act III (Closure) | Refs+Thanks | Backup |
|----------|----------------|----------------------|------------------|-------------|--------|
| 5min     | 2              | 2–3                  | 1                | 1           | 2–3    |
| 10min    | 3–4            | 4–5                  | 1–2              | 1–2         | 3–4    |
| 15min    | 5–6            | 6–8                  | 2                | 2           | 3–5    |
| 20min    | 5–7            | 8–10                 | 2–3              | 2           | 3–5    |
| 45min    | 8–10           | 14–18                | 3–4              | 2           | 4–6    |

### Step 3: Related Work as Storytelling Chain

The related work section is **not** a flat survey. It is a **narrative chain** that builds tension toward your contribution:

```
RW₁ (established approach)
  ↓ "but it faces challenge X"
RW₂ (addresses challenge X)
  ↓ "but it introduces new challenge Y"
  ↓ … (repeat if needed)
RWₙ
  ↓ "leaving open challenge Z"
═══════════════════════════
Challenge Summary slide:
  "This talk addresses challenges X', Y', Z'"
```

**Rules for the chain:**
- Each RW slide: **contribution** (what it does well) + **limitation** (what it cannot do) — use `\pos{}` and `\con{}` semantic colors
- The chain must logically connect: RW₂ should address RW₁'s gap
- The final limitation of the chain = the motivation for THIS work
- **Challenge Summary slide** (mandatory): consolidate all open challenges into one slide; each challenge maps to a contribution in Step 5+

**Anti-patterns:**
- ❌ Listing 10 related works with one bullet each (flat survey)
- ❌ Spending 3+ slides on a single related work (too deep)
- ❌ Challenge summary that doesn't match the contributions

### Step 5: Per-Contribution Section Pattern

Each contribution follows a **fixed 5-part micro-structure**. Depending on talk duration, these parts may occupy 1–3 slides:

| Part | Content | Slide tip |
|------|---------|-----------|
| **Task Setting** | Formal problem definition; input/output | Can merge with Challenge on one slide |
| **Challenge** | Why naive/prior approaches fail | Use `\con{}` to highlight difficulty |
| **Core Idea** | The key insight in 1–2 sentences | Frame as "Our key observation is…" |
| **Method** | Architecture/algorithm/design — prefer TikZ diagram | Largest part; may span 1–2 slides |
| **Results** | Table, plot, or key numbers proving it works | Use `\HL{}` for headline numbers |

**For short talks (≤15 min):** merge Task+Challenge into one slide; merge Core Idea+Method into one slide; share a combined Results slide across contributions.

**For long talks (≥30 min):** each part gets its own slide; add worked examples between Method and Results.

### Step 8: Future Work Guidelines

- 3–5 concrete directions (not vague "improve performance")
- Each direction: one sentence + why it matters
- Optional: categorize as short-term / long-term
- This slide naturally invites Q&A questions

---

## Phase 2: Structure Plan (GATE — user must approve)

Produce a detailed outline **following the Narrative Arc** (Phase 1.5). For each section:
- Section title
- Number of slides allocated
- Key content points per slide (1–2 lines each)
- TikZ diagrams or figures planned (brief description)
- Notation to introduce
- Which Narrative Arc step it corresponds to (1–9)

The structure plan must include:
1. **Challenge-contribution mapping**: each challenge from the Summary slide maps to exactly one contribution section
2. **Related work chain**: the logical sequence of RW₁ → RW₂ → … → open challenge
3. **Per-contribution breakdown**: which of the 5 parts (task/challenge/idea/method/results) get dedicated slides vs. merged slides

**Do NOT proceed to drafting until user approves.**

---

## Phase 3: Draft (iterative, batched)

### Writing Style
- **Telegraphic keywords**, not full sentences (one framing sentence per slide is OK)
- **Formulas and analysis interleave tightly** — define, then immediately show cost/property/implication
- **No conversational hedging** — never "wait, not exactly" or "actually, let me clarify"
- Use `\textbf{}` for key terms on first introduction; `\pos{...}` for positive, `\con{...}` for drawbacks, `\HL{...}` for key findings

### Opening Strategies (pick one):
- **Surprising statistic** — a counter-intuitive number
- **Provocative question** — something the audience cannot immediately answer
- **Real-world failure/problem** — "System X failed because..."
- **Visual demonstration** — show the phenomenon before explaining
- **Goal-then-gap** (recommended for Narrative Arc) — state the research objective, then immediately show why current approaches fall short → leads naturally into the RW chain

### Closing Strategies:
- **Call-back to opening** — revisit the opening question, now answered
- **3 key takeaways** — numbered, telegraphic, one slide
- **Open question / future direction** — invites Q&A
- **Never end on a bare "Thank You"** — the second-to-last content slide delivers the lasting impression

### Mathematical Slide Patterns

**Definition slide:**
```
[Framing sentence: why this definition matters]
[Formal definition in display math]
[Key properties / immediate consequences as 2-3 bullet items]
```

**Construction/Algorithm slide:**
```
[One-line goal statement]
[Core equation / algorithm steps]
[Complexity analysis: prover cost, verifier cost, soundness]
```

**Comparison slide:**
```
[Side-by-side table: prior work vs this work]
[1-2 lines highlighting the key difference]
```

**Theorem/Proof slide:**
```
[Framing sentence: informal statement of the result]
\begin{theorem}[Optional name]
  [Formal statement]
\end{theorem}
[Key implication as 1-2 bullets]
```
- Proof on the **next** slide (never theorem + proof on one slide)
- For long proofs: proof sketch only; full proof in backup slides

### Content Density Constraints

**Upper bounds (per slide):**
- ≤ 7 bullet points
- ≤ 2 displayed equations
- ≤ 5 new symbols introduced
- ≤ 2 colored boxes

**Lower bounds (per slide):**
- Each slide MUST contain at least one substantive element
- A slide with only ≤ 3 short text-only bullets is too sparse — merge or enrich
- Pure text-only bullet slides ≤ 30% of total deck

### Batch Workflow
- Work in batches of 5–10 slides, following the approved structure
- After each batch: self-check notation consistency, density constraints, motivation-before-formalism
- Continue only after current batch passes self-check

### Table Best Practices
- Always `booktabs` (`\toprule`, `\midrule`, `\bottomrule`) — never vertical lines
- Numbers right-aligned, text left-aligned, short labels centered
- Max 6–7 columns, 8–10 rows per slide
- Highlight key cells with `\cellcolor{positive!15}` or `\textbf{}`

### Algorithm and Code Display
- Pseudocode ≤ 10 lines per slide
- Highlight critical line(s) via `escapeinside` or `\colorbox`
- Input/output clearly stated at top

---

## Phase 4: Figures

- TikZ diagrams in Beamer source (single source of truth)
- Apply TikZ quality standards (see `references/beamer-tikz-standards.md`)

### Data Visualization (slide ≠ journal figure)
- **Simplify ruthlessly** — remove minor gridlines, detailed legends
- **Enlarge everything** — axis labels ≥ 18pt, line width 2–4pt, marker size 8–12pt
- **Direct labeling** — label lines/bars directly instead of separate legend
- **One message per figure** — split multi-panel journal figures across slides
- **Highlight the result** — key data in bold saturated color, comparison in muted gray
- **Color-blind safe** — blue+orange over red+green; add line style differences
- **Progressive disclosure** — build complex figures incrementally across separate slides

---

## Phase 5: Quality Loop (MANDATORY — iterative)

```
┌─→ 5a. Compile (2-pass XeLaTeX via compile_slides.py)
│   5b. Self-Review (structure + content + visual)
│   5c. Score (apply rubric, start at 100)
│   5d. Fix all issues found
└── If score < 90 and round < 3: loop back to 5a
    If score ≥ 90 or round = 3: report to user
```

### Scoring Rubric
- **Critical issues** (overflow, undefined refs): −10 to −20 each
- **Major issues** (sparse slides, notation inconsistency, TikZ inaccuracy): −3 to −10
- **Minor issues** (`\vspace` overuse, spacing): −1

**Thresholds**: ≥90 Ready | 80–89 Acceptable | <80 Must Fix

### Self-Review Checklist

**Structure (Narrative Arc):**
- [ ] Slide count matches plan (±2 tolerance)
- [ ] Narrative Arc: objective → application → RW chain → challenges → contributions → conclusion → future
- [ ] Challenge Summary slide present; each challenge maps to a contribution
- [ ] Per-contribution sections follow task → challenge → idea → method → results pattern
- [ ] No section has >4 consecutive formal slides without example or visual break
- [ ] Transition sentences between major sections

**Content density:**
- [ ] No slide has only ≤3 short bullets with no math/diagram
- [ ] Pure text-only slides ≤ 30%
- [ ] No slide exceeds upper bounds (7 bullets, 2 equations, 5 symbols, 2 boxes)

**TikZ and visuals:**
- [ ] No label overlaps
- [ ] No content overflowing slide boundary or inside colored boxes
- [ ] All marked points computed via `\pgfmathsetmacro`
- [ ] Tables fit within slide width

**Notation:**
- [ ] Same symbol used consistently
- [ ] Every symbol defined before use

### Post-Creation Final Gate
```
[ ] Compiles without errors
[ ] No overfull hbox > 10pt
[ ] All citations resolve
[ ] Score ≥ 90
[ ] Every definition has motivation + worked example
[ ] Max 2 colored boxes per slide
[ ] No sparse slides
[ ] TikZ diagrams visually verified
[ ] References slide present (second-to-last)
[ ] Backup slides after \appendix
```

### Verification Protocol (after every task)
```
[ ] Compiled without errors (xelatex exit code 0)
[ ] No overfull hbox > 10pt
[ ] All citations resolve
[ ] PDF opens correctly
[ ] Visual spot-check of changes
```

---

## Common Troubleshooting

| Problem | Solution |
|---------|----------|
| `Undefined control sequence. \llbracket` | Add `\usepackage{stmaryrd}` |
| Overfull vbox | Reduce `\vspace` → shorten text → split → `\small` → `\footnotesize` |
| Content overflows inside blocks | Beamer suppresses warnings; visually verify. Remove `\vspace`, limit to one equation or few bullets |
| Equations overflow slide width | Use `\begin{align}` with breaks → introduce variables → `\resizebox` (last resort) |
