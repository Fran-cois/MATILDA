# Using TikZ Figures in Your Thesis

## Individual Figures

Include individual TikZ figures in your LaTeX document:

```latex
\documentclass{article}
\usepackage{pgfplots}
\usepackage{tikz}
\pgfplotsset{compat=1.18}

\begin{document}

\begin{figure}[htbp]
    \centering
    \input{tikz_runtime.tex}
    \caption{Runtime scalability of MATILDA TGD discovery.}
    \label{fig:scalability_runtime}
\end{figure}

\end{document}
```

## Complete Document

Compile the complete document:

```bash
pdflatex scalability_report.tex
```

## Customization

Edit the .tex files to customize:
- Colors: Change `color=blue` to your preferred color
- Line styles: `dashed`, `dotted`, `solid`
- Markers: `*`, `square*`, `triangle*`, `diamond*`
- Grid: `grid=major`, `grid=minor`, `grid=both`
- Dimensions: `width=`, `height=`

## Required Packages

Make sure your LaTeX installation has:
- pgfplots (for graphs)
- tikz (for drawing)
- calc (for positioning in combined view)

Install with:
```bash
# TeX Live
tlmgr install pgfplots tikz

# MiKTeX
mpm --install pgfplots
```

## Files Generated

- `tikz_runtime.tex` - Runtime vs size graph
- `tikz_rules.tex` - Rules discovered graph
- `tikz_throughput.tex` - Throughput analysis
- `tikz_memory.tex` - Memory usage (if available)
- `tikz_combined.tex` - 2x2 overview
- `scalability_report.tex` - Complete standalone document

## Benefits of TikZ

✅ Vector graphics (perfect scaling)
✅ Native LaTeX integration
✅ Publication-quality output
✅ Consistent fonts with document
✅ Easy customization
✅ No external dependencies at runtime
