# Worked example: a short review paper

**[→ Read the compiled output: `main.pdf`](main.pdf)**

This directory is a complete CameraReady project, produced by the gated
workflow in [`../../SKILL.md`](../../SKILL.md) and committed so you can see
what the pipeline actually delivers before installing anything.

It is deliberately small — 2 pages, 8 citations — because the point is the
*shape* of the output, not the paper. A real review targets 6-10 pages and
60-80 citations.

## Read it in this order

The order matters: it is the order the workflow produces them in, and each
artifact is the contract for the next.

| # | File | What it shows |
|---|---|---|
| 1 | [`plan/`](plan/) | The approved plan. Scope, outline, citation policy, and the titles that were rejected. Nothing is written until this is approved. |
| 2 | [`issues/`](issues/) | The execution contract as CSV. Twelve rows, each with acceptance criteria, a dependency, and a verified-citation count. |
| 3 | [`ref.bib`](ref.bib) | Eight entries, every one fetched from the arXiv API by ID. None written from memory. |
| 4 | [`main.tex`](main.tex) | The paper. One TikZ figure, one `booktabs` table, a real Limitations section. |
| 5 | [`main.pdf`](main.pdf) | The compiled result. |
| 6 | [`notes/`](notes/) | Gate output: the anti-AI scan report and the arXiv submission report. |

## Reproduce it

From the skill root (`camera-ready/`):

```bash
# Compile — exit 0, no undefined citations, no overfull hbox
python scripts/compile_paper.py --project-dir examples/minimal-review-paper

# Contract validation
python scripts/validate_paper_issues.py \
  examples/minimal-review-paper/issues/2026-09-05_10-00-00-scaling-attention-review.csv

# Quality and integrity gates
python scripts/anti_ai_scan.py       --project-dir examples/minimal-review-paper
python scripts/paper_privacy_scan.py --project-dir examples/minimal-review-paper
python scripts/anonymity_check.py    --project-dir examples/minimal-review-paper

# Venue gate — see the note below about the expected FAILs
python scripts/format_gate.py --project-dir examples/minimal-review-paper --venue neurips

# arXiv packaging — builds a tarball, uploads nothing
python scripts/arxiv_package.py --project-dir examples/minimal-review-paper
```

You need a LaTeX distribution for the first command. The rest are pure Python
standard library.

## Two results that look like failures and are not

**`format_gate.py --venue neurips` reports three FAILs.** That is the correct
answer. This paper was written for arXiv with the IEEEtran template, so it has
no Broader Impact section, no paper checklist, and no `neurips_2025.sty`. The
gate is showing you exactly what you would have to fix to retarget it — which
is what a gate is for. Run it before you assume a paper is submittable
somewhere it was not written for.

**`anonymity_check.py` reports three BLOCKERs.** Also correct. The paper is
signed, and it links to a public repository. arXiv is not double-blind, so
none of that is a problem here. Run the same command against a real
double-blind submission and the same three findings become the reason it does
not get desk rejected.

Both tools are demonstrated here in the state where they *report* something,
because a tool that only ever prints "OK" teaches you nothing about what it
checks.

## What the example does not show

- A real experimental section, so no error bars, seeds, or compute budget.
- The post-acceptance track: Beamer slides, PowerPoint, poster, narrated video.
- The codebase-grounded paper type, which reads a real repository as evidence.
- The rebuttal workflow.

Those are all in `SKILL.md` and `references/`. Keeping them out of this example
is what makes it readable in five minutes.
