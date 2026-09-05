# Conference Submission Guides

Purpose: venue-specific requirements for top ML/AI conferences.

## Quick Reference

| Venue | Pages (main) | Pages (total) | Template | Checklist | Key Requirement |
|-------|-------------|---------------|----------|-----------|-----------------|
| NeurIPS | 9 | 9 + refs + appendix | `neurips_2025.sty` | Mandatory | Paper checklist, broader impact |
| ICML | 8 | 8 + refs + appendix | `icml2026.sty` | Mandatory | Broader Impact Statement |
| ICLR | 9 | 9 + refs + appendix | `iclr2026_conference.sty` | Required | LLM disclosure required |
| ACL | 8 | 8 + refs + appendix | `acl.sty` | Required | Limitations section mandatory |
| AAAI | 7 | 7 + 1 (refs) + 1 (ethics) | `aaai26.sty` | Required | Strict style adherence |
| CVPR | 8 | 8 + refs + appendix | `cvpr.sty` | Not required | Supplementary materials encouraged |

## Venue Tooling

Every venue in the table above has a machine-readable config in
`assets/venues/<venue>.yaml` and a checklist question set in
`assets/checklists/<venue>.md`. Four commands cover the venue-specific work:

```bash
# List what is configured
python scripts/venue_setup.py --list-venues

# Write notes/venue.md into a project and fetch the official style file
python scripts/venue_setup.py --venue <venue> --project-dir <paper_dir>

# Check page limit, required sections, and style file (needs a compiled paper)
python scripts/format_gate.py --project-dir <paper_dir> --venue <venue> --strict

# Generate and validate the checklist worksheet
python scripts/paper_checklist.py --project-dir <paper_dir> --venue <venue> --emit-tex
python scripts/paper_checklist.py --project-dir <paper_dir> --venue <venue> --validate
```

For every double-blind venue in the table — which is all of them — also run:

```bash
python scripts/anonymity_check.py --project-dir <paper_dir>
```

Three constraints these tools hold to, and will not be changed to violate:

- **Style files are never bundled.** `venue_setup.py` downloads from the
  official URL at run time. Several venues forbid redistribution, and a
  bundled copy silently goes stale between editions. When the download fails,
  the script prints the URL for manual download.
- **Checklist question sets are paraphrases.** `assets/checklists/*.md` is a
  worksheet aid, not the verbatim block from the venue style file. Before
  submitting, replace the generated `checklist.tex` scaffold with the verbatim
  block from the current template — most venues require the questions and
  guidelines to be unmodified.
- **No tool answers a checklist question.** Detected signals are printed as
  hints; `Answer:` and `Justification:` stay `[TODO]` for the author.

Every number in the config files is dated to a specific edition
(`reference_year` in the YAML) and sourced from the official author guide.
**Verify against the current year's guide before submitting.**

## Per-Venue Details

### NeurIPS
- **Page limit**: 9 pages main text; unlimited references and appendix
- **Required sections**: Paper checklist (appended), Broader Impact Statement
- **Anonymization**: Double-blind; no author names, no identifying URLs
- **Template**: https://neurips.cc/Conferences/2025/PaperInformation/StyleFiles
- **Formatting**: 10pt font, two-column not required (single-column), 5.5×9 in text area
- **Common rejections**: Missing checklist, insufficient novelty, weak baselines
- **Checklist tooling**: `python scripts/paper_checklist.py --project-dir <paper_dir> --emit-tex` generates a `notes/paper-checklist.md` worksheet (16 official questions, with detected signals like limitations/error-bars/compute as hints only — never auto-answered) plus a `checklist.tex` **pre-fill scaffold** (paraphrased text, not submission-ready). Validate the worksheet with `--validate` before the final QA gate, then **replace `checklist.tex` with the verbatim checklist block from the current venue `.sty`/template** (questions/guidelines must be unmodified) before `\input`-ing it into `main.tex`. Re-check question wording against the current year's official guide (https://neurips.cc/public/guides/PaperChecklist) since it can change.

