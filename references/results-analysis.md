# Experimental Results Analysis

Purpose: systematic analysis of ML/AI experimental data for publication-quality presentation.

## Supported Data Formats

- CSV, TSV (tabular results)
- JSON (structured experiment logs)
- TensorBoard event files
- Pickle / NPY (serialized arrays)

## 6-Step Pipeline

1. **Data Loading** — Parse all experiment logs into a unified table
2. **Validation** — Check completeness, consistency, reproducibility
3. **Statistical Analysis** — Compute means, significance tests, effect sizes
4. **Visualization** — Generate publication-quality figures
5. **Writing** — Draft results narrative with proper statistical language
6. **Quality Check** — Verify all numbers match source data

## Data Validation Checklist

- [ ] All expected runs/seeds present (no missing entries)
- [ ] Consistent evaluation metrics across all experiments
- [ ] Results reproducible from saved checkpoints/configs
- [ ] Outliers identified and explained (not silently removed)
- [ ] Training converged (loss curves stable)

## Statistical Methods

### When to Use What

| Scenario | Test | Assumption |
|----------|------|------------|
| Compare 2 models | Paired t-test | Normal differences |
| Compare 2 models (non-normal) | Wilcoxon signed-rank | No normality assumption |
| Compare 3+ models | One-way ANOVA | Normal, equal variance |
| Compare 3+ models (non-normal) | Friedman test | No normality assumption |
| Multiple comparisons | Bonferroni / Holm correction | After ANOVA |

### Effect Size
- **Cohen's d**: small (0.2), medium (0.5), large (0.8)
- **Confidence intervals**: report 95% CI alongside p-values
- Always report effect size, not just significance

### Reporting Template
> "Method A outperforms Method B by X.X points (p < 0.01, Cohen's d = 0.72, 95% CI [X.X, X.X])."

## Visualization Requirements

- **Format**: Vector (PDF or EPS) for all figures; never rasterize plots
- **Colors**: Colorblind-safe palette (e.g., Okabe-Ito, viridis)
- **Labels**: Axis labels with units, legend inside or adjacent, readable font size (≥8pt in final print)
- **No titles inside figures** — use captions instead
- **Captions**: Self-contained; reader should understand the figure without reading main text
- **Consistency**: Same color = same method across all figures

## Results Section Structure

1. **Overview**: Brief summary of experimental setup and main findings
2. **Experimental Setup**: Datasets, metrics, baselines, hyperparameters
3. **Main Comparison**: Performance table with all baselines
4. **Ablation Study**: Contribution of each component
5. **Statistical Significance**: Tests and effect sizes
6. **Qualitative Analysis**: Examples, visualizations, case studies (if applicable)

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Cherry-picking results | Report all experiments; explain failures |
| Reporting std instead of stderr | Use stderr = std/√n for mean estimates |
| Misleading axes | Start y-axis at 0 or clearly mark truncation |
| Over-interpretation | Distinguish statistically significant from practically meaningful |
| Insufficient precision | Use consistent decimal places; match measurement precision |
| Missing baselines | Include at least one classic and one recent SOTA baseline |

## Table Best Practices

- Use `booktabs` package (no vertical lines, clean horizontal rules)
- **Bold** best values per column
- Direction symbols: ↑ (higher is better), ↓ (lower is better)
- Right-align all numbers
- Consistent decimal precision within each column
- Include ± for standard deviation/error
- Mark statistically significant improvements (e.g., with *)

### Example Format
```latex
\begin{table}[t]
\centering
\caption{Results on Dataset X. Best in \textbf{bold}. ↑ = higher is better.}
\begin{tabular}{lcc}
\toprule
Method & Acc ↑ & FLOPs ↓ \\
\midrule
Baseline A & 85.2 ± 0.3 & 4.1G \\
Baseline B & 87.1 ± 0.2 & 3.8G \\
\textbf{Ours} & \textbf{89.4 ± 0.2} & \textbf{3.2G} \\
\bottomrule
\end{tabular}
\end{table}
```

## Integration

- Results feed into Writing issues in the issues CSV
- See `references/writing-style.md` for narrative tone
- See `references/integrity-verification.md` for number verification
