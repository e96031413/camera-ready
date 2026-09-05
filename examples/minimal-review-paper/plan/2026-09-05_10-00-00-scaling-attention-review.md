---
title: "From Attention to Adaptation: A Short Review of Scaling Levers in Deep Learning"
slug: scaling-attention-review
timestamp: 2026-09-05_10-00-00
paper_type: review
venue: arXiv (IEEEtran two-column)
status: DONE
---

# Paper Plan: Scaling levers in deep learning

This is the **worked example** shipped with CameraReady. It is deliberately
small — four sections, eight citations — so that the whole pipeline can be
read end to end in a few minutes. A real review targets 6-10 pages and 60-80
citations, as the default plan template says.

Everything here was produced by the gated workflow in `SKILL.md`. Read this
file, then `issues/`, then `main.tex`, then `main.pdf`, in that order: that is
the order the workflow produces them in, and the point of the example is the
order, not the paper.

## Goal

- Produce a short review of the levers that made deep learning scale:
  architecture, optimization, pre-training, and parameter-efficient adaptation.
- Every citation verified against a primary source. No BibTeX from memory.
- One visualization (timeline figure) plus one comparison table.

## Scope

- **In**: synthesis of eight landmark papers, one figure, one table.
- **Out**: novel experiments, exhaustive coverage, benchmark numbers we did
  not reproduce ourselves.

## Kickoff Gate

- [x] Scope and outline confirmed.
- Venue/template: IEEEtran two-column (arXiv).
- Target length: 2 pages of main text. Deliberately below the usual 6-10, since
  this is a pipeline demonstration, not a submission.
- "Latest" definition: as-of date 2026-09-05.
- Scope boundaries: architecture, optimization, pre-training, adaptation. Not
  covered: reinforcement learning, multimodality, systems and hardware.

## Clarification Q&A

| Question | Answer |
|---|---|
| What venue and page limit? | arXiv, no hard limit; 2 pages by choice. |
| Which subtopics must be covered? | The four levers named above. |
| Emphasis? | The trade-off each lever made, not its headline result. |
| Required datasets or baselines? | None; this is a synthesis, not a benchmark. |
| Expected visualizations? | One timeline figure, one comparison table. |

## Confirmed Outline

1. **Introduction** — the scaling question, and the four levers this review
   covers. 2 citations.
2. **Architecture and Optimization** — residual connections and adaptive
   optimization as the enablers of depth. 3 citations.
3. **Pre-training and Transfer** — the shift from task-specific training to
   pre-train-then-adapt. 3 citations.
4. **Efficient Adaptation** — why full fine-tuning stopped being affordable.
   1 citation.
5. **Discussion and Limitations** — what this short review does not cover.

## Citation Policy

Every entry in `ref.bib` was fetched with:

```bash
python scripts/arxiv_registry.py --project-dir examples/minimal-review-paper \
  fetch-bibtex <arxiv_id> --out-bib examples/minimal-review-paper/ref.bib
```

No entry was written by hand, and no entry carries a `PLACEHOLDER_` prefix.
The arXiv API is the source of the author lists, titles, and years — not
anyone's recollection of them. Anyone can re-run that command and get byte-for-
byte the same entries.

Note the year fields: the API reports the year of the latest arXiv version, so
`vaswani2023attentionneed` says 2023 for a paper first posted in 2017. That is
what the source says, so that is what the bibliography says. Correcting it to
the first-posting year is an editorial decision for the author to make and
record — not something the tool should do silently.

## Plan Notes

- Discovery keywords: "transformer", "residual learning", "adaptive optimizer",
  "pre-training", "parameter-efficient fine-tuning".
- Candidate titles considered:
  1. "From Attention to Adaptation: A Short Review of Scaling Levers in Deep
     Learning" (**chosen** — names both endpoints of the arc)
  2. "Four Levers of Deep Learning Scale" (too cute, undersells the synthesis)
  3. "A Short Review of Scaling in Deep Learning" (too broad for eight
     citations to support)

## Reviewer Notes

Deliberate limitations of this example, stated so nobody mistakes them for
oversights:

- Eight citations cannot support a survey claim. The paper says so in its
  Limitations section rather than pretending otherwise.
- No experiments, so no error bars, seeds, or compute budget to report.
- The venue is arXiv, which has no checklist and no anonymity requirement. To
  see the venue gates working, run `format_gate.py` against this project with
  `--venue neurips`: it reports the missing Broader Impact section and the
  missing style file, which is the correct answer for a paper not written for
  NeurIPS.
