---
name: camera-ready
description: >
  Write academic papers end to end with a gated workflow: verified citations, machine-checked
  claims, venue rules, and post-acceptance materials. Covers LaTeX and Word, IEEE/ACM plus
  APA, MLA, Chicago and Vancouver, and STEM plus humanities, law, medicine, psychology,
  education and business. Handles review, conference, empirical, qualitative, survey,
  clinical and systematic-review/meta-analysis papers. Use when: writing or revising a
  paper, running a literature review, preparing a submission package, answering reviewers,
  or making slides, a poster or a talk video. Not for: non-academic documents or standalone
  coding tasks. Output: a compiled paper with every citation fetched from a source.
license: MIT
compatibility: >
  Python 3.10+ (standard library only for the core workflow). Windows, Linux and macOS.
  LaTeX (pdflatex/latexmk) for LaTeX output; XeLaTeX for Beamer. Pandoc for Word, Markdown
  and Typst output. Web access for citation lookup. Optional: Node.js and PptxGenJS for
  PowerPoint, Playwright for posters, Remotion and a TTS backend for video, an external
  model API for cross-model review.
metadata:
  short-description: Gated academic paper workflow with verified citations, across disciplines and formats
  homepage: https://github.com/e96031413/SKILLS
---

# Gated Academic Paper Workflow

## When to Use
- **Full research lifecycle**: ideation -> literature -> plan -> experiments -> paper -> review -> revision -> camera-ready -> slides/poster/video
- Any discipline with a profile in `assets/disciplines/`: computer science, psychology, medicine, education, business, social science, humanities, law
- Any style in `assets/styles/`: IEEE, APA 7, MLA 9, Chicago (both systems), Vancouver
- LaTeX output, or Word/ODT/Markdown/Typst through pandoc
- Review, conference, empirical, clinical, qualitative, survey, systematic-review and interpretive papers
- Rebuttal, post-acceptance materials, **Beamer slides**, **PowerPoint (.pptx)**, **HTML posters**

## When NOT to Use
- Non-academic documents
- Legal citation formatting (Bluebook, OSCOLA): authorities are tracked, not formatted
- Non-English manuscripts: citation machinery works, prose heuristics are English-tuned

## Inputs / Outputs

**Inputs**: Topic description (required), constraints (venue/page limit), codebase path (for codebase-grounded), reviewer comments (for rebuttal), experimental data.

**Outputs**: `main.tex`, `ref.bib`, `IEEEtran.cls`, `plan/`, `issues/`, figures/tables, `main.pdf`, `submission.tar.gz` (arXiv), various `notes/` artifacts. See output listing in `references/standalone-workflows.md`.

**Conventions**: Run `python scripts/...` from this skill folder; `<paper_dir>` is the paper/project root. `python` is written throughout because Windows ships no `python3`; on a system where `python` is Python 2, use `python3`. For arXiv metadata/BibTeX, use `scripts/arxiv_registry.py`.

**Platforms**: Windows, macOS and Linux. `python scripts/portability_check.py --docs` is the gate that keeps it that way; run it before any pull request.

## alphaxiv MCP Setup
See [references/alphaxiv-setup.md](references/alphaxiv-setup.md) for auto-install and tools reference.

---

## Gated Workflow

> Tip: Run `python scripts/<script>.py --help` before use. Open reference files only when a step calls them out.

### Autopilot: topic to camera-ready

For an end-to-end run, drive the gates below through the state machine rather
than by memory. It records where the run is, checks each exit condition against
files that exist, and refuses to skip a phase.

```
python scripts/autopilot.py init --project-dir <paper_dir> --topic "<topic>" --discipline <slug>
python scripts/autopilot.py status  --project-dir <paper_dir>   # what closes the current phase
python scripts/autopilot.py advance --project-dir <paper_dir>   # only if the condition is met
python scripts/autopilot.py log     --project-dir <paper_dir> --note "<what changed and why>"
```

Two phases never close on their own: `plan` needs `--approved-by "<name>"`, and
`camera-ready` ends with a built package because submission is always manual.
An override is `--force --reason "<why>"`, and the reason is written into the
run journal permanently. Use `autopilot.py phases` for the full list.

For a first, disposable project in one command, use
`python scripts/quick_start.py --title "<title>" --discipline <slug>`. It writes
a buildable skeleton with no prose in it and starts a run at phase 1.

