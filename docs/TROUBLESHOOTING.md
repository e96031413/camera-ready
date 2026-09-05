# Troubleshooting

Problems people actually hit, with the fix. Each entry names the symptom you
would search for.

---

## Install and environment

### `python: command not found` (macOS, Linux)

Some systems install Python 3 under the name `python3` and leave `python`
unset. Every command in these docs is written `python`, because Windows ships
no `python3`.

```bash
alias python=python3   # portability: ignore -- this line is the fix itself
```

Or run the commands with `python3` instead. The scripts do not care.

### `ModuleNotFoundError: No module named 'paper_utils'`

The scripts import each other by module name, so `scripts/` must be on the
path. Run them from the repository root, as the docs show:

```bash
python scripts/citation_style.py list       # right
cd scripts && python citation_style.py list # also right
python /elsewhere/scripts/citation_style.py list   # wrong
```

### Which Python version do I need?

3.10 or newer. The core workflow imports nothing outside the standard library.
CI runs 3.10 and 3.12 on Windows, Linux and macOS.

---

## Tests

### `PermissionError: [WinError 5]` on every `tmp_path` test

```
ERROR tests/test_beamer_slides.py - PermissionError: [WinError 5]:
'C:\\Users\\You\\AppData\\Local\\Temp\\pytest-of-You'
```

pytest calls `os.scandir` on `pytest-of-<user>` to garbage-collect old runs.
On a locked-down or corporate-managed Windows machine that directory can exist
while refusing to be enumerated, and every test that needs a temporary
directory errors before its body runs.

`conftest.py` detects this and falls back to a repository-local
`.pytest-tmp/`. You will see one line on stderr saying so. If you are running
pytest from somewhere that does not pick up `conftest.py`, pass the path
yourself:

```bash
python -m pytest -q --basetemp=.pytest-tmp
```

This is an environment problem, not a code problem. The tests pass either way.

### `UnicodeEncodeError` when a test prints

Windows consoles default to a legacy code page. `conftest.py` reconfigures
stdout and stderr to UTF-8 for the test session, and `paper_utils.enable_utf8_stdout()`
does the same for the CLIs. If you see this in your own script, call it first.

---

## Encoding and platform

### Report text prints as `â€"` or `?`

The file is fine; the console is not. On Windows:

```powershell
chcp 65001                    # switch the console to UTF-8
$env:PYTHONUTF8 = "1"         # or make Python force it
```

The scripts already reconfigure their own output; this affects piping through
other tools.

### A file I edited now has mixed line endings

`.gitattributes` normalises text files to LF in the repository and lets git
check them out natively. If you edited a file before that existed, re-normalise:

```bash
git add --renormalize .
```

### My contribution fails CI on Windows but passes locally on Linux

Run the lint that CI runs:

```bash
python scripts/portability_check.py --docs
```

It catches the four things that differ between platforms: text I/O without an
explicit encoding, subprocess output decoded with the locale encoding,
POSIX-only path literals, and a `python3` command in the documentation. Each finding
names the file, the line and the rule.

For a deliberate platform-specific line, mark it:

```python
CANDIDATES = ["/usr/bin/soffice"]  # portability: ignore -- Linux install location
```

---

## LaTeX

### `LaTeX Error: File 'biblatex-apa.sty' not found`

APA, MLA, Chicago and Vancouver each need a package beyond base LaTeX. Ask the
style profile what it needs:

```bash
python scripts/citation_style.py show apa7 | grep -A5 latex_required_packages
```

Then install it. TeX Live: `tlmgr install biblatex-apa`. MiKTeX installs
missing packages on demand if you let it. The safest route is a full TeX Live
or MiKTeX installation.

### The bibliography is empty, but the document compiles

Two causes, and the profile tells you which applies:

- **biblatex styles** need `biber`, not `bibtex`. Run
  `pdflatex → biber → pdflatex → pdflatex`.
