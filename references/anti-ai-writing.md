# Anti-AI Writing Patterns

Purpose: detect and remove LLM-generated writing patterns to improve authenticity. Based on Wikipedia's "Signs of AI writing" guide.

## 5 Core Rules

| # | Rule | Before | After |
|---|------|--------|-------|
| 1 | Cut filler phrases | "It is worth noting that X improves..." | "X improves..." |
| 2 | Break formulaic structures | "First... Second... Third... In conclusion..." | Vary connectors; merge or reorder |
| 3 | Vary rhythm | All sentences 15-20 words | Mix 5-word and 25-word sentences |
| 4 | Trust readers | "This is important because..." | State the fact; let readers infer importance |
| 5 | Cut "quotable" passages | "In the ever-evolving landscape of AI..." | Delete entirely or replace with specifics |

## AI Pattern Detection (English)

| Pattern | Example | Fix |
|---------|---------|-----|
| Undue emphasis | "It is crucial to note..." | Delete the wrapper |
| Promotional language | "groundbreaking", "revolutionary" | Use measured terms |
| Vague attributions | "Research has shown..." | Cite specific work |
| Superficial -ing analysis | "highlighting the growing importance" | State the specific importance |
| AI vocabulary | Additionally, crucial, delve, enhance, furthermore, landscape, leveraging, multifaceted, notably, pivotal, realm, robust, streamline, tapestry, transformative, underscore | Replace with plain alternatives |
| Em-dash overuse | "Our method — which is novel — outperforms..." | Use commas or restructure |
| Elegant variation | Alternating "the model/the system/the framework" for the same thing | Pick one term; be consistent |

## AI Pattern Detection (Chinese)

| Pattern | Fix |
|---------|-----|
| 值得注意的是 | Delete or state directly |
| 這不僅...更... | Simplify; use two sentences |
| 在...背景下 | State the context plainly |
| 無疑 / 毋庸置疑 | Remove; let evidence speak |
| 提供了...視角/啟示 | Be specific about what insight |
| 具有重要意義 | State the specific significance |
| 為...提供了新的思路 | Name the specific idea |
| 深入探討/分析/研究 | Just say "we study" or "we analyze" |

## "Adding Soul"

- Have opinions: state what you think and why, backed by evidence
- Vary rhythm intentionally: short punchy sentences after long explanatory ones
- Acknowledge complexity: "This works well for X but fails when Y"
- Use first-person when appropriate: "We observe..." not "It can be observed..."
- Show domain expertise: use precise terminology, not generic descriptions

## Scoring Rubric

| Dimension | 0-2 (AI-like) | 3-5 (Mixed) | 6-8 (Human) | 9-10 (Expert) |
|-----------|----------------|--------------|--------------|----------------|
| Directness | Filler-heavy | Some filler | Mostly direct | Every word earns its place |
| Rhythm | Monotone | Some variation | Natural flow | Deliberate pacing |
| Trust | Over-explains | Moderate | Respects reader | Assumes peer-level audience |
| Authenticity | Generic | Some personality | Clear voice | Distinctive perspective |
| Density | Padded | Average | Lean | Maximum signal per sentence |

- **Total**: 50 max (5 dimensions × 10 points)
- **Target**: ≥ 35/50

## Workflow

1. Write draft (do not self-censor during drafting)
2. Scan with the English/Chinese pattern tables above
3. Rewrite every flagged passage
4. Score using the rubric
5. Iterate until score ≥ 35/50

## Integration

- Run between Phase 2 writing and Phase 2.4 integrity gate
- Complements `references/writing-style.md` (style) and `references/integrity-verification.md` (factual accuracy)
