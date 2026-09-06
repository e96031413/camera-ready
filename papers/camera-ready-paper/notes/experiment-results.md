# Experiment Results

All measurements taken 2026-09-05 on Windows 10 (10.0.19045), Python 3.13.9,
MiKTeX + latexmk, from CameraReady at commit `7f2239a` (pre-fix) and `c80fb39` (post-fix) (plus one patch recorded
in E6). Every command below is in the repository; nothing here is simulated.

## E1 — Test suite
`python -m pytest -q` -> **545 passed, 0 failed** in 48.87 s. 34 test modules,
covering all verification gates, schemas, CLI tools, and failure modes.

## E2 — Repository-level self-checks
- `portability_check.py --docs` -> clean, 182 files scanned.
- `skill_spec_check.py` -> conforms to spec, 0 warnings.

## E3 — Gates refuse to advance (negative controls)
| Attempt | Command | Result |
|---|---|---|
| Advance a fresh run past `ideate` with no research question | `autopilot.py advance` | refused, exit 1: "notes/research-question.md is missing" |
| Create the issues CSV before the kickoff box is ticked | `bootstrap_ieee_review_paper.py --stage issues` | refused, exit 1: "Kickoff gate is not confirmed in the plan" |
| Force the same transition with a reason | `autopilot.py advance --force --reason "..."` | allowed, and written into the run journal: "forced past 'ideate' despite: notes/research-question.md is missing. Reason: demonstration of override journaling" |

The override is not a silent escape hatch: the state file keeps both the
violated condition and the stated reason.

## E4 — Rule gates on a manuscript that violates them
Target: `examples/minimal-review-paper` (a normal, non-anonymous IEEE paper).
| Gate | Command | Verdict |
|---|---|---|
| Citation style | `citation_style.py validate ieee --bib ref.bib` | PASS (8/8 entries carry the fields IEEE needs) |
| Citation style, entry missing `journal` | same, on a one-entry fixture | FAIL, exit 1, names the entry and the missing field |
| Privacy | `paper_privacy_scan.py` | pass |
| Anti-AI prose scan | `anti_ai_scan.py` | LOW, 1 pattern |
| Anonymity (double-blind) | `anonymity_check.py` | 3 BLOCKERs, exit 1: `\author{`, `\IEEEauthorblockA{`, and a named GitHub URL |
| Venue format, NeurIPS | `format_gate.py --venue neurips --strict` | FAIL, exit 1: 2 missing mandatory sections, style file absent; page limit SKIPped with the reason (no page count in `main.log`) |
| Integrity, final stage | `integrity_gate.py --stage final` | FAIL, exit 1: names the claim registry (MISSING when none generated; 0 filled verdicts when one exists) |

Compile of the same example: `compile_paper.py` -> exit 0 in 5.8 s.

## E5 — Citation path: no route from model memory to `ref.bib`
- Fabricated but plausible title, `fetch_bibtex.py --title "Gated Diffusion
  Transformers for Bibliographic Provenance Repair"` -> `[VERIFY] — not found in
  DBLP or CrossRef`. No BibTeX is emitted, so nothing can be appended to a `.bib`.
- The 45 references of this paper were all fetched by `arxiv_registry.py`
  (arXiv API) and exported to `ref.bib`; the file was never hand-written.

## E6 — Post-hoc verification, and a defect it exposed
`verify_citations.py` on this paper's 45-entry `ref.bib`, every entry of which
came from the arXiv API minutes earlier:

- **Before the patch (1 run):** VERIFIED 5, SUSPICIOUS 0, HALLUCINATED 34,
  SKIPPED 6 — i.e. 34 false positives on references of known provenance.
  Cause, confirmed by isolating layer 1: the arXiv Atom feed opens with a feed
  `<title>` reading `arXiv Query: search_query=&id_list=...`, and the layer-1
  regex matched that instead of the `<entry>` title. Similarity against the real
  title was then near zero, so every arXiv-sourced entry fell through to the
  layer-3 title search, which the rate-limited Semantic Scholar endpoint answered
  with `not_found` -> HALLUCINATED.
- **Patch (2026-09-05-v2):** read the title inside `<entry>`; raise the inter-request
  sleep from 0.5 s to the 3 s arXiv asks for. 9 insertions, 4 deletions, one file.
  Test suite still 422/422.
- **After the patch (6 runs):** VERIFIED 39 / 38 / 41 / 38 / 45 / 45; SUSPICIOUS 0;
  **HALLUCINATED 0 in all six runs**; SKIPPED 6 / 7 / 4 / 7 / 0 / 0. Every entry
  verified in at least one run (union 45/45). The residual SKIPPED count is
  transient API unavailability, not a verdict about the reference.
- **Fabricated fixture, 3 entries with no `eprint`, after the patch:** VERIFIED 0,
  HALLUCINATED 0, SKIPPED 3 — with Semantic Scholar unreachable the detector
  cannot decide, and declines rather than guessing.

Reading: a post-hoc detector is a function of API weather. It produced 34 false
accusations on this bibliography before the patch and 0-3 "cannot tell" verdicts
after it, while the fetch-time provenance path produced the same 45 correct
entries under every condition. This is the paper's central measured claim, and it
is a claim about where verification is placed, not about detector quality.

## E7 — Coverage
8 discipline profiles, 6 citation styles, 6 conference venue configs, 50
reference documents, 62 scripts of which 57 can exit non-zero (i.e. can block).

## Threats to validity
- Single machine, single OS; no cross-platform timing.
- E6 run-to-run variance comes from third-party APIs and is not controlled.
- E4 uses one worked example, not a corpus of manuscripts.
- The claim registry extractor (E4, integrity gate) picks up preamble and TikZ
  bodies as "claims"; the registry is a worksheet for a human, not a classifier.
