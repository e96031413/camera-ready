---
mode: paper-plan
paper_type: codebase
topic: "camera-ready: a gated, verification-first agent workflow for end-to-end academic paper production"
timestamp: 2026-09-05_14-47-07
slug: camera-ready-paper
created_at: "2026-09-05T14:47:07+08:00"
complexity: complex
codebase_name: camera-ready
latex_available: true
---
# Paper Plan: camera-ready: a gated, verification-first agent workflow for end-to-end academic paper production

## Goal
- Produce a system/engineering paper grounded in an existing codebase
- Codebase input: camera-ready
- Prioritize correctness and traceability (claims must be backed by code/docs/measurements)
- Include 5+ implementation-grounded visualizations (architecture, module map, dataflow, state machine, latency/cost)

## Scope
- In: Architecture, components, workflows, reliability/safety, evaluation methodology, reproducibility
- Out: Speculative claims, unverified results, unrelated literature survey

## Kickoff Gate (must be confirmed before writing)
- **STOP**: Do not write prose into `main.tex` until this gate is confirmed and the issues CSV exists.
- [x] User confirmed scope + outline in chat (2026-09-05, Yanwei Liu)
- Target audience: researchers and engineers building LLM-agent writing systems
- Target length: 6-10 pages of main text (references excluded)
- Evidence policy: codebase snapshot + selected source files + docs (README/architecture) + measurements (if provided)

## Clarification Q&A (record answers)
| Question | Answer |
|---|---|
| What is the intended audience and pitch? | Researchers and engineers building LLM-agent writing/research systems; venue: arXiv (cs.DL / cs.SE / cs.CL). Pitch: manuscript integrity is a property of the *process*, not of the model. |
| Which components MUST be covered? | The gate state machine (autopilot), the citation path (arxiv_registry + fetch_bibtex), the claim/integrity gate, the anti-AI scan, venue and discipline profiles, the arXiv packaging step. |
| What are the top 3 contributions/claims (must be evidenced)? | (1) A gate model where every phase transition is decided by a deterministic script over files on disk, not by model assertion; (2) a citation path with no code route from model memory to ref.bib; (3) an open, testable implementation covering 8 disciplines, 6 styles, 6 venues, evidenced by its own test suite and worked examples. |
| Any private/sensitive parts that must be omitted? | None. Public MIT repository. |
| Preferred evaluation metrics? | System evaluation only: test-suite pass rate, gate behaviour on shipped examples, script/rule coverage counts. No new human study, no acceptance-rate claim. |

## Decisions (user-approved, 2026-09-05)
- Title: "CameraReady: A Gated, Verification-First Workflow for Agentic Academic Paper Production"
- Positioning: system/engineering paper; evaluation from existing reproducible evidence only.
- Author: Yanwei Liu (independent), repository link included; no anonymisation (arXiv is not double-blind).

## Inputs captured (generated artifacts)
- Codebase snapshot: notes/codebase-snapshot.md
- Dependencies summary: notes/dependencies.md (optional)
- Entrypoints summary: notes/entrypoints.md (optional)

## Confirmed Outline (user-approved)
1. Introduction - the integrity failure of agentic writing; contributions
2. Background and Related Work - autonomous research agents; citation hallucination; verification and provenance for tool-using agents
3. Threat Model - what an unconstrained writing agent gets wrong, and why prompting does not fix it
4. Design Principles - five principles (state outside the model; refusal by default; source-or-nothing; discipline before draft; human gates stay human)
5. System Architecture - layers, script inventory, state file, refinement markers
6. The Gate Model - 10 phases, exit conditions, override with recorded reason
7. Verification Mechanisms - citation path, claim registry + integrity gate, anti-AI scan, format/anonymity/style gates
8. Evaluation - test suite, gate behaviour on worked examples, coverage of disciplines/styles/venues, self-application (this paper)
9. Discussion, Limitations and Future Work
10. Conclusion
+ Data and Code availability statements (required by the CS profile)

## Plan Notes
- Repo URL: https://github.com/e96031413/SKILLS (skill: camera-ready)
- Commit used for snapshot: 7f2239adc7bbaa411ab6ee48f0ff4160a291c50f
- Visualizations plan:
  - Fig. 1 gate state machine (10 phases + exit conditions) -> Sec. Gate Model
  - Fig. 2 layered architecture / module map -> Sec. Architecture
  - Fig. 3 citation dataflow: query -> registry -> ref.bib (no path from model memory) -> Sec. Verification
  - Fig. 4 claim -> evidence -> integrity verdict pipeline -> Sec. Verification
  - Tab. I discipline/style/venue coverage matrix -> Sec. Architecture
  - Tab. II gate inventory: script, decision, blocking or advisory -> Sec. Gate Model
  - Tab. III evaluation results: tests, example runs, coverage -> Sec. Evaluation
- Open questions / missing evidence: none blocking; all evidence is from the repository at the pinned commit.
