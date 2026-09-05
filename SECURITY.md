# Security Policy

## Reporting a vulnerability

Email **e96031413@gmail.com** with the subject line `[CameraReady security]`.
Please do not open a public issue for a vulnerability report.

Include: what the issue is, which script or asset is affected, and the minimal
steps to reproduce it. You should get an acknowledgement within 7 days.

## What this project does to your machine

CameraReady is a set of local Python scripts plus a skill definition. It is
not a service and it has no server component. Before you run it, know that:

**It reads and writes local files.**
Scripts take a `--project-dir` and read and write inside it: `main.tex`,
`ref.bib`, `plan/`, `issues/`, `notes/`, `figures/`, and LaTeX build output.
`scripts/codebase_snapshot.py` additionally reads a codebase directory that
you point it at, in order to ground a systems paper in real source.

**It runs external binaries.**
`pdflatex`, `bibtex`, `latexmk`, `xelatex`, `pandoc`, `soffice`, `ffprobe`,
`npx remotion`, and a Playwright-controlled Chromium — each only in the
feature that needs it. These execute with your user's privileges.

**It calls external APIs over the network.**
DBLP and CrossRef (`scripts/fetch_bibtex.py`), arXiv
(`scripts/arxiv_registry.py`), conference websites (`scripts/venue_setup.py`,
which downloads style files), an optional TTS backend
(`scripts/synthesize_tts.py` — a local model, or an `--api-url` you supply),
and an optional cross-model review provider
(`scripts/cross_model_review.py`). Paper text and metadata may be transmitted
to these services. Review what a script sends before running it on
unpublished or embargoed work.

**It does not upload your paper anywhere.**
`scripts/arxiv_package.py` builds a submission tarball on disk and stops
there. Uploading to arXiv or a conference system is always a manual step you
perform yourself. `SKILL.md` enforces this: submission sits in the "Ask
first" tier of the Follow-Through Policy.

## Protecting your own data

Run `python scripts/paper_privacy_scan.py --project-dir <paper_dir>` before
sharing a project. It flags secrets, API keys, private key blocks, internal
hostnames, and absolute local paths that have leaked into paper sources.

Run `python scripts/anonymity_check.py --project-dir <paper_dir>` before a
double-blind submission. It flags author identity that would break anonymity.

Neither scanner is a guarantee. Read the diff before you publish.

## Scope

In scope: anything that lets a crafted input file, codebase, or API response
cause a CameraReady script to execute unintended code, escape the project
directory, or exfiltrate data.

Out of scope: vulnerabilities in LaTeX distributions, pandoc, Node.js
packages, or the external APIs themselves. Report those upstream.
