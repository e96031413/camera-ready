# Evo-Memory: Cross-Cycle Research Memory System

Based on EvoScientist/EvoSkills methodology for persistent research learning across paper cycles.

## Overview

Evo-Memory prevents repeating failed research directions and preserves successful experiment strategies across multiple paper-writing cycles. It operates through three evolution mechanisms tied to specific workflow events.

## Memory Stores

### M_I: Ideation Memory
Tracks research directions — both promising and dead-end.

| Field | Description |
|-------|-------------|
| `direction_id` | Unique identifier (e.g., `DIR-2026-001`) |
| `title` | Research direction title |
| `description` | 2-3 sentence summary |
| `source` | Which paper/cycle generated this |
| `status` | `promising` / `exhausted` / `infeasible` / `merged` |
| `failure_type` | `implementation` / `fundamental` / `none` (see IVE) |
| `evidence` | Key experimental results or literature citations |
| `last_updated` | Timestamp |

### M_E: Experimentation Memory
Stores reusable strategies for data processing, training, architecture, and debugging.

| Field | Description |
|-------|-------------|
| `strategy_id` | Unique identifier (e.g., `STR-2026-001`) |
| `category` | `data_processing` / `model_training` / `architecture` / `debugging` / `evaluation` |
| `title` | Strategy title |
| `description` | What the strategy does and when to use it |
| `context` | Under what conditions this strategy works |
| `counter_context` | When this strategy does NOT work |
| `source` | Which experiment/paper produced this |
| `success_count` | Times successfully reused |
| `last_used` | Timestamp |

## Three Evolution Mechanisms

### IDE: Idea Direction Evolution
**Trigger**: After Idea Tournament (Gate -0.5) completes.
**Action**: Extract promising directions that were NOT selected for the current paper.

Protocol:
1. From tournament top-3, the selected idea becomes the paper; remaining 2 go to M_I as `promising`
2. From bottom ideas, extract any that were novel but infeasible → M_I as `infeasible` with reason
3. From cross-pollination ideas, extract technique combinations that scored high → M_I as `promising`
4. Tag all entries with the current paper topic for retrieval context

### IVE: Idea Validation Evolution
**Trigger**: When Experiment Pipeline Stage 3 (proposed method) fails.
**Action**: Classify failure as implementation vs. fundamental, and update M_I.

Decision tree:
```
Stage 3 failed
├── Did a simpler version of the method work?
│   ├── YES → Implementation failure
│   │   └── M_I: keep direction as `promising`, add debugging notes to M_E
│   └── NO → Is the core assumption valid (literature + theory)?
│       ├── YES → Implementation failure (likely infrastructure)
│       │   └── M_I: keep as `promising`, add infra notes to M_E
│       └── NO → Fundamental failure
│           └── M_I: mark as `exhausted`, record why the assumption failed
```

**Critical distinction**: Implementation failures mean the idea is still viable — just the execution needs work. Fundamental failures mean the research direction itself is flawed. Only fundamental failures should prevent revisiting.

### ESE: Experiment Strategy Evolution
**Trigger**: When Experiment Pipeline Stage 3 or 4 succeeds.
**Action**: Extract reusable strategies into M_E.

Extraction protocol:
1. **What worked**: Specific technique/config that led to success
2. **Why it worked**: Causal analysis (not just correlation)
3. **When to reuse**: Conditions under which this strategy applies
4. **When NOT to reuse**: Counter-conditions (e.g., "only works with ≥10k training samples")
5. **Abstraction level**: Generalize from specific values to principles (e.g., "LR=3e-4 for ViT-B" → "ViT models converge well at LR ~3e-4 with cosine schedule")

## Memory Retrieval

Before starting any new paper cycle, query both memory stores:

### For Ideation (Gate -1)
```
Query M_I:
- Filter: status != 'exhausted'
- Sort by: relevance to new topic (embedding similarity)
- Return: top-5 promising directions + all exhausted directions in related area
```
The exhausted directions are equally important — they tell you what NOT to pursue.

### For Experiments (Phase 1.5)
```
Query M_E:
- Filter: category matches current experiment type
- Sort by: success_count DESC, relevance to current setup
- Return: top-3 strategies per category
```

## Memory Maintenance

### Pruning Rules
1. **Staleness**: Entries not updated in 6+ months get flagged for review
2. **Contradiction**: If a strategy in M_E fails in a new context, add the counter-context rather than deleting
3. **Supersession**: If a better strategy emerges, link the old one as `superseded_by`
4. **Version tracking**: Major updates create a new version; minor updates edit in-place

### 6 Counterintuitive Memory Rules
1. **Abstract before storing**: "LR=3e-4 worked" is useless; "ViT-B converges well at LR~3e-4 with cosine schedule on ImageNet-scale data" is reusable
2. **Failed directions are valuable**: M_I's exhausted entries prevent wasting months on dead-ends
3. **Distinguish implementation vs direction failures**: This is the single most important classification (IVE)
4. **Active pruning > passive accumulation**: A lean, high-quality memory beats a bloated one
5. **Cross-pollination**: Strategies from M_E in one domain may apply to another — always search broadly
6. **Human-readable reports**: Generate evolution reports after each paper cycle for the research team

## File Structure

```
<paper_dir>/notes/
├── evo-memory/
│   ├── ideation-memory.json    # M_I entries
│   ├── experiment-memory.json  # M_E entries
│   ├── evolution-report.md     # Per-cycle summary
│   └── retrieval-log.md        # What was retrieved and how it influenced decisions
```

## Integration with camera-ready

- **Gate -1**: Query M_I before ideation to avoid exhausted directions
- **Gate -0.5**: IDE extracts non-selected directions after tournament
- **Phase 1.5**: Query M_E for relevant experiment strategies
- **Phase 1.7**: IVE/ESE triggered by experiment pipeline outcomes
- **Phase 3**: Generate evolution report summarizing what was learned
- **Issues CSV**: Add `EM0` (memory retrieval) and `EM1` (memory update) issues
