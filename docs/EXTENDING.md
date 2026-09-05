# Extending CameraReady

Five things are drop-in. You add a file; nothing in the Python needs to change.

| You want to support | Add | Validated by |
|---|---|---|
| A new venue | `assets/venues/<slug>.yaml` | `scripts/venue_config.py` |
| A new citation style | `assets/styles/<slug>.yaml` | `scripts/citation_style.py` |
| A new discipline | `assets/disciplines/<slug>.yaml` | `scripts/discipline_profile.py` |
| A new reporting guideline | `assets/checklists/<slug>.md` | `scripts/reporting_guideline.py` |
| A new venue checklist | `assets/checklists/<slug>.md` | `scripts/paper_checklist.py` |

Two things need code: a citation provider, and a phase in the autopilot state
machine. Both are described at the end.

Every profile is parsed by the small YAML subset in
`scripts/venue_config.py`. It supports scalars, block lists, folded (`>`) and
literal (`|`) block scalars, and comments. It rejects nested mappings, flow
collections and anchors, on purpose: a profile is configuration, not a place
for YAML cleverness. When the parser refuses your file, the message names the
line.

---

## Citation style

A style profile answers three questions: how to make LaTeX produce it, which
CSL file pandoc needs for the Word path, and which BibTeX fields an entry needs
before it can render correctly.

Create `assets/styles/<slug>.yaml`:

```yaml
style: harvard-cite-them-right          # must equal the filename stem
display_name: Harvard (Cite Them Right)
full_name: Cite Them Right, 12th edition
family: author-date                     # author-date | author-page | numeric | note
disciplines:
  - business
  - education

latex_backend: biblatex                 # biblatex | natbib | bst
latex_package_line: \usepackage[style=authoryear,backend=biber]{biblatex}
latex_extra_preamble: ""
latex_language_setup: \usepackage[british]{babel}
latex_bibliography_line: \printbibliography[title={Reference list}]
latex_cite_parenthetical: \parencite
latex_cite_narrative: \textcite
latex_required_packages:
  - biblatex
  - csquotes
bib_processor: biber                    # biber | bibtex | none

csl_id: harvard-cite-them-right         # the pandoc --csl identifier
csl_url: https://www.zotero.org/styles/harvard-cite-them-right
word_supported: true

required_fields_article:
  - author
  - title
  - journaltitle
  - year
required_fields_book: [author, title, year, publisher]
required_fields_inproceedings: [author, title, booktitle, year]
required_fields_thesis: [author, title, year, institution, type]
required_fields_misc: [author, title, year, doi|url]

reference_url: https://www.citethemrightonline.com/
notes: >
  Anything a contributor needs to know that the fields cannot say.
```

Three details decide whether it works:

**`latex_backend` picks the bibliography mechanics.** `biblatex` emits
`\addbibresource{ref.bib}` in the preamble and your `latex_bibliography_line`
at the end of the document. `bst` emits `\bibliographystyle{...}` in the
preamble and `\bibliography{ref}` at the end. Choosing the wrong one produces
a document that compiles and prints no references.

**Field names follow the backend, not the style.** biblatex wants
`journaltitle` and `institution`; classic BibTeX wants `journal` and `school`.
A profile that mixes them will pass its own gate and fail at build time.

**`doi|url` means "at least one of".** Use it wherever a style accepts either.

Check your work:

```bash
python scripts/citation_style.py list
python scripts/citation_style.py preamble harvard-cite-them-right
python scripts/citation_style.py validate harvard-cite-them-right --bib ref.bib
```

`tests/test_citation_style.py` runs the schema check over every installed
profile, so a broken file fails CI rather than a paper.

---

## Discipline

A discipline profile is what the workflow consults before any writing starts:
which style, which output format, which reporting guideline, which sections and
statements are not optional, and what gets papers rejected in that field.

Create `assets/disciplines/<slug>.yaml`:

```yaml
discipline: linguistics                 # must equal the filename stem
display_name: Linguistics
default_style: apa7
allowed_styles:                         # default_style must appear here
  - apa7
  - chicago-author-date
default_format: docx                    # latex | docx | markdown | typst
document_class: article
evidence_model: mixed-methods           # experimental | clinical | mixed-methods
                                        # | interpretive | doctrinal | empirical

reporting_guidelines:                   # each needs assets/checklists/<slug>.md
  - coreq
required_sections:
  - Abstract
  - Introduction
  - Data and Methods
  - Analysis
  - Discussion
  - References

ethics_approval_required: true
preregistration_expected: false
data_availability_required: true
code_availability_required: false
conflict_of_interest_required: true
funding_statement_required: true

peer_review_norm: journal, double-anonymized
common_rejections:
  - Elicitation procedure under-described
  - Claims about a language family from a single variety

reference_url: https://www.linguisticsociety.org/
notes: >
  What a contributor from outside the field would get wrong.
```

