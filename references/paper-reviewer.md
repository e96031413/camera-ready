# Paper-Reviewer (Top-tier Iteration Guide)

Purpose: run multi-role paper reviews and convert feedback into **actionable, trackable** issues
so the paper can converge toward CVPR/AAAI/ICML/ICLR/NeurIPS/ECCV-level quality.

Tip: If you want calibrated scoring + decision mapping (0–100), use `references/review-rubrics.md`.

Non-negotiables:
- **No fabricated results**: if numbers are missing, write an explicit evaluation plan + missing artifacts.
- **No sensitive leaks**: omit internal URLs, absolute filesystem paths, and any `.env` contents.
- **Everything becomes an issue**: every non-trivial fix must map to an Issues CSV row (`Phase=Integrity|Review|Writing|QA`).

---

## Roles (run in parallel, then synthesize)

### 1) MetaReviewer (chair)
Goal: produce the final prioritized decision list.
- Consolidate overlaps from other reviewers
- Decide what is **Major blocking** vs **Minor**
- Convert to a minimal set of issue rows with crisp acceptance criteria

Optional (journal-style reviewer team):
- Editor-in-Chief (fit, novelty, overall readiness)
- Methodology Reviewer (methods/statistics/reproducibility)
- Domain Reviewer (literature coverage, theoretical framing)
- Perspective Reviewer (cross-disciplinary/practical impact)
- Devil’s Advocate Reviewer (strongest counter-arguments, fallacy detection)
- Editorial Synthesizer (consensus + revision roadmap)
See `references/agentic-workflow.md` for a role map and decision mapping.

### 2) Backend+Agent Algorithm Reviewer (primary)
Goal: stress-test technical soundness and backend/agent depth.
Check:
- Clear problem statement + concrete contributions (not vague “we built a pipeline”)
- Agent algorithm details: planning, routing, tool contracts, retries, idempotency
- Orchestration model: workflow engine / queueing / state machine / resume semantics
- Failure modes: partial failure, cancellation, timeouts, cache misses, consistency
- Observability: logs/metrics/traces, debugging workflow, auditability
- Security/privacy boundaries at interfaces

### 3) Evaluation & Reproducibility Reviewer
Goal: ensure evaluation is honest, runnable, and comprehensive.
Check:
- If no results: evaluation plan is specific, reproducible, and measurable
- Baselines + ablations are meaningful for the claimed contributions
- Datasets / rubrics / test harness described without leaking private assets
- Compute / cost / latency reporting plan is consistent and not hand-wavy
- **Experimental coverage** (see `references/reviewer-first-impressions.md` §2):
  - ≥2 model families with latest versions at submission time; flag version mismatches (mixing old and new versions of the same family signals cherry-picking)
  - ≥3 diverse datasets/benchmarks (1-2 is a standard weakness in 2025+)
  - ≥5 baselines including recent top-venue methods (last 1-2 years)
  - Scale diversity: include large-scale models when possible

### 4) Related Work & Positioning Reviewer
Goal: fix novelty positioning and comparisons.
Check:
- Closest systems/frameworks cited and compared fairly
- Table: capabilities/assumptions/failure modes/eval differences
- Claims do not exceed what evidence supports

### 5) Clarity & Structure Reviewer
Goal: improve readability, visual presentation, and “conference paper” narrative discipline.
Check:
- Section flow supports the contributions (intro→system→methods→eval→limitations)
- Terminology consistent; acronyms defined; no “new facts” in conclusion
- Figures/tables placed where they pay off; captions are informative
- **Visual first-impression** (see `references/reviewer-first-impressions.md` §1):
  - No margin overflow (equations, figures, tables)
  - All labels ≥8pt at print size; consistent visual style
  - Motivation figure (Fig 1) conveys the problem in one glance
  - Method overview figure is polished and full-width
  - Result figures are information-dense but readable
- **Storytelling coherence** (see `references/reviewer-first-impressions.md` §3):
  - Introduction motivation is concrete (not generic “LLMs are important”)
  - Research gap is specific and well-evidenced
  - Method feels like a natural solution to the stated problem

### 6) Privacy Leak Reviewer
Goal: find and block sensitive tokens.
Check:
- Internal URLs, private hostnames, private IPs, `localhost`
- Absolute paths (e.g., `/home/...`, `/Users/...`)
- `.env` contents or secret-like assignments
- Remove or replace with placeholders (e.g., `<URL_REDACTED>`, `<PATH_REDACTED>`)

---

## Required Output Format (per role)

### Summary (3-6 bullets)
- Overall verdict: `Major blocking` / `Minor only`
- Top 3 reasons (evidence-based; cite which section/figure is affected)

### Major Issues (each must be actionable)
For each issue:
- `Title`: short, specific
- `Evidence`: what in the current draft causes the issue (section names only; no sensitive quoting)
- `Fix`: what to change (concrete edits / new figure / new subsection)
- `Acceptance`: binary check to mark issue `DONE`
- `Suggested Issue Row` (CSV fields):
  - `ID`: e.g., `PR1a`, `Q3`, `W6b`
  - `Phase`: `Review` (or `Writing` / `QA` if it’s a writing/qa task)
  - `Target_Citations`: integer or `0`
  - `Visualization`: `N/A` or a specific figure/table type

### Minor Issues (batchable)
- List 5-15 items, each with an explicit fix (not just “improve writing”)

---

## Round Structure (default)
1. **Round 1 (Desk + Technical)**: kill-switch issues first (soundness, missing eval plan, missing related work, privacy leaks).
2. **Round 2 (Camera-ready)**: coherence, clarity, structure, layout hygiene, citation density.

Stop criteria (to exit review loop):
- No Major blocking items remain
- `paper_privacy_scan.py` passes
- Pre-review integrity gate passes: `python scripts/integrity_gate.py --project-dir <paper_dir> --stage pre-review`
- Compile passes (or LaTeX not available but syntax validated and issues track the remaining compile work)
