#!/usr/bin/env python3
"""
Generate TikZ/LaTeX code for scalability visualizations.

Creates publication-quality LaTeX figures using TikZ/PGFPlots for thesis integration.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any


class TikzScalabilityGenerator:
    """Generate TikZ/LaTeX code for scalability graphs."""
    
    def __init__(self, results_file: str, output_dir: str = None):
        """
        Initialize TikZ generator.
        
        :param results_file: Path to scalability_summary.json
        :param output_dir: Directory for output .tex files
        """
        self.results_file = Path(results_file)
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.results_file.parent
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load results
        with open(self.results_file, 'r') as f:
            self.data = json.load(f)
        
        # Extract data
        self.extract_data()
    
    def extract_data(self):
        """Extract data arrays from results."""
        self.sizes_labels = []
        self.sizes_tuples = []
        self.sizes_millions = []
        self.runtimes = []
        self.num_rules = []
        self.rules_per_sec = []
        self.memory_peak = []
        
        datasets = self.data.get('datasets', {})
        sorted_labels = sorted(datasets.keys(), 
                              key=lambda x: datasets[x]['num_tuples'])
        
        for label in sorted_labels:
            dataset = datasets[label]
            results = dataset.get('results', {})
            
            if 'matilda' not in results:
                continue
            
            matilda = results['matilda']
            tuples = dataset['num_tuples']
            
            self.sizes_labels.append(label)
            self.sizes_tuples.append(tuples)
            self.sizes_millions.append(tuples / 1_000_000)
            
            self.runtimes.append(matilda.get('runtime_seconds', 0))
            self.num_rules.append(matilda.get('num_rules', 0))
            self.rules_per_sec.append(matilda.get('rules_per_second', 0))
            self.memory_peak.append(matilda.get('memory_peak_mb', 0))
    
    def generate_tikz_runtime(self) -> str:
        """Generate TikZ code for runtime vs size."""
        tikz = r"""\begin{tikzpicture}
\begin{axis}[
    width=0.8\textwidth,
    height=0.5\textwidth,
    xlabel={Dataset Size (Million Tuples)},
    ylabel={Runtime (seconds)},
    title={Scalability: Runtime vs Dataset Size},
    grid=major,
    legend pos=north west,
    ymajorgrids=true,
    xmajorgrids=true,
    mark size=3pt,
]

% MATILDA data
\addplot[
    color=blue,
    mark=*,
    line width=1.5pt,
] coordinates {
"""
        
        # Add coordinates
        for size, runtime in zip(self.sizes_millions, self.runtimes):
            tikz += f"    ({size:.1f},{runtime:.2f})\n"
        
        tikz += r"""};
\addlegendentry{MATILDA (A* + Hybrid)}

"""
        
        # Add linear reference if we have enough points
        if len(self.sizes_millions) >= 2:
            slope = self.runtimes[-1] / self.sizes_millions[-1]
            tikz += r"""% Linear reference
\addplot[
    color=gray,
    dashed,
    line width=1pt,
] coordinates {
"""
            for size in self.sizes_millions:
                linear = slope * size
                tikz += f"    ({size:.1f},{linear:.2f})\n"
            
            tikz += r"""};
\addlegendentry{Linear reference}

"""
        
        tikz += r"""\end{axis}
\end{tikzpicture}
"""
        
        return tikz
    
    def generate_tikz_memory(self) -> str:
        """Generate TikZ code for memory vs size."""
        if not any(self.memory_peak):
            return "% No memory data available\n"
        
        tikz = r"""\begin{tikzpicture}
\begin{axis}[
    width=0.8\textwidth,
    height=0.5\textwidth,
    xlabel={Dataset Size (Million Tuples)},
    ylabel={Memory Usage (MB)},
    title={Scalability: Memory Usage vs Dataset Size},
    grid=major,
    legend pos=north west,
    ymajorgrids=true,
    xmajorgrids=true,
    mark size=3pt,
]

% Memory data
\addplot[
    color=red,
    mark=square*,
    line width=1.5pt,
] coordinates {
"""
        
        for size, mem in zip(self.sizes_millions, self.memory_peak):
            tikz += f"    ({size:.1f},{mem:.2f})\n"
        
        tikz += r"""};
\addlegendentry{Peak Memory}

\end{axis}
\end{tikzpicture}
"""
        
        return tikz
    
    def generate_tikz_rules(self) -> str:
        """Generate TikZ code for rules vs size."""
        tikz = r"""\begin{tikzpicture}
\begin{axis}[
    width=0.8\textwidth,
    height=0.5\textwidth,
    xlabel={Dataset Size (Million Tuples)},
    ylabel={Number of Rules},
    title={Scalability: Rules Discovered vs Dataset Size},
    grid=major,
    legend pos=north west,
    ymajorgrids=true,
    xmajorgrids=true,
    mark size=3pt,
]

% Rules data
\addplot[
    color=orange,
    mark=triangle*,
    line width=1.5pt,
] coordinates {
"""
        
        for size, rules in zip(self.sizes_millions, self.num_rules):
            tikz += f"    ({size:.1f},{rules})\n"
        
        tikz += r"""};
