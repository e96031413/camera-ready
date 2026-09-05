# TikZ Quality Standards for Beamer Slides

Purpose: TikZ diagram quality rules, reusable patterns, and iterative review process for Beamer presentations.

---

## Quality Standards

- Labels NEVER overlap with curves, lines, dots, or other labels
- When two labels are near the same vertical position, stagger them
- Visual semantics: solid = observed, dashed = counterfactual, filled = observed, hollow = counterfactual
- Line weights: axes = `thick`, data = `thick`, annotations = `thick` (not `very thick`)
- Standard scale: `[scale=1.1]` for full-width diagrams
- Dot radius: `4pt` for data points
- Minimum 0.2 units between any label and nearest graphical element

---

## Mathematical Accuracy of Plotted Points

NEVER hardcode y-coordinates for points on curves. ALL coordinates must be computed from the SAME function via `\pgfmathsetmacro`.

**WRONG — hardcoded y:**
```latex
\draw[thick] plot[domain=0.8:10] (\x, {0.3*\x + 2.7/\x});
\draw[dashed] (2, 0) -- (2, 3.2);  % BAD: 3.2 ≠ 0.3*2+2.7/2=1.95
```

**CORRECT — always compute:**
```latex
\draw[thick] plot[domain=0.8:10] (\x, {0.3*\x + 2.7/\x});
\pgfmathsetmacro{\yTwo}{0.3*2 + 2.7/2}  % = 1.95, exactly on curve
\draw[dashed] (2, 0) -- (2, \yTwo);
\fill (2, \yTwo) circle (2pt);
\node[above left] at (2, \yTwo) {BiPerm};
```

**Curve intersections — solve algebraically first:**
```latex
% Intersection of y=0.5x and y=2.5/x+0.3:
% 0.5x = 2.5/x + 0.3 => x² - 0.6x - 5 = 0 => x = (0.6+sqrt(20.36))/2
\pgfmathsetmacro{\xint}{(0.6 + sqrt(20.36))/2}
\pgfmathsetmacro{\yint}{0.5*\xint}
\fill (\xint, \yint) circle (3pt);
```

---

## TikZ Sizing on Mixed-Content Slides

Beamer 16:9 at 10pt has ~70mm usable height below the title bar.

**Before writing TikZ code**, estimate:
1. Text + equations above: count displayed equations (~12–15mm each) + text lines (~5mm each) + spacing
2. Remaining height = 70mm − text height
3. TikZ bounding box height = (max y − min y) × yscale × 0.3528mm/pt
4. If diagram won't fit: reduce `yscale`, shrink coordinate ranges, or move to separate slide

**Safe defaults:** mixed slides: `xscale=0.5–0.7`, `yscale=0.4–0.6`. Full-slide: `scale=0.9–1.1`.

---

## Edge Labels on Short Arrows

1. Estimate label text width vs. arrow length; if label > ~80% of gap, increase gap or shrink font
2. Use `above=4pt` instead of bare `above` for vertical clearance
3. For flow diagrams with 3+ boxes: total width = N × box_width + (N−1) × gap ≤ 14cm for 16:9
4. Compile and visually verify no label overlaps any box border

---

## Common Diagram Patterns

All patterns assume `arrows.meta`, `positioning`, `decorations.pathreplacing` libraries.

### Flowchart (horizontal)
```latex
\begin{tikzpicture}[
  box/.style={draw, rounded corners, minimum width=2.2cm, minimum height=0.8cm,
              font=\small, fill=positive!10},
  arr/.style={-{Stealth}, thick}
]
  \node[box] (A) {Step 1};
  \node[box, right=1.5cm of A] (B) {Step 2};
  \node[box, right=1.5cm of B] (C) {Step 3};
  \draw[arr] (A) -- node[above, font=\scriptsize] {label} (B);
  \draw[arr] (B) -- (C);
\end{tikzpicture}
```

### Timeline
```latex
\begin{tikzpicture}
  \draw[-{Stealth}, thick] (0,0) -- (12,0) node[right] {Time};
  \foreach \x/\lab in {1.5/Event A, 5/Event B, 9/Event C} {
    \draw[thick] (\x, 0.15) -- (\x, -0.15);
    \node[above=3pt, font=\small] at (\x, 0.15) {\lab};
  }
\end{tikzpicture}
```

### Tree Diagram
```latex
\begin{tikzpicture}[
  level distance=1.2cm, sibling distance=2.5cm,
  every node/.style={draw, rounded corners, font=\small, minimum width=1.5cm}
]
  \node {Root}
    child { node {A} child { node {A1} } child { node {A2} } }
    child { node {B} child { node {B1} } };
\end{tikzpicture}
```

### Decision Diamond
```latex
\node[diamond, draw, aspect=2, inner sep=1pt, font=\small] (D) {condition?};
\draw[arr] (D) -- node[right, font=\scriptsize] {yes} ++(0,-1.2);
\draw[arr] (D) -- node[above, font=\scriptsize] {no} ++(2.5,0);
```

### Coordinate Plot with Computed Intersection
```latex
\begin{tikzpicture}[scale=1.1]
  \draw[-{Stealth}, thick] (0,0) -- (6,0) node[right] {$x$};
  \draw[-{Stealth}, thick] (0,0) -- (0,4) node[above] {$y$};
  \draw[thick, positive] plot[smooth, domain=0.5:5.5] (\x, {0.5*\x});
  \draw[thick, negative, dashed] plot[smooth, domain=0.5:5.5] (\x, {2.5/\x + 0.3});
  \pgfmathsetmacro{\xint}{(0.6 + sqrt(20.36))/2}
  \pgfmathsetmacro{\yint}{0.5*\xint}
  \fill (\xint, \yint) circle (3pt);
\end{tikzpicture}
```

### Annotated Brace
```latex
\draw[decorate, decoration={brace, amplitude=6pt, raise=2pt}]
  (start) -- (end) node[midway, above=10pt, font=\small] {annotation};
```

---

## Iterative TikZ Review Loop

For complex diagrams (≥ 5 nodes or plotted curves):

```
┌─→ Step 1: Mentally render — trace every coordinate
│   Step 2: Check — overlaps, misalignments, inconsistent semantics
│   Step 3: Classify — CRITICAL / MAJOR / MINOR
│   Step 4: Fix all CRITICAL and MAJOR
│   Step 5: Re-compile and visually verify in PDF
└── If CRITICAL/MAJOR remain and round < 3: loop back
    If clear or round = 3: declare verdict
```

**Verdicts:**
- **APPROVED**: Zero CRITICAL, zero MAJOR
- **NEEDS REVISION**: CRITICAL or MAJOR issues remain
- **REJECTED**: Fundamental structural problems → redesign

---

## TikZ Checklist

```
[ ] No label-label overlaps
[ ] No label-curve overlaps
[ ] No edge labels overlapping adjacent nodes
[ ] Diagram bounding box fits within remaining slide space
[ ] ALL marked points computed via \pgfmathsetmacro
[ ] Dashed reference lines terminate exactly at the curve
[ ] Consistent dot style (solid=observed, hollow=counterfactual)
[ ] Consistent line style (solid=observed, dashed=counterfactual)
[ ] Arrow annotations: FROM label TO feature
[ ] Axes extend beyond all data points
[ ] Labels legible at presentation size
[ ] Minimum spacing between labels and graphical elements
```
