# Paper Mining (Knowledge Extraction)

Purpose: extract actionable writing knowledge from research papers to improve your own writing. Use when studying exemplary papers from your target venue.

## Input Types

- PDF (downloaded papers)
- DOCX (shared drafts)
- arXiv link (fetch and parse)

## IMRaD Analysis Framework

### Introduction
- How is the problem framed? (gap-driven, motivation-driven, question-driven)
- Contribution statement style (bullet list, inline, numbered)
- Literature review approach (chronological, thematic, methodological)
- Hook technique (surprising fact, open question, practical consequence)

### Methods
- Technical description approach (top-down overview → details, or bottom-up components → assembly)
- Algorithm presentation (pseudocode, flowchart, mathematical formulation)
- Component breakdown (how are sub-modules introduced and connected?)
- Notation conventions

### Results
- Findings presentation order (best result first? or build-up?)
- Table/figure integration (referenced inline or in dedicated subsections?)
- Quantitative language ("outperforms by X%" vs "achieves comparable performance")
- How are negative results handled?

### Discussion
- Interpretation style (cautious vs assertive)
- Limitations acknowledgment (dedicated subsection? inline? honest or perfunctory?)
- Future work framing (concrete next steps vs vague directions)

## 4 Knowledge Categories

### 1. Structure Patterns
- Section organization and ordering
- Transition strategies between sections
- Citation integration style (parenthetical vs narrative)
- How claims are supported (experiment, theory, reference, example)

### 2. Writing Techniques
- Transition phrases used between paragraphs
- Sentence templates for common moves (e.g., "Unlike X, our approach...")
- Active vs passive voice distribution
- Recurring rhetorical patterns

### 3. Submission Conventions
- Venue-specific section naming
- Required content (ethics, limitations, checklist)
- Figure/table placement conventions
- Supplementary material organization

### 4. Review Response Patterns
- How authors handle major concerns (if camera-ready differs from submission)
- Common revision strategies visible in final papers
- Appendix content that likely came from reviewer requests

## Extraction Template

Use this format when recording extracted knowledge:

```markdown
### Pattern: [Name]
**Source:** [Paper Title], [Venue] ([Year])
**Context:** [When to use this pattern]
**Description:**
[Concise description with a concrete example from the source paper]

**Example:**
> [Direct quote or paraphrase demonstrating the pattern]
```

## Mining Workflow

1. Select 3-5 exemplary papers from your target venue (best paper awards, high-cite)
2. Read each paper through the IMRaD framework above
3. Extract patterns into the 4 categories
4. Record using the extraction template
5. Identify patterns that appear across multiple papers (high-signal)
6. Apply extracted patterns to your own draft

## Integration

- Extracted writing techniques enrich `references/writing-style.md`
- Venue conventions feed into `references/conference-guides.md`
- Structure patterns inform outline design in Phase 1
