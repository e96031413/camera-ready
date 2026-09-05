# Autonomous Research Workflow

Purpose: cross-model adversarial review, novelty verification, DBLP/CrossRef citation, experiment planning, and state recovery for overnight autonomous research loops.

Concepts adapted from [ARIS (Auto-claude-code-research-in-sleep)](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep).

---

## Cross-Model Adversarial Review

### Why Two Models, Not One?

Single model self-reviewing creates **self-consistent blind spots** — the same model reviewing its own patterns falls into local minima. Cross-model review is fundamentally adversarial: the reviewer probes weaknesses the executor didn't anticipate.

### Architecture

- **Executor** (Claude Code): fast, fluid implementation — writes LaTeX, fixes issues, runs scripts
- **Reviewer** (external LLM via Codex MCP or any OpenAI-compatible API): slower, deliberate critique with maximum reasoning depth

### Review Protocol (Phase 2.5 Enhancement)

```
┌─→ Phase A: Send full paper context to external reviewer (xhigh reasoning)
│   Phase B: Parse score (1-10), verdict, action items
│   Phase B.5: Human checkpoint (if AUTO_PROCEED=false)
│   Phase C: Implement fixes (highest priority first)
│   Phase D: Update documentation
│   Phase E: Save state to REVIEW_STATE.json
└── If score < 6/10 and round < 4: loop back to Phase A
    If score ≥ 6/10 or round = 4: report to user
```

### MCP Call Templates

**Round 1** (fresh start):
```
mcp__codex__codex:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    [Round 1/4 of autonomous review loop]
    [Full paper context: title, abstract, sections, figures, claims]

    Act as a senior ML reviewer (NeurIPS/ICML level).
    1. Score this work 1-10 for a top venue
    2. List remaining critical weaknesses (ranked by severity)
    3. For each weakness, specify the MINIMUM fix
    4. State clearly: is this READY for submission? Yes/No/Almost

    Be brutally honest. Do NOT hide weaknesses.
```

**Round 2+** (threaded conversation):
```
mcp__codex__codex-reply:
  threadId: [saved from round 1]
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    [Round N update]
    Since your last review, we have:
    1. [Action 1]: [result]
    2. [Action 2]: [result]
    Please re-score and re-assess.
```

### Scoring Rubric

| Score | Meaning |
|-------|---------|
| 1-3 | Rejected — fundamental issues |
| 4-5 | Borderline reject — significant weaknesses |
| 6 | Weak accept — ready with minor fixes |
| 7-8 | Accept — solid contribution |
| 9-10 | Strong accept — top paper |

**Positive threshold**: score ≥ 6/10 AND verdict contains "ready"/"accept"/"almost"

### Key Rules

- ALWAYS implement fixes BEFORE re-reviewing (not just promises)
- Prefer reframing/analysis over new experiments when both address the concern
- Do NOT hide weaknesses to game a positive score
- Document EVERYTHING — the review log should be self-contained
- Be honest — include negative results and failed experiments
- Skip fixes requiring excessive compute (flag for manual follow-up)

---

## State Recovery (REVIEW_STATE.json)

Long-running loops may hit context window limits. State persistence enables recovery.

### State File Format

```json
{
  "round": 2,
  "max_rounds": 4,
  "status": "in_progress",
  "topic": "research topic",
  "scores": [5.0, 6.5],
  "verdicts": ["not ready", "almost ready"],
  "thread_id": "019cd392-...",
  "pending_fixes": ["fix 1", "fix 2"],
  "timestamp": "2026-03-19T21:00:00+08:00"
}
```

### Recovery Logic

1. If `REVIEW_STATE.json` not found → fresh start
2. If `status` = `"completed"` → fresh start
3. If `timestamp` older than 24 hours → fresh start (stale)
4. If `status` = `"in_progress"` and < 24h → **resume** from saved round + 1

### State Management Script

```bash
# Initialize
python scripts/cross_model_review.py --project-dir <paper_dir> init --topic "your topic"

# Check status
python scripts/cross_model_review.py --project-dir <paper_dir> status

# Update after a round
python scripts/cross_model_review.py --project-dir <paper_dir> update --round 2 --score 6.5 --verdict "almost ready"

# Mark complete
python scripts/cross_model_review.py --project-dir <paper_dir> complete
```

---

## Novelty Verification

### Protocol