\addlegendentry{Rules Discovered}

\end{axis}
\end{tikzpicture}
"""
        
        return tikz
    
    def generate_tikz_throughput(self) -> str:
        """Generate TikZ code for throughput vs size."""
        tikz = r"""\begin{tikzpicture}
\begin{axis}[
    width=0.8\textwidth,
    height=0.5\textwidth,
    xlabel={Dataset Size (Million Tuples)},
    ylabel={Throughput (Rules/second)},
    title={Scalability: Discovery Throughput vs Dataset Size},
    grid=major,
    legend pos=north west,
    ymajorgrids=true,
    xmajorgrids=true,
    mark size=3pt,
]

% Throughput data
\addplot[
    color=green!70!black,
    mark=diamond*,
    line width=1.5pt,
] coordinates {
"""
        
        for size, throughput in zip(self.sizes_millions, self.rules_per_sec):
            tikz += f"    ({size:.1f},{throughput:.2f})\n"
        
        tikz += r"""};
\addlegendentry{Throughput}

\end{axis}
\end{tikzpicture}
"""
        
        return tikz
    
    def generate_tikz_combined(self) -> str:
        """Generate TikZ code for combined 2x2 overview."""
        tikz = r"""\begin{tikzpicture}

% Runtime (top-left)
\begin{axis}[
    name=runtime,
    width=0.45\textwidth,
    height=0.35\textwidth,
    xlabel={Size (M tuples)},
    ylabel={Runtime (s)},
    title={Runtime},
    grid=major,
    mark size=2pt,
]
\addplot[color=blue, mark=*, line width=1pt] coordinates {
"""
        for size, runtime in zip(self.sizes_millions, self.runtimes):
            tikz += f"    ({size:.1f},{runtime:.2f})\n"
        
        tikz += r"""};
\end{axis}

% Rules (top-right)
\begin{axis}[
    name=rules,
    at={($(runtime.east)+(1cm,0)$)},
    anchor=west,
    width=0.45\textwidth,
    height=0.35\textwidth,
    xlabel={Size (M tuples)},
    ylabel={Rules},
    title={Rules Discovered},
    grid=major,
    mark size=2pt,
]
\addplot[color=orange, mark=triangle*, line width=1pt] coordinates {
"""
        for size, rules in zip(self.sizes_millions, self.num_rules):
            tikz += f"    ({size:.1f},{rules})\n"
        
        tikz += r"""};
\end{axis}

% Throughput (bottom-left)
\begin{axis}[
    name=throughput,
    at={($(runtime.south)-(0,1cm)$)},
    anchor=north,
    width=0.45\textwidth,
    height=0.35\textwidth,
    xlabel={Size (M tuples)},
    ylabel={Rules/s},
    title={Throughput},
    grid=major,
    mark size=2pt,
]
\addplot[color=green!70!black, mark=diamond*, line width=1pt] coordinates {
"""
        for size, throughput in zip(self.sizes_millions, self.rules_per_sec):
            tikz += f"    ({size:.1f},{throughput:.2f})\n"
        
        tikz += r"""};
\end{axis}

% Memory or Scaling factor (bottom-right)
\begin{axis}[
    name=memory,
    at={($(throughput.east)+(1cm,0)$)},
    anchor=west,
    width=0.45\textwidth,
    height=0.35\textwidth,
    xlabel={Size (M tuples)},
    ylabel={Memory (MB)},
    title={Peak Memory},
    grid=major,
    mark size=2pt,
]
"""
        
        if any(self.memory_peak):
            tikz += r"\addplot[color=red, mark=square*, line width=1pt] coordinates {"
            tikz += "\n"
            for size, mem in zip(self.sizes_millions, self.memory_peak):
                tikz += f"    ({size:.1f},{mem:.2f})\n"
            tikz += "};\n"
        
        tikz += r"""\end{axis}

\end{tikzpicture}
"""
        
        return tikz
    
    def generate_complete_document(self) -> str:
        """Generate complete standalone LaTeX document with all figures."""
        doc = r"""\documentclass[11pt]{article}
\usepackage{pgfplots}
\usepackage{tikz}
\usetikzlibrary{positioning,calc}
\pgfplotsset{compat=1.18}

\usepackage[margin=1in]{geometry}
\usepackage{graphicx}

\title{MATILDA Scalability Analysis}
\author{Generated from scalability\_summary.json}
\date{\today}

\begin{document}

\maketitle

\section{Scalability Results}

This document presents scalability test results for MATILDA TGD discovery system.

\textbf{Configuration:}
\begin{itemize}
"""
        
        config = self.data.get('configuration', {})
        doc += f"    \\item Algorithm: {config.get('algorithm', 'N/A')}\n"
        doc += f"    \\item Heuristic: {config.get('heuristic', 'N/A')}\n"
        doc += f"    \\item Max N: {config.get('max_table', 'N/A')}\n"
        doc += f"    \\item Max Variables: {config.get('max_vars', 'N/A')}\n"
        
        doc += r"""\end{itemize}

