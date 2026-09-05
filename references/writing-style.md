# Writing Style (Concise)

## Clarity and rhythm
- Vary paragraph length (short / medium / long); avoid monotone blocks
- Prefer active voice and concrete verbs
- Keep transitions minimal; let structure carry flow

## Citation density
- Never 3 consecutive sentences without citations
- Use citations for every non-trivial claim or comparison
- Meet per-section targets in the issues CSV

## Tone
- Expert, precise, and evidence-first
- Separate facts from open questions
- Avoid overclaiming; qualify uncertainty
- See `references/counterintuitive-principles.md` (Writing section) for underclaiming-in-prose and mechanism-first framing guidance

## Avoid
- Wordy fillers ("in order to", "it is worth noting", "due to the fact that")
- Vague claims without evidence
- Repetitive sentence openings

## Anti-AI Writing Discipline
- Cut filler phrases: "Due to the fact that" → "Because"; "In order to" → "To"; "It is worth noting that" → cut entirely
- Break formulaic structures: avoid negative parallelisms, rule of three lists, "not only...but also"
- Vary rhythm: alternate short/medium/long sentences intentionally
- Trust readers: don't over-explain obvious implications
- Avoid AI vocabulary: Additionally, crucial, delve, enhance, furthermore, landscape, leveraging, multifaceted, notably, pivotal, realm, robust, streamline, tapestry, transformative, underscore
- Avoid Chinese AI patterns: 值得注意的是, 這不僅...更..., 無疑, 具有重要意義, 深入探討

## Quantitative Style Gates (opt-in with `--strict`)

These checks are enforced by `anti_ai_scan.py --strict` and `voice_selfloop.py`:

### Zero-Tolerance Patterns (must be 0 occurrences)
Generator/planner voice leaks — instant FAIL:
- "this subsection surveys", "this section surveys"
- "this pipeline", "this workspace"
- "in this section, we survey/review/discuss/examine/explore"
- "the remainder of this", "we organize this section"
- "this survey aims to"

### Per-Pattern Occurrence Caps
| Pattern | Max occurrences |
|---------|----------------|
| "taken together" | 2 |
| "it is worth noting" | 1 |
| "in summary" | 3 |
| "as mentioned earlier/above/previously" | 2 |

### Mid-Sentence Citation Ratio
- Target: ≥30% of `\cite` commands appear mid-sentence (not at sentence boundaries)
- Weave citations into prose: "As shown by Smith et al.~\cite{smith2024}, ..." rather than appending at the end

### Opener Diversity
- No ≥3 consecutive paragraphs starting with the same 2-word pattern
- Vary paragraph openings deliberately

## Proactive Writing
- Deliver complete first drafts; iterate based on feedback
- Use confidence levels: high → full draft; medium → draft with flags; low → ask targeted questions
- Scientists are busy — provide concrete work products to react to

## Two-Stage Writing Protocol (Outline → Prose)

Never write prose directly from an issue description. Always go through two explicit stages:

### Stage 1: Bullet Outline (planning artifact — NOT the deliverable)

For each section, create a structured outline with:
- Main argument or finding for each paragraph (1 sentence)
- Key citations planned (author, year, claim they support)
- Data points, statistics, or figure references to include
- Logical flow indicators (transition notes between paragraphs)

Example outline for a Methods subsection:
```text
OUTLINE: Section 3.2 — Attention Mechanism
- P1: Problem with standard attention at scale [cite vaswani2017, child2019]
  - O(n^2) complexity makes >4k tokens impractical
  - Existing linear approximations lose expressiveness [cite katharopoulos2020]
- P2: Our approach — sparse attention with learned patterns
  - Formal definition of sparsity mask M (Eq. 3)
  - Connection to mixture-of-experts routing
- P3: Training procedure
  - Two-phase: pre-train mask → fine-tune jointly
  - Cite similar curriculum strategies [cite bengio2009]
- P4: Complexity analysis
  - Table 2 reference: O(n√n) vs O(n^2)
```

### Stage 2: Convert to Flowing Prose (the actual deliverable)

Transform each bullet cluster into a paragraph:
1. Turn bullet points into complete sentences with subjects, verbs, objects
2. Add transitions between sentences ("However," "Building on this," "In contrast,")
3. Weave citations mid-sentence: "As shown by Smith et al.~\cite{smith2024}, ..." (not appended at end)
4. Expand with context that bullets omit
5. Vary sentence length deliberately (see rhythm rules above)

### Why This Matters

Writing prose directly from an issue description produces:
- Monotone paragraph structure (every paragraph has the same shape)
- Missing citations (hard to remember what needs citing without an outline)
- Logical gaps (skipped transitions between ideas)
- Difficulty revising (no skeleton to restructure around)

The outline is a planning artifact that can be reviewed cheaply before committing to prose.

### Integration

- **Phase 2 per-issue loop**: For each writing issue, create Stage 1 outline first,
  then convert to Stage 2 prose. Save outline in the issue's Notes field or `notes/outlines/`.
- **Review benefit**: Reviewers can compare outline intent vs. actual prose to catch drift.
