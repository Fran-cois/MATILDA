# 📊 LaTeX Table Generation for MATILDA

Generate professional LaTeX tables from MATILDA benchmark results.

## 🚀 Quick Start

### Generate Table from Existing Results (Fast)

```bash
# Simple table
python generate_latex_table.py

# Detailed table with all metrics
python generate_latex_table.py --detailed
```

**Output:** `latex_table_[simple|detailed]_TIMESTAMP.tex`

### Run Benchmark with Statistics (5+ runs)

```bash
# 5 runs with mean ± std
python run_benchmark.py --runs 5

# Specific datasets
python run_benchmark.py --runs 5 --datasets Bupa BupaImperfect

# Multiple algorithms
python run_benchmark.py --runs 5 --algorithms MATILDA SPIDER ANYBURL
```

**Output:** `benchmark_results_TIMESTAMP.json` + `benchmark_table_TIMESTAMP.tex`

## 📋 Scripts

| Script | Purpose | Speed | Statistics |
|--------|---------|-------|------------|
| `generate_latex_table.py` | Quick table from existing results | ⚡ Fast | No (single values) |
| `run_benchmark.py` | Run N times + generate stats table | 🐢 Slow | Yes (mean ± std) |

## 📊 Table Formats

### Simple Table
- Columns: Algorithm, Dataset, #Rules, Accuracy, Confidence, Time
- Format: Single values from existing results

### Detailed Table
- Columns: Algorithm, Dataset, #Rules, Acc., Conf., T_compat, T_index, T_CG
- Format: All time metrics included

### Statistics Table (from benchmark)
- Columns: Algorithm, Dataset, #Rules, Time (s), Time Building CG (s)
- Format: Mean ± Standard Deviation (e.g., $9 \pm 0.0$, $15.23 \pm 1.34$)

## 📝 Use in LaTeX

```latex
% Add to preamble
\usepackage{booktabs}
\usepackage{graphicx}

% Include table
\input{latex_table_detailed_20260112_132654.tex}
```

## ⚙️ Options

### `generate_latex_table.py`

```bash
python generate_latex_table.py [OPTIONS]

Options:
  --results-dir DIR          Results directory (default: data/output)
  --output FILE              Output file (default: auto-generated)
  --algorithms ALG1 ALG2 ... Algorithm list
  --datasets DS1 DS2 ...     Dataset list
  --detailed                 Detailed table with all time metrics
```

### `run_benchmark.py`

```bash
python run_benchmark.py [OPTIONS]

Options:
  --runs N                   Number of runs (default: 5)
  --datasets DS1 DS2 ...     Dataset list
  --algorithms ALG1 ALG2 ... Algorithm list
  --config FILE              Config file (default: config.yaml)
  --output-dir DIR           Output directory (default: data/output)
  --no-latex                 Skip LaTeX generation (JSON only)
```

## 📈 Example Output

### Command
```bash
python generate_latex_table.py --detailed
```

### Result
```latex
\begin{table}[htbp]
\centering
\caption{Detailed Rule Discovery Performance}
\label{tab:detailed_results}
\begin{tabular}{llrrrrrr}
\toprule
\textbf{Algorithm} & \textbf{Dataset} & \textbf{\#Rules} & \textbf{Acc.} & \textbf{Conf.} & \textbf{T_compat} & \textbf{T_index} & \textbf{T_CG} \\
\midrule
MATILDA & Bupa & 9 & 1.000 & 1.000 & 0.0378 & 0.0382 & 0.0387 \\
\bottomrule
\end{tabular}
\end{table}
```

## ✅ Testing

```bash
# Test both scripts
python test_latex_generation.py
```

## 📚 Documentation

- **Full Guide:** [LATEX_TABLES_GUIDE.md](LATEX_TABLES_GUIDE.md) - Complete documentation
- **Summary:** [LATEX_TABLES_COMPLETE.md](LATEX_TABLES_COMPLETE.md) - Quick reference

## 🎯 Use Cases

| Use Case | Command |
|----------|---------|
| Quick presentation table | `python generate_latex_table.py` |
| Detailed research paper table | `python generate_latex_table.py --detailed` |
| Statistical comparison (5 runs) | `python run_benchmark.py --runs 5` |
| Multi-algorithm comparison | `python generate_latex_table.py --algorithms MATILDA SPIDER --detailed` |

## 📊 Metrics Included

- **#Rules:** Number of discovered rules
- **Accuracy:** Average rule accuracy
- **Confidence:** Average rule confidence
- **T_compat:** Time to compute compatible attributes (s)
- **T_index:** Time to compute indexed attributes (s)
- **T_CG:** Time to build constraint graph (s)

## 🔧 Files Generated

```
data/output/
├── latex_table_simple_TIMESTAMP.tex
├── latex_table_detailed_TIMESTAMP.tex
├── benchmark_results_TIMESTAMP.json
├── benchmark_table_TIMESTAMP.tex
└── example_document.tex
```

## 💡 Tips

- Use `--detailed` for comprehensive results
- Run `--runs 5` or more for reliable statistics
- Combine with existing results for quick tables
- Customize output with `--algorithms` and `--datasets`

## ✨ Features

✅ Professional booktabs LaTeX format  
✅ Fast generation from existing results  
✅ Statistical benchmarking with mean ± std  
✅ Customizable algorithms and datasets  
✅ Multiple table formats  
✅ Ready for publication  

---

**Quick command for publication:**
```bash
python generate_latex_table.py --detailed --algorithms MATILDA SPIDER ANYBURL
```
