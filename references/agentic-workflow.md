# Role-Based Workflow (Framework-Agnostic) — Research → Write → Integrity → Review → Revise

This reference imports the *best ideas* from multi-agent academic workflows (Deep Research / Academic Paper / Paper Reviewer / Academic Pipeline),
but adapts them to this skill’s constraints:

- **Final output is a LaTeX paper** (IEEEtran by default; conference papers use venue-specific templates — see `references/conference-guides.md`).
- The “agents” are **roles / personas** (you can run them sequentially or in parallel) — no dependency on any specific agent framework.
- Everything maps back to this skill’s **gated plan + issues CSV** workflow.

## 0) How to use “agents” without an agent framework

Treat each role as a checklist with a strict output format:
- Run role A → capture artifacts / decisions
- Run role B → challenge or refine
- Convert results into **issues CSV rows** (actionable, trackable)

If you want parallelism: run roles independently, then do a synthesis pass (MetaReviewer / Editorial Synthesizer).

## 0.5) Memory Isolation — What Each Role Reads and Writes

When running roles sequentially in a single session, context pollution degrades output quality.
Each role should load ONLY the files in its "Read" column and write ONLY to the files in its "Write" column.
Files not listed are invisible to that role — do not reference or modify them.

| Role Category | Reads (load before running) | Writes (output to) | Never Touches |
|---|---|---|---|
| **Orchestrator / Conductor** | plan/*.md, issues/*.csv, notes/project-state.json, notes/decision-log.md, notes/review-log.md | notes/project-state.json, notes/decision-log.md, issues/*.csv | main.tex, ref.bib, notes/experiment-* |
| **Literature / Bibliography** | notes/project-state.json (read-only), notes/literature-notes.md, ref.bib | notes/literature-notes.md, notes/gap-matrix.md, ref.bib | main.tex, plan/*.md, notes/experiment-* |
| **Experiment Driver** | notes/project-state.json (read-only), notes/experiment-plan.md, notes/experiment-tracker.md, notes/decision-log.md | experiments/*, notes/experiment-tracker.md, notes/result-summary.md | main.tex, ref.bib, plan/*.md |
| **Draft Writer** | notes/project-state.json (read-only), notes/result-summary.md, notes/literature-notes.md, issues/*.csv (current section row) | main.tex, sections/*.tex | notes/experiment-*, plan/*.md, notes/decision-log.md |
| **Reviewer** | notes/project-state.json (read-only), main.tex, ref.bib, notes/result-summary.md | notes/review-log.md, issues/*.csv (new review rows) | main.tex (report issues, do NOT edit), notes/experiment-* |

### Isolation enforcement (manual protocol)

Since this is a skill (not a plugin with automated hooks), enforce discipline manually:
1. **State your role** before beginning work: "Acting as [Role]..."
2. **Load only listed files** — do not read files outside your scope
3. **Write only to listed files** — if you need to modify something outside your scope, stop and switch roles
4. **Orchestrator updates state after every role switch**: append a progress entry to `notes/project-state.json`

This prevents the most common failure mode: a "writer" role accidentally modifying experiment configs,
or a "reviewer" role silently editing the paper instead of reporting issues.


## 1) Deep Research (inspired) — 13 roles

Use these primarily in **Gate 0** and in **per-section research** during writing.

| Role | What it does | Output (must be concrete) |
|---|---|---|
| Research Question (FINER) | Turn vague topic into answerable research questions + scope | 1–3 RQs + FINER scores + in/out scope boundaries |
| Research Architect | Design methodology blueprint (even for a review paper) | Search plan + inclusion/exclusion criteria + synthesis method |
| Bibliography | Systematic discovery (not a paper dump) | Candidate list + search strings + screening notes |
| Source Verification | Evidence grading + predatory screening | Source quality notes + red flags + “use / use-with-caveats / reject” |
| Synthesis | Cross-source integration and contradictions | Themes + contradictions + gaps → feeds literature matrix |
| Report Compiler | Drafts a *research report* | **Do not** output APA here; instead output “findings → paper section bullets” |
| Editor-in-Chief | Q1 editorial lens | Fit + novelty positioning + “accept / revise / reject (readiness)” |
| Devil’s Advocate | Challenge assumptions at 3 checkpoints | PASS / REVISE with specific failure modes + counter-arguments |
| Ethics Review | Disclosure, citation integrity, dual-use | AI disclosure notes + integrity warnings + required edits |
| Socratic Mentor | Guided scoping dialogue + convergence criteria | Questions only until convergence; then a crisp scope statement |
| Risk of Bias | RoB 2 / ROBINS-I style checks | Bias flags + whether claims must be weakened |
| Meta-analysis | Effect sizes / heterogeneity / GRADE | Only if you truly have extractable quantitative corpus |
| Monitoring | Post-completion literature alerts | Tracking keywords + alert plan + “what triggers a revision” |

Notes:
- If you do **not** run a full systematic review, do not label the paper “systematic review”.
- For source grading, see `references/source-quality-hierarchy.md`.
- For PRISMA-lite scaffolding, see `references/systematic-review-addon.md`.

## 2) Academic Paper (inspired) — 12 roles (mapped to IEEE output)

Use these in the **per-issue writing loop** (Phase 2).

| Role | What it does | Output (IEEE-aligned) |
|---|---|---|
| Intake | Config interview + handoff detection | Constraints + paper type (review/codebase) + must-have sections |
| Literature Strategist | Search strategy + annotated bibliography | Section-driven sources + query strings + inclusion criteria |
| Structure Architect | Outline + word count allocation | IEEE section map + per-section goals + figure plan |
| Argument Builder | Claim–evidence chains | Per-section “claim → evidence → implication” bullets |
| Draft Writer | Writes section prose | IEEE-style prose + citation density discipline |
| Citation Compliance | Cross-check citations; format rules | Missing keys list + formatting issues + fixes |
| Abstract (Bilingual) | Optional bilingual abstract | Only if user requests; keep IEEE abstract conventions |
| Peer Reviewer | 5-dimension review (max 2 loops) | Scores + major blockers + minor issues → issues CSV rows |
| Formatter | Output conversion | For this skill: **IEEEtran LaTeX only** (no APA7 class) |
| Socratic Mentor | Chapter-by-chapter guided plan | Questions + convergence criteria → approved outline |
| Visualization | Figure/table generation guidance | Figure specs + placement + caption requirements |
| Revision Coach | Convert messy feedback into a roadmap | Response-to-reviewers draft + issues row insertion |

## 3) Academic Paper Reviewer (inspired) — 7 roles + decision mapping

Use these roles inside this skill’s Paper-Reviewer loop:
- Field Analyst → reviewer persona calibration
- Editor-in-Chief → fit / novelty / overall decision
- Methodology Reviewer → methods / statistics / reproducibility
- Domain Reviewer → literature coverage / theoretical framing
- Perspective Reviewer → cross-disciplinary & practical impact
- Devil’s Advocate Reviewer → strongest counter-arguments + fallacy detection
- Editorial Synthesizer → consensus + revision roadmap

Decision mapping (recommended; see `references/review-rubrics.md`):
- ≥ 80: Accept / Minor only
- 65–79: Minor Revision
- 50–64: Major Revision
- < 50: Reject / Not ready

## 4) Academic Pipeline (inspired) — stage mapping to this skill

This skill already has gates; treat these as stage labels:

| Pipeline stage | This skill step | Mandatory? |
|---:|---|---|
| 1 Research | Gate 0 research snapshot + draft plan | Yes |
| 2 Write | Phase 2 per-issue writing loop | Yes |
| 2.5 Integrity (pre-review) | Run integrity helpers + claim registry sample | **Yes (do not skip)** |
| 3 Review | Phase 2.5 Paper-Reviewer loop | Yes |
| 4 Revise | Back to Phase 2 writing issues (revision loop) | If review says revise |
| 3' Re-review | Reviewer verification pass (focused) | If major revision |
| 4' Re-revise | Final revision loop | If needed |
| 4.5 Final Integrity | 100% claim verification + final integrity gate | **Yes (do not skip)** |
| 5 Finalize | Compile + layout hygiene + deliver PDF | Yes |
| 6 Process record | Create a process record + collaboration quality notes | Optional but recommended |

Practical rule:
- Anything that becomes “real work” must become an **issues CSV row**.


## 5) Structured Output Format per Role

When a role completes its work, emit a standardized completion block.
This makes handoffs traceable and allows the Orchestrator to audit progress.

### Completion block format (paste at end of role execution)

```text
--- ROLE COMPLETION ---
Role: [role name]
Task: [what was done, 1 sentence]
Artifacts: [list of files created or modified]
Issues updated: [list of issue IDs moved to DONE/DOING]
Blockers: [any blockers for the next role, or “none”]
Confidence: high | medium | low
Next recommended role: [which role should run next]
--- END ---
```

### Why this matters
- The Orchestrator can scan completion blocks to decide the next step
- Blockers are surfaced immediately rather than discovered mid-task
- Artifact lists prevent “phantom work” (claiming done without creating a file)


## 6) Orchestrator Auto-Update Contract

When operating as the Orchestrator / Conductor role, you MUST update state after every subtask:

### Mandatory updates after each role completes

1. **Update `notes/project-state.json`** — set the completed task's status, record the timestamp
2. **Update `issues/*.csv`** — change Status of relevant rows from DOING to DONE
3. **Append to `notes/decision-log.md`** — record any decisions made (accepted/rejected directions)

### Trigger conditions

| Event | Required update |
|---|---|
| Literature search completes | project-state + issues CSV |
| Experiment run finishes | project-state + issues CSV + decision-log (if pivot/proceed) |
| Section draft completes | project-state + issues CSV |
| Review round completes | project-state + issues CSV + review-log |
| Idea tournament completes | project-state + decision-log |

Do not wait for the user to say “update progress” — do it immediately when a role emits a completion block.


## 7) Stage-to-Tool Mapping (camera-ready)

Use this to select the right scripts and reference docs for each pipeline stage.

| Stage | Primary Scripts | Reference Docs | Roles (from above) |
|---|---|---|---|
| Ideation (Gate -1, -0.5) | novelty_check.py | research-ideation.md, idea-tournament.md | Research Question, Socratic Mentor |
| Research (Gate 0) | bootstrap_ieee_review_paper.py, arxiv_registry.py | research-workflow.md, source-quality-hierarchy.md | Bibliography, Research Architect, Source Verification |
| Evidence (Phase 1.5) | evidence_pack.py, experiment_plan.py | experiment-pipeline.md, [evidence-pack.md](evidence-pack.md) | Experiment Driver |
| Writing (Phase 2) | compile_paper.py | writing-style.md, [ml-writing-philosophy.md](ml-writing-philosophy.md), anti-ai-writing.md | Draft Writer, Citation Compliance, Visualization |
| Integrity (Phase 2.3-2.4) | anti_ai_scan.py, claim_registry.py, bibtex_audit.py, integrity_gate.py | integrity-verification.md, citation-workflow.md | Source Verification, Ethics Review |
| Review (Phase 2.5) | paper_context_pack.py, cross_model_review.py | paper-reviewer.md, review-rubrics.md | All Reviewer roles, MetaReviewer |
| QA (Phase 3) | integrity_gate.py, workspace_status.py | quality-report.md, quality-phases.md | Editor-in-Chief |
| Post-Acceptance (Phase 4) | compile_slides.py, poster_generate.py, pptx_* | beamer-workflow.md, poster-workflow.md, post-acceptance.md | Formatter |

