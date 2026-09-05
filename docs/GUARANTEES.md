# What is guaranteed, and what is not

This workflow makes a narrow promise and refuses a wide one. The distinction
matters because the wide promise is the one that gets papers retracted.

Three categories, and everything the tooling does falls into exactly one.

---

## 1. Machine-verified — the tool decides, and can fail your build

These checks read files and produce a verdict. They do not ask a model. They do
not have an opinion. If one fails, something is measurably wrong.

| Check | Command | What a failure means |
|---|---|---|
| Every citation was fetched from a source | `verify_citations.py` | An entry has no provenance, or a `PLACEHOLDER_` key survived |
| Entries carry the fields the style needs | `citation_style.py validate` | The reference will render incomplete |
| Every `\cite` key exists in the bibliography | `bibtex_audit.py` | The build will emit `?` |
| The paper fits the venue's page limit | `format_gate.py` | Desk rejection |
| No author identity leaks in a blind submission | `anonymity_check.py` | Desk rejection |
| No private path, key or internal URL is in the source | `paper_privacy_scan.py` | A disclosure you cannot undo |
| The document compiles | `compile_paper.py` | The obvious one |
| The submission tarball contains what arXiv needs | `arxiv_package.py` | A failed upload |
| Every issue in the CSV is closed | `autopilot.py check` | Work you believe is done is not |
| Every reporting-guideline item has an answer and a location | `reporting_guideline.py --validate` | An incomplete checklist |
| Every review comment has a resolution | `autopilot.py check --phase revise` | A comment was quietly dropped |
| Sources run on Windows, Linux and macOS alike | `portability_check.py` | An encoding or path bug that only appears on one platform |
| `SKILL.md` matches the Agent Skills spec | `skill_spec_check.py` | The skill will be rejected on upload |

These are the guarantees. They hold regardless of who or what wrote the paper.

---

## 2. Detected and reported — the tool points, you decide

These produce signals, not verdicts. A signal is evidence for a human
judgement, and acting on one without reading it is a mistake.

| Signal | Command | Why it is not a verdict |
|---|---|---|
| Prose reads as machine-generated | `anti_ai_scan.py` | Heuristics over phrasing. Good writing sometimes trips them; bad writing sometimes does not |
| A claim may exceed its cited evidence | `claim_registry.py`, `integrity_gate.py` | Whether a source supports a claim is a reading, not a string match |
| The contribution may not be novel | `novelty_check.py` | Novelty is a judgement about a field |
| A reviewer would likely object here | `paper_self_review.py`, `cross_model_review.py` | A model's guess at a reviewer, not a reviewer |
| A checklist answer looks supported by the text | `paper_checklist.py`, `reporting_guideline.py` | The hint says a phrase appears, not that the claim is true |
| The argument has a gap | `logic_selfloop.py`, `argument_selfloop.py` | Structural heuristics over prose |

Every one of these tools reports. None rewrites. That is deliberate: a tool
that silently fixes what it flags removes the evidence you needed to judge it.

**No tool here ever answers a checklist question.** `paper_checklist.py` and
`reporting_guideline.py` both write `[TODO]` into every answer field and refuse
to validate until a person has replaced it. A detected signal appears beside
the question as a hint, clearly labelled, and never in the answer.

---

## 3. Yours alone — no tool touches these

| | Why |
|---|---|
| Whether the research question is worth asking | A judgement about a field's priorities |
| Whether the method answers the question | Domain expertise |
| Whether an interpretation of a source is right | Reading, not matching |
| Whether the statistics were chosen correctly | Requires knowing what the data are |
| Whether a limitation is disclosed honestly | Requires knowing what you did not report |
| Whether authorship and contribution claims are accurate | Only the authors know |
| Whether the ethics approval covers what was done | Only you and the committee know |
| Whether to submit | Always manual, by design |

The workflow scaffolds, verifies and blocks. The research, the argument, and
every checklist answer are yours. The gates are built so that skipping that
work fails a check rather than producing something that looks finished.

---

## The autopilot does not change this

`autopilot.py` runs a paper from a topic to a camera-ready package. It is
sequencing and gate enforcement, not judgement. The agent does the research,
the writing and the revision; the state machine decides what comes next and
refuses to advance when a phase's exit condition is unmet.

Two phases will not close on their own, whatever the agent does:

- **plan** — an approving person's name must be recorded, by hand
- **camera-ready** — the package gets built; submitting is always yours

You can force past any gate with `--force --reason "<why>"`. The reason is
written into the run's journal and stays there. That is the intended escape
hatch: overrides are allowed, and they are on the record.

---

## What this cannot catch

Be clear-eyed about the residue.

- **A citation that is real, fetched, correctly formatted, and does not support
  the sentence it is attached to.** Provenance is verifiable; relevance is not.
- **A number that is wrong in the source data.** Nothing here re-runs your
  analysis.
- **A subtly wrong paraphrase of a source's finding.** The tools compare
  structure, not meaning.
- **A guideline or venue rule that changed after a profile was written.** Every
  profile records the date it was checked. Check it again before you submit.
- **Whether pandoc's conversion preserved a complex table or equation.**
  `export_document.py` says so on every run, and the answer is: open the file
  and look.

Spot-check your citations. The Quickstart shows a real case where a title
search returned the wrong Adam.
