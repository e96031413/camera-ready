# Quality Phases (Phase 2.3 - 2.75)

## Phase 2.3: Anti-AI Writing Check
After completing writing issues, scan for AI writing patterns:
1. Run scan: `python scripts/anti_ai_scan.py --project-dir <paper_dir>`
2. If MEDIUM/HIGH severity: rewrite flagged passages using `references/anti-ai-writing.md` guidelines.
3. For strict quantitative gates:
   ```bash
   python scripts/anti_ai_scan.py --project-dir <paper_dir> --strict
   ```
   See `references/writing-style.md` for thresholds.
4. Target: LOW severity (<=5 total AI patterns) before proceeding.
5. Update Anti-AI issue row to DONE when target met.

## Phase 2.35: Outline Completeness Check
Before writing prose for any section, verify its Stage 1 outline exists:
1. Check that each writing issue (Wx) has an outline in the Notes field or in `notes/outlines/`
2. Verify the outline lists: key arguments, planned citations, data points, logical flow
3. If no outline exists for a section about to be written, create one first (see `references/writing-style.md` § Two-Stage Writing)
This prevents the most common writing failure: jumping straight to prose without a plan.

## Phase 2.4: Integrity Gate (Pre-review; Stage 2.5)
Before reviewer rounds, run integrity checks (see `references/integrity-verification.md`):
1. Generate claim registry:
   ```bash
   python scripts/claim_registry.py --project-dir <paper_dir> --mode broad --write-csv
   ```
2. Audit BibTeX health + recency:
   ```bash
   python scripts/bibtex_audit.py --project-dir <paper_dir> --window-years 3 --min-recent-ratio 0.70 --fail-on-duplicate-keys
   ```
3. Run the gate:
   ```bash
   python scripts/integrity_gate.py --project-dir <paper_dir> --stage pre-review
   ```
If the gate fails, convert failures into `Integrity` issue rows and fix them first.

## Phase 2.5: Paper-Reviewer Loop (Top-tier)
After all writing issues are `DONE`, run reviewer rounds (see `references/paper-reviewer.md`):
1. Create reviewer context pack: `python scripts/paper_context_pack.py --project-dir <paper_dir>`
2. Ensure pre-review integrity gate has passed.
3. Run Round 1 + Round 2 (parallel roles -> meta-synthesis).

**Cross-Model Adversarial Review** (optional):
If Codex MCP is available, enhance with external LLM (see `references/autonomous-research.md`):
```bash
python scripts/cross_model_review.py --project-dir <paper_dir> init --topic "paper topic"
```
Up to 4 rounds. Score threshold: >=6/10 with positive verdict.

**DBLP/CrossRef Citation Verification**:
```bash
python scripts/fetch_bibtex.py --title "Paper Title" --author "First Author" --out-bib ref.bib
```

**4-Layer Citation Verification** (before final submission):
```bash
python scripts/verify_citations.py --bib-file <paper_dir>/ref.bib
python scripts/verify_citations.py --bib-file ref.bib --remove-hallucinated --out-bib ref.clean.bib
```

**PROCEED/REFINE/PIVOT Decision**:
```bash
python scripts/research_decision.py --project-dir <paper_dir> evaluate
python scripts/research_decision.py --project-dir <paper_dir> record --decision PROCEED --reason "claims supported"
```

## Phase 2.53: Multi-Layer Selfloop
Run three orthogonal quality checks (order: logic -> argument -> voice):
1. **Logic selfloop**: `python scripts/logic_selfloop.py --project-dir <paper_dir>`
2. **Argument selfloop**: `python scripts/argument_selfloop.py --project-dir <paper_dir>`
3. **Voice selfloop**: `python scripts/voice_selfloop.py --project-dir <paper_dir>`

If any selfloop fails, convert findings into issue rows and fix before proceeding.

## Phase 2.55: Paper Self-Review
After reviewer rounds converge:
1. Generate self-review report: `python scripts/paper_self_review.py --project-dir <paper_dir>`
2. Walk through 6-dimension checklist in `references/paper-self-review.md`.
3. For conference papers: verify venue-specific requirements using `references/conference-guides.md`.

## Phase 2.6: Systems-Paper Hardening (Strict Limits + Repro)
If targeting a venue with a strict page limit and double-blind anonymity requirements (e.g., top-tier CV/ML conferences), apply `references/systems-paper-hardening.md`:
- Treat page limit as a compile gate.
- Privacy/anonymity as a release gate.

Both are now enforced by tools rather than by discipline. Run them early and often, not once at the deadline:
```bash
python scripts/format_gate.py --project-dir <paper_dir> --venue <venue>       # page limit, sections, style file
python scripts/anonymity_check.py --project-dir <paper_dir>                    # identity leaks
```
`format_gate.py` reads the compiled `main.log`/`main.aux`, so compile first, and put `\label{sec:bib}` at the
bibliography so main text can be separated from references. Fix an overrun by cutting content: shrinking
margins, font size, or line spacing is checked for and rejected.

## Phase 2.75: Rhythm Refinement
After reviewer rounds converge, refine prose section-by-section: cut fillers, vary sentence lengths, fix voice leaks. Apply `references/writing-style.md` and `references/anti-ai-writing.md` guidelines. Run `python scripts/voice_selfloop.py --project-dir <paper_dir>` and `python scripts/anti_ai_scan.py --project-dir <paper_dir> --strict` to verify.

## Phase 3.5: Evo-Memory Update (Cross-Cycle Learning)
After QA gate passes, update research memory (see `references/evo-memory.md`):
1. **ESE**: Extract successful experiment strategies.
2. **IVE**: Classify experiment failures.
3. **Evolution report**: Generate `notes/evo-memory/evolution-report.md`.

## Phase 3.7: Autoresearch -- Skill Self-Optimization (Optional)
Based on Andrej Karpathy's autoresearch methodology. See `references/autoresearch.md` and `references/eval-guide.md`.

**Trigger phrases**: "optimize this skill", "improve this skill", "run autoresearch on", "make this skill better".

**Workflow**: Gather context -> Read skill -> Build eval suite -> Establish baseline -> Run experiment loop -> Write changelog -> Deliver results.

**Output files** (in `autoresearch-[skill-name]/`): `dashboard.html`, `results.json`, `results.tsv`, `changelog.md`, `SKILL.md.baseline`.
