# Third-Party Notices

CameraReady is released under the [MIT License](LICENSE). The files listed
below are **not** covered by that license. They keep the license of their
original author.

## Bundled in this repository

### `assets/template/IEEEtran.cls`

- **Upstream**: <http://www.ctan.org/pkg/ieeetran>
- **Copyright**: (c) 1993-2000 Gerry Murray, Silvano Balemi, Jon Dixon,
  Peter Nüchter, Jürgen von Hagen; (c) 2001-2015 Michael Shell.
- **License**: LaTeX Project Public License, version 1.3c or later
  (LPPL-1.3c). See the header of the file itself for the full statement.
- **Why it is bundled**: IEEEtran is the default paper template. LPPL-1.3c
  permits redistribution of an unmodified copy. This copy is unmodified
  (V1.8b, 2015/08/26).
- **Second copy**: `examples/minimal-review-paper/IEEEtran.cls` is the same
  unmodified file. It is committed so the worked example compiles from a clean
  checkout, exactly as a scaffolded project would. Same license.

### `assets/template/poster/template.html`

- **Upstream**: `ethanweber/posterskill`, commit
  `ff2d55cba7026aa446ac8b4260aebe5cab103ade` (noted in the file header).
- **Status**: adapted, not verbatim. Retained upstream attribution in the
  file header. Consult the upstream repository for its license terms before
  redistributing this file separately.

## NOT bundled — downloaded at run time

Venue style files (`neurips_20XX.sty`, `icml20XX.sty`,
`iclr20XX_conference.sty`, `acl.sty`, `aaai2X.sty`, `cvpr.sty`, and their
supporting `.bst`/`.tex` files) are **deliberately absent** from this
repository. Each conference publishes its own template under its own terms,
and several forbid redistribution.

`scripts/venue_setup.py` downloads them from the official URLs recorded in
`assets/venues/<venue>.yaml` into your paper project directory. Those files
are governed by the license of the issuing conference, not by this project's
MIT license. If a download fails, the script prints the official URL so you
can fetch the template manually.

The checklist question sets in `assets/checklists/*.md` **paraphrase** the
official venue checklists for worksheet purposes. They are not verbatim
copies, and they are not a substitute for the verbatim checklist block in the
venue style file. See `scripts/paper_checklist.py` for the submission rule.

## Run-time dependencies

Python and Node.js packages listed in `requirements.txt`,
`requirements-dev.txt`, and `assets/template/video/package.json` are not
redistributed here. They are installed from their own registries under their
own licenses.
