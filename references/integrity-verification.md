# Integrity Verification (Pre-review + Final)

Purpose: ensure the paper is *verifiable* (citations + claims + evidence) and does not overclaim.
This is framework-agnostic: it works the same whether you are using Codex, Claude Code, or a manual workflow.

## Non-negotiables
- **No fabricated citations** or unverifiable BibTeX entries.
- **No fabricated results** (numbers, comparisons, “SOTA”, latency/cost claims).
- **No sensitive leaks**: run the privacy gate before sharing any excerpts.
- **Claim-level verification**: verifying that a citation exists is not enough; verify that the *claim matches the source*.

## Artifacts (recommended)
- `notes/claim-registry.md` (+ optional `notes/claim-registry.csv`)
- `notes/bibtex-audit.md`

Create them with:
```bash
python scripts/claim_registry.py --project-dir <paper_dir>
python scripts/bibtex_audit.py --project-dir <paper_dir>
```

## Workflow

### I0) Privacy gate (always)
```bash
python scripts/paper_privacy_scan.py --project-dir <paper_dir>
```

### I1) BibTeX audit (structure + recency)
Run:
```bash
python scripts/bibtex_audit.py --project-dir <paper_dir> --window-years 3
```

Targets (defaults used by this skill):
- **0 duplicates** (BibTeX keys)
- **0 missing years** (or explicitly tracked)
- **70%+ from the last 3 years** (relative to the plan as-of date; see your plan file)

If you want a hard gate, enforce it:
```bash
python scripts/bibtex_audit.py --project-dir <paper_dir> --window-years 3 --min-recent-ratio 0.70
```

### I2) Claim registry (extract what must be verified)
Run:
```bash
python scripts/claim_registry.py --project-dir <paper_dir> --mode broad
```

The registry focuses on:
- Quantitative claims (counts, %, p-values, effect sizes)
- Trend claims (“increasing/declining”, “faster/slower”)
- Categorical “first/most/largest” claims
- Causal claims (“X causes/leads to Y”)

### I3) Claim verification — pre-review (sample)
Before reviewer rounds, verify a sample:
- **30% random sample**, minimum **10 claims**
- Record a verdict per claim in the registry

### I4) Claim verification — final (100%)
Before final delivery, verify **100%** of claims in the registry.

## Verdict taxonomy (recommended)

| Verdict | Meaning | Severity |
|---|---|---|
| `VERIFIED` | Claim matches the source (allow rounding tolerance) | OK |
| `MINOR_DISTORTION` | Paraphrase is slightly loose but meaning preserved | Minor |
| `MAJOR_DISTORTION` | Exaggeration / wrong numbers / wrong conditions / wrong direction | Blocking |
| `UNVERIFIABLE` | Source does not contain support for the claim | Blocking |
| `UNVERIFIABLE_ACCESS` | Source exists but full text is not accessible | Track + caveat |

## Pass / Fail criteria (suggested)
- **PASS**: zero `MAJOR_DISTORTION` and zero `UNVERIFIABLE`
- **PASS_WITH_NOTES**: only `MINOR_DISTORTION` and/or `UNVERIFIABLE_ACCESS`
- **FAIL**: any `MAJOR_DISTORTION` or `UNVERIFIABLE`

## Codebase-grounded variant (systems/engineering papers)
For claims grounded in a repository:
- Evidence can be **code paths**, **docs**, **config**, **measurements/logs**, **tests**, **commit hash**.
- Prefer *relative* file paths and module names (avoid absolute paths).
- Do not claim guarantees (“always”, “provably”, “fully reliable”) unless backed by explicit mechanisms and tests/measurements.
