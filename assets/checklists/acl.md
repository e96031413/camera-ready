# ACL / ARR Responsible NLP Research Checklist — Question Set

Source: ACL Rolling Review "Responsible NLP Research" checklist,
<https://aclrollingreview.org/responsibleNLPresearch/>.
Answer options: Yes / No / NA.

**Before submission**: re-check this file's wording against the current ARR
checklist form and the `acl.sty` template. ARR administers the checklist
through the submission form rather than through a LaTeX block, and the
question set is revised regularly. This file **paraphrases** the official
sections A-E; it is not a verbatim copy.

Two ACL requirements the checklist does not cover on its own:

- **Limitations is a mandatory section** in the paper. It does not count
  toward the page limit. A submission without it can be desk rejected.
- An **Ethics Statement** is optional but expected whenever section D or E
  below applies.

## 1. Limitations Section
**Question:** Does the paper have a Limitations section discussing the weaknesses of the work?
**Guidance:** Mandatory at ACL venues, placed after the conclusion and before the references. It is not a "future work" section — describe what the current work cannot do.

## 2. Risks
**Question:** Does the paper discuss the potential risks of the work?
**Guidance:** Misuse, dual use, and harms to the populations represented in the data. NA only if the work genuinely has no foreseeable risk, and say why.

## 3. Claims and Scope
**Question:** Do the abstract and introduction summarize the paper's claims accurately, without generalizing beyond the languages, domains, and datasets tested?
**Guidance:** A method validated on English news text should not be described as language-agnostic.

## 4. Use of Existing Artifacts
**Question:** Does the paper cite the creators of every artifact it uses — datasets, models, code, and other resources?
**Guidance:** Cite the paper, not just the repository or the model card.

## 5. License and Terms of Existing Artifacts
**Question:** Does the paper state the license or terms of use of each existing artifact, and is the paper's use consistent with them?
**Guidance:** Cannot be inferred automatically — the author must confirm the licenses were checked. Research-only licenses restrict what you may release.

## 6. Intended Use of Artifacts
**Question:** Is the paper's use of each artifact consistent with its documented intended use, including for artifacts derived from it?
**Guidance:** State it explicitly where a dataset was collected for one purpose and is used here for another.

## 7. Personal and Offensive Content in Data
**Question:** Does the paper report whether the data contains personally identifying information or offensive content, and what was done about it?
**Guidance:** Anonymization and filtering steps go here. NA only if no data was collected or reused.

## 8. Documentation of Artifacts
**Question:** Does the paper document the artifacts it uses or releases — domain, language, linguistic phenomena, demographic coverage?
**Guidance:** Coverage gaps are findings, not embarrassments. State them.

## 9. Data Statistics
**Question:** Does the paper report the relevant statistics of the data — number of examples, split sizes, and average lengths?
**Guidance:** Appendix placement is acceptable.

## 10. Computational Budget
**Question:** Does the paper report the number of parameters, the compute budget, and the computing infrastructure used?
**Guidance:** Include total compute across the whole project, not only the final reported runs.

## 11. Experimental Setup and Hyperparameters
**Question:** Does the paper report the hyperparameter search, the best-found values, and the criterion used to select them?
**Guidance:** Report the search space, not only the winner.

## 12. Descriptive Statistics of Results
**Question:** Are the reported results a single run or a summary over multiple runs, and is that stated with the corresponding variability?
**Guidance:** State the number of runs and what the reported interval covers.

## 13. Existing Packages
**Question:** Does the paper report which existing implementations, packages, and evaluation scripts were used, with their versions and settings?
**Guidance:** Tokenizer version and metric implementation change scores; name them.

## 14. Human Annotation Instructions
**Question:** For work involving human annotators or participants, does the paper include the full instructions and the screenshots or interface given to them?
**Guidance:** NA if the paper involves no human annotation.

## 15. Annotator Recruitment and Payment
**Question:** Does the paper report how annotators were recruited, how they were paid, and whether the pay meets the local minimum wage?
**Guidance:** NA if the paper involves no human annotation.

## 16. Annotator Consent and Ethics Review
**Question:** Were participants informed of how their data would be used, did they consent, and was ethics-board approval obtained where required?
**Guidance:** NA if the paper involves no human participants.

## 17. Annotator Demographics
**Question:** Does the paper report the basic demographic and geographic characteristics of the annotator population?
**Guidance:** Report at the level that is relevant to the task and that does not itself identify individuals.

## 18. Use of AI Assistants
**Question:** Does the paper disclose the use of AI assistants — including large language models — in the research or the writing?
**Guidance:** ARR asks for this explicitly. Cover coding assistance, data generation, analysis, and writing separately, since they carry different risks. The authors remain responsible for the correctness of everything in the paper.
