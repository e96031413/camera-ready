# Pipeline State Management

Purpose: centralized project metadata, stage tracking, and session continuity.
Complements the Issues CSV (execution contract) with project-level state.

## Project State File: `notes/project-state.json`

Create this file at Gate 0 alongside the plan and issues CSV.
It serves as the single source of truth for project metadata and stage tracking.

### Schema

```json
{
  "projectId": "<timestamp>-<slug>",
  "topic": "<paper topic>",
  "venue": "<target venue or arXiv>",
  "paperType": "review | conference | codebase",
  "currentStage": "ideation | research | experiment | writing | review | qa | post-acceptance",
  "stageHistory": [
    {"stage": "ideation", "enteredAt": "ISO-datetime", "exitedAt": "ISO-datetime | null"}
  ],
  "qualityGates": {
    "ideation": {"status": "passed | pending | failed", "notes": ""},
    "research": {"status": "pending", "notes": ""},
    "writing": {"status": "pending", "notes": ""},
    "integrity": {"status": "pending", "notes": ""},
    "review": {"status": "pending", "notes": ""},
    "qa": {"status": "pending", "notes": ""}
  },
  "decisions": [
    {"date": "ISO-datetime", "decision": "text", "rationale": "text"}
  ],
  "sessionLog": [
    {"sessionId": "ISO-datetime", "role": "Orchestrator|Writer|Reviewer|...", "summary": "what was done"}
  ],
  "lastUpdated": "ISO-datetime"
}
```

### When to Update

| Event | Update |
|---|---|
| Gate passed | Set qualityGates[stage].status = "passed", advance currentStage |
| Decision made | Append to decisions array |
| Role switch | Append to sessionLog |
| Issues CSV batch completed | Update currentStage if all phase issues are DONE |
| Session start (resuming work) | Read this file first; check currentStage and pending gates |

### Relationship to Issues CSV

The Issues CSV remains the execution contract (per-issue tracking).
`project-state.json` tracks the macro view:
- Which stage is the project in?
- Which quality gates have passed?
- What decisions have been made?
- Who worked on what (session log)?

Both files must agree: if all Writing-phase issues are DONE in the CSV,
the writing quality gate should be "passed" in project-state.json.


## Decision Log: `notes/decision-log.md`

Append-only log of rejected/accepted directions. Prevents repeating failed approaches across sessions.

### Format

```markdown
## YYYY-MM-DD — Decision: [direction name]

- **Verdict**: accepted | rejected | deferred
- **Reason**: [1-2 sentences]
- **Alternative**: [if rejected, what to try instead]
- **Stage**: [which pipeline stage this relates to]
```

### Who writes it
- Orchestrator role appends entries after idea selection, experiment outcomes, and review decisions.
- All other roles check it at session start to avoid pursuing rejected directions.


## Session Continuity Protocol

For multi-session research projects:

### At session start
1. Read `notes/project-state.json` — determine currentStage and pending work
2. Read `notes/decision-log.md` — know what NOT to pursue
3. Read the latest issues CSV — find next TODO/DOING items
4. State your role before beginning work (see `references/agentic-workflow.md`)

### At session end
1. Emit a role completion block (see `references/agentic-workflow.md` § 5)
2. Update `notes/project-state.json` with session log entry
3. If any decisions were made, append to `notes/decision-log.md`

### Recovery from stale state
If `project-state.json` was last updated more than 7 days ago:
1. Treat it as potentially stale
2. Cross-reference with issues CSV (which is the ground truth for task status)
3. Run `python scripts/workspace_status.py --project-dir <paper_dir>` to reconcile


## Declarative Stage Requirements

Each pipeline stage has required outputs and a quality gate.
Use this checklist to verify stage completion before advancing.

| Stage | Required Outputs | Quality Gate |
|---|---|---|
| Ideation | Research questions, gap analysis, (optional) tournament results | User approved direction |
| Research | Plan, outline, issues CSV, 10-20 seed papers | User approved plan; issues CSV validates |
| Experiment | Experiment tracker, result summary, validated claims | Baseline reproduced; method beats baseline; ablations run |
| Writing | main.tex with all section prose, ref.bib | All writing issues DONE; anti-AI scan passes (LOW) |
| Integrity | Claim registry, BibTeX audit, privacy scan | integrity_gate.py passes at pre-review stage |
| Review | Review log, reviewer issue rows resolved | No Major blocking items; integrity gate passes |
| QA | Final compilation, quality report | compile_paper.py exit 0; no warnings; final integrity gate |
| Post-Acceptance | Slides/poster/video as requested | Compilation passes; validation scripts pass |
