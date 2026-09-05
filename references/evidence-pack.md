# Evidence Packs

## Purpose
Evidence packs are per-section JSON bundles generated before the writing phase. They provide structured context so that each section is written with a clear brief, citation budget, and anchor points — enforcing the "evidence-first, prose-last" principle.

## Generation
```bash
python scripts/evidence_pack.py --project-dir <paper_dir> [--issues-csv <path>] [--default-budget 8]
```

## Output
One JSON file per section under `notes/evidence-packs/<section_id>.json`:
```json
{
  "section_id": "3",
  "section_title": "Architecture and Components",
  "subsections": ["3.1 Backend Services", "3.2 Frontend Layer"],
  "citation_budget": 8,
  "available_citations": ["smith2024", "jones2023"],
  "claims": [],
  "anchors": [],
  "gaps": [],
  "created_at": "2026-03-13T10:00:00+08:00"
}
```

## Fields
| Field | Description |
|-------|-------------|
| `section_id` | Numeric section index (from `\section{}` order) |
| `section_title` | Section title from `main.tex` |
| `subsections` | List of "N.M Title" subsection labels |
| `citation_budget` | Target citation count (from issues CSV `Target_Citations` or `--default-budget`) |
| `available_citations` | BibTeX keys already cited in this section that exist in `ref.bib` |
| `claims` | Empty list — to be filled during writing with key claims |
| `anchors` | Empty list — key evidence anchors for the section |
| `gaps` | Empty list — identified gaps needing additional evidence |

## Workflow Integration
1. Run after Gate 1 (issues CSV exists) and before writing issues.
2. Each writing issue should consult its section's evidence pack.
3. After writing, the pack's `claims` and `anchors` fields can be updated for claim registry cross-reference.
4. Packs respect refinement markers (`.refined`); use `--force` to overwrite refined packs.

## Skipped Sections
The following sections are automatically excluded: Abstract, Acknowledgment, References, Bibliography.
