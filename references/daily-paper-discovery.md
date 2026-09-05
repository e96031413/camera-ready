# Daily Paper Discovery

Purpose: systematic arXiv monitoring to stay current with research trends. Use to maintain awareness of latest work during paper writing.

## Search Strategy

- Define 3-5 keyword groups covering your topic from different angles
- Search arXiv with date sorting (most recent first)
- Default window: last 3 months
- Check both primary category (e.g., cs.CL) and cross-listed categories
- Supplement with Semantic Scholar and Google Scholar alerts

### Example Keyword Groups
```
Group 1 (core): "large language model" + "reasoning"
Group 2 (method): "chain of thought" OR "tree of thought"
Group 3 (application): "code generation" + "benchmark"
Group 4 (adjacent): "instruction tuning" + "alignment"
```

## Quality Evaluation

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Innovation | 30% | Novel approach, insight, or formulation? |
| Method | 25% | Sound methodology? Complete description? Reproducible? |
| Experiments | 25% | Thorough evaluation? Proper baselines? Statistical rigor? |
| Writing | 10% | Clear presentation? Well-structured? |
| Relevance | 10% | Directly relevant to your current research? |

### Scoring
- Rate each dimension 1-5
- Compute weighted sum: Innovation×0.30 + Method×0.25 + Experiments×0.25 + Writing×0.10 + Relevance×0.10
- **Threshold**: ≥ 3.5 for inclusion in reading list
- **Priority read**: ≥ 4.0. For priority reads from your target venue, apply `references/paper-mining.md` to extract actionable writing knowledge (IMRaD framing, structure, hooks)

## Summary Format

For each paper meeting the threshold, produce:

```markdown
## [Paper Title]
- **Authors**: First Author, ...
- **Link**: https://arxiv.org/abs/XXXX.XXXXX
- **Score**: X.X / 5.0
- **Summary (Chinese)**: ~300 words covering motivation, method, results
- **Summary (English)**: ~200 words, technical summary
- **Key Contributions**:
  1. ...
  2. ...
- **Relevance to Our Work**: How this connects to your paper
- **Potential Use**: Cite as related work / baseline / methodology reference
```

## File Naming

```
daily-paper/YYYY-MM-DD-HHMM-paper-N.md
```

- Example: `daily-paper/2026-03-12-0900-paper-1.md`
- One file per paper for easy tracking and retrieval
- Create the `daily-paper/` directory at project root

## Weekly Review

- Every 5-7 days, consolidate findings into a brief trends summary
- Identify emerging patterns: new methods gaining traction, shifting benchmarks
- Update your related work section if a new relevant paper appears

## Integration

- Discovered papers feed into Gate 0 research snapshot (see `references/research-workflow.md`)
- High-relevance papers feed into per-section research in Phase 2
- Use `arxiv_registry.py` to cache BibTeX and avoid duplicates
