# CVPR Submission Worksheet — Question Set

Source: CVPR author guidelines,
<https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines>.
Answer options: Yes / No / NA.

**CVPR does not currently require a paper checklist.** The corresponding
venue config sets `checklist_required: false`, and
`scripts/paper_checklist.py` will not be run for CVPR by the QA gate.

This file is a **self-review worksheet**, not an official form. It collects
the requirements from the author guidelines and the failure modes that
account for most CVPR desk rejects and low soundness scores. Nothing here is
submitted to the conference. If CVPR introduces an official checklist, replace
this file with a paraphrase of that question set and flip
`checklist_required` to `true` in `assets/venues/cvpr.yaml`.

## 1. Page Limit
**Question:** Is the main text within the page limit, with references starting on the page after the limit and no content shrunk to fit?
**Guidance:** Run `python scripts/format_gate.py --project-dir <paper_dir> --venue cvpr`. Reducing font size, margins, or line spacing to fit is grounds for rejection.

## 2. Anonymity
**Question:** Is the submission fully anonymous — no author names, affiliations, acknowledgements, funding statements, or identifying URLs?
**Guidance:** Run `python scripts/anonymity_check.py --project-dir <paper_dir>` first, then read the flagged lines yourself. Check the PDF metadata too, not only the LaTeX source.

## 3. Self-Citation Phrasing
**Question:** Are references to the authors' own prior work written in the third person?
**Guidance:** Write "Prior work [12] showed", not "In our previous work [12] we showed". This is the most common anonymity break in practice.

## 4. Claims
**Question:** Do the abstract and introduction state contributions that the experiments actually support?
**Guidance:** Each claimed contribution should map to a specific table or figure.

## 5. Related Work
**Question:** Does the paper cite and compare against the current state of the art, including work from the last twelve months?
**Guidance:** CVPR reviewers penalize missing recent baselines heavily.

## 6. Quantitative Comparison
**Question:** Does the paper compare against strong baselines under the same protocol, data, and compute budget?
**Guidance:** State clearly when a baseline number is copied from another paper rather than reproduced.

## 7. Qualitative Comparison
**Question:** Does the paper show visual results, including failure cases, alongside the competing methods?
**Guidance:** For a vision paper, missing qualitative comparison is a common reason for a weak-reject. Show the cases where the method fails.

## 8. Ablation Study
**Question:** Does the paper isolate the contribution of each component through an ablation?
**Guidance:** Every component claimed as a contribution needs a row in the ablation table.

## 9. Implementation Details
**Question:** Are the architecture, training schedule, hyperparameters, augmentation, and initialization specified well enough to reproduce the results?
**Guidance:** Appendix or supplementary placement is fine; point to it from the main text.

## 10. Compute Resources
**Question:** Does the paper report the hardware and training time required?
**Guidance:** Necessary for readers to judge whether the comparison is compute-matched.

## 11. Reproducibility Assets
**Question:** Are code, models, or data released, or is their absence explained?
**Guidance:** Use an anonymized repository during review.

## 12. Licensing and Credit
**Question:** Are third-party datasets, models, and code cited, with their licenses respected and stated?
**Guidance:** Cannot be inferred automatically — the author must confirm the licenses were checked.

## 13. Human Subjects and User Studies
**Question:** For user studies, does the paper report the participant recruitment, instructions, compensation, and ethics review?
**Guidance:** NA if the paper contains no user study.

## 14. Ethics and Societal Impact
**Question:** Does the paper address foreseeable misuse, especially for generative, biometric, or surveillance-adjacent methods?
**Guidance:** NA is rarely right for face, person, or generative work.

## 15. Supplementary Material
**Question:** Is the supplementary material a separate file containing only material that supports the paper, with nothing essential to the review placed there exclusively?
**Guidance:** Reviewers are not obliged to read supplementary material. Anything needed to judge the contribution belongs in the main paper.

## 16. Figure Quality
**Question:** Are all figures vector or at least 300 DPI, legible in grayscale, and readable at print size?
**Guidance:** Check the smallest font in each figure against the paper's body text size.