### Non-Negotiable Rules
1. **No prose in `main.tex`** until plan approved AND issues CSV exists.
2. First deliverable: research snapshot + outline + clarification questions + draft plan.
3. **Use plan + issues tracking for all papers; do not opt out.**
4. Issues CSV is the execution contract; update `Status` and `Verified_Citations` per issue.
5. **Template**: IEEEtran two-column by default. For conferences, use venue-specific templates (`references/conference-guides.md`).
6. Optional: adopt role-based sub-workflows (`references/agentic-workflow.md`).
7. **Anti-AI check**: `python scripts/anti_ai_scan.py --project-dir <paper_dir>` before integrity gates. Target: LOW severity.
8. **Memory isolation**: When using role-based sub-workflows, enforce per-role read/write scopes (`references/agentic-workflow.md` § 0.5).
9. **Two-stage writing**: For each writing issue, create a bullet outline (Stage 1) BEFORE writing prose (Stage 2). See `references/writing-style.md`.
10. **Discipline first**: Before scaffolding, resolve the discipline, citation style and output format (Gate -2). A CS default applied to a clinical or humanities paper fails the wrong checks and skips the right ones.
11. **Citation anti-hallucination**: NEVER generate BibTeX from memory. Use `scripts/fetch_bibtex.py` (DBLP/CrossRef) and `scripts/arxiv_registry.py fetch-bibtex` (arXiv). Unverified citations use `PLACEHOLDER_` prefix. See `references/citation-workflow.md`.

### Gate -2: Discipline, Style and Format

Resolve these three before anything is scaffolded. They decide which gates
apply for the rest of the run.

1. `python scripts/discipline_profile.py list` -- pick the field.
2. `python scripts/discipline_profile.py requirements <discipline>` -- read what
   that field demands: mandatory sections, mandatory statements (ethics,
   preregistration, data and code availability, conflicts, funding), the
   reporting guidelines it recognises, and what gets papers rejected in it.
3. `python scripts/citation_style.py list` -- confirm the style. The discipline
   profile names a default and the styles the field also accepts.
4. `python scripts/citation_style.py preamble <style>` -- take the LaTeX block
   from here rather than writing package lines by hand. biblatex styles need
   `biber`; the IEEE profile is the only one that uses classic BibTeX, and the
   two use different field names.
5. Decide the output format. `latex` compiles with the toolchain in
   `references/`; `docx`, `markdown` and `typst` go through
   `python scripts/export_document.py`, which needs pandoc
   (`--check` reports whether it is installed).

If the field has no profile, add one: `docs/EXTENDING.md` has the schema. Do not
proceed under a default that does not fit the field.

### Gate -1: Research Ideation (Optional)
1. Apply 5W1H framework (`references/research-ideation.md`).
2. Conduct gap analysis (5 types). Formulate 1-3 RQs using SMART + FINER.
3. **Novelty check**: `python scripts/novelty_check.py --project-dir <paper_dir>`. Use alphaxiv for semantic similarity search.
4. **STOP** until user selects direction.

### Gate -0.5: Idea Tournament (Optional)
See [references/idea-tournament.md](references/idea-tournament.md). Generate candidates, run Elo tournament,
then evaluate top idea with 3-persona review + active novelty verification (Phase 2.5 of tournament).
Present evaluated top-3. **STOP** until user picks one.

### Gate 0: Research Snapshot + Draft Plan
1. Confirm constraints. Run light discovery (10-20 papers) using alphaxiv (see `references/alphaxiv-setup.md`).
2. Propose 2-4 candidate titles.
3. Scaffold: `python scripts/bootstrap_ieee_review_paper.py --stage kickoff --topic "<topic>"` (add `--paper-type codebase/conference` as needed). This delegates to `scripts/create_paper_plan.py` internally — always use `bootstrap_ieee_review_paper.py`, not `create_paper_plan.py` directly. See `references/template-usage.md` for how to work with the scaffolded template (structure, figures/tables, formatting, bibliography).
4. Create framework skeleton in `main.tex` (headings + bullets + seed citations; **no prose**).
5. Compile: `python scripts/compile_paper.py --project-dir <paper_dir>`. Fix `Overfull \hbox`.
6. **Venue setup** (conference papers): `python scripts/venue_setup.py --venue <venue> --project-dir <paper_dir>`.
   Writes `notes/venue.md` (page limit, required sections, checklist status, official URLs) and downloads the
   official style file. Venue style files are never bundled with this skill; if the download fails the script
   prints the official URL for manual download. Supported: neurips, icml, iclr, acl, aaai, cvpr
   (`python scripts/venue_setup.py --list-venues`).
7. Return outline + planned visualizations + clarification questions. **STOP** until user approves.
8. Initialize project state: create `notes/project-state.json` with project metadata (see `references/pipeline-state.md`).

