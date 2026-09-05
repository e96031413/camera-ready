# Systems-Paper Hardening Playbook (CVPR/ICCV/ICML)

This reference captures a reusable, reviewer-driven hardening workflow for **codebase-grounded** systems papers about agentic multimedia generation pipelines.

Use this when:
- The venue has a **strict main-text page limit** (e.g., 8 pages, refs excluded).
- The system is **workflow-orchestrated** (durable execution, replay, signals).
- Claims must be **auditable** (no fabricated numbers; anonymity/privacy constraints).

## Non-negotiables (submission safety)

1) **Anonymity & privacy**
- No internal URLs.
- No absolute filesystem paths.
- No environment-file contents (e.g., `.env`).
- Prefer external-friendly naming and abstract descriptions.

Gate:
```bash
python scripts/paper_privacy_scan.py --project-dir <paper_dir>
```

2) **No fabricated results**
- If you do not have measured evidence, write a **reproducible evaluation plan**.
- If you report numbers, include enough artifacts so a reader can recompute them.

3) **Page budget is a hard constraint**
- Treat page limit as a compile gate, not a style preference.

Gate:
```bash
python scripts/compile_paper.py --project-dir <paper_dir> --report-page-counts
```

## Reviewer loop → minimal fix policy

Convert every reviewer blocker into a smallest-possible patch list:
- Prefer **replacing** sentences over adding paragraphs.
- Avoid new tables when page budget is tight.
- After each patch: recompile + re-run privacy scan.

## Systems wording patterns that avoid overclaim

### Replay determinism (must be scoped)
Recommended pattern:
- Define **determinism under replay** as *workflow controller control flow* determinism:
  given the same workflow history and explicit parameters, replay yields the same
  branching decisions and state transitions.
- Explicitly state it **does not imply deterministic model outputs**.

### Progress protocol: make the contract implementable
If you claim late-join progress correctness, you need a **minimal, checkable** contract.

Contract skeleton (paper-ready, short):
- Two message types: **Snapshot** and **Event**.
- Snapshot contains: `job_id`, `progress_version v`, and scalar fields (status/phase/counters).
- Events contain: `(job_id, v, kind, payload)` and are delivered at-least-once.
- Kinds should be enumerated (minimum):
  - `progress`: complete scalar snapshot at version `v` (at most one per `v`)
  - `shot_complete`: per-shot artifact pointer update
  - `control(action=...)`: pause/resume/cancel and `reset_artifacts`
  - terminal kinds: `complete`, `error`

Event id (for dedup):
- `(job_id, v, kind)` plus kind-specific keys.
  - For `shot_complete`: `(shot_key, resource_type)`
  - For `control`: `action`

Apply rules (idempotent, out-of-order safe):
- Scalars: apply only if incoming `v` is greater than the locally stored scalar version.
- Artifact pointers: model as a **keyed pointer map**
  `(shot_key × resource_type → URL or tombstone)`.
  Apply per-key **last-write-wins** by `v`.
- Re-plan boundary: a `control(action=reset_artifacts)` event raises a **pointer floor** to `v`.
  Drop pointers last-written before the floor (or ignore pointer events with `v' < floor`).

Key alignment (avoid internal inconsistency):
- If your IR has stable `shots[i].id`, prefer using `shot_id` as `shot_key`.
- If UI uses `shot_order`, explicitly state the stability assumption (no reorder without reset).

### Deterministic patching: DurBudget must be a real rule
If you claim a deterministic pacing patch, define it minimally.

Recommended minimal rule:
- Fix a chars/sec calibration `cps` (constant or config parameter) and record it in the
  configuration fingerprint/run-plan.
- For each shot narration `n_i`:
  `d_i = clamp(round(|n_i| / cps), d_min, d_max)`
- If the resulting plan still violates the global duration constraints, retry the planner
  (do not silently weaken gates).

Also define a patch whitelist:
- Allow patching only visual-slot fields and per-shot durations.
- Never allow patching roles or narration.

## Reproducible evaluation when benchmarks are missing

If you cannot ship a large-scale benchmark:
- Provide a **protocol** (inputs, configs, instrumentation, metrics, summarizer).
- Include at least one small measured ablation for a core claim.
- For systems correctness claims (protocol semantics), add a micro-eval.

## Micro-eval template: progress protocol convergence (synthetic)

Purpose:
- Validate that client-side apply rules converge to the persisted record under
  at-least-once + out-of-order delivery and late-join.

Design constraints (to avoid ambiguous specs):
- Exactly one `progress` event per version `v`.
- For a fixed `(shot_key, resource_type)`, at most one pointer update per `v`.
- `reset_artifacts` defines a floor; pointers last-written below the floor are dropped.

Minimum artifacts to include in `supplementary/`:
- `results.jsonl`: per-delivery records (seed, trace_id, v0, counts, converged bool)
- `trace_hashes.csv`: SHA256 per synthetic trace (auditability)
- `summary.json`: aggregated counts used by the paper
- `manifest.json`: SHA256 for all shipped supplementary files
- `recompute_summary.py`: recompute the aggregate from `results.jsonl` (stdlib-only)

Paper phrasing (avoid overclaim):
- State it is **synthetic**.
- State what it validates: *client reconstruction convergence vs persisted record*.
- Do not present it as end-to-end production reliability.

## Page-budget tactics (venue page limit)

When you must hold main text to the venue page limit:
- Prefer sentence replacements and compressions.
- Remove non-essential tables; convert to 2–4 sentences if possible.
- Keep micro-eval results to a single sentence; put logs/scripts in supplementary.
- Re-run page count report after every meaningful edit.
