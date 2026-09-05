# Paper Plan: <paper topic>

## Goal
- Produce a system/engineering paper grounded in an existing codebase
- Codebase input: <codebase_name>
- Prioritize correctness and traceability (claims must be backed by code/docs/measurements)
- Include 5+ implementation-grounded visualizations (architecture, module map, dataflow, state machine, latency/cost)

## Scope
- In: Architecture, components, workflows, reliability/safety, evaluation methodology, reproducibility
- Out: Speculative claims, unverified results, unrelated literature survey

## Kickoff Gate (must be confirmed before writing)
- **STOP**: Do not write prose into `main.tex` until this gate is confirmed and the issues CSV exists.
- [ ] User confirmed scope + outline in chat
- Target audience: (engineers/researchers) TBD
- Target length: 6-10 pages of main text (references excluded)
- Evidence policy: codebase snapshot + selected source files + docs (README/architecture) + measurements (if provided)

## Clarification Q&A (record answers)
| Question | Answer |
|---|---|
| What is the intended audience and pitch? | TBD |
| Which components MUST be covered (backend/frontend/infra)? | TBD |
| What are the top 3 contributions/claims (must be evidenced)? | TBD |
| Any private/sensitive parts that must be omitted? | TBD |
| Preferred evaluation metrics (latency/cost/quality/reliability)? | TBD |

## Inputs captured (generated artifacts)
- Codebase snapshot: notes/codebase-snapshot.md
- Dependencies summary: notes/dependencies.md (optional)
- Entrypoints summary: notes/entrypoints.md (optional)

## Confirmed Outline (edit to match the user-approved outline)
1. Introduction — context, problem, contributions
2. System Overview — high-level flow + architecture diagram
3. Architecture and Components — module/component breakdown + responsibilities
4. End-to-End Workflow — typical run, failure paths, recovery/retry behavior
5. Reliability, Safety, and Observability — guardrails, logging/metrics, idempotency, auditing
6. Evaluation — what was measured and how (or an explicit evaluation plan)
7. Related Work — key frameworks and closest systems (cite when needed)
8. Limitations and Future Work
9. Conclusion

## Plan Notes
- Repo URL (if public): TBD
- Commit hash/tag used for snapshot: TBD
- Visualizations plan (type → section placement):
- Open questions / missing evidence:

## Issue CSV
- Path: issues/<YYYY-MM-DD_HH-mm-ss>-<slug>.csv
- Must share the same timestamp/slug as this plan
- This CSV is the execution contract: update issue status as you write and QA
- Issues may be added/split/inserted during execution; re-validate after edits and keep going until all issues are `DONE`/`SKIP` (when feasible, in the same run).
