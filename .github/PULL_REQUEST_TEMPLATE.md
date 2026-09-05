# Pull Request

## What does this change?

<!-- One paragraph. What behaviour is different after this PR? -->

## Why?

<!-- Link the issue, or describe the failure this fixes. -->

Closes #

## How was it verified?

<!-- Paste the commands you ran and the relevant output. -->

```
```

---

## Checklist

### Always

- [ ] `python -m pytest -q` passes locally.
- [ ] `--help` smoke test passes for every script:
      `for f in scripts/*.py; do python "$f" --help >/dev/null || echo "FAIL $f"; done`
- [ ] New or changed behaviour is covered by a test.
- [ ] Core code paths add no new required third-party dependency. Optional
      dependencies are imported lazily and fail with an actionable message.

### If you touched documentation

- [ ] All three READMEs are in sync: `README.md`, `README.zh-CN.md`,
      `README.zh-TW.md`. Section structure must match; translations are full,
      not summaries.
- [ ] Internal links resolve.
- [ ] `CHANGELOG.md` has an entry under `## [Unreleased]`.

### If you added or changed a venue

- [ ] `assets/venues/<venue>.yaml` is complete and every value is sourced from
      the official author guide (link it in the PR description).
- [ ] `assets/checklists/<venue>.md` exists, or the YAML sets
      `checklist.required: false`.
- [ ] No venue style file (`.sty`, `.cls`, `.bst`) is committed — the URL goes
      in the YAML and `venue_setup.py` downloads it at run time.
- [ ] No verbatim checklist LaTeX block from a venue template is committed.
- [ ] `references/conference-guides.md` is updated.
- [ ] `tests/test_venue_config.py` passes; `tests/test_paper_checklist.py`
      covers the new checklist.

### If you touched a gate or a validator

- [ ] The tool reports signals; it does not fabricate an answer, a citation,
      or a checklist justification.
- [ ] Failure output names the file and the line, so the author can act on it.
- [ ] `SKILL.md` is updated if the gate's position in the workflow changed.