1. **Extract claims**: Identify 3-5 core technical claims from the paper
2. **Multi-source search**: For EACH claim, search arXiv, Scholar, DBLP with 3+ query formulations
3. **Cross-model verification** (optional): Send method + found papers to external reviewer
4. **Report**: Structured assessment with HIGH/MEDIUM/LOW per claim

### Script

```bash
python scripts/novelty_check.py --project-dir <paper_dir>
# or with method description:
python scripts/novelty_check.py --project-dir <paper_dir> --method "our method does X by Y"
```

Output: `notes/novelty-check.md` with claims, search queries, and assessment template.

### Important Rules

- Be BRUTALLY honest — false novelty claims waste months of research
- "Applying X to Y" is NOT novel unless the application reveals surprising insights
- Check both the METHOD and the EXPERIMENTAL SETTING for novelty
- Always check the most recent 6 months of arXiv

---

## DBLP/CrossRef Verified BibTeX

### Why This Matters

LLM-generated BibTeX frequently hallucinates venue names, page numbers, or co-authors. DBLP and CrossRef return publisher-verified metadata.

### Three-Step Fallback Chain

1. **DBLP** (best quality): `dblp.org/search/publ/api` → `dblp.org/rec/{key}.bib`
2. **CrossRef DOI** (fallback): `doi.org/{doi}` with Accept: application/x-bibtex
3. **Mark [VERIFY]** (last resort): placeholder with manual verification flag

### Script

```bash
# Single paper
python scripts/fetch_bibtex.py --title "Attention Is All You Need" --author "Vaswani"

# With DOI
python scripts/fetch_bibtex.py --doi "10.48550/arXiv.1706.03762"

# Scan .tex for citation keys
python scripts/fetch_bibtex.py --scan-tex main.tex

# Append to bib file
python scripts/fetch_bibtex.py --title "..." --author "..." --out-bib ref.bib
```

### Integration with Existing Workflow

Use `fetch_bibtex.py` alongside `arxiv_registry.py`:
- `arxiv_registry.py`: arXiv-specific metadata + BibTeX cache
- `fetch_bibtex.py`: DBLP/CrossRef for non-arXiv papers and verification

---

## Experiment Planning (Claims-Evidence-Runs)

### Philosophy

The goal is NOT a giant benchmark wishlist. The goal is a **claim → evidence → run order** roadmap.

### Script

```bash
python scripts/experiment_plan.py --project-dir <paper_dir>
```

Output: `notes/experiment-plan.md` + `notes/experiment-tracker.md`

### 5-Stage Milestone Structure

| Stage | Goal | Decision Gate |
|-------|------|---------------|
| M0: Sanity | Data pipeline + metric correctness | Pass/fail |
| M1: Baseline | Reproduce strongest baseline | Numbers match? |
| M2: Main Method | Run on primary setting | Beats baseline? |
| M3: Decision | Ablations for novelty + simplicity | Claims supported? |
| M4: Polish | Robustness, qualitative, appendix | Nice-to-have |

### Key Rules

- Every experiment must defend a claim. If it doesn't change a reviewer's belief, cut it.
- Prefer one strong baseline family over many weak ones (max 3)
- Separate MUST-RUN from NICE-TO-HAVE
- Do NOT fabricate results — plan evidence, don't claim evidence
- Max 2 primary claims (one dominant + one supporting)

---

## Human Checkpoint / AUTO_PROCEED

### Configurable Automation Level

| Mode | Behavior |
|------|----------|
| `AUTO_PROCEED=true` (default) | Fully autonomous — auto-select top options, continue without pause |
| `AUTO_PROCEED=false` | Pause at gates — present results, wait for user confirmation |
| `human_checkpoint=true` | Pause after each review round — user can approve/customize/skip/stop |

### Checkpoint UI Pattern

When paused, present:
```
Round N/4 review complete.

Score: X/10 — [verdict]
Top weaknesses:
1. [weakness 1]
2. [weakness 2]

Options:
- "go" → implement all suggested fixes
- Custom instructions → implement your modifications
- "skip 2" → skip fix #2
- "stop" → end the loop
```

---

## Outputs

| File | Description |
|------|-------------|
| `REVIEW_STATE.json` | State recovery for cross-model review loop |
| `notes/cross-model-review.md` | Cumulative review log with raw reviewer responses |
| `notes/novelty-check.md` | Structured novelty verification report |
| `notes/experiment-plan.md` | Claim-driven experiment roadmap |
| `notes/experiment-tracker.md` | Run-by-run execution table |

