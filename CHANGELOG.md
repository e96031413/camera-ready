# Changelog

All notable changes to CameraReady are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Development history from before the first public release is preserved in
[`docs/history-zh.md`](docs/history-zh.md) (Chinese, unedited).

## [Unreleased]

### Added

**Beyond computer science**

- `assets/disciplines/*.yaml` — eight discipline profiles (computer science,
  psychology, medicine, education, business, social science, humanities, law).
  Each names the citation style, output format, reporting guidelines, mandatory
  sections, mandatory statements and common rejection reasons for its field.
- `scripts/discipline_profile.py` — loads and validates them, and prints the
  actionable requirement list for a field.
- `assets/styles/*.yaml` — six citation style profiles: APA 7, MLA 9, Chicago
  (author-date and notes), Vancouver and IEEE. Each carries the LaTeX preamble
  that makes it compile, the pandoc CSL identifier, and the BibTeX fields it
  needs per entry type.
- `scripts/citation_style.py` — lists and shows styles, emits the LaTeX
  preamble, and fails a `.bib` whose entries would render as incomplete
  references. A requirement written `doi|url` is satisfied by either.
- `assets/checklists/` — nine reporting-guideline question sets: PRISMA 2020,
  CONSORT, STROBE, CARE, COREQ, SRQR, CHERRIES, JARS-Quant and JARS-Qual.
  Each paraphrases the guideline, cites its source, and records the date it was
  checked.
- `scripts/reporting_guideline.py` — generates a worksheet with every answer
  blank, scans the manuscript for hints, and validates that a person filled it
  in. It never answers a question.
- `scripts/export_document.py` — the non-LaTeX output path. Converts a LaTeX or
  Markdown manuscript to Word, ODT, Markdown, Typst or HTML through pandoc,
  resolving citations with the style's CSL file, which it fetches and caches on
  demand.

**Topic to camera-ready**

- `scripts/autopilot.py` — a ten-phase state machine from a research topic to a
  built submission package. Each phase's exit condition is checked against
  files that exist. The plan phase needs an approving name; the camera-ready
  phase never closes, because submission is manual. Overrides need a reason and
  are written into the run journal.
- `scripts/quick_start.py` — creates a buildable project in one command:
  manuscript skeleton in the field's format, empty bibliography, plan, issues
  CSV and a started run. It writes no prose and invents no citation.

**Cross-platform and specification conformance**

- `scripts/portability_check.py` — fails the build on text I/O without an
  explicit encoding, subprocess output decoded with the locale encoding,
  POSIX-only path literals, `shell=True`, and a `python3` command in the
  documentation. Suppress a deliberate case with `# portability: ignore`.
- `scripts/skill_spec_check.py` — validates `SKILL.md` against the Agent Skills
  specification: the six allowed frontmatter fields, the name and length
  limits, and that every file linked from the body exists.
- `conftest.py` — falls back to a repository-local temporary root when the
  system temp directory cannot be enumerated, which is what made the suite
  error out on some managed Windows machines.
- `.gitattributes` — normalises line endings so the repository behaves the same
  on all three platforms.
- CI now runs on macOS as well as Windows and Linux, and runs both lint gates.

**Documentation**

- `docs/GUARANTEES.md` — the line between what is machine-verified, what is
  detected and reported, and what is the author's alone, plus what none of it
  can catch.
- `docs/EXTENDING.md` — the schema for a venue, style, discipline or reporting
  guideline, and the contract for a citation provider or an autopilot phase.
- `docs/TROUBLESHOOTING.md` — symptoms and fixes, including the Windows pytest
  permission error and the LaTeX package each style needs.
- `docs/DEMO.md` and `docs/demo-script.sh` — an annotated transcript that a
  script reproduces.
- `.github/labels.yml` — the triage labels, and what each one means.

### Changed

- `SKILL.md` frontmatter now uses only the six fields the Agent Skills
  specification allows, so the same directory loads in Claude Code, uploads to
  claude.ai and packages unchanged. `disable-model-invocation` was removed for
  that reason, and `compatibility` was trimmed under the 500-character limit.
- `SKILL.md` gains Gate -2, which resolves discipline, citation style and
  output format before anything is scaffolded, and an autopilot section.
- The QA gate now includes the reporting-guideline worksheet and the
  citation-style field check.
- The YAML subset parser in `venue_config.py` accepts folded (`>`) and literal
  (`|`) block scalars, so a profile can carry a paragraph of notes.
- Documentation writes `python`, not `python3`, throughout: Windows ships no
  `python3`, and the lint gate now enforces it.
- `README.md` leads with a five-minute path and states the scope, including
  what is deliberately not covered.

### Fixed

- Thirteen file reads and writes across the PowerPoint scripts used the
  platform's default text encoding, which corrupts non-ASCII content on
  Windows. All now specify UTF-8.
- Forty-one subprocess calls decoded captured output with the locale encoding,
  with the same effect. All now specify UTF-8 with replacement.
- CLI output is now UTF-8 on Windows consoles, so a report containing a dash or
  an accented name prints rather than raising `UnicodeEncodeError`.


## [0.1.0] - 2026-09-05

First public release. The gated paper workflow, the citation-verification
rules, and the post-acceptance tooling all predate this tag; what `0.1.0`
adds is everything needed to install it, submit with it, and contribute to it.