### ICML
- **Page limit**: 8 pages main text; unlimited references and appendix
- **Required sections**: Broader Impact Statement
- **Anonymization**: Double-blind
- **Template**: https://icml.cc/Conferences/2026/StyleAuthorInstructions
- **Formatting**: 10pt font, two-column, 6.75×9.25 in text area
- **Common rejections**: Overclaiming, missing error bars, limited ablations
- **Checklist tooling**: `python scripts/paper_checklist.py --project-dir <paper_dir> --venue icml --emit-tex`. Question set: `assets/checklists/icml.md` (paraphrased from the official author instructions, 15 items). Re-check the wording against the current `icml20XX.sty` block before submitting.

### ICLR
- **Page limit**: 9 pages main text; unlimited references and appendix
- **Required sections**: LLM use disclosure
- **Anonymization**: Double-blind
- **Template**: https://iclr.cc/Conferences/2026/AuthorGuide
- **Formatting**: 10pt font, single-column, custom margins
- **Common rejections**: Incremental contribution, insufficient analysis, weak related work
- **Checklist tooling**: `python scripts/paper_checklist.py --project-dir <paper_dir> --venue iclr --emit-tex`. Question set: `assets/checklists/iclr.md` (15 items). ICLR expects the Reproducibility Statement, Ethics Statement, and LLM disclosure as sections in the paper; the worksheet does not replace them.

### ACL
- **Page limit**: 8 pages (long paper) / 4 pages (short paper); unlimited refs + appendix
- **Required sections**: Limitations (mandatory), Ethics Statement (encouraged)
- **Anonymization**: Double-blind
- **Template**: https://acl-org.github.io/ACLPUB/formatting.html
- **Formatting**: 11pt font, two-column, A4 paper
- **Common rejections**: Missing Limitations section, weak evaluation, narrow scope
- **Checklist tooling**: `python scripts/paper_checklist.py --project-dir <paper_dir> --venue acl --emit-tex`. Question set: `assets/checklists/acl.md`, paraphrasing the ARR Responsible NLP Research checklist (18 items across sections A-E). ARR collects it through the submission form, not through a LaTeX block.

### AAAI
- **Page limit**: 7 pages main text + 1 page references + 1 page ethics (if needed)
- **Required sections**: Ethics statement if applicable
- **Anonymization**: Double-blind
- **Template**: https://aaai.org/authorkit/
- **Formatting**: Two-column, strict adherence to template required
- **Common rejections**: Style violations, insufficient comparisons, lack of novelty
- **Checklist tooling**: `python scripts/paper_checklist.py --project-dir <paper_dir> --venue aaai --emit-tex`. Question set: `assets/checklists/aaai.md` (16 items). AAAI enforces formatting strictly, so run `format_gate.py --venue aaai --strict` as well and read the author kit's list of prohibited packages.

### CVPR
- **Page limit**: 8 pages main text; unlimited references; supplementary file separate
- **Required sections**: None mandatory beyond standard, but supplementary encouraged
- **Anonymization**: Double-blind
- **Template**: https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines
- **Formatting**: 10pt font, two-column, letter paper
- **Common rejections**: Missing visual comparisons, weak ablations, poor figure quality
- **Checklist tooling**: CVPR requires no paper checklist, so `assets/venues/cvpr.yaml` sets `checklist_required: false`. `assets/checklists/cvpr.md` is a self-review worksheet built from the author guidelines and the usual causes of a weak-reject; nothing from it is submitted.

## Format Conversion Workflow

1. Identify source/target format differences (page limit, required sections, column layout)
2. Copy target venue template directory
3. Migrate content **section by section** — never copy preamble
4. Adjust content for page limit differences
5. Add/remove conference-specific sections (checklist, broader impact, limitations)
6. Verify formatting with target template compilation
7. Run the format gate against the new target: `python scripts/format_gate.py --project-dir <paper_dir> --venue <target> --strict`. It reports the page overrun and any newly-mandatory section before you discover them at the submission deadline.

## Universal Rules

- **Anonymization**: All listed venues are double-blind; remove all identifying information
- **References**: Do not count toward page limit (all venues)
- **Format**: LaTeX required for all venues; Word templates exist but are discouraged
- **Figures**: Vector format (PDF/EPS) preferred; raster at ≥300 DPI minimum
- **Supplementary**: Never include content essential for review in supplementary only
- **Anonymity checking**: run `python scripts/anonymity_check.py --project-dir <paper_dir>` before every submission to any venue in this table. It reports; you decide.
- **Page limits**: never meet one by shrinking margins, font size, or line spacing. Venues check, and it is a desk reject.
