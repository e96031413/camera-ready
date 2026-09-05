# Idea Tournament: Competitive Research Idea Ranking

Based on EvoScientist/EvoSkills methodology for systematic idea generation and competitive ranking.

## Overview

When starting from scratch without a clear research direction, the Idea Tournament generates N candidate ideas, ranks them via Elo-style tournament, and produces a structured research proposal for the top idea.

## Phase 1: Tree-Structured Idea Generation

Generate up to **N_I = 21** candidate ideas by varying along 3 axes:

| Axis | Description | Example Variations |
|------|-------------|-------------------|
| **Technique** | Core methodology | Attention, contrastive learning, diffusion, RL, graph neural nets |
| **Domain** | Application area | NLP, CV, robotics, healthcare, code generation |
| **Formulation** | Problem framing | Classification → generation, supervised → self-supervised, static → dynamic |

### Generation Rules
1. Start with 3 seed ideas from literature gaps (Gate -1 output)
2. Expand each seed along all 3 axes → 9 first-level children
3. Cross-pollinate: combine techniques from different subtrees → 9-12 hybrid ideas
4. Diversity check: no two ideas share the same (technique, domain) pair
5. Each idea card contains: **Title** (≤15 words), **Core Mechanism** (1 sentence), **Key Advantage** (1 sentence), **Feasibility Score** (1-5), **Novelty Claim** (1 sentence)

## Phase 2: Elo Tournament Ranking

### 4 Quality Dimensions (each scored 1-10)

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| **Novelty** | 0.30 | Not a trivial extension of existing work; introduces new insight |
| **Feasibility** | 0.25 | Achievable within available compute/data/time budget |
| **Relevance** | 0.25 | Addresses an important open problem; community demand |
| **Clarity** | 0.20 | Can be explained in one paragraph; clear evaluation metric |

### Swiss-System Pairing (4-5 Rounds)
1. **Round 1**: Random pairing (all ideas start at Elo = 1500)
2. **Round 2-5**: Match ideas with similar Elo scores
3. **Per match**: Compare two ideas head-to-head across all 4 dimensions
4. **Elo update**: K-factor = 32 (standard); update after each match
5. **Convergence**: Stop when top-3 ranking is stable for 2 consecutive rounds

### Win Condition
Idea A beats Idea B if:
```
weighted_score(A) = 0.30*novelty + 0.25*feasibility + 0.25*relevance + 0.20*clarity
weighted_score(A) > weighted_score(B)
```

## Phase 2.5: Multi-Persona Idea Evaluation

After the Elo tournament produces a top-3 ranking, evaluate the top idea through
3 independent reviewer personas before presenting to the user. This catches weaknesses
that head-to-head comparison misses.

### Active Novelty Verification (run first)

Before persona reviews, proactively search for prior art:
1. Extract 4 search queries from the top idea:
   - **Core method**: the primary technical approach
   - **Problem domain**: the application area + specific problem
   - **Key component**: the most novel sub-component
   - **Broad approach**: a general query capturing the overall direction
2. For each query, search arXiv + Semantic Scholar (use alphaxiv MCP or `novelty_check.py`)
3. Deduplicate results by title similarity; exclude known inspiration sources
4. Classify novelty threat level:

| Threat Level | Definition | Action |
|---|---|---|
| critical_overlap | A paper implements the same method on the same problem | STOP — present to user: Proceed / Refine / Abandon |
| high_overlap | Multiple papers collectively cover most contributions | Flag in persona evidence; likely score 2-5 on novelty |
| moderate_overlap | Components exist separately, combination is new | Note in evidence; typical score 4-7 on novelty |
| low_overlap | Only tangentially related work found | Proceed normally |
| novel | No significantly related work found | Note: may reflect query limitations, not true novelty |

5. Save verification report to `notes/novelty-check.md` (feeds into persona reviews)

### Three Reviewer Personas

