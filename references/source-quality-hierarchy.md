# Source Quality Hierarchy (Evidence Grading + Predatory Red Flags)

Purpose: keep the paper’s evidence base strong and avoid low-quality or misleading sources.
Use this both for review papers and for “Related Work” in codebase-grounded systems papers.

## Evidence hierarchy (generic)
Evidence expectations vary by field, but this hierarchy is a good default:

1. **Systematic reviews / meta-analyses**
2. **Well-controlled experimental studies** (where applicable)
3. **Controlled observational / quasi-experimental studies**
4. **Observational studies** (cohort, case-control, large surveys)
5. **Descriptive / qualitative studies** (context-rich but limited generalizability)
6. **Expert opinion / committee reports / editorials**
7. **Blogs / marketing / self-published claims** (use only as context, not evidence)

## Practical grading (A–F)

| Grade | Use as… | Typical sources |
|---|---|---|
| A | Primary evidence | Peer-reviewed, rigorous methods, reproducible, strong venues |
| B | Supporting evidence | Solid peer-reviewed work with minor limitations |
| C | Use with caveats | Preprints, limited samples, older-but-foundational work |
| D | Only if unavoidable | Weak methods, unclear venue, incomplete reporting |
| F | Do not use as evidence | Predatory, unverifiable, or clearly conflicted sources |

## Field adjustments (CS/AI/systems)
For fast-moving CS/AI, peer-reviewed **top conferences/journals** often carry more weight than:
- Random blogs or vendor benchmarks
- Unreviewed “whitepapers” without methodology

Still: do not treat “top venue” as a substitute for verifying claims. Run claim verification on the paper’s own claims.

## Predatory / low-integrity red flags (quick checklist)
Treat as suspicious if multiple red flags apply:
- Acceptance in days with no real review
- No real editorial board (or unverifiable names)
- Fake “impact factor” / invented indexing claims
- Journal scope is implausibly broad (“Journal of Everything”)
- Site has broken policies (retraction, ethics, COI) or obvious copy-paste text
- Aggressive spam solicitation and APC pressure

## What to do when a source is weak but useful
- Cite it explicitly as **context** (not as evidence for quantitative/causal claims)
- Add a caveat sentence: what it can and cannot support
- Prefer triangulation: add at least 1–2 stronger sources covering the same point