### Gate 1: Create Issues CSV
1. Check kickoff gate in plan.
2. Create issues: `python scripts/bootstrap_ieee_review_paper.py --stage issues --topic "<topic>" --with-literature-notes`
3. Validate: `python scripts/validate_paper_issues.py <issues.csv>`

### Phase 1.5: Evidence Pack + Experiment Planning
```bash
python scripts/evidence_pack.py --project-dir <paper_dir>
python scripts/experiment_plan.py --project-dir <paper_dir>  # conference papers
```

### Phase 1.7: Experiment Pipeline (conference papers)
4-stage budgeted pipeline. See [references/experiment-pipeline.md](references/experiment-pipeline.md).

### Phase 2: Per-Issue Writing Loop
For each issue: **Outline** (Stage 1: bullet outline with key points + citations planned; `references/writing-style.md`)
-> **Write** (Stage 2: convert to flowing prose; citations required) -> **Visualize** (`references/visual-templates.md`)
-> **Verify** (web search before adding to `ref.bib`; use `PLACEHOLDER_` prefix for unverified) -> **Update** (mark DONE).
Compile after meaningful changes.

### Phase 2.3-2.75: Quality Checks
Anti-AI scan, integrity gate, reviewer loop, selfloops, self-review, rhythm refinement. See [references/quality-phases.md](references/quality-phases.md).

### Phase 3: QA Gate
1. Run QA checklist (`references/quality-report.md`) and readiness checklist (`references/quality_checklist.md`).
2. Final integrity gate: `python scripts/integrity_gate.py --project-dir <paper_dir> --stage final`
3. **Format gate** (conference papers): `python scripts/format_gate.py --project-dir <paper_dir> --venue <venue> --strict`.
   Checks the main-text page count against the venue limit (needs a compiled `main.log`/`main.aux` and a
   `\label{sec:bib}` at the bibliography), the presence of every venue-mandated section, and that the venue
   style file is both present and loaded. FAIL is blocking. Never fix a page overrun by shrinking margins,
   font size, or line spacing — venues check for that and reject it.
4. **Anonymity check** (double-blind venues): `python scripts/anonymity_check.py --project-dir <paper_dir>`.
   Any BLOCKER (author macro, `\thanks`, email, named repository, PDF author metadata) must be resolved
   before submission. Read every flagged line: a clean run is evidence, not proof.
5. If the target venue requires a paper checklist (see [references/conference-guides.md](references/conference-guides.md)): `python scripts/paper_checklist.py --project-dir <paper_dir> --venue <venue> --emit-tex`, fill in the generated `notes/paper-checklist.md`, validate with `python scripts/paper_checklist.py --project-dir <paper_dir> --venue <venue> --validate` (this only checks the worksheet), then replace the generated `checklist.tex` **scaffold** with the verbatim checklist block from the current venue `.sty`/template before `\input`-ing it — `--validate` passing does not mean the in-PDF checklist is submission-ready. Never fill in an answer on the author's behalf.
6. **Reporting guideline** (any discipline whose profile lists one): pick the
   guideline that matches the study design -- PRISMA for a systematic review or
   meta-analysis, CONSORT for a randomized trial, STROBE for an observational
   study, COREQ or SRQR for qualitative work, CHERRIES for a web survey, CARE
   for a case report, JARS for APA journals. Then:
   `python scripts/reporting_guideline.py --for-discipline <discipline>` to choose,
   `--guideline <slug> --project-dir <paper_dir>` to generate the worksheet, and
   `--validate` once every item has an answer and a location. Never fill in an
   answer on the author's behalf; the detected signals are hints beside the
   question, never in it.
7. **Citation style gate**: `python scripts/citation_style.py validate <style> --bib <paper_dir>/ref.bib`.
   An entry missing a field the style needs renders as an incomplete reference.
8. Compile; ensure no warnings. Deliver the manuscript, `ref.bib`, figures and the
   built document. For a Word target:
   `python scripts/export_document.py --input <manuscript> --style <style>`, then
   open the result -- pandoc does not translate every construct and fails quietly.

### Phase 3.5-3.7: Evo-Memory + Autoresearch
Cross-cycle learning and self-optimization. See [references/quality-phases.md](references/quality-phases.md).

### Phase 3.8: arXiv Submission Package
```bash
python scripts/arxiv_package.py --project-dir <paper_dir>
```
Flattens the directory, inlines the compiled `.bbl` (arXiv does not run BibTeX), strips comments and
`\todo` macros (uploaded arXiv source is public), and reports missing figures, unsupported graphics
formats, absolute paths, and oversized files. Writes `submission.tar.gz` plus
`notes/arxiv-submission-report.md`.

Before handing the tarball over, unpack it into an empty directory and compile it there with two
`pdflatex` passes and no `bibtex` — a build that works in the project directory can still fail on arXiv.

