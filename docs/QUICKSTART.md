# Quickstart

> In a hurry? `python scripts/quick_start.py --title "<title>" --discipline <field>`
> creates a buildable project in one command; [DEMO.md](DEMO.md) shows the whole
> run. This page is the longer path, with the expected output at each step.

From nothing to a compiled PDF. Fifteen minutes, most of it spent installing
LaTeX.

If you only want to see what the output looks like, skip all of this and open
[`examples/minimal-review-paper/main.pdf`](../examples/minimal-review-paper/main.pdf).

---

## 1. Install

### Requirements

| | Needed for | How to check |
|---|---|---|
| **Python 3.10+** | Everything | `python --version` |
| **A LaTeX distribution** | Compiling to PDF | `pdflatex --version` |
| Claude Code, or any agent that reads `SKILL.md` | The guided workflow | — |

TeX Live (Linux), MacTeX (macOS), or MiKTeX (Windows) all work. Install the
full distribution rather than the minimal one; the templates use packages the
minimal installs omit, and chasing missing `.sty` files one at a time is a bad
first hour.

The core scripts import nothing outside the Python standard library. There is
no `pip install` step for the main workflow. Optional extras — poster
rendering, PowerPoint math, narrated video — are listed in
[`requirements.txt`](../requirements.txt) and are only needed if you use those
features.

### Get the files

```bash
git clone https://github.com/e96031413/camera-ready.git
cd camera-ready
```

**To use it as a Claude Code skill**, copy the whole folder into your skills
directory:

```bash
# macOS / Linux
cp -r . ~/.claude/skills/camera-ready

# Windows (PowerShell)
Copy-Item -Recurse . "$env:USERPROFILE\.claude\skills\camera-ready"
```

Then invoke it with `/camera-ready` in Claude Code. The skill sets
`disable-model-invocation: true`, so it never activates on its own — you ask
for it.

**To use the scripts on their own**, stay in the cloned directory and run them
directly. Every script is standalone and self-documented:

```bash
python scripts/compile_paper.py --help
```

### Verify the install

```bash
python -m pytest -q
python scripts/compile_paper.py --project-dir examples/minimal-review-paper
```

Expected: the test suite passes, and the second command exits 0 after writing
`examples/minimal-review-paper/main.pdf`. If the compile fails on a missing
`.sty`, your LaTeX install is the minimal one — install the full distribution.

---

## 2. Start a paper

Pick your target venue first. It determines the page limit, the required
sections, and whether you need a checklist — and it is much cheaper to know
that before you write than after.

```bash
python scripts/venue_setup.py --list-venues
```

```
aaai       AAAI     7 pages, two-column
acl        ACL      8 pages, two-column
cvpr       CVPR     8 pages, two-column
iclr       ICLR     9 pages, single-column
icml       ICML     8 pages, two-column
neurips    NeurIPS  9 pages, single-column
```

Scaffold the project:

```bash
python scripts/bootstrap_ieee_review_paper.py \
  --stage kickoff \
  --topic "efficient attention mechanisms for long-context models"
```

Expected output: a new project directory containing `plan/`, `main.tex`,
`ref.bib`, and `IEEEtran.cls`. The command prints the path — call it
`<paper_dir>` from here on.

Then pull in the venue requirements:

```bash
python scripts/venue_setup.py --venue neurips --project-dir <paper_dir>
```

Expected output: `<paper_dir>/notes/venue.md` with the page limit, required
sections, and the official URLs. If the style file cannot be downloaded
automatically, the command prints the official URL and tells you where to
unpack it — that is a normal outcome, not an error. Style files are never
bundled with this repository; see
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) for why.

---

## 3. Approve the plan, then write

Open the generated file in `<paper_dir>/plan/`. It contains a **kickoff gate**
that is unchecked, and the workflow will not write prose past it.

This is the part people want to skip. Don't. The plan fixes the scope, the
outline, and the citation budget, and every later gate checks against it. A
paper whose plan says "8 pages, NeurIPS" fails the format gate loudly at page
10; a paper with no plan just quietly becomes 14 pages.

Fill in the outline, check the gate box, then create the execution contract:

