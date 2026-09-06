# Benchmark Comparison

- Created at: 2026-09-05T18:45:37+08:00
- Arms: 2
- Discipline profile: computer-science

Every number here is read from files the arms produced. A blank cell
means the arm has no artifact to read, which is a fact about the
pipeline, not a score of zero.

| Metric | gated | example |
|---|---|---|
| `references` | 45 | 8 |
| `identified` | 1 | 1 |
| `placeholders` | 0 | 0 |
| `cited_but_missing` | 0 | 0 |
| `entries_uncited` | 0 | 0 |
| `verified` | 1 |  |
| `hallucinated` | 0 |  |
| `required_sections` | 0.714 | 0.429 |
| `claims_with_verdicts` | 0 |  |
| `pages` | 7 |  |

## What each arm could not be measured on

- **gated**: every metric had an artifact behind it
- **example**: no citation-verification report; no claim registry; no compiled main.log

## What this table does not measure

Scientific quality, novelty, reviewer judgement and the time a human
spends repairing the draft. A pipeline can win every column here and
still produce a paper nobody should publish. See docs/BENCHMARK.md for
the protocol these numbers belong to.
