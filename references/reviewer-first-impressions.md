# Reviewer First Impressions Guide

Purpose: codify what experienced reviewers notice first and weight heavily — layout quality, experimental coverage, and narrative coherence. Apply these principles during writing (Phase 2), self-review (Phase 2.55), and reviewer simulation (Phase 2.5).

---

## 1. Layout / Aesthetics / Figures

Reviewers scan the full paper visually before reading. First impressions are hard to reverse.

### Non-Negotiables
- **No overflow**: equations, figures, and tables must never exceed column/page margins. An `Overfull \hbox` on a formula is treated as author negligence — immediate impression penalty.
- **Readable labels**: all axis labels, legend text, and table entries must be legible at print size (≥8pt). If a reviewer must zoom to read result figures, it signals disregard for the reader.
- **Consistent style**: uniform font families, line weights, and color palettes across all figures. Mixed matplotlib defaults and hand-drawn diagrams look careless.

### High-Impact Visual Elements
| Element | Reviewer expectation | Impression effect |
|---|---|---|
| **Motivation figure** (Fig 1) | Conveys the core problem/gap in one glance | Positive: reviewer immediately "gets" the paper; Negative if missing or unclear |
| **Method overview figure** | Shows the full pipeline/architecture clearly and aesthetically | Strong positive if well-designed; reviewer uses it as a mental map for the rest of the paper |
| **Result figures/tables** | Dense but readable; many benchmarks visible at a glance | Conveys thoroughness; sparse results signal weak evaluation |

### Aesthetic Targets
- Paper should look "visually dense with information" on a quick scroll: clear method figure, multiple result tables/plots, ablation figures.
- Aim for ≥1 figure or table per 1.5 pages of main text.
- Method overview should be a `figure*` (full-width) in the first 2-3 pages.
- Use vector graphics (PDF/EPS) for all plots; raster only for photos/screenshots.

---

## 2. Experimental Coverage

Reviewers check whether experiments are comprehensive enough to support claims. Insufficient coverage is a standard Weakness.

### Model Family Coverage
- **Minimum**: ≥2 distinct model families (e.g., Llama + Qwen + Mistral). Single-family results (Llama only) are a clear weakness.
- **Version consistency**: use the latest available versions within each family at submission time. Mixing older versions of one family with newer versions of another raises suspicion that unfavorable results were intentionally avoided.
- **Scale diversity**: include both small (≤10B) and large (≥30B) parameter models when possible. Large-scale results are a strong positive signal. If compute is limited, state it explicitly rather than leaving the gap unexplained.
- **Red flag**: cherry-picking model versions or sizes that favor your method.

### Dataset Coverage
- **Minimum**: ≥3 diverse datasets/benchmarks. One or two datasets is a standard weakness in current top-venue submissions.
- **Diversity**: span different task types, domains, or difficulty levels to demonstrate generalization.
- **Rationale**: all ideas sound reasonable on paper — the differentiator is breadth of evidence. More datasets = stronger empirical credibility.

### Baseline Coverage
- **Recency**: must include methods from top venues in the last 1-2 years. Missing recent baselines is an easily identifiable weakness.
- **Breadth**: ≥5 baselines for the main comparison table. Include both classic and SOTA methods.
- **Fairness**: use the same evaluation protocol for all baselines. If re-implementing, state it clearly.
- **Red flag**: omitting a well-known recent method without justification.

### Presentation of Results
- More results are generally better — unless they contradict your claims. Ablations, scaling curves, qualitative examples, and error analyses all add credibility.
- Organize results logically: main comparison → ablation → analysis → qualitative.
- Every table/figure should have a clear takeaway stated in the text.

---

## 3. Idea / Storytelling

Reviewers assess whether the narrative is coherent and the contribution is clear, even if they are not domain experts.

### Introduction Quality
- The motivation must be compelling and concrete — not generic ("LLMs are important").
- The research gap should be specific and well-evidenced (cite prior work that fails or is insufficient).
- Contributions should be listed as concrete, falsifiable claims (not vague "we explore...").

### Method Positioning
- Clearly identify the pain point of prior work that your method addresses.
- If proposing a new insight, explain why it opens new directions (not just marginal improvement).
- The method should feel like a natural solution to the stated problem — not a technique searching for a problem.

### Narrative Coherence
- The story should flow: problem → gap → insight → method → evidence → conclusion.
- Each section should build on the previous one. No "new facts" in the conclusion.
- AI-assisted writing has raised the baseline for narrative quality — a disjointed story stands out more than ever.

### Practical Advice
- A well-told story with modest results often scores higher than strong results with poor framing.
- Reviewers increasingly cannot distinguish idea quality by novelty alone — execution and evidence matter more. "All ideas sound equally reasonable; the winner shows more evidence."
- If the method is incremental, frame it honestly as a practical improvement with thorough empirical validation, not as a paradigm shift.

---

## Integration Checklist

Use during self-review (Phase 2.55) and reviewer simulation (Phase 2.5):

```
Layout / Aesthetics:
- [ ] No Overfull \hbox warnings in compile log
- [ ] All figure/table labels ≥8pt at print size
- [ ] Motivation figure in first 2 pages conveys the problem clearly
- [ ] Method overview figure is full-width, aesthetically polished
- [ ] Result figures are information-dense but readable without zooming
- [ ] ≥1 figure or table per 1.5 pages of main text
- [ ] All plots in vector format (PDF/EPS)
- [ ] Consistent visual style across all figures

Experimental Coverage:
- [ ] ≥2 model families with latest versions
- [ ] Scale diversity (small + large models, or justified limitation)
- [ ] ≥3 diverse datasets/benchmarks
- [ ] ≥5 baselines including methods from last 1-2 years
- [ ] Results organized: main → ablation → analysis → qualitative
- [ ] Every table/figure has a clear takeaway in text

Idea / Storytelling:
- [ ] Introduction has concrete motivation (not generic)
- [ ] Research gap is specific and cited
- [ ] Contributions are falsifiable claims
- [ ] Method is positioned against specific prior-work pain points
- [ ] Narrative flows: problem → gap → insight → method → evidence → conclusion
- [ ] No new claims in conclusion
```