---

## MCP Prerequisites

| MCP Server | Purpose | Required? |
|-----------|---------|-----------|
| Codex MCP (`@openai/codex`) | Cross-model review via external LLM (xhigh reasoning) | Optional (skip review if absent) |
| Any OpenAI-compatible MCP | Alternative reviewer (any capable model) | Optional alternative |

**Setup** (see `references/alphaxiv-setup.md` for alphaxiv; adjust model in Codex config):
```bash
npm install -g @openai/codex
codex setup                    # configure your preferred model
claude mcp add codex -s user -- codex mcp-server
```

All features degrade gracefully if MCP is unavailable — review steps are skipped, other workflows continue normally.

---

## 4-Layer Citation Verification

Concept from [AutoResearchClaw](https://github.com/aiming-lab/AutoResearchClaw). Goes beyond DBLP/CrossRef to verify citations against multiple academic APIs with similarity scoring.

### Verification Chain

| Layer | Source | Best For |
|-------|--------|----------|
| 1 | arXiv API (by eprint ID) | arXiv preprints |
| 2 | DOI resolution (CrossRef/DataCite) | Published papers |
| 3 | Semantic Scholar (title search, >0.80 similarity) | Any paper |
| 4 | LLM relevance scoring (manual) | Topical fit |

### Classifications

| Status | Meaning | Action |
|--------|---------|--------|
| VERIFIED | Found + metadata matches (≥0.80) | Keep |
| SUSPICIOUS | Found but metadata diverges (0.50-0.80) | Manual check |
| HALLUCINATED | Not found or similarity < 0.50 | Remove |
| SKIPPED | No title or APIs unreachable | Retry later |

### Script

```bash
# Verify all citations in ref.bib
python scripts/verify_citations.py --bib-file ref.bib

# Remove hallucinated entries
python scripts/verify_citations.py --bib-file ref.bib --remove-hallucinated --out-bib ref.clean.bib
```

Output: `notes/citation-verification.md` with per-entry classification.

**Integration**: Run after `bibtex_audit.py` (Phase 2.4) and before final integrity gate.

---

## PROCEED / REFINE / PIVOT Decision Loop

Concept from [AutoResearchClaw](https://github.com/aiming-lab/AutoResearchClaw). After analyzing experiment results, make an autonomous decision about research direction.

### Decision Framework

| Decision | When | Action |
|----------|------|--------|
| **PROCEED** | Core claims supported by evidence, review score ≥6/10 | Continue to paper writing or submission |
| **REFINE** | Partial support, fixable weaknesses | Tweak experiments → re-run (max 3 refines) |
| **PIVOT** | Fundamental hypothesis falsified | Discard → new direction (max 2 pivots) |

### Artifact Versioning

Each decision creates a version checkpoint:
- `v0`: Initial proposal
- `v1`: After first REFINE cycle
- `v2`: After second REFINE or PIVOT

### Script

```bash
# Evaluate readiness
python scripts/research_decision.py --project-dir <paper_dir> evaluate

# Record a decision
python scripts/research_decision.py --project-dir <paper_dir> record --decision PROCEED --reason "claims supported by ablation"

# View history
python scripts/research_decision.py --project-dir <paper_dir> status
```

Output: `notes/research-decisions.json` (decision history with timestamps).

### Integration with Review Loop

After each cross-model review round:
1. If score ≥ 6 → `PROCEED`
2. If score 4-5 and fixable → `REFINE` (implement fixes, re-review)
3. If score < 4 or core hypothesis fails → `PIVOT` (restart from Gate -1)

---

## Methodology-Evidence Consistency

Concept from AutoResearchClaw's Stage 18 peer review. Verifiers check whether paper claims match actual experimental evidence.

### Checks

- Paper claims N trials → verify actual run count matches
- Paper reports metrics → verify they appear in actual results
- Paper describes methods → verify code implements them
- Paper claims statistical tests → verify code performs them

### Integration

Add to Phase 2.4 (Integrity Gate) or Phase 2.55 (Self-Review):
1. Cross-reference `notes/claim-registry.md` with `notes/experiment-tracker.md`
2. For each claim, verify supporting evidence exists
3. Flag unsupported claims as integrity issues
