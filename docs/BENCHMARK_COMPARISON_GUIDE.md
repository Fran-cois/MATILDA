# MATILDA Benchmark Comparison Guide

## Overview

The `compare_matilda_benchmark.py` script compares MATILDA against baseline algorithms (SPIDER, ANYBURL, POPPER) on two key dimensions:

1. **Coverage**: How well MATILDA's rules match baseline algorithms
2. **Speed**: Execution time comparison

## Quick Start

### Run Full Benchmark + Comparison

```bash
# 1. Run benchmark (creates MLflow experiment)
python3 run_full_benchmark.py --runs 5

# 2. Generate comparison report
python3 compare_matilda_benchmark.py
```

The comparison script automatically analyzes the most recent MLflow experiment.

## Output Files

The script generates three files in the MLflow experiment directory:

### 1. Markdown Report (`MATILDA_COMPARISON_REPORT.md`)
Human-readable report with:
- Coverage metrics (Match % and Completeness %)
- Speed metrics (execution time and speedup factor)
- Summary statistics across all datasets
- Interpretation of results

**Example**:
```markdown
## Dataset: Bupa

### Coverage Comparison
| Algorithm | # Rules | MATILDA Rules | Match % | Completeness % |
|-----------|---------|---------------|---------|----------------|
| SPIDER    |     290 |            45 |    0.0% |           0.0% |

### Speed Comparison
| Algorithm | Time (s) | MATILDA Time (s) | Speedup |
|-----------|----------|------------------|---------|
| SPIDER    | 1.86±0.04| 1.52±0.12        | **1.2x faster** |
```

### 2. LaTeX Table (`matilda_comparison_table.tex`)
Publication-ready LaTeX table:

```latex
\begin{table}[htbp]
\centering
\caption{MATILDA Benchmark: Coverage and Speed Comparison}
\begin{tabular}{llrrrrr}
...
\end{tabular}
\end{table}
```

### 3. JSON Data (`matilda_comparison_data.json`)
Machine-readable format for further analysis:

```json
[
  {
    "dataset": "Bupa",
    "other_algorithm": "SPIDER",
    "matilda_rules": 45,
    "other_rules": 290,
    "match_pct": 0.0,
    "completeness_pct": 0.0,
    "matilda_time": 1.52,
    "other_time": 1.86,
    "speedup": 1.2
  }
]
```

## Metrics Explained

### Coverage Metrics

#### Match Percentage
```
Match % = (Number of baseline rules matching MATILDA rules / Total baseline rules) × 100
```

**Interpretation**:
- **High Match (>50%)**: MATILDA closely aligns with baseline algorithms
- **Moderate Match (20-50%)**: MATILDA partially aligns with baselines
- **Low Match (<20%)**: MATILDA discovers different rules (more selective)

#### Completeness Percentage
```
Completeness % = (MATILDA rules matching joinable baseline rules / Total joinable baseline rules) × 100
```

**Joinability Constraint**: Only considers baseline rules where body and head share at least one variable (valid TGDs).

**Interpretation**:
- **High Completeness (>50%)**: MATILDA recovers most joinable baseline rules
- **Moderate Completeness (20-50%)**: MATILDA recovers significant portion
- **Low Completeness (<20%)**: MATILDA is highly selective

### Speed Metrics

#### Speedup Factor
```
Speedup = Baseline Time / MATILDA Time
```

**Interpretation**:
- **Speedup > 1**: MATILDA is faster (e.g., 2.0x = MATILDA is 2× faster)
- **Speedup = 1**: Equal performance
- **Speedup < 1**: MATILDA is slower

**Example**:
- SPIDER: 1.86s, MATILDA: 1.52s → Speedup = 1.86/1.52 = **1.2x faster**
- ANYBURL: 108s, MATILDA: 1.52s → Speedup = 108/1.52 = **71x faster**

## Usage Examples

### Compare Specific Experiment

```bash
# Analyze a specific experiment by ID
python3 compare_matilda_benchmark.py --experiment-id abc123
```

### Analyze Latest Results

```bash
# Automatically uses most recent experiment
python3 compare_matilda_benchmark.py
```

