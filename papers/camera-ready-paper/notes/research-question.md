# Research Question

**RQ.** Can the failure modes of LLM-agent paper writing — fabricated citations,
claims unsupported by the artifacts they cite, and violations of venue and
discipline rules — be suppressed by *tool-enforced gates* that a language model
cannot satisfy by assertion, rather than by prompting or post-hoc detection?

## Why the question is open
Existing agentic research systems (AI Scientist, Agent Laboratory and successors)
optimise for autonomy over the research loop and treat manuscript integrity as a
property of the generating model. Large-scale audits of published references show
non-existent citations rising with LLM adoption, and detection work is post-hoc:
it inspects a finished manuscript instead of preventing the defect at write time.
Whether a *process* design — deterministic checks that hold state outside the
model's context and refuse to advance — removes these defects by construction has
not been described as an engineering contribution.

## Population / object of study
The CameraReady skill: a 62-script, ~18.5k-line Python workflow (commit 7f2239a)
that drives a paper from topic to an arXiv submission package across 8 discipline
profiles, 6 citation styles and 6 conference venues.

## Claim boundary — what this paper does NOT claim
- No claim that gated generation improves *scientific quality*, novelty or
  acceptance rates; the gates target verifiability and rule compliance only.
- No human-subject study, no reviewer-perception study, no A/B comparison against
  an ungated agent baseline; the evaluation is a system evaluation over the
  repository's own test suite and worked examples.
- No claim of coverage beyond the 8 profiles, 6 styles and 6 venues shipped.
- No claim about non-English manuscripts: citation machinery is language-neutral,
  prose heuristics are English-tuned.
