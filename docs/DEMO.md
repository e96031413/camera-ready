# Demo: a psychology paper, from nothing to a Word file

A real transcript, captured on Windows with Python 3.12 and pandoc 3.8. Paths
are shortened; nothing else is edited. Every command works the same on macOS
and Linux.

The point of this walkthrough is what the tool refuses to do. It writes no
prose, invents no citation, and answers no checklist question. What it produces
is a structure that will fail a gate if you skip a step.

---

## 1. Pick a field

```console
$ python scripts/quick_start.py --list
Disciplines:
  business           Business, management and economics       style=apa7
  computer-science   Computer science and machine learning    style=ieee
  education          Education research                       style=apa7
  humanities         Humanities                               style=mla9
  law                Law and legal studies                    style=chicago-notes
  medicine           Medicine and health sciences             style=vancouver
  psychology         Psychology and cognitive science         style=apa7
  social-science     Social science                           style=chicago-author-date
```

The style is not a preference. Psychology gets APA because APA journals require
it, and picking the field picks the style, the output format, the mandatory
sections and the reporting guidelines together.

## 2. Create the project

```console
$ python scripts/quick_start.py --title "Sleep duration and next-day recall" --discipline psychology
quick_start 2026-09-05-v1: created papers/sleep-duration-and-next-day-recall

  main.md          6 stub sections
  ref.bib             empty, with the fetch command in a comment
  plan/2026-09-05_13-00-03-sleep-duration-and-next-day-recall.md
  issues/2026-09-05_13-00-03-sleep-duration-and-next-day-recall.csv
  notes/autopilot-state.json   run started at phase 1 of 10

Next, in order:

  1. python scripts/discipline_profile.py requirements psychology
  2. python scripts/export_document.py --input papers/…/main.md --style apa7
  3. python scripts/autopilot.py status --project-dir papers/…

The skeleton builds but says nothing. That is the point: the argument is yours.
```

Markdown, not LaTeX, because APA journals take Word. `main.md` holds six stub
sections and a Declarations block; every stub is an HTML comment saying what
belongs there. There is no generated sentence anywhere in the file.

## 3. Read what the field demands

```console
$ python scripts/discipline_profile.py requirements psychology
# Psychology and cognitive science — what this field requires

Evidence model: experimental
Default output format: docx
Default citation style: apa7
Also accepted: nothing else; this field expects one style
  -> APA 7th edition, author-date, processed by biber
  -> pandoc CSL id for the Word path: apa

## Required sections
  - Abstract
  - Introduction
  - Method
  - Results
  - Discussion
  - References

## Required statements
  - Ethics approval / IRB statement
  - Preregistration or protocol reference
  - Data availability statement
  - Code availability statement
  - Conflict of interest statement
  - Funding statement

## Reporting guidelines
  Choose the one that matches the study design, then run:
    python scripts/reporting_guideline.py --guideline jars-quant --project-dir <dir>
    python scripts/reporting_guideline.py --guideline consort --project-dir <dir>
    python scripts/reporting_guideline.py --guideline prisma2020 --project-dir <dir>

## What gets rejected here
  - Underpowered sample with no a priori power analysis
  - Analyses that were not preregistered and are not labelled exploratory
  - Effect sizes and confidence intervals omitted in favour of p-values alone
  - Missing IRB or ethics approval statement
```

Six required statements, three candidate guidelines, and the four rejection
reasons a psychology reviewer reaches for first. That list is why a
computer-science default does not transfer.

## 4. Try to advance without doing the work

```console
$ python scripts/autopilot.py advance --project-dir papers/sleep-duration-and-next-day-recall
autopilot 2026-09-05-v1: cannot leave 'ideate' — notes/research-question.md is missing

Phase 1/10: ideate
  Goal:  Turn the topic into one answerable research question with a stated scope.
  Exit:  notes/research-question.md exists and names the question, the population
         and what is out of scope
  Next:
    - Write notes/research-question.md: the question, why it is open, and the
      boundary of the claim.
```

A title is not a research question. The gate says which file is missing and
what has to be in it.

Writing a one-line question does not pass either — the check requires enough
text to state a population and a boundary, because a question without either is
a question no method can answer.

## 5. Write the question, then advance

```console
$ python scripts/autopilot.py advance --project-dir papers/sleep-duration-and-next-day-recall
autopilot 2026-09-05-v1: left 'ideate' — notes/research-question.md, 48 words

Phase 2/10: literature
  Goal:  Find what already exists, and fetch every citation from a source.
  Exit:  ref.bib has at least --min-citations entries and none carries a
         PLACEHOLDER_ key
  Next:
    - python scripts/fetch_bibtex.py --help        # never write BibTeX from memory
    - python scripts/novelty_check.py --help       # what does this add over what exists?
```

## 6. The bibliography gate is not about count

```console
$ python scripts/citation_style.py validate apa7 --bib papers/…/ref.bib
1 entr(ies) missing fields required by APA 7th edition:

  smith2019 (@misc): APA 7th edition needs author, doi|url

citation_style 2026-09-05-v1: FAIL
```

APA needs a DOI or a stable URL for anything that has one. The gate catches the
entry that would render as an unusable reference, before a reviewer does.

## 7. Build the Word file

```console
$ python scripts/export_document.py --input papers/…/main.md --style apa7
Wrote papers/sleep-duration-and-next-day-recall/main.docx (11,201 bytes)
  Citation style: apa7 via apa.csl
  Open the file and check tables, figures and equations; pandoc does not
  translate every LaTeX construct, and it fails quietly when it cannot.
```

The CSL file was fetched on first use and cached in `assets/csl/`. Citations are
resolved by citeproc, so the reference list is generated from `ref.bib` and
never typed.

## 8. Where the run is

```console
$ python scripts/autopilot.py status --project-dir papers/sleep-duration-and-next-day-recall
autopilot 2026-09-05-v1
  topic:      Sleep duration and next-day recall
  discipline: psychology   style: apa7   format: docx

  [done]  1. ideate
  [NOW ]  2. literature
  [    ]  3. plan
  [    ]  4. issues
  [    ]  5. experiments
  [    ]  6. draft
  [    ]  7. verify
  [    ]  8. review
  [    ]  9. revise
  [    ] 10. camera-ready
```

Phase 3 will not close until a person's name is recorded against the plan.
Phase 10 never closes: it builds the package and stops, because submitting is
always yours.

---

## What this demo did not do

It did not write a sentence of the paper, choose a method, decide whether the
question was worth asking, or answer a single checklist item. Those are the
parts the workflow is built to make you do, not to do for you. See
[GUARANTEES.md](GUARANTEES.md).

## Recording your own

Every command here is copy-pasteable. To record a terminal capture:

```bash
# asciinema, then upload or convert to a GIF with agg
asciinema rec demo.cast -c "bash docs/demo-script.sh"
agg demo.cast demo.gif
```

A contributed recording is welcome — open a pull request with the `.gif` under
`docs/` and a link from this page.
