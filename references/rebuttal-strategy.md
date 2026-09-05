# Rebuttal & Review Response Strategy

Purpose: systematic approach to crafting reviewer responses. Use after receiving peer reviews.

## Comment Classification

| Type | Priority | Action |
|------|----------|--------|
| Major issues | P0 — address first | Requires new experiments, analysis, or significant rewriting |
| Minor concerns | P1 | Clarifications, additional references, minor edits |
| Misunderstandings | P2 | Clarify without defensiveness; often indicates unclear writing |
| Typographical errors | P3 | Fix silently; acknowledge briefly |

## Response Strategies

| Strategy | When to Use | Template |
|----------|-------------|----------|
| **Accept** | Reviewer is right | "We agree. We have [specific change] in Section X." |
| **Defend** | You have evidence | "We respectfully note that [evidence]. See [reference/result]." |
| **Clarify** | Ambiguity in your text | "We apologize for the confusion. We have clarified in Section X that [rewrite]." |
| **Experiment** | Reviewer wants more evidence | "We have conducted [new experiment]. Results in Table X / Appendix Y." |

## Rebuttal Structure

1. **Thank reviewers** — one sentence acknowledging effort
2. **Summarize changes** — bullet list of all major modifications
3. **Per-reviewer responses** — use R→A→C format:
   - **R[n].Q[m]**: Quote or paraphrase the reviewer comment
   - **A**: Your response (strategy from above)
   - **C**: Specific change made (section, page, line if possible)
4. **Summary table** — all modifications with locations

```
| Change | Section | Type | Reviewer |
|--------|---------|------|----------|
| Added ablation on X | 4.3 | New experiment | R2 |
| Clarified Y definition | 3.1 | Rewrite | R1, R3 |
```

## 5 Success Factors

1. **Acknowledge strengths first** — begin each per-reviewer section by thanking them for specific positive feedback
2. **Provide clarity** — expand unclear sections; add appendix details for space-constrained content
3. **Justify experimental choices** — use ablation studies to defend design decisions
4. **Address ethical implications proactively** — don't wait for reviewers to push harder
5. **Emphasize practical applicability** — connect contributions to real-world impact

## Tone Management

- Professional and grateful, never defensive
- Use "We appreciate the reviewer's insight..." not "The reviewer is wrong..."
- Acknowledge valid points before disagreeing
- Use data and evidence, not assertions
- Keep responses concise; reviewers read many rebuttals

## Tactical Tips

- **Identify supportive reviewers**: Reinforce their positive assessment; make it easy for them to champion your paper
- **Target borderline papers**: Rebuttals have maximum impact when scores are split; focus energy there
- **Reinforce core contributions**: Remind reviewers of what makes the work valuable
- **Demonstrate responsiveness**: Show you took every comment seriously, even minor ones
- **Use color in revised manuscript**: Blue for additions, red for deletions (if venue allows)

## Integration

- Feeds into existing `response-to-reviewers-template.md`
- Convert reviewer comments into issues CSV rows for tracking
- See `references/paper-reviewer.md` for understanding reviewer perspective