```bash
python scripts/bootstrap_ieee_review_paper.py \
  --stage issues --topic "<same topic>" --with-literature-notes

python scripts/validate_paper_issues.py <paper_dir>/issues/<file>.csv
```

Expected output: `Validation passed!` with a per-phase summary. Each CSV row is
one unit of work with its own acceptance criteria and verified-citation count.
You mark rows `DONE`; nothing marks them for you.

---

## 4. Add citations — never from memory

This is the rule the whole project is built around. Bibliographic metadata is
fetched from a source, never recalled:

```bash
# By arXiv ID — authoritative, and the way to go when you have the ID
python scripts/arxiv_registry.py --project-dir <paper_dir> \
  fetch-bibtex 1706.03762 --out-bib <paper_dir>/ref.bib

# By title, via DBLP and CrossRef
python scripts/fetch_bibtex.py --title "Attention Is All You Need" \
  --out-bib <paper_dir>/ref.bib
```

Expected output: a complete BibTeX entry appended to `ref.bib`. When the
lookup fails, you get a `[VERIFY]` placeholder instead of an invented entry —
which is the correct behaviour, and your cue to find the paper yourself.

Title search is fuzzy. Check that the entry you got back is the paper you
meant; a title query for "Adam" will happily return a different paper about
Adam. Fetching by arXiv ID or DOI avoids this entirely.

---

## 5. Compile

```bash
python scripts/compile_paper.py --project-dir <paper_dir>
```

Expected output: exit 0, a page-count report, and `<paper_dir>/main.pdf`.
Anything reported as `Overfull \hbox` is a line running into the margin — fix
it rather than ignoring it.

For the page-count report to separate main text from references, put a label
at the bibliography:

```latex
\label{sec:bib}
\bibliography{ref}
```

Without it the tool can only report total pages, and it says so.

---

## 6. Run the gates before you submit

```bash
# Does it fit the venue's rules?
python scripts/format_gate.py --project-dir <paper_dir> --venue neurips

# Does anything identify you? (double-blind venues)
python scripts/anonymity_check.py --project-dir <paper_dir>

# Does the writing read as machine-generated?
python scripts/anti_ai_scan.py --project-dir <paper_dir>

# Do the claims match the cited evidence?
python scripts/integrity_gate.py --project-dir <paper_dir> --stage final

# Venue checklist worksheet (fill it in yourself; the tool never answers for you)
python scripts/paper_checklist.py --project-dir <paper_dir> --venue neurips
python scripts/paper_checklist.py --project-dir <paper_dir> --validate
```

Every one of these reports and stops. None of them edits your paper, and none
of them answers a checklist question on your behalf.

---

## 7. Package for arXiv

```bash
python scripts/arxiv_package.py --project-dir <paper_dir>
```

Expected output: `submission.tar.gz` plus
`<paper_dir>/notes/arxiv-submission-report.md`. The tarball is flattened, the
`.bbl` is embedded (arXiv does not run BibTeX), and comments and `\todo` macros
are stripped, because uploaded arXiv source is public.

Before uploading, do the one check that catches most failures — unpack it
somewhere empty and compile it there:

```bash
mkdir /tmp/check && tar xzf submission.tar.gz -C /tmp/check
cd /tmp/check && pdflatex main.tex && pdflatex main.tex
```

Two passes, no `bibtex`. If the bibliography renders with no `[?]` markers, the
tarball is good.

**This tool never uploads anything.** Submission is yours to do, at
<https://arxiv.org/submit>.

---

## Where to go next

| You want to | Read |
|---|---|
| See a finished project | [`examples/minimal-review-paper/`](../examples/minimal-review-paper/) |
| Understand the full gated workflow | [`../SKILL.md`](../SKILL.md) |
| Target a specific conference | [`../references/conference-guides.md`](../references/conference-guides.md) |
| Write a paper grounded in your codebase | [`../references/standalone-workflows.md`](../references/standalone-workflows.md) |
| Make slides, a poster, or a narrated video | [`../references/post-acceptance-materials.md`](../references/post-acceptance-materials.md) |
| Write a rebuttal | [`../references/rebuttal-strategy.md`](../references/rebuttal-strategy.md) |
| Add a venue | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
