# Issues CSV Schema (12-column)

Columns: `ID, Phase, Title, Description, Target_Citations, Visualization, Acceptance, Status, Verified_Citations, Notes, Depends_On, Owner`

- **`Depends_On`**: semicolon-delimited IDs (e.g., `E1;W1`). Validated for existence and cycle-free by `validate_paper_issues.py`.
- **`Owner`**: `AI` | `HUMAN` | `BOTH` (who executes this issue).
- Legacy 10-column CSVs (without `Depends_On`/`Owner`) are auto-detected and accepted; use `--legacy` flag for explicit legacy mode.

| Phase | Issues |
|-------|--------|
| Ideation | ID0: 5W1H + gap analysis + RQ definition (optional); IT0: idea tournament; IT1: proposal extension (optional) |
| Research | Rx: discovery, scaffolding, framework, viz planning |
| Experiment | EX1: baseline implementation; EX2: hyperparameter tuning; EX3: proposed method; EX4: ablation study (conference papers) |
| Evidence | E1: per-section evidence pack assembly |
| Writing | Wx: each section + Ax: anti-AI scan |
| Integrity | Ix: privacy scan, BibTeX audit, claim registry |
| SelfReview | SLx: logic / argument / voice selfloops; SRx: 5-dimension self-review |
| Review | PRx: multi-role reviewer rounds |
| Refinement | RFx: rhythm and style refinement (voice selfloop + anti-AI scan; see `references/writing-style.md`) |
| QA | Qx: checklist, compilation, final review |
| Slides | SLx: Beamer slide creation |
| PPTX | PXx: PowerPoint slide creation |
| Video | VDx: narrated video |
| Poster | PSx: poster creation |
| Evo-Memory | EM0: memory retrieval (start of cycle); EM1: memory update (end of cycle) |
| AutoResearch | AR0: baseline establishment; AR1: experiment loop; AR2: results delivery |
| Post-Acceptance | PAx: promotion (optional) |

Status: `TODO` -> `DOING` -> `DONE`. Schema validated by `validate_paper_issues.py`.
