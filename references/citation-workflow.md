# Citation Workflow (Concise)

Purpose: ensure every claim is supported and every BibTeX entry is real, accurate, and verified.

## During writing (iterative)
Trigger additional citations when:
- Starting a new section
- Introducing or comparing concepts
- Making quantitative or factual claims
- Noticing a paragraph with no citations
- Adding/adapting a figure/table/plot that includes externally sourced content (nodes/labels/data/results)

Visual citation rule of thumb:
- Prefer citing sources in the figure/table caption (keeps diagrams readable) or in the immediately surrounding text.
- Put `\cite{}` inside TikZ/node labels only when necessary (e.g., many distinct sourced items and caption would be ambiguous).

Protocol:
1. Identify the exact claim needing support
2. Search by title/author/year
3. Open the source page (venue/arXiv/DOI) and confirm metadata
4. Add to `ref.bib` only after verification
5. Cite immediately in text
   - For arXiv entries, use `arxiv_registry.py export-bibtex` to populate `ref.bib` (stable keys, dedup)

Citation density:
- Never 3 consecutive sentences without citations
- Meet per-section targets in the issues CSV

## Claim-level integrity (recommended)
Citation existence is necessary but not sufficient. For quantitative / factual / causal claims:
- Generate a claim registry: `python scripts/claim_registry.py --project-dir <paper_dir> --mode broad --write-csv`
- Record a verdict per claim (VERIFIED / MINOR_DISTORTION / MAJOR_DISTORTION / UNVERIFIABLE / UNVERIFIABLE_ACCESS)
- Run the integrity gate before review/final delivery: `python scripts/integrity_gate.py --project-dir <paper_dir> --stage pre-review|final`

## Standalone validation (existing project)
1. Extract all `\cite{}` keys from the LaTeX source
2. Compare against `ref.bib` to find missing/orphaned entries
3. Verify every BibTeX entry online and correct metadata
4. Fix or remove invalid entries; summarize changes in chat if requested

## BibTeX hygiene
- Required fields present for entry type
- Special characters escaped; accented names use LaTeX commands
- No duplicates; consistent key format

## Anti-Hallucination Citation Rules (mandatory)

### Rule 1: NEVER generate BibTeX entries from memory
LLM-generated BibTeX has ~40% error rate on metadata (wrong venue, wrong year, fabricated co-authors).
Always obtain BibTeX from an authoritative source:
1. DBLP (`dblp.org/rec/{key}.bib`) — best quality
2. CrossRef via DOI (`doi.org/{doi}` with Accept: application/x-bibtex) — good fallback
3. arXiv API + `arxiv_registry.py export-bibtex` — for preprints
4. Google Scholar BibTeX export — acceptable but verify venue name

### Rule 2: Placeholder syntax for unverified citations
When you need to cite a paper but cannot verify it immediately, use:
```latex
\cite{PLACEHOLDER_authorYYYY_verify_this}
```
This creates a compile warning that is impossible to miss during QA.
Do NOT use a plausible-looking key like `\cite{smith2024attention}` for unverified entries —
this masks hallucinated citations as real ones.

### Rule 3: Pre-submission verification checklist
Before any delivery (draft, review round, or final):
- [ ] Zero `PLACEHOLDER_` keys remaining in main.tex
- [ ] Every `ref.bib` entry has been verified via web search (DBLP/CrossRef/arXiv)
- [ ] `verify_citations.py` run with no HALLUCINATED entries
- [ ] No BibTeX entry was typed from memory (all sourced from APIs or copy-pasted from publisher pages)

### Action table

| Situation | Action |
|-----------|--------|
| Found paper, got DOI, fetched BibTeX | Use the citation |
| Found paper, no DOI | Use arXiv BibTeX or manual entry from paper page |
| Paper exists but can't fetch BibTeX | Mark `PLACEHOLDER_`, inform user |
| Uncertain if paper exists | Mark `[CITATION NEEDED]`, inform user |
| "I think there's a paper about X" | **NEVER cite** — search first or mark placeholder |
