# Quality & Readiness Checklist

Purpose: single-panel readiness gate for all paper variants. Run each section at the indicated phase; record PASS/FAIL and evidence. A paper is **ready for delivery** only when all applicable sections show PASS.

---

## How to Use

1. Copy this checklist into `notes/quality-checklist-run.md` at project start.
2. After each gate, fill in the result column with PASS / FAIL / SKIP (+ reason).
3. At final delivery, all non-SKIP rows must be PASS.

---

## A. Format & Compilation

| # | Check | Command / Method | Pass Criteria | Phase |
|---|-------|-----------------|---------------|-------|
| A1 | LaTeX compiles without error | `python scripts/compile_paper.py --project-dir <paper_dir>` | Exit 0 | Gate 0, Phase 2+, Phase 3 |
| A2 | No "Citation undefined" warnings | Check compilation log | 0 occurrences | Phase 2+, Phase 3 |
| A3 | No `Overfull \hbox` > 1pt | Check compilation log | 0 critical overflows | Phase 2+, Phase 3 |
| A4 | Page count within target | `python scripts/compile_paper.py --project-dir <paper_dir> --report-page-counts` | Main text 6-10 pages (or venue limit) | Phase 3 |
| A5 | Figures/tables referenced in text | Manual or grep `\ref{fig:` / `\ref{tab:` | All floats referenced | Phase 3 |
| A6 | Two-column sizing respected | Visual check of PDF | No overflow, no orphan captions | Phase 3 |

## B. Plan & Issues Contract

| # | Check | Command / Method | Pass Criteria | Phase |
|---|-------|-----------------|---------------|-------|
| B1 | Plan file exists and approved | Check `plan/` directory | Kickoff gate box checked | Gate 0 |
| B2 | Issues CSV exists and valid | `python scripts/validate_paper_issues.py <issues.csv>` | Exit 0 | Gate 1 |
| B3 | All issues DONE or SKIP (with reason) | Check `Status` column in issues CSV | 0 open issues | Phase 3 |
| B4 | Outline exists for every writing issue | Check Notes field or `notes/outlines/` | Each Wx has Stage 1 outline | Phase 2.35 |

## C. Citation & BibTeX Integrity

| # | Check | Command / Method | Pass Criteria | Phase |
|---|-------|-----------------|---------------|-------|
| C1 | No PLACEHOLDER_ citations remain | `grep -c 'PLACEHOLDER_' ref.bib` | 0 matches | Phase 2, Phase 3 |
| C2 | BibTeX audit: structure | `python scripts/bibtex_audit.py --project-dir <paper_dir> --fail-on-duplicate-keys` | 0 duplicates, 0 missing years | Phase 2.4, Phase 3 |
| C3 | BibTeX audit: recency | `python scripts/bibtex_audit.py --project-dir <paper_dir> --window-years 3 --min-recent-ratio 0.70` | >=70% from last 3 years | Phase 2.4, Phase 3 |
| C4 | Citation density | Manual check per section | 8+ citations/section (review); adequate (conference) | Phase 3 |
| C5 | 4-layer citation verification | `python scripts/verify_citations.py --bib-file <paper_dir>/ref.bib` | 100% verified | Phase 3 |
| C6 | No 3+ consecutive sentences without citation | Manual check (abstracts exempted) | 0 violations | Phase 3 |

## D. Claim & Evidence Integrity

| # | Check | Command / Method | Pass Criteria | Phase |
|---|-------|-----------------|---------------|-------|
| D1 | Claim registry generated | `python scripts/claim_registry.py --project-dir <paper_dir> --mode broad --write-csv` | Registry file exists | Phase 2.4 |
| D2 | Pre-review claim verification (sample) | Verify 30% random sample, min 10 claims | 0 MAJOR_DISTORTION, 0 UNVERIFIABLE | Phase 2.4 |
| D3 | Final claim verification (100%) | Verify all claims in registry | 0 MAJOR_DISTORTION, 0 UNVERIFIABLE | Phase 3 |
| D4 | Pre-review integrity gate | `python scripts/integrity_gate.py --project-dir <paper_dir> --stage pre-review` | PASS | Phase 2.4 |
| D5 | Final integrity gate | `python scripts/integrity_gate.py --project-dir <paper_dir> --stage final` | PASS | Phase 3 |

## E. Writing Quality