`evidence_model` carries weight beyond documentation: `interpretive` and
`doctrinal` disciplines skip the autopilot's experiment phase, because there is
no experiment to run. Every other value keeps it.

The six boolean fields become the Declarations section that `quick_start.py`
writes into the skeleton, and the statement list that
`discipline_profile.py requirements` prints.

Check your work:

```bash
python scripts/discipline_profile.py list
python scripts/discipline_profile.py requirements linguistics
```

The validator refuses a profile whose `default_style` has no file in
`assets/styles`, or whose reporting guideline has no question set. That
prevents a profile that reads well and does nothing.

---

## Reporting guideline

A guideline question set is Markdown with a fixed item shape. Create
`assets/checklists/<slug>.md`:

```markdown
# SQUIRE 2.0 — Question Set (quality improvement studies)

Source: https://www.equator-network.org/reporting-guidelines/squire/ (checked 2026-09-05).
Answer options: Yes / No / NA. Every answer needs a location or a reason.

This file paraphrases the guideline so the workflow can generate a worksheet.
It is not the official checklist; journals want that file submitted separately.

## 1. Title
**Question:** Does the title indicate that the report concerns an improvement initiative?
**Guidance:** Name the intervention and the setting.

## 2a. Problem description
**Question:** Is the nature and significance of the local problem described?
**Guidance:** Say who it affects and how it was measured before the change.
```

The parser requires `## <number>. <Topic>` followed by `**Question:**` and
`**Guidance:**` lines. The number may carry a trailing letter (`2a`), which is
how guidelines with lettered sub-items are represented. Anything else in the
file is treated as prose and ignored, so headers, licence notes and the source
citation are all fine.

Two rules the repository holds to:

**Paraphrase; do not copy.** Reproduce the topic and the substance, not the
official wording. Say so in the header, and link to the authoritative version.

**State when you checked.** Guidelines are revised. A question set with no
"checked" date is a question set nobody can trust.

Then reference it from the disciplines it serves and check:

```bash
python scripts/reporting_guideline.py --list
python scripts/reporting_guideline.py --guideline squire --project-dir papers/x
```

To make the worksheet pre-fill a hint for your new items, add a detector to
`SIGNAL_DETECTORS` in `scripts/reporting_guideline.py`: a topic pattern, a
manuscript pattern, and the hint text. A detector is always a hint. Nothing in
this workflow answers a checklist question, and a pull request that makes one
do so will not be merged.

---

## Venue

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the four-step recipe. In short:
add `assets/venues/<slug>.yaml`, add `assets/checklists/<slug>.md` if the venue
has a checklist, source every value from the official author guide, and record
the year you read it. Venue rules change annually and a stale profile is worse
than none.

---

## Citation provider (needs code)

`scripts/fetch_bibtex.py` resolves a citation through DBLP, then CrossRef, then
arXiv via CrossRef. To add a source — OpenAlex, PubMed, Semantic Scholar, an
institutional repository — write a function with this shape:

```python
def fetch_from_openalex(title: str, author: str = "") -> str | None:
    """Return a BibTeX string, or None when the source has no confident match."""
```

Three requirements, and they are not negotiable:

1. **Return None rather than a guess.** A wrong entry that looks right is the
   single worst failure mode in this workflow. Ambiguity is not a match.
2. **Return what the source returned.** Do not reformat, complete, or
   "improve" a record. The value of a fetched entry is that it is not invented.
3. **Report which source answered.** `fetch_bibtex()` returns
   `(bibtex, source)`; the source string ends up in the audit trail.

Add the call to the chain in `fetch_bibtex()`, ordered by how much you trust
the source's precision, and add a test that a near-miss title returns None.

---

## Autopilot phase (needs code)

`scripts/autopilot.py` holds a list of `Phase` objects and a `CHECKS` mapping
from phase name to a function `(project_dir, state) -> (passed, detail)`.

To add a phase, append a `Phase` in the right position and add its check:

```python
Phase(
    name="ethics",
    goal="Obtain and record ethics approval before any data are collected.",
    exit_condition="notes/ethics-approval.md names the approving body and the protocol number",
    next_actions=["Record the body, the number, and the approval date."],
    needs_human=True,
),
```

```python
def check_ethics(project_dir: Path, state: dict) -> tuple[bool, str]:
    path = project_dir / "notes" / "ethics-approval.md"
    if not path.is_file():
        return False, "notes/ethics-approval.md is missing"
    text = path.read_text(encoding="utf-8")
    if not re.search(r"\b(IRB|REC|protocol)\b.*\d", text):
        return False, "no approving body and protocol number recorded"
    return True, "ethics approval recorded"
```

A check reads the filesystem and the state file, and nothing else. That is what
makes a run inspectable, interruptible and resumable: the state is on disk, not
in a process. A check that calls a model, hits the network, or depends on the
order commands were run in breaks that property.

Phases are ordered and the state machine will not skip one. If a phase does not
apply to a discipline, make its check return `True` with a reason, the way
`check_experiments` does for interpretive fields. Do not make it optional.