### View Results

```bash
# Find experiment ID
ls -lt data/output/mlruns/

# View Markdown report
cat data/output/mlruns/<exp_id>/MATILDA_COMPARISON_REPORT.md

# View LaTeX table
cat data/output/mlruns/<exp_id>/matilda_comparison_table.tex

# View JSON data
python3 -m json.tool data/output/mlruns/<exp_id>/matilda_comparison_data.json
```

## Understanding Results

### Scenario 1: Low Coverage, High Speed
```
Match: 5%, Completeness: 8%, Speedup: 50x
```

**Interpretation**: MATILDA is highly selective and extremely fast. It discovers a small subset of high-quality rules that baselines miss or find redundant.

**Use Case**: When you need fast, precise rule discovery with minimal redundancy.

### Scenario 2: Moderate Coverage, Moderate Speed
```
Match: 35%, Completeness: 40%, Speedup: 2x
```

**Interpretation**: MATILDA balances coverage and speed, recovering a significant portion of baseline rules while being faster.

**Use Case**: When you need good coverage with improved performance.

### Scenario 3: High Coverage, Low Speed
```
Match: 85%, Completeness: 90%, Speedup: 0.8x
```

**Interpretation**: MATILDA achieves excellent coverage but is slightly slower than baselines.

**Use Case**: When coverage is more important than speed.

## Troubleshooting

### No Experiments Found

**Error**: `❌ No experiments found in mlruns/`

**Solution**: Run benchmark first:
```bash
python3 run_full_benchmark.py --runs 5
```

### No MATILDA Runs

**Error**: `❌ No MATILDA runs found in experiment`

**Solution**: Ensure MATILDA is included in benchmark:
```bash
python3 run_full_benchmark.py --algorithms MATILDA SPIDER --runs 5
```

### Coverage Always 0%

**Issue**: Rule matching might be too strict or rule formats differ.

**Debug**:
1. Check rule formats in JSON files:
   ```bash
   cat data/output/mlruns/<exp_id>/<run_id>/rules.json | head -20
   ```

2. Verify TGD format includes `body` and `head` fields

3. Check `compute_coverage_metrics.py` for matching algorithm

## Integration with MLflow

The comparison script works seamlessly with the MLflow structure:

```
data/output/mlruns/
└── <experiment_id>/
    ├── experiment_meta.json         # Experiment metadata
    ├── runs.json                    # All runs summary
    ├── summary.json                 # Aggregated statistics
    ├── MATILDA_COMPARISON_REPORT.md # 📊 Generated comparison
    ├── matilda_comparison_table.tex # 📊 Generated LaTeX
    ├── matilda_comparison_data.json # 📊 Generated data
    └── <run_id>/
        ├── params.json
        ├── metrics.json
        └── rules.json
```

## Advanced Usage

### Custom Analysis

```python
import json
from pathlib import Path

# Load comparison data
with open('data/output/mlruns/<exp_id>/matilda_comparison_data.json') as f:
    data = json.load(f)

# Filter by dataset
bupa_results = [r for r in data if r['dataset'] == 'Bupa']

# Compute average speedup
avg_speedup = sum(r['speedup'] for r in data) / len(data)
print(f"Average speedup: {avg_speedup:.1f}x")
```

### Export to CSV

```bash
python3 -c "
import json
import csv

with open('data/output/mlruns/<exp_id>/matilda_comparison_data.json') as f:
    data = json.load(f)

with open('comparison.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
"
```

## Best Practices

1. **Run Multiple Iterations**: Use `--runs 5` or more for statistical significance
2. **Compare Across Datasets**: Test on multiple datasets to ensure robustness
3. **Document Results**: Keep Markdown reports for reproducibility
4. **Version Control**: Commit LaTeX tables with paper manuscripts

## References

- **MLflow Guide**: `MLFLOW_GUIDE.md`
- **Coverage Guide**: `COVERAGE_GUIDE.md`
- **Benchmark Runner**: `run_full_benchmark.py`
- **Coverage Computer**: `compute_coverage_metrics.py`
