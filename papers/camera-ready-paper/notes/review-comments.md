# Review Comments (adversarial self-review, round 1)

Reviewer stance: a program-committee member who dislikes tool papers and
distrusts self-evaluation.

## 1. Abstract is over length

274 words against the 150--250 convention for IEEE. Cut the mechanism recital;
keep the result and the negative finding.
Resolution: rewritten; now ~251 words by `paper_self_review.py`.

## 2. The "57 of 62" figure is over-precise

The number comes from searching for non-zero exit paths, which also counts
argument-parsing failures. State how it was obtained, or a reviewer will assume
it was counted by hand and is wrong.
Resolution: the sentence in Section V now names the counting method.

## 3. The self-application claim omits an override

Section VIII-D said the run passed through every phase, but the draft phase was
forced past its exit condition because 16 SKIP rows count as open. A paper whose
thesis is that overrides are journaled rather than silent has to disclose its
own.
Resolution: disclosed in the self-application subsection.

## 4. No baseline

An ungated agent writing the same paper would make the comparison concrete.
Already stated as a limitation, and a reviewer will still want it.
Resolution: none. Fabricating a baseline would be worse than admitting its absence.

## 5. Related work does not close

Section II ends on reporting norms without saying where this system sits among
the systematic-review pipelines it cites.
Resolution: one positioning sentence added at the end of Section II-D.

## 6. Table IV mixes one pre-patch run with six post-patch runs

The asymmetry is honest but should be labelled, so nobody reads the table as a
controlled comparison.
Resolution: caption now says the pre-patch row is the run that exposed the defect,
not a control arm.

## 7. The abstract overstated what gates prevent

The model can pass `--force`. Section VI says so; the abstract did not.
Resolution: abstract now says most of the process can be enforced by tools, and that
an override is available and journaled.