Run each persona independently (do not let one persona see another's review):

| Persona | Priority Dimensions | Evidence Level |
|---|---|---|
| **Senior ML Researcher** | Validity, Novelty | Full: all papers + code + novelty report |
| **Domain Expert** | Significance, Feasibility | Medium: abstracts + task context + novelty report |
| **Methods Specialist** | Feasibility, Clarity | Medium: code + implementation details + novelty report |

### 5 Evaluation Dimensions (each scored 1-10)

| Dimension | What to evaluate |
|---|---|
| **Clarity** | Can this be explained precisely in one paragraph? Is the evaluation metric obvious? |
| **Novelty** | How does this differ from existing work? (Use novelty verification report) |
| **Validity** | Are the theoretical claims sound? Do methods match goals? |
| **Feasibility** | Achievable within available compute/data/time? Building blocks exist? |
| **Significance** | Does this solve an important problem? Would practitioners adopt this? |

### Scoring Calibration

- 9-10 (10% of ideas): Groundbreaking / paradigm-shifting
- 7-8 (25%): Strong contribution with clear novelty
- 5-6 (45%): Solid but incremental
- 3-4 (15%): Notable weaknesses
- 0-2 (5%): Fundamentally flawed

### Area Chair Meta-Review

After all 3 personas review independently:
1. Compute average score per dimension
2. Where personas disagree by >3 points, resolve based on relevant expertise
   (Validity disagreements → weight Senior ML; Feasibility → weight Methods Specialist)
3. Compute overall average and apply decision thresholds:

| Average Score | Decision | Action |
|---|---|---|
| >= 7.0 | strong_accept | Present to user with full confidence |
| >= 6.0 | accept | Present to user; proceed to Gate 0 |
| >= 5.0 | borderline | Present report; ask user: proceed or refine? |
| < 5.0 | reject | Build feedback; refine idea (max 2 iterations) |

### Refinement Loop (if triggered)

1. Aggregate weaknesses and suggestions from all 3 personas
2. Revise the idea (not generate new) — address specific criticisms
3. Re-run evaluation (novelty verification + 3 personas + meta-review)
4. Maximum 2 refinement iterations before requiring user decision
5. If accepted after refinement, update the idea card before proceeding to Phase 3

### Integration with Existing Tournament

- **Input**: Top-ranked idea from Elo tournament (Phase 2)
- **Output**: Evaluated idea with decision and scores → feeds Phase 3
- **Issues CSV**: Add `IT0.5` (persona evaluation) issue in Ideation phase
- **Novelty report**: Reuses `novelty_check.py` from Gate -1 with targeted queries

## Phase 3: Direction Summarization

After tournament converges, summarize top-3 ideas:

For each top idea, produce:
1. **One-paragraph summary**: What, Why, How
2. **Differentiation**: How it differs from the other top-2
3. **Risk assessment**: Primary risk + mitigation strategy
4. **Resource estimate**: Compute, data, timeline

Present to user for selection. **STOP** until user picks one direction.

## Phase 4: Proposal Extension (5+1 Sections)

Expand selected idea into a structured proposal:

| Section | Content |
|---------|---------|
| **1. Problem Statement** | Gap in literature + why existing solutions fail |
| **2. Proposed Approach** | Core mechanism + technical novelty |
| **3. Expected Contributions** | 2-4 concrete contributions with evaluation criteria |
| **4. Experiment Plan** | Datasets, baselines, metrics, ablation variables |
| **5. Risk & Mitigation** | Top-3 risks with fallback plans |
| **+1. Timeline** | 4-week breakdown with milestones |

## Counterintuitive Tournament Rules

1. **Quantity before quality**: Generate 21 ideas even if first 5 seem good — breakthrough ideas often emerge from forced variation
2. **Feasibility is not optional**: A brilliant but infeasible idea scores 0 — weight feasibility at 0.25 minimum
3. **Cross-pollination wins**: The best ideas often combine techniques from different subtrees
4. **Kill your darlings**: If your favorite idea loses the tournament, respect the ranking
5. **Narrow beats broad**: "Improve transformers" loses to "Fix attention collapse in 100+ layer vision transformers"

## Integration with camera-ready

- **Input**: Gap analysis + candidate RQs from Gate -1
- **Output**: Structured proposal → feeds directly into Gate 0 (research snapshot)
- **Issues CSV**: Add `IT0` (tournament) and `IT1` (proposal) issues in Ideation phase