### Added

**Submission tooling**

- `scripts/venue_setup.py` — writes `notes/venue.md` for a target venue and
  downloads the official style file. Style files are never bundled; when the
  download does not yield a usable file, the script prints the official URL
  and the manual step.
- `scripts/format_gate.py` — checks main-text page count against the venue
  limit, the presence of every venue-mandated section, and that the venue
  style file is both present and loaded. Reuses the page parsing in
  `compile_paper.py`, so the compiled `main.log`/`main.aux` is the source of
  truth rather than a guess from the LaTeX source.
- `scripts/anonymity_check.py` — reports double-blind violations at three
  severities: author macros, `\thanks`, acknowledgements, emails, named
  repository URLs, and PDF author metadata as BLOCKER; ORCID iDs, institutional
  domains, and first-person self-citation phrasing as WARN.
- `scripts/arxiv_package.py` — builds an arXiv submission tarball. Flattens the
  directory and rewrites `\input`/`\includegraphics` paths, inlines the
  compiled `.bbl` (arXiv does not run BibTeX), strips comments and `\todo`
  macros, and reports missing figures, unsupported graphics formats, absolute
  paths, and oversized files. Writes `notes/arxiv-submission-report.md`. It
  builds a file and stops; uploading remains a manual user action.
- `scripts/venue_config.py` — loads and validates `assets/venues/*.yaml`.
  Includes a strict YAML-subset parser so the core workflow keeps its
  zero-dependency guarantee.

**Venue support: NeurIPS only → six venues**

- `assets/venues/{neurips,icml,iclr,acl,aaai,cvpr}.yaml` — page limits, column
  layout, font size, required sections, review model, checklist status, and
  official URLs. Every value is sourced from the official author guide and
  dated to a specific edition via `reference_year`.
- `assets/checklists/{icml,iclr,acl,aaai,cvpr}.md` — checklist question sets,
  paraphrased from the official guides. `cvpr.md` is a self-review worksheet,
  since CVPR requires no checklist.

**Release and contribution infrastructure**

- `README.md`, `README.zh-CN.md`, `README.zh-TW.md` — full translations, not
  summaries.
- `LICENSE` (MIT), `THIRD_PARTY_NOTICES.md`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`.
- `docs/QUICKSTART.md` — install to first PDF, with the expected output at each
  step.
- `examples/minimal-review-paper/` — a complete, compiled paper committed to
  the repository: plan, issues CSV, `ref.bib` (eight entries, all fetched from
  the arXiv API by ID), `main.tex`, `main.pdf`, and gate reports.
- GitHub Actions CI — Ubuntu and Windows × Python 3.10 and 3.12, running the
  test suite plus a `--help` smoke test on every script.
- Issue templates for bugs, features, and venue requests; a pull request
  template.
- `requirements.txt` / `requirements-dev.txt`, documenting which dependencies
  are optional and which feature needs each.

**Tests**

- `tests/test_venue_config.py`, `tests/test_format_gate.py`,
  `tests/test_anonymity_check.py`, `tests/test_arxiv_package.py`.
- `tests/test_paper_checklist.py` extended to cover all six venues, including
  a check that checklist assets stay paraphrases rather than verbatim venue
  LaTeX.

### Changed

- `scripts/paper_checklist.py` is venue-driven. Display names come from
  `assets/venues/*.yaml`, and `--list-venues` reports what is available.
  `--project-dir` is no longer required when only listing venues.
- Checklist signal detection now matches on the item's **topic** rather than
  its number. Item 2 is "Limitations" at NeurIPS and "Risks" at ACL, so
  number-keyed detectors attached hints to the wrong questions at every venue
  but NeurIPS.
- `SKILL.md`: `venue_setup.py` added to Gate 0; `format_gate.py` and
  `anonymity_check.py` added to the Phase 3 QA Gate; new Phase 3.8 for arXiv
  packaging. Success Criteria updated from "currently NeurIPS only" to the six
  configured venues. The Follow-Through Policy places the new validators and
  `arxiv_package.py` in "Do directly", and keeps submission in "Ask first".
- `references/conference-guides.md`: venue tooling section, per-venue checklist
  commands, and the removal of the ICML "not yet templated" note. CVPR's
  checklist column corrected from "Required" to "Not required".
- `references/quality-phases.md` and `references/standalone-workflows.md`
  updated for the new gates, plus new arXiv-packaging and venue-retargeting
  variant workflows.
- `CHANGELOG.md` rewritten in Keep a Changelog format. The previous Chinese
  development log moved to `docs/history-zh.md`, unedited.

### Fixed

- `scripts/pptx_soffice.py --help` crashed with exit 1 when LibreOffice was not
  installed. It now documents the wrapper without requiring the binary, which
  is what the CI smoke test checks.
- `scripts/anonymity_check.py` does not scan `.cls`/`.sty`/`.bst` files. They
  *define* `\author` and `\thanks`, so scanning them reported the venue
  template's own macro definitions as author identity.

### Renamed

- `references/magic_studio_cvpr_systems_hardening.md` →
  `references/systems-paper-hardening.md`. The old filename carried an internal
  project codename.

### Removed

- The empty `tasks/` directory.

[Unreleased]: https://github.com/e96031413/SKILLS/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/e96031413/SKILLS/releases/tag/v0.1.0
