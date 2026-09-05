# Standalone Workflows (No Paper Required)

## Standalone Beamer Slide Workflow
When only slides are requested (no paper):
1. Create a project directory with `slides/` subfolder.
2. Copy template: `cp assets/template/beamer-preamble.tex <project_dir>/slides/slides.tex`
3. Follow the full Beamer workflow (Phase 0-5) from `references/beamer-workflow.md`.
4. Track progress using `SL1-SL5` issues from the issues CSV.
5. Compile: `python scripts/compile_slides.py --project-dir <project_dir>/slides/`
6. Validate: `python scripts/validate_slides.py --project-dir <project_dir>/slides/ --duration <minutes>`

## Standalone Poster Workflow
When only a poster is requested (no paper):
1. Create a project directory with `poster/` subfolder.
2. Generate from template: `python scripts/poster_generate.py --project-dir <project_dir> --standalone --dimensions A0 --orientation landscape`
3. Follow the full poster workflow (Phase PS0-PS5) from `references/poster-workflow.md`.
4. Track progress using `PS1-PS6` issues from the issues CSV.
5. Convert figures: `python scripts/poster_convert_figures.py --source-dir <figures_dir> --output-dir <project_dir>/poster`
6. Optimize: `python scripts/poster_optimize.py --project-dir <project_dir> --sweep --pdf`
7. Validate: `python scripts/poster_validate.py --project-dir <project_dir>`

## Standalone PowerPoint Workflow
When only PowerPoint slides are requested (no paper):
1. Create a project directory with `pptx/` subfolder and `pptx/images/formulas/`, `pptx/images/diagrams/`.
2. Follow the 5-Phase Pipeline from the Post-Acceptance materials (Phase 4e).
3. Track progress using `PX1-PX5` issues from the issues CSV.
4. Key scripts:
   - `python scripts/pptx_render_latex.py formulas.json pptx/images/formulas/ [--theme <name>]`
   - `python scripts/pptx_render_diagrams.py diagrams.json pptx/images/diagrams/ [--theme <name>]`
   - `cd pptx && node generate_slides.js`
   - `python scripts/pptx_inject_omml.py pptx/output.pptx formulas.json pptx/output_final.pptx`
   - `python scripts/pptx_check_overlaps.py pptx/output_final.pptx --json pptx/overlap_report.json`
   - `python scripts/pptx_thumbnail.py pptx/output_final.pptx pptx/thumbnails`
5. QA: review thumbnails, fix CRITICAL/MAJOR overlap issues, re-generate until `pptx_check_overlaps.py` exits 0.

## Existing Paper Workflow (No Re-Scaffold)
If a paper folder already exists, do NOT rerun scaffold:
```bash
# Create plan (review paper)
python scripts/create_paper_plan.py --topic "<topic>" --paper-type review --stage plan --output-dir <paper_dir>
# STOP for approval, then check kickoff gate box
# Create issues (use timestamp/slug from plan filename/frontmatter)
python scripts/create_paper_plan.py --topic "<topic>" --paper-type review --stage issues --timestamp "<TS>" --slug "<slug>" --output-dir <paper_dir> --with-literature-notes

# Create plan (codebase-grounded paper)
python scripts/create_paper_plan.py --topic "<topic>" --paper-type codebase --codebase-dir <codebase_dir> --stage plan --output-dir <paper_dir>
# STOP for approval, then check kickoff gate box
# Create issues (use timestamp/slug from plan filename/frontmatter)
python scripts/create_paper_plan.py --topic "<topic>" --paper-type codebase --codebase-dir <codebase_dir> --stage issues --timestamp "<TS>" --slug "<slug>" --output-dir <paper_dir>
```

## arXiv Submission Packaging Variant
When a paper is finished and only needs packaging (no re-scaffold, no re-review):
```bash
python scripts/arxiv_package.py --project-dir <paper_dir> --dry-run   # inspect first
python scripts/arxiv_package.py --project-dir <paper_dir>             # build the tarball
```
The script flattens the directory, inlines the compiled `.bbl` (arXiv does not run BibTeX), strips comments
and `\todo` macros, and reports missing figures, unsupported graphics formats, absolute paths, and oversized
files. Outputs `submission.tar.gz` and `notes/arxiv-submission-report.md`.

**Verify before handing it over**: unpack the tarball into an empty directory and compile it there with two
`pdflatex` passes and no `bibtex`. A build that succeeds in the project directory can still fail on arXiv,
because the project directory contains files the tarball does not.

**The script never uploads.** Submission is the user's action; see the Follow-Through Policy in `SKILL.md`.

## Venue Retargeting Variant
Moving a finished paper to a different venue:
```bash
python scripts/venue_setup.py --venue <target> --project-dir <paper_dir>   # notes/venue.md + style file
python scripts/format_gate.py --project-dir <paper_dir> --venue <target> --strict
python scripts/paper_checklist.py --project-dir <paper_dir> --venue <target> --emit-tex
python scripts/anonymity_check.py --project-dir <paper_dir>
```
Read `notes/venue.md` before editing anything: the page limit, the mandatory sections, and the review model
usually all differ. Migrate section by section and never copy the preamble
(`references/conference-guides.md` § Format Conversion Workflow).

## Citation-Validation Variant
1. Treat provided path as LaTeX project root.
2. Follow `references/citation-workflow.md`.
3. Use `references/bibtex-guide.md` for BibTeX rules if entries need repair.
4. Deliver validation report and corrected `ref.bib` if requested.

## Rebuttal Workflow
When responding to peer review comments:
1. Classify each comment: Major / Minor / Typo / Misunderstanding.
2. Apply response strategy per comment (see `references/rebuttal-strategy.md`):
   Accept / Defend / Clarify / Experiment.
3. Draft rebuttal using `assets/response-to-reviewers-template.md` (R->A->C format).
4. Convert required changes into issues CSV rows and execute.
5. Run integrity gate after all changes: `python scripts/integrity_gate.py --project-dir <paper_dir> --stage pre-review`

## Daily Paper Discovery
For ongoing literature monitoring (see `references/daily-paper-discovery.md`):
1. Define 3-5 keyword groups for your research topic.
2. Search arXiv with date sorting (last 3 months).
   **alphaxiv-powered monitoring**: For each keyword group, call in parallel:
   - `mcp__alphaxiv__full_text_papers_search` -- keyword search
   - `mcp__alphaxiv__embedding_similarity_search` -- semantic search with research context
   - `mcp__alphaxiv__agentic_paper_retrieval` -- broad coverage search
   Use `mcp__alphaxiv__get_paper_content` to quickly read promising papers' AI-generated reports.
3. Evaluate papers using 5-dimension scoring (Innovation 30%, Method 25%, Experiments 25%, Writing 10%, Relevance 10%).
4. Save summaries to `notes/daily-paper/YYYY-MM-DD-HHMM-paper-N.md`.
5. Papers scoring >=3.5 feed into the paper's research and citation pool.