\subsection{Runtime Scaling}

"""
        doc += self.generate_tikz_runtime()
        
        doc += r"""

\subsection{Rules Discovery}

"""
        doc += self.generate_tikz_rules()
        
        doc += r"""

\subsection{Throughput Analysis}

"""
        doc += self.generate_tikz_throughput()
        
        if any(self.memory_peak):
            doc += r"""

\subsection{Memory Usage}

"""
            doc += self.generate_tikz_memory()
        
        doc += r"""

\subsection{Overview}

"""
        doc += self.generate_tikz_combined()
        
        # Add scalability metrics if available
        if 'scalability_metrics' in self.data:
            metrics = self.data['scalability_metrics']
            doc += r"""

\section{Scalability Metrics}

\begin{itemize}
"""
            doc += f"    \\item Average Scaling Factor: {metrics.get('avg_scaling_factor', 0):.2f}\n"
            doc += f"    \\item Interpretation: {metrics.get('interpretation', 'N/A')}\n"
            doc += r"""\end{itemize}

\textbf{Interpretation:}
\begin{itemize}
    \item $< 1.0$ = Sub-linear (excellent scaling)
    \item $\approx 1.0$ = Linear (good scaling)
    \item $> 1.0$ = Super-linear (poor scaling)
\end{itemize}
"""
        
        doc += r"""

\end{document}
"""
        
        return doc
    
    def save_individual_tikz_files(self):
        """Save individual TikZ files for each graph."""
        print(f"\n{'='*70}")
        print("GENERATING TikZ/LaTeX FILES")
        print(f"{'='*70}\n")
        
        # Runtime
        runtime_file = self.output_dir / "tikz_runtime.tex"
        with open(runtime_file, 'w') as f:
            f.write(self.generate_tikz_runtime())
        print(f"✓ Generated: {runtime_file}")
        
        # Rules
        rules_file = self.output_dir / "tikz_rules.tex"
        with open(rules_file, 'w') as f:
            f.write(self.generate_tikz_rules())
        print(f"✓ Generated: {rules_file}")
        
        # Throughput
        throughput_file = self.output_dir / "tikz_throughput.tex"
        with open(throughput_file, 'w') as f:
            f.write(self.generate_tikz_throughput())
        print(f"✓ Generated: {throughput_file}")
        
        # Memory
        if any(self.memory_peak):
            memory_file = self.output_dir / "tikz_memory.tex"
            with open(memory_file, 'w') as f:
                f.write(self.generate_tikz_memory())
            print(f"✓ Generated: {memory_file}")
        
        # Combined
        combined_file = self.output_dir / "tikz_combined.tex"
        with open(combined_file, 'w') as f:
            f.write(self.generate_tikz_combined())
        print(f"✓ Generated: {combined_file}")
        
        # Complete document
        doc_file = self.output_dir / "scalability_report.tex"
        with open(doc_file, 'w') as f:
            f.write(self.generate_complete_document())
        print(f"✓ Generated: {doc_file} (complete LaTeX document)")
        
        # Usage instructions
        usage_file = self.output_dir / "TIKZ_USAGE.md"
        usage_content = """# Using TikZ Figures in Your Thesis

## Individual Figures

Include individual TikZ figures in your LaTeX document:

```latex
\\documentclass{article}
\\usepackage{pgfplots}
\\usepackage{tikz}
\\pgfplotsset{compat=1.18}

\\begin{document}

\\begin{figure}[htbp]
    \\centering
    \\input{tikz_runtime.tex}
    \\caption{Runtime scalability of MATILDA TGD discovery.}
    \\label{fig:scalability_runtime}
\\end{figure}

\\end{document}
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
"""
        
        with open(usage_file, 'w') as f:
            f.write(usage_content)
        print(f"✓ Generated: {usage_file} (usage instructions)")
        
        print(f"\n{'='*70}")
        print("✅ ALL TikZ FILES GENERATED")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Generate TikZ/LaTeX code for scalability visualizations.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate TikZ files
  python scripts/utils/generate_tikz_scalability.py results/scalability/scalability_summary.json
  
  # Custom output directory
  python scripts/utils/generate_tikz_scalability.py results/scalability/scalability_summary.json \\
    --output-dir thesis/figures/
  
  # Compile the LaTeX document
  cd results/scalability/
  pdflatex scalability_report.tex
        """
    )
    
    parser.add_argument('results_file', help='Path to scalability_summary.json')
    parser.add_argument('--output-dir', '-o',
                       help='Output directory (default: same as results file)')
    
    args = parser.parse_args()
    
    if not Path(args.results_file).exists():
        print(f"ERROR: Results file not found: {args.results_file}")
        return 1
    
    generator = TikzScalabilityGenerator(args.results_file, args.output_dir)
    generator.save_individual_tikz_files()
    
    print("\n📘 To use in your thesis:")
    print("   \\input{tikz_runtime.tex}")
    print("\n📄 To compile standalone document:")
    print("   pdflatex scalability_report.tex")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