- **`.bst` styles (IEEE)** need `\bibliography{ref}` in the document body and
  `\bibliographystyle{IEEEtran}` in the preamble. Having only one of them
  produces exactly this symptom.

`python scripts/citation_style.py preamble <style>` emits the correct pair.

### `Package biblatex Error: Incompatible package 'biblatex-chicago'`

Chicago is loaded through `biblatex-chicago`, which loads `biblatex` itself.
Loading both is an option clash. Use the profile's package line unchanged:

```latex
\usepackage[authordate,backend=biber]{biblatex-chicago}
```

### Citations show as `[?]`

The key is cited but not in `ref.bib`, or biber has not run since it was added.
Run the audit:

```bash
python scripts/bibtex_audit.py --help
```

---

## Word, Markdown and Typst output

### `pandoc is not installed`

```bash
python scripts/export_document.py --check
```

prints the install command for your platform. Windows:
`winget install --id JohnMacFarlane.Pandoc`. macOS: `brew install pandoc`.

### Converting `main.tex` to `.docx` fails with `unexpected #1`

pandoc reads a large subset of LaTeX, not all of it. `\newcolumntype`, TikZ,
and custom macros are the usual casualties:

```
Error at "main.tex" (line 161): unexpected #1
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
```

For a field that submits Word, write the manuscript in Markdown from the start.
`quick_start.py` does that automatically for every discipline whose
`default_format` is `docx`. Converting a LaTeX manuscript full of custom macros
into Word is a conversion project, not a command.

### Citations are unresolved in the Word output

Three things must all be true: `ref.bib` exists beside the manuscript, the CSL
file is cached, and `--style` was passed.

```bash
python scripts/export_document.py --fetch-csl apa7
python scripts/export_document.py --input main.md --style apa7
```

CSL files are cached in `assets/csl/` and are not committed; they are fetched
on demand.

### The Word file ignores my journal's template

Pass it:

```bash
python scripts/export_document.py --input main.md --style vancouver \
  --reference-doc journal-template.docx
```

pandoc adopts the styles defined in that document.

---

## Citations

### `fetch_bibtex.py` returned the wrong paper

Title search is fuzzy. Searching "Adam" returns several papers with that word
in the title, and the ranking is not always right. Prefer an identifier:

```bash
python scripts/fetch_bibtex.py --doi 10.48550/arXiv.1412.6980
```

Then read the entry. Provenance is verifiable; relevance is not. See
[GUARANTEES.md](GUARANTEES.md).

### A style gate fails on entries that look complete

Field names follow the bibliography backend, not the style name. biblatex
styles (APA, MLA, Chicago, Vancouver) want `journaltitle` and `institution`;
classic BibTeX (IEEE) wants `journal` and `school`. An entry fetched for one
will fail the other:

```bash
python scripts/citation_style.py show apa7 | grep -A8 required_fields_article
```

---

## Autopilot

### `cannot leave 'literature' — ref.bib has 3 entries; the run requires at least 8`

The threshold is set at `init` and stored in the run state. Either fetch more
citations, or start the run with a threshold that matches the paper:

```bash
python scripts/autopilot.py init --project-dir papers/x --topic "..." --min-citations 4
```

### A gate is wrong for my paper and I need to move on

Overrides are allowed and are recorded:

```bash
python scripts/autopilot.py advance --project-dir papers/x \
  --force --reason "the question is stated in the plan, not a separate file"
```

The reason goes into the run journal in `notes/autopilot-state.json` and stays
there.

### `no run at .../notes/autopilot-state.json`

Either the directory is wrong, or no run was started. `quick_start.py` starts
one for you; otherwise `autopilot.py init`.

### The run says the plan is unapproved and I am the only author

Approve it under your own name. The gate exists so that a plan is read by a
person before writing starts, not to require a second person:

```bash
python scripts/autopilot.py advance --project-dir papers/x --approved-by "Your Name"
```

---

## Still stuck

Open an issue with the command you ran, the full output, your OS, and
`python --version`. If it is a venue or a style, say which and link the
official page — that is usually the whole fix.
