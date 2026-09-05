# Review Rubrics (0–100) + Decision Mapping

Purpose: make reviewer rounds reproducible and actionable (not vibes-driven).
Use this rubric in `Paper-Reviewer` rounds to produce calibrated scores and clear acceptance criteria per issue.

## Core dimensions (recommended)

| Dimension | Weight | What “good” looks like |
|---|---:|---|
| Originality / Contribution | 0.15 | Clear, specific contributions; proper positioning; no “we built a pipeline” vagueness |
| Methodological rigor / Correctness | 0.20 | Methods and claims match evidence; no hidden assumptions; reproducible descriptions |
| Evidence sufficiency | 0.20 | Adequate citations; high-quality sources; claim verification has no blockers |
| Visual presentation | 0.15 | No margin overflow; ≥8pt labels; polished method figure; info-dense result plots; consistent style (see `references/reviewer-first-impressions.md` §1) |
| Experimental coverage | 0.15 | ≥2 model families (latest versions); ≥3 datasets; ≥5 baselines incl. recent top-venue methods; scale diversity (see `references/reviewer-first-impressions.md` §2) |
| Coherence / Structure | 0.08 | Clean narrative; no missing steps; no new claims in conclusion |
| Writing quality | 0.07 | Precise terms; consistent definitions; readable in 2-column constraints |

## Decision mapping (suggested)

| Weighted average | Decision |
|---:|---|
| ≥ 80 | Accept (or “Minor only”) |
| 65–79 | Minor Revision |
| 50–64 | Major Revision |
| < 50 | Reject (or “Not ready for review”) |

## Major blocker policy
Regardless of numerical score, the following are *blocking*:
- Any privacy scan failure
- Any fabricated / unverifiable citations
- Any `MAJOR_DISTORTION` / `UNVERIFIABLE` claim in claim verification
- Any fabricated results (numbers without measurements/sources)

## How to convert review → issues
For each major issue, always produce:
- **Evidence** (which section is affected; do not paste sensitive content)
- **Fix** (concrete edits / new figure / new subsection / new citation)
- **Acceptance** (binary “DONE” criteria)
- **Suggested issue row** fields (ID, Phase, Target_Citations, Visualization)
