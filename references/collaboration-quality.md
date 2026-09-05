# Collaboration Quality Evaluation (Optional)

Purpose: create an honest, reusable “process record” of how the paper was produced, including integrity and reproducibility signals.
This is framework-agnostic and intentionally lightweight.

## Six dimensions (1–100)

Score each dimension independently (avoid averaging away critical failures).

1) **Scope control**
- Did the work stay within the approved outline?
- Were scope changes explicitly recorded as new issues?

2) **Traceability**
- Can a reader trace each key claim to (a) citations or (b) codebase evidence?
- Are artifacts organized (`plan/`, `issues/`, `notes/`)?

3) **Evidence discipline**
- No fabricated citations or results
- Claim registry exists and is completed (as applicable)

4) **Reproducibility**
- Methods / evaluation plan are runnable or explicitly bounded
- Compile/QA commands are recorded and pass

5) **Review responsiveness**
- Reviewer feedback converted to tracked issues
- Response-to-reviewers is complete and specific (R→A→C)

6) **Privacy & safety**
- Privacy scan passes
- No internal URLs/paths/secrets in artifacts

## How to use
- Generate `notes/process-record.md` (see `scripts/process_record.py`)
- Fill in scores and short rationale for each dimension
- Keep it honest: a single integrity failure should heavily reduce Evidence/Privacy scores

