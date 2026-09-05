# ML Paper Writing Philosophy

Purpose: synthesized writing advice from top ML researchers. Use as a mindset guide during paper writing.

## Time Allocation (Nanda)

Spend roughly equal effort on each of:
1. **Abstract** — 25% of writing effort
2. **Introduction** — 25%
3. **Figures** — 25%
4. **Everything else combined** — 25%

Most papers are accepted or rejected based on the first two pages. Invest accordingly.

## Core Definition (Nanda)

> "A paper is a short, rigorous, evidence-based technical story with a takeaway readers care about."

Not a lab notebook. Not a progress report. A **story**.

## The Three Pillars

By the end of the introduction, the reader must know:

- **The What**: 1-3 specific novel claims
- **The Why**: Rigorous empirical evidence supporting each claim
- **The So What**: Why readers should care (practical impact, theoretical insight, new capability)

## 7 Reader Expectation Principles (Gopen & Swan)

1. **Subject-verb proximity** — Keep subject and verb close together; don't separate with long clauses
2. **Stress position** — Place the most important information at the end of the sentence
3. **Topic position** — Begin sentences with familiar/contextual information
4. **Old before new** — Progress from known → unknown within each sentence
5. **One unit, one function** — Each paragraph makes exactly one point
6. **Action in verbs** — Use verbs for actions, not nominalizations ("we analyze" not "we perform an analysis")
7. **Context before new** — Set the stage before presenting new information

## Proactive Writing

- Deliver complete first drafts; don't ask approval per section
- Use confidence levels to calibrate:
  - **High confidence** → Full draft, ready for review
  - **Medium confidence** → Draft with flagged uncertainties
  - **Low confidence** → Ask targeted questions before drafting
- Scientists are busy — provide something concrete to react to, not questions to answer

## Abstract Formula (5 sentences)

1. What you achieved (the result)
2. Why this is hard or important (the gap)
3. How you do it (the method, one sentence)
4. What evidence you have (key metrics)
5. Most remarkable result (the hook)

Note: lead with the result, not the problem. Reviewers read hundreds of abstracts.

## Micro-Level Clarity

- **Minimize pronouns** — Use specific nouns; "the encoder" not "it"
- **Position verbs early** — "We propose X" not "In this paper, we introduce and propose X"
- **Delete fillers** — actually, basically, quite, essentially, in order to, it should be noted that
- **Be specific** — "improves accuracy by 3.2%" not "significantly improves performance"
- **Avoid intensifiers** — very, quite, really, highly (if you need emphasis, use evidence)
- **Eliminate hedging stacks** — "may potentially" → "may"; "seems to suggest" → "suggests"

## Introduction Rules

- Maximum 1-1.5 pages
- Contribution list: 2-4 bullet points, each with a concrete claim
- Methods should start by page 2-3 at the latest
- End the introduction with a roadmap paragraph only if the paper structure is non-obvious

## Figure 1

- Critical for reader engagement — draft early, before writing begins
- Should convey the core idea visually without reading any text
- Self-contained with an informative caption (≥2 sentences)
- Often the single most important element for acceptance
- Common types: method overview, comparison diagram, motivating example, teaser result

## Writing Anti-Patterns

- Starting every paragraph with "We" or "In this section"
- Using "novel" or "state-of-the-art" without evidence
- Describing what you will do instead of doing it ("We will now discuss...")
- Writing the related work section as a disconnected list of paper summaries
- Burying the main contribution in the middle of a paragraph

## Integration

- Applies throughout all writing phases
- Complements `references/writing-style.md` (tactical rules) and `references/anti-ai-writing.md` (authenticity)
