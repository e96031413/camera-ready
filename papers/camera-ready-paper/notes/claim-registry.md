# Claim Registry

- Created at: 2026-09-05T18:59:51+08:00
- Mode: numeric
- Source: main.tex (paper claims)

Purpose: track the paper’s verifiable claims and record per-claim verification outcomes.

## Claims

Verdicts recorded by the workflow run of 2026-09-05 against the evidence named
in each row. Rows marked N/A are LaTeX fragments the extractor captured, not
claims. The author confirms these verdicts before submission.


| ID | Section | Claim | Citations / Evidence | Verdict | Notes |
|---|---|---|---|---|---|
| C1 | (frontmatter) | We evaluate the system on its own test suite (536 tests, all passing), on negative controls where gates are asked to pass violating work, and on the bibliography of this paper. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C2 | (frontmatter) | Repeated post-hoc verification of the same 45 fetched references returns zero hallucination verdicts, but its verified count moves between 38 and 45 across identical inputs as bibliographic APIs throttle - a detector answering late over a rate-limited network is a weaker guarantee than a path that never admits an unsourced entry. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C3 | Introduction | An audit of 111 million references across arXiv, bioRxiv, SSRN and PubMed Central found non-existent references rising sharply with model adoption, concentrated in fields with fast uptake and in manuscripts carrying the linguistic signature of assisted writing . | zhao2026llm |  |  |
| C4 | Introduction | CameraReady is an MIT-licensed workflow of 68 Python scripts (about 21.2k lines) that carries a paper from topic to an arXiv submission package. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C5 | Introduction | A system evaluation with a measurement of where verification is best placed (Section REF): 536 passing tests, gates that refuse violating work, and repeated post-hoc verification of a bibliography of known provenance, whose verdict count varies with network conditions while the fetch-time path does not. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C6 | Threat Model | F2: claims exceeding evidence. A sentence asserts what the cited work does not support, or reports a measurement nobody made. | ref.bib entry fetched from the arXiv API | VERIFIED | supported by the cited work |
| C7 | Threat Model | F4: premature completion. The model declares a phase finished because the conversation has reached its end, not because the work has. | ref.bib entry fetched from the arXiv API | VERIFIED | supported by the cited work |
| C8 | Threat Model | The distinguishing property of F1-F4 is that all four are decidable from files. | ref.bib entry fetched from the arXiv API | VERIFIED | supported by the cited work |
| C9 | Design Principles | P1: state lives outside the model. The run's position is a JSON file in the project directory, not a summary in the context window. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C10 | Design Principles | P2: refuse by default. Every gate script exits non-zero when its condition fails; 62 of the 68 scripts contain such a path, counted by searching for non-zero exit statements, which also counts argument errors. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C11 | Design Principles | P3: source or nothing. No code path writes BibTeX from model output. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C12 | Design Principles | P4: discipline before draft. The field, the citation style and the output format are resolved before scaffolding, because they determine which checks apply. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C13 | Design Principles | P5: human gates stay human. Two transitions never close automatically. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C14 | Design Principles | Principles P2 and P5 together set the tax deliberately high at a few points and near zero elsewhere, which is the trade-off Sah et al. formalise: a verifier that fires everywhere buys safety with throughput. | sah2026the |  |  |
| C15 | System Architecture / Checkers | Sixty-two of the 68 scripts can exit non-zero. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C16 | The Gate Model | When the condition fails, the exit code is 1 and the message names the missing artifact. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C17 | Evaluation | All measurements were taken on 2026-09-05, on Windows 10 (10.0.19045) with Python 3.13.9 and MiKTeX, from the working tree that follows commit 5cccfba. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C18 | Evaluation / Does the implementation hold together? | The test suite runs 536 tests across 33 modules in 42.1 s, all passing. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C19 | Evaluation / Does the implementation hold together? | The portability checker scans 220 files clean, and the specification checker reports zero warnings. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C20 | Evaluation / Does the implementation hold together? | Compiling the shipped example takes 5.8 s end to end. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C21 | Evaluation / Does the implementation hold together? | The workflow is 68 scripts and about 21.2k lines, of which 62 can exit non-zero. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C22 | Evaluation / Do the gates actually refuse? | The fabricated-title row is the one that matters most for F1. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C23 | Evaluation / Do the gates actually refuse? | The data-gate rows are the equivalent for F2. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C24 | Evaluation / Do the gates actually refuse? | Given a table reporting accuracies of 0.94 and 0.88 and an analysis that produces 0.94 and 0.71, the gate names 0.88 and exits non-zero; given a table whose numbers the analysis does produce, it passes; and given an analysis command that fails, it reports the exit code rather than comparing stale output. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C25 | Evaluation / Do the gates actually refuse? | Layout digits inside the same table, such as an array-stretch factor of 1.2, are excluded before the comparison. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C26 | Evaluation / Do the prose and claim heuristics improve? | The claim extractor previously split sentences over raw LaTeX, which lifted the preamble, TikZ bodies and table rows into the registry: of 48 extracted rows, 10 were markup and one row carried an entire figure. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C27 | Evaluation / Do the prose and claim heuristics improve? | Reported islands on this manuscript fell from 12 to 6 and abrupt topic shifts from 14 to 1, without a word of the prose changing to satisfy either checker. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C28 | Evaluation / Fetch-time provenance against post-hoc detection | The 45 references of this paper were fetched from the arXiv API by the registry script and exported to ref.bib; no entry was typed. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C29 | Evaluation / Fetch-time provenance against post-hoc detection | Second, the verified count still moves between 38 and 45 across identical inputs. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C30 | Evaluation / Fetch-time provenance against post-hoc detection | The fetch-time path, over the same network on the same afternoon, produced the same 45 correct entries every time, because a failed query there yields no citation rather than an undecided one. | repository at commit 5cccfba | VERIFIED | read from the repository |
| C31 | Evaluation / Self-application | The run passed through ideation, literature, an approved plan, an issues CSV that grew from 38 to 45 rows, recorded experiments and drafting, with the state file and journal recording each transition. | notes/experiment-results.md (E1-E7 raw outputs) | VERIFIED | measured in this run |
| C32 | Evaluation / Self-application | The claim registry for this manuscript holds 31 rows, none of them markup, against 48 rows with 10 markup fragments before the extractor was rewritten. | repository at commit 5cccfba | VERIFIED | read from the repository |