**This script builds a file and nothing else.** Uploading to arXiv or any submission system is "Ask
first" and is performed by the user, never by the model.

### Phase 4: Post-Acceptance Materials
Beamer slides, narrated video, HTML poster, PowerPoint, promotion. See [references/post-acceptance-materials.md](references/post-acceptance-materials.md).

---

## Variant Workflows
Standalone Beamer/Poster/PowerPoint (no paper), existing paper (no re-scaffold), citation validation, rebuttal, daily paper discovery. See [references/standalone-workflows.md](references/standalone-workflows.md).

---

## Success Criteria

**Compilation**: `python scripts/compile_paper.py --project-dir <paper_dir>` (exit 0, no "Citation undefined").

**Quality**: 6-10 pages main text, 60-80 citations (review: 8+/section; conference: varies), 100% citation verification, 70%+ recent (3yr), 5+ viz types, all issues DONE/SKIP.

**Conference**: `scripts/format_gate.py --venue <venue> --strict` passes (page limit, required sections, style file); `scripts/anonymity_check.py` reports no BLOCKER for double-blind venues; venue checklist worksheet filled and validated via `scripts/paper_checklist.py --venue <venue>`; Anti-AI LOW severity. Venues configured: neurips, icml, iclr, acl, aaai, cvpr (`assets/venues/*.yaml`).

---

## Default Follow-Through Policy

**Do directly** (low-risk, reversible, no external side effects):
- Run compilation: `compile_paper.py`, `compile_slides.py`
- Run validation/audit scripts: `validate_paper_issues.py`, `bibtex_audit.py`, `anti_ai_scan.py`, `integrity_gate.py`, `verify_citations.py`, `paper_privacy_scan.py`, `workspace_status.py`, `paper_checklist.py`, `format_gate.py`, `anonymity_check.py`, `venue_config.py`
- Set up a venue: `venue_setup.py` (writes `notes/venue.md`; downloads a public style file from the official URL)
- Build the arXiv submission tarball: `arxiv_package.py` (writes files only; it cannot and does not upload)
- Run selfloops: `logic_selfloop.py`, `argument_selfloop.py`, `voice_selfloop.py`
- Generate claim registry, evidence pack, context pack, self-review report
- Create/update issues CSV rows, plan files, outline files in `notes/`
- Fix LaTeX compilation errors, overfull hbox, BibTeX formatting
- Add verified citations to `ref.bib` (after web verification)

**Ask first** (irreversible, affects polished work, or external side effects):
- Overwrite or substantially rewrite sections with `.refined` markers
- Delete existing citations from `ref.bib` or remove issue rows from CSV
- Change paper structure (add/remove/reorder sections) after plan approval
- Change the approved plan or pivot research direction
- Submit to arXiv or any external platform (`arxiv_package.py` only builds the tarball; uploading it is always the user's action)
- Run cross-model adversarial review (consumes external API credits)
- Choose PIVOT decision in research decision flow

**Stop and report** (cannot proceed without user input):
- Gate -1, Gate 0, Gate 1: require explicit user approval before continuing
- Idea Tournament: present top-3 and wait for selection
- Novelty check reveals significant overlap with existing work
- Integrity gate fails with MAJOR_DISTORTION or UNVERIFIABLE claims
- Anti-AI scan returns HIGH severity
- `format_gate.py` reports FAIL on the page limit (cutting content is an editorial decision, not a formatting one)
- `anonymity_check.py` reports a BLOCKER on a submission the user intends to send to a double-blind venue
- Missing critical input (topic, venue, constraints) that cannot be inferred
- Privacy scan detects sensitive data leaks

## Safety & Guardrails
- **Never fabricate** citations or results; add TODO and ask if evidence missing.
- **Verify every citation** via web search + source page before adding to `ref.bib`.
- **Verify claims**: use `claim_registry.py` + `integrity_gate.py`.
- **Issues CSV** is the contract; mark `DONE` only when criteria met.

## Issues CSV Schema
See [references/issues-csv-schema.md](references/issues-csv-schema.md).

## Refinement Markers
Scripts respect `.refined` marker files. Create markers to prevent accidental overwrite of polished artifacts. Utilities: `is_refined()`, `mark_refined()`, `check_refined_guard()`.

## Workspace Status
```bash
python scripts/workspace_status.py --project-dir <paper_dir>
```

## Layout Hygiene
- Figures: start with `figure` + `\columnwidth`; switch to `figure*` + `\textwidth` if needed
- Tables: prefer `p{...}` column widths over `\resizebox`
- Equations: use `split`, `multline`, `aligned`, or `IEEEeqnarray`
