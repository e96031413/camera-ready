# Benchmark protocol: gated against ungated agentic writing

2026-09-05-v1

CameraReady claims that tool-enforced gates suppress fabricated citations,
unsupported claims and rule violations. The claim is about a process, so it can
only be settled by running the same task through more than one process and
measuring the outputs the same way. This document is the protocol for that
comparison. `scripts/benchmark_compare.py` implements the measurement half; it
does not run the arms, and it takes no position on which arm should win.

## What is being compared

An **arm** is a pipeline that turns a topic into a finished paper project
directory. At least two are needed:

| Arm | Description |
|---|---|
| `gated` | CameraReady, gates enforced, overrides journaled |
| `ungated` | The same model with the same tools and no gate enforcement |
| `ungated-prompted` | The same model told in the prompt to verify every citation |

The third arm matters more than it looks. Without it, a result only shows that
tools beat nothing; with it, the result speaks to whether enforcement beats
instruction, which is the actual claim.

## What has to be held constant

Vary one thing. Everything below is part of the task, not part of the arm:

- the topic, and the exact wording of the task given to each arm;
- the model, including version, temperature and any reasoning setting;
- the tool surface: the same search and fetch tools, reachable the same way;
- the wall-clock and token budget per arm, stated in the report;
- the target: venue, page limit, citation style, discipline profile;
- the machine, the network, and the day (bibliographic APIs vary by the hour).

Record every one of these in the report. An arm that ran on a different
afternoon has a different network, and citation verification is sensitive to it.

## Sampling

One topic proves nothing. Use at least 10 topics, drawn from a fixed list
written before the arms run, spanning fields where the pipeline claims coverage.
Run each arm on each topic; report per-topic results, not only the mean. Three
repetitions per cell if the budget allows, because generation is stochastic and
so is the network.

Pre-register the topic list, the arms and the metrics before running anything,
and publish it with the results. Choosing metrics after seeing outputs is how a
tool paper reports a win it did not earn.

## Machine-checkable metrics

`benchmark_compare.py` reads these from the finished projects:

| Metric | Meaning | Direction |
|---|---|---|
| `references` | entries in `ref.bib` | context, not a score |
| `identified` | share of entries carrying an arXiv id or DOI | higher |
| `placeholders` | entries still marked unverified | lower |
| `cited_but_missing` | `\cite` keys with no entry | lower |
| `entries_uncited` | entries never cited | lower |
| `verified` | share a stored verification run called VERIFIED | higher |
| `hallucinated` | entries a stored verification run rejected | lower |
| `required_sections` | share of the discipline's mandatory sections present | higher |
| `claims_with_verdicts` | share of claim-registry rows carrying a verdict | higher |
| `ai_patterns` | count from a stored anti-AI report | lower |
| `pages` | page count from a compiled `main.log` | context |

Run the verification, claim-registry and anti-AI steps on **every** arm with the
same commands, including the ungated ones. Measuring an arm with a gate it never
ran is measuring the measurement, not the arm.

```
python scripts/verify_citations.py --bib-file <arm>/ref.bib --output <arm>/notes/citation-verification.md
python scripts/claim_registry.py --project-dir <arm> --write-csv --overwrite
python scripts/anti_ai_scan.py --project-dir <arm>
python scripts/compile_paper.py --project-dir <arm>
python scripts/benchmark_compare.py --arm gated=<a> --arm ungated=<b> --discipline computer-science
```

## Human metrics the tool cannot compute

The interesting outcomes need people:

- **Repair time.** A domain expert, blind to the arm, brings each manuscript to
  submittable quality; the measure is minutes spent and edits made.
- **Citation correctness.** A second expert samples 20 citations per paper and
  judges whether the citing sentence describes the cited work. Provenance and
  alignment are different failures, and only a reader separates them.
- **Reviewer judgement.** Reviewers score the papers under normal venue
  criteria, blind to the arm.

Report inter-rater agreement for every human metric. Two annotators minimum.

## Reporting

Publish, for each cell: the arm, topic, repetition, raw metrics JSON, the
manuscript, and the environment record. State the failures: arms that produced
nothing compilable, runs abandoned at budget, gates that crashed.

A blank metric means the arm produced no artifact to measure. It is not a zero,
and averaging it as one is the easiest way to fake this benchmark.

## What a result here does not establish

Neither arm's score speaks to whether the paper is worth publishing. This
protocol measures verifiability and rule compliance, and a pipeline can win
every column while producing work that answers no question anyone asked.
