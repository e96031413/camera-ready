# figures/

Empty on purpose.

The only figure in this example (`fig:timeline`) is drawn inline with TikZ in
`main.tex`, not included from a file. That keeps the example compiling from a
clean checkout with no binary assets and no external tooling.

A real paper puts its figures here as PDF (vector) or PNG at 300 DPI or better,
and references them with `\includegraphics{figures/<name>}`.
`scripts/arxiv_package.py` resolves those paths, flattens them into the
submission tarball, and reports any that do not resolve.
