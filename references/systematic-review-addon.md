# Systematic Review Add-on (PRISMA-lite + Literature Matrix)

Purpose: optional workflow add-on when you want a *more reproducible* literature process than a standard narrative review.
This is intentionally “PRISMA-lite”: use what helps, and do not claim “systematic review” unless you actually follow the protocol.

## When to use
- You want reproducible search + screening decisions.
- You expect contested findings and want explicit contradiction handling.
- You are writing a survey that could be audited later.

## Minimal PRISMA-lite steps

### S0) Research question + scope boundary
- Write 1–2 primary research questions.
- Define inclusion/exclusion criteria (years, language, study types, domain).

### S1) Search strategy + log
- Databases/sources you used (arXiv, Google Scholar, ACL Anthology, IEEE Xplore, ACM DL, etc.).
- Boolean queries + synonyms.
- Date range and as-of cutoff (use the plan timestamp).

### S2) Screening + dedup
- Record counts: discovered → screened → included.
- Record top exclusion reasons (e.g., “not in-scope”, “no evaluation”, “non-primary source”).

### S3) Literature matrix (Source × Theme)
Use the matrix to avoid cherry-picking and to force contradiction reporting.

Scaffold:
```bash
python scripts/scaffold_notes.py --project-dir <paper_dir> --artifact literature-matrix
```

### S4) Synthesis discipline
- For each theme, report: evidence **for**, evidence **against**, and **quality level**.
- Explicitly list knowledge gaps (no sources / weak evidence / only one region / only one method).

## Output artifacts (recommended)
- `notes/literature-matrix.md` (living document)
- Optional: `notes/screening-log.md` (simple bullet log)