| # | Check | Command / Method | Pass Criteria | Phase |
|---|-------|-----------------|---------------|-------|
| E1 | Anti-AI scan | `python scripts/anti_ai_scan.py --project-dir <paper_dir>` | LOW severity (<=5 patterns) | Phase 2.3 |
| E2 | Anti-AI strict mode (conference) | `python scripts/anti_ai_scan.py --project-dir <paper_dir> --strict` | Passes quantitative thresholds | Phase 2.3 |
| E3 | Logic selfloop | `python scripts/logic_selfloop.py --project-dir <paper_dir>` | No blocking findings | Phase 2.53 |
| E4 | Argument selfloop | `python scripts/argument_selfloop.py --project-dir <paper_dir>` | No blocking findings | Phase 2.53 |
| E5 | Voice selfloop | `python scripts/voice_selfloop.py --project-dir <paper_dir>` | No blocking findings | Phase 2.53 |
| E6 | Paper self-review | `python scripts/paper_self_review.py --project-dir <paper_dir>` | 6-dimension pass | Phase 2.55 |
| E7 | Terminology consistent | Manual check across sections | No contradictions | Phase 3 |
| E8 | Acronyms defined on first use | Manual check | All acronyms expanded once | Phase 3 |

## F. Privacy & Safety

| # | Check | Command / Method | Pass Criteria | Phase |
|---|-------|-----------------|---------------|-------|
| F1 | Privacy scan | `python scripts/paper_privacy_scan.py --project-dir <paper_dir>` | Exit 0 | Phase 2.4, Phase 3 |
| F2 | No fabricated results | Manual verification of all tables/figures | All data traceable to source | Phase 3 |
| F3 | No new claims in conclusion | Manual check | Conclusion only restates prior claims | Phase 3 |

## G. Reviewer Loop

| # | Check | Command / Method | Pass Criteria | Phase |
|---|-------|-----------------|---------------|-------|
| G1 | Context pack generated | `python scripts/paper_context_pack.py --project-dir <paper_dir>` | File exists | Phase 2.5 |
| G2 | Reviewer Round 1 + Round 2 complete | Check reviewer issue rows | All review issues DONE/SKIP | Phase 2.5 |
| G3 | Cross-model review (optional) | `python scripts/cross_model_review.py --project-dir <paper_dir> init` | Score >=6/10 positive verdict | Phase 2.5 |
| G4 | PROCEED/REFINE/PIVOT decision recorded | `python scripts/research_decision.py --project-dir <paper_dir> evaluate` | Decision recorded | Phase 2.5 |

## H. Conference-Specific (when applicable)

| # | Check | Command / Method | Pass Criteria | Phase |
|---|-------|-----------------|---------------|-------|
| H1 | Venue page limit met | Compile + page count | Within venue limit | Phase 3 |
| H2 | Venue-specific checklist | `references/conference-guides.md` | All venue requirements met | Phase 3 |
| H3 | Systems hardening (CVPR/ICCV/ICML) | `references/systems-paper-hardening.md` | Page limit as compile gate; anonymity as release gate | Phase 2.6 |

## I. Post-Acceptance Materials (when applicable)

| # | Check | Command / Method | Pass Criteria | Phase |
|---|-------|-----------------|---------------|-------|
| I1 | Beamer slides compile | `python scripts/compile_slides.py --project-dir <paper_dir>/slides/` | Exit 0 | Phase 4a |
| I2 | Slides validated | `python scripts/validate_slides.py --project-dir <paper_dir>/slides/ --duration <min>` | Score >= 90 | Phase 4a |
| I3 | Poster validated | `python scripts/poster_validate.py --project-dir <paper_dir>` | Score >= 85, Exit 0 | Phase 4c |
| I4 | PowerPoint overlap check | `python scripts/pptx_check_overlaps.py <pptx_file>` | Exit 0, 0 CRITICAL/MAJOR | Phase 4e |
| I5 | Video validated | `python scripts/validate_video.py --project-dir <paper_dir>` | Exit 0 | Phase 4b |

---

## Final Verdict

| Verdict | Condition |
|---------|-----------|
| **PASS** | All applicable rows are PASS. |
| **PASS_WITH_NOTES** | All rows PASS except items marked SKIP with documented justification. |
| **FAIL** | Any applicable row is FAIL. |

**Rule**: Do not declare delivery until this checklist shows PASS or PASS_WITH_NOTES.
