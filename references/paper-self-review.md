# Paper Self-Review Checklist

Purpose: systematic quality check before submission or advisor review. Run after all writing and revision rounds converge.

## 5 Review Dimensions

### 1. Structure
- Abstract includes problem, method, results, and contributions?
- Introduction states motivation and research gap clearly?
- Method section detailed enough for reproduction?
- Results support conclusions with evidence?
- Discussion addresses limitations and future work?

### 2. Logic Consistency
- Research questions match methodology?
- Experimental design supports stated hypotheses?
- Interpretations reasonable given the data?
- Conclusions evidence-backed, not overclaimed?
- No logical gaps between sections?

### 3. Citation Completeness
- All in-text citations appear in references?
- All references cited at least once in text?
- Citation format consistent throughout (author-year vs numbered)?
- Key related work cited (check top-cited papers in your area)?
- Citations accurately reflect the source content?

### 4. Figure/Table Quality
- All figures and tables referenced in text?
- Captions informative and self-contained?
- Figures readable at print size (≥8pt labels)?
- Tables use booktabs style, no vertical lines?
- Vector format for all plots?
- Motivation figure (Fig 1) conveys the problem in one glance?
- Method overview figure is full-width and aesthetically polished?
- ≥1 figure or table per 1.5 pages of main text?
- Consistent visual style (fonts, colors, line weights) across all figures?

### 4b. Experimental Coverage (see `references/reviewer-first-impressions.md`)
- ≥2 model families with latest versions (no suspicious version mismatches)?
- ≥3 diverse datasets/benchmarks?
- ≥5 baselines including recent top-venue methods (last 1-2 years)?
- Scale diversity: small + large models (or justified limitation)?
- Results organized: main comparison → ablation → analysis → qualitative?
- Every table/figure has a clear takeaway stated in text?

### 5. Writing Clarity
- Language concise; no filler phrases?
- Technical terms defined on first use?
- Sentence structures varied and clear?
- Paragraph organization logical (topic sentence → support → transition)?
- Consistent terminology throughout?

## Quality Checklist

```
- [ ] Abstract includes problem, method, results, contributions
- [ ] Introduction clearly states research motivation and gap
- [ ] Method is detailed enough for reproduction
- [ ] Results support conclusions with statistical evidence
- [ ] Discussion addresses limitations and future work
- [ ] All figures/tables have informative captions
- [ ] All figures in vector format (PDF/EPS)
- [ ] Motivation figure conveys the problem in one glance
- [ ] Method overview figure is full-width and polished
- [ ] ≥1 figure/table per 1.5 pages; result figures readable without zooming
- [ ] ≥2 model families, ≥3 datasets, ≥5 baselines (incl. recent top-venue)
- [ ] Citations complete and accurately reflect sources
- [ ] No AI writing patterns (see anti-ai-writing.md)
- [ ] Meets venue page limit
- [ ] No Overfull \hbox warnings
- [ ] Consistent notation throughout
- [ ] Acronyms defined on first use
- [ ] No TODO/FIXME markers remaining
- [ ] Supplementary material referenced where needed
```

## Review Process (6 steps)

1. **Structure review** — Check overall completeness; verify all required sections present
2. **Content review** — Per-section accuracy; claims supported by evidence
3. **Citation check** — Completeness, accuracy, format consistency
4. **Figure/Table review** — Quality, captions, formatting
5. **Writing quality** — Clarity, conciseness, anti-AI check (see `references/anti-ai-writing.md`)
6. **Final checklist pass** — Run the checklist above; fix remaining items

## Best Practices

- Wait 1-2 days after completing the draft before reviewing (fresh eyes)
- Do multiple rounds, each focusing on a different dimension
- Read backwards (conclusion → intro) to check logic flow
- Read aloud to catch awkward phrasing and rhythm issues
- Adopt the reviewer perspective: "Would I accept this paper?"
- Ask a colleague to read the abstract and introduction only — can they explain your contribution?

## Integration

- Run after Phase 2 writing converges
- Complements `references/paper-reviewer.md` (external reviewer simulation)
- Anti-AI check uses `references/anti-ai-writing.md`
- Quality targets align with `references/review-rubrics.md`
