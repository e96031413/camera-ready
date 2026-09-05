# Contributing to CameraReady

Thanks for helping. This document covers the development setup, the test
suite, and the two contributions we most want: **new venues** and **new
reference documents**.

## Development setup

```bash
git clone https://github.com/e96031413/camera-ready.git
cd camera-ready

python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements-dev.txt
```

A LaTeX distribution (TeX Live, MiKTeX, or MacTeX) is required for the
compilation tests. Tests that need `pdflatex` skip themselves when it is
absent, so the suite still runs without LaTeX — but please install it before
touching anything under `assets/template/`.

The core scripts use only the Python standard library. **Keep it that way.**
If a feature needs a third-party package, import it lazily inside the
function that needs it, fail with an actionable message when it is missing,
and list it as optional in `requirements.txt`.

## Running the tests

```bash
python -m pytest -q                 # full suite
python -m pytest tests/test_format_gate.py -q   # one file
```

Every script must also survive a `--help` smoke test. CI runs this, and it
has caught real crashes before:

```bash
for f in scripts/*.py; do python "$f" --help >/dev/null || echo "FAIL $f"; done
```

The `--help` path must never import an optional dependency or touch the
filesystem. Build the `ArgumentParser` before doing any work.

Two lint gates run in CI and must pass locally before you open a pull request:

```bash
python scripts/portability_check.py --docs   # Windows/macOS/Linux hazards
python scripts/skill_spec_check.py --strict  # SKILL.md against the Agent Skills spec
```

`portability_check.py` fails on text I/O without an explicit encoding,
subprocess output decoded with the locale encoding, POSIX-only path literals,
`shell=True`, and a `python3` command in the documentation. Mark a deliberate
platform-specific line with `# portability: ignore -- <reason>`.

## Adding a citation style, discipline or reporting guideline

Each is a drop-in file with a documented schema, and none of them needs a code
change. The schemas, the required fields and the checks are in
[docs/EXTENDING.md](docs/EXTENDING.md):

| Contribution | File | Verify with |
|---|---|---|
| Citation style | `assets/styles/<slug>.yaml` | `python scripts/citation_style.py list` |
| Discipline | `assets/disciplines/<slug>.yaml` | `python scripts/discipline_profile.py requirements <slug>` |
| Reporting guideline | `assets/checklists/<slug>.md` | `python scripts/reporting_guideline.py --list` |

Three rules hold for all three:

1. **Source every value.** Link the authoritative page and record the date you
   read it. A profile with no date is a profile nobody can trust.
2. **Paraphrase; never copy.** Reproduce the substance of a checklist item, not
   its official wording, and say so in the header.
3. **Never make a tool answer a question.** Detected signals are hints beside
   the question. A pull request that pre-fills an answer will not be merged.

The test suite validates every installed profile, so a broken file fails CI
rather than a paper.

## Adding a new venue

This is the highest-value contribution. Four steps:

1. **`assets/venues/<venue>.yaml`** — copy an existing file and fill in every
   field. `page_limit_main`, `columns`, `anonymous`, `style_file_url`, and
   `author_guide_url` are required. Cite the official author guide for every
   number; do not guess.
2. **`assets/checklists/<venue>.md`** — the checklist question set, if the
   venue has one. Use the exact `## N. Topic` / `**Question:**` /
   `**Guidance:**` block structure that `scripts/paper_checklist.py` parses.
   **Paraphrase** the official questions; do not paste the verbatim LaTeX
   block from the venue style file into this repository. If the venue has no
   checklist, set `checklist: false` in the YAML and skip this file.
3. **`references/conference-guides.md`** — add the venue to the quick
   reference table and add a per-venue detail section.
4. **Tests** — `tests/test_venue_config.py` iterates every YAML
   automatically, so schema coverage is free. Add a checklist case to
   `tests/test_paper_checklist.py` if you added a checklist.

Two rules that are not negotiable:

- **Never bundle a venue style file.** `venue_setup.py` downloads it from the
  official URL at run time. See `THIRD_PARTY_NOTICES.md` for why.
- **Never make a tool answer a checklist question.** `paper_checklist.py`
  emits detected signals as *hints*; `Answer:` and `Justification:` stay
  `[TODO]` for the author. A tool that fills them in is a tool that helps
  authors lie to reviewers.

## Adding a reference document

`references/*.md` files are loaded on demand by the model, so they are
context budget. Keep each one under ~300 lines, lead with the actionable
rule, and put the rationale after it. Link the new file from `SKILL.md` or
from another reference — an orphan reference is never read.

Do not put project-internal names, client names, or private URLs in a
reference file.

## Citation integrity

The one rule the whole project is built around: **BibTeX is never generated
from memory.** Entries come from `scripts/fetch_bibtex.py` (DBLP/CrossRef) or
`scripts/arxiv_registry.py` (arXiv), and unverified entries carry a
`PLACEHOLDER_` prefix. Any change that weakens this will be rejected.

## Commit conventions

Conventional Commits, imperative mood, present tense:

```
feat(venue): add ICML 2026 configuration and checklist
fix(arxiv-package): embed .bbl when bibliography is in a subdirectory
docs(readme): sync zh-TW translation with English
test(anonymity): cover \thanks detection
```

Scopes in use: `venue`, `style`, `discipline`, `guideline`, `checklist`,
`format-gate`, `anonymity`, `arxiv-package`, `autopilot`, `export`, `slides`,
`poster`, `video`, `citation`, `portability`, `docs`, `ci`.

## Issue triage

Labels are defined in [`.github/labels.yml`](.github/labels.yml) and applied on
triage. Two of them tell you where to start:

- **`good first issue`** — self-contained, with the acceptance condition written
  into the issue. Adding a venue, a style or a discipline profile usually lands
  here: the schema is documented and the tests tell you when you are done.
- **`help wanted`** — we want this and are not working on it. Say so in a
  comment before you start, so two people do not build it twice.

A type label (`bug`, `enhancement`, `documentation`, `venue-request`) and an
area label (`area:citations`, `area:gates`, `area:autopilot`, `area:output`,
`area:portability`, `area:skill-spec`) go on every issue. `needs-repro` means we
could not reproduce it from what was written; a command and its full output
usually clears it in one round.

## Your first contribution

1. Run the suite and both lint gates. They should be green before you change
   anything, so you know what your change caused.
2. Pick a `good first issue`, or add the profile for a field or style you
   actually work in — that is the contribution nobody else can make as well as
   you can.
3. Read [docs/GUARANTEES.md](docs/GUARANTEES.md) before touching a gate. The
   split between what is machine-verified, what is merely detected, and what is
   the author's alone is the project's central commitment, and a change that
   blurs it is a change we will decline however useful it looks.

## Pull requests

Fill in `.github/PULL_REQUEST_TEMPLATE.md`. In short: tests pass, `--help`
smoke test passes, all three READMEs stay in sync if you touched one, and a
new venue ships with its checklist.
