# AAAI Reproducibility Checklist — Question Set

Source: AAAI author kit and reproducibility checklist,
<https://aaai.org/authorkit/>.
Answer options: Yes / No / NA.

**Before submission**: re-check this file's wording against the current AAAI
author kit. AAAI administers the reproducibility checklist through the
submission form, and it revises the questions between editions. This file
**paraphrases** the official topics; it is not a verbatim copy.

AAAI enforces its formatting rules strictly and rejects papers that modify
the style file, change margins, or shrink the references. Run
`python scripts/format_gate.py --project-dir <paper_dir> --venue aaai` before
submitting, and read the author kit's list of prohibited LaTeX packages.

## 1. Claims
**Question:** Do the abstract and introduction state the main claims, including the contributions and the scope in which they hold?
**Guidance:** Reviewers score novelty against the claims. Overclaiming is the most common cause of a low soundness score.

## 2. Limitations
**Question:** Does the paper describe the limitations of the approach?
**Guidance:** A Limitations subsection or an explicit paragraph in the conclusion.

## 3. Related Work
**Question:** Does the paper position the contribution against the relevant prior work, with citations?
**Guidance:** AAAI reviewers frequently reject for missing closely related work. Search beyond the last two years.

## 4. Theoretical Contributions — Assumptions
**Question:** For each theoretical result, does the paper state the complete set of assumptions?
**Guidance:** NA if the paper makes no theoretical claims.

## 5. Theoretical Contributions — Proofs
**Question:** Is a complete proof provided for every theoretical result, in the paper or the appendix?
**Guidance:** A proof sketch in the main text with the full proof in the appendix is acceptable. NA if the paper makes no theoretical claims.

## 6. Datasets — Description
**Question:** Does the paper describe every dataset used, including how it was collected or obtained?
**Guidance:** NA if the paper runs no experiments on data.

## 7. Datasets — Availability and Licensing
**Question:** Are the datasets publicly available, or does the paper explain the access restriction and state the license?
**Guidance:** Cannot be inferred automatically — the author must confirm this.

## 8. Datasets — Preprocessing and Splits
**Question:** Does the paper specify the preprocessing steps and the train/validation/test splits, including how they were produced?
**Guidance:** State whether the split is a standard one or newly created.

## 9. Code Availability
**Question:** Is the source code available, with instructions sufficient to reproduce the main results?
**Guidance:** Use an anonymized repository at submission time. AAAI review is double-blind.

## 10. Experimental Setup
**Question:** Does the paper specify the model architecture, the hyperparameters, and the procedure used to select them?
**Guidance:** Report the search space and the selection criterion, not only the final values.

## 11. Compute Resources
**Question:** Does the paper report the computing infrastructure and the runtime for the reported experiments?
**Guidance:** Hardware type, count, and wall-clock time.

## 12. Number of Runs and Variability
**Question:** Does the paper report how many times each experiment was run and the resulting variability?
**Guidance:** State the number of seeds and what the reported interval represents. A single run should be labelled as such.

## 13. Statistical Comparison
**Question:** For claims that one method outperforms another, does the paper support the comparison with an appropriate statistical test or variability measure?
**Guidance:** A difference smaller than the seed variance is not a result.

## 14. Evaluation Metrics
**Question:** Does the paper define every evaluation metric and cite the implementation used?
**Guidance:** Metric implementations differ; name the package and version.

## 15. Ethics Statement
**Question:** Does the paper include an ethics statement where the work has foreseeable societal impact, involves human subjects, or releases a potentially harmful asset?
**Guidance:** AAAI allows one additional page for this. NA only after considering each category and finding none applies.

## 16. Reproducibility of Reported Results
**Question:** Taking the paper and the released material together, could an independent researcher reproduce the main results?
**Guidance:** Cannot be inferred automatically — answer this from the reader's position, not the author's.
