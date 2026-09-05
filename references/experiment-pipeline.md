# Experiment Pipeline: 4-Stage Budgeted Execution

Based on EvoScientist/EvoSkills methodology for systematic experiment execution with attempt budgets.

## Overview

Structured framework with budgeted stages and gate conditions to prevent rabbit holes while ensuring thorough validation. Each stage has a fixed attempt budget — if exceeded, the experiment is escalated or pivoted.

## Stage 1: Initial Implementation (≤20 attempts)

**Goal**: Reproduce baseline and validate infrastructure.

| Item | Detail |
|------|--------|
| **Budget** | ≤20 attempts |
| **Gate condition** | Baseline metric within 5% of reported value |
| **Deliverable** | Working training loop + evaluation script |
| **Failure action** | If budget exhausted: diagnose via Experiment Craft; do NOT proceed |

### Checklist
- [ ] Data loading pipeline verified (shapes, dtypes, splits)
- [ ] Baseline model runs end-to-end without errors
- [ ] Loss curve shows expected convergence pattern
- [ ] Evaluation metric matches published baseline (±5%)
- [ ] Random seed fixed for reproducibility
- [ ] Training time per epoch is reasonable

## Stage 2: Hyperparameter Tuning (≤12 attempts)

**Goal**: Optimize configuration for the target setup.

| Item | Detail |
|------|--------|
| **Budget** | ≤12 attempts |
| **Gate condition** | Best config identified; metric stable across 3 seeds |
| **Deliverable** | Tuned config file + validation curves |
| **Failure action** | If all configs underperform: check data pipeline; consider simpler model |

### Tuning Protocol
1. **Phase A** (4 attempts): Coarse grid — learning rate (1e-2, 1e-3, 1e-4, 1e-5)
2. **Phase B** (4 attempts): Batch size + scheduler (cosine vs step vs warmup)
3. **Phase C** (4 attempts): Fine-grained — narrow around best from A+B

### One Variable Rule
**Change exactly one variable per attempt.** If you change LR and batch size simultaneously, you cannot attribute improvement/regression. Log every attempt with:
- Config diff from previous attempt
- Metric delta
- Hypothesis tested

## Stage 3: Proposed Method (≤12 attempts)

**Goal**: Validate the novel contribution.

| Item | Detail |
|------|--------|
| **Budget** | ≤12 attempts |
| **Gate condition** | Method outperforms tuned baseline on primary metric |
| **Deliverable** | Method implementation + comparison table |
| **Failure action** | Invoke Experiment Craft debugging; if fundamental failure, trigger IVE (Evo-Memory) |

### Validation Checklist
- [ ] Method implemented as described in paper plan
- [ ] Fair comparison: same data splits, same compute budget, same evaluation protocol
- [ ] Statistical significance: report mean ± std across 3+ seeds
- [ ] Improvement is consistent across all evaluation metrics (not just cherry-picked)
- [ ] Computational overhead is acceptable (≤2x baseline)

## Stage 4: Ablation Study (≤18 attempts)

**Goal**: Prove each component's contribution.

| Item | Detail |
|------|--------|
| **Budget** | ≤18 attempts |
| **Gate condition** | Each component shows measurable contribution |
| **Deliverable** | Ablation table + analysis |
| **Failure action** | Remove non-contributing components; simplify method |

### Ablation Design
For a method with components A, B, C:
1. Full method (A+B+C) — already from Stage 3
2. Remove A: (B+C) — measures A's contribution
3. Remove B: (A+C) — measures B's contribution
4. Remove C: (A+B) — measures C's contribution
5. Baseline only — already from Stage 1
6. Component interaction: if A depends on B, test (A alone) vs (A+B)

### What Makes a Good Ablation
- Each row removes exactly ONE component
- Metric drop should be statistically significant
- If removing a component doesn't hurt: **remove it from the method** (simpler is better)
- Report both absolute performance and relative contribution percentage

## Budget Adjustment Rules

| Situation | Action |
|-----------|--------|
| Stage gate met early | Move remaining budget to next stage |
| Budget exhausted, gate not met | STOP — invoke Experiment Craft debugging |
| Two stages fail consecutively | Escalate to REFINE/PIVOT decision |
| Unexpected finding during experiment | Log it; create a new issue row; do not chase tangents |

## Experiment Craft: 5-Step Debugging (When Stage Fails)

Invoked automatically when a stage exhausts its budget:

1. **Collect failure cases**: What specifically went wrong? Gather error messages, loss curves, metric values
2. **Find a working version**: Identify the last configuration that worked (even partially)
3. **Bridge the gap**: Bisect between working and failing configs — isolate the breaking change
4. **Hypothesize and verify**: Form 3 hypotheses ranked by likelihood; test each with minimal experiments
5. **Propose and implement fix**: Apply the fix; verify stage gate is now met

### Cause Taxonomy
| Category | Examples |
|----------|---------|
| **Data** | Wrong preprocessing, label noise, distribution shift, data leak |
| **Model** | Architecture bug, gradient issues, wrong initialization |
| **Training** | LR too high/low, overfitting, underfitting, numerical instability |
| **Evaluation** | Wrong metric, test set contamination, implementation bug |
| **Infrastructure** | GPU memory, random seed, library version mismatch |

## Code Trajectory Logging

Every experiment attempt must be logged for Evo-Memory integration:

```
## Attempt [N] — Stage [X]
- **Config**: {key changes from previous}
- **Hypothesis**: {what we expect and why}
- **Result**: {metric values}
- **Analysis**: {why it worked/didn't}
- **Next step**: {what to try next}
```

## Integration with camera-ready

- **Input**: Experiment plan from Phase 1.5 (`notes/experiment-plan.md`)
- **Output**: Validated results → feeds into Phase 2 writing loop (experiments section)
- **Issues CSV**: Add `EX1` (baseline), `EX2` (tuning), `EX3` (method), `EX4` (ablation) issues in Experiment phase
- **Results analysis**: For systematic statistical analysis and writing of the experiments section once results are collected, see `references/results-analysis.md`
- **Evo-Memory**: Stage 3 failures trigger IVE; Stage 3+4 successes trigger ESE
