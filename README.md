# MATILDA

MATILDA is a logical rule discovery system from relational databases.

## 🚀 Quick Start with CLI

MATILDA now features a **unified command-line interface** for all operations:

```bash
# General help
python cli.py --help

# Main commands
python cli.py validate --auto                    # Validate metrics
python cli.py benchmark --algorithm spider       # Run benchmark
python cli.py metrics --all                      # Calculate metrics
python cli.py test --all                         # Run tests
python cli.py clean --cache                      # Clean up
python cli.py report --latex                     # Generate reports
python cli.py info --scripts --results           # Project information
```

---

## 📦 Installation

### Installation

#### Download database requirements

**macOS:**

```bash
brew install mysql-client@8.4
```

**Linux:**

```bash
sudo apt-get install mysql-client-8.4
```

**Windows:**

```powershell
choco install mysql --version=8.4
```

#### Set up Python3 virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip3 install -r requirements.txt
```

### Run the application

1. Activate the virtual environment:

```bash
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

2. Start the application:

```bash
cd src 
python main.py
```

### Optional: Run AnyBURL

To use the AnyBURL algorithm, download the AnyBURL jar from the official page and either:

- place it under `src/algorithms/bins/anyburl/` (any `*.jar` filename), or
- set the environment variable `ANYBURL_JAR` to the absolute path of the jar.

Then set `algorithm.name: "ANYBURL"` in your config and run as usual.

---

## 📊 Benchmarking & LaTeX Tables (NEW!)

**Need to benchmark MATILDA for a publication?**

### One-Click Solution ⭐

```bash
# Complete benchmark: all algorithms × all datasets × N runs + LaTeX table
python run_full_benchmark.py --runs 5
```

**What it does:**

- ✅ Runs MATILDA, SPIDER, ANYBURL, POPPER on all datasets
- ✅ Repeats N times, calculates **mean ± standard deviation**
- ✅ Generates professional LaTeX table automatically
- ✅ Saves results and statistics as JSON

**Duration:** 1-2 hours (5 runs)  
**Output:** `data/output/benchmark_table_*.tex`

### Three Available Scripts

| Script                      | Usage                               | Speed       | Statistics   |
| --------------------------- | ----------------------------------- | ----------- | ------------ |
| `run_full_benchmark.py`   | Complete benchmark (all algos)      | 🐢🐢 1-4h   | ✅ Yes      |
| `run_benchmark.py`        | Benchmark 1 algo with stats         | 🐢 5-30 min | ✅ Yes      |
| `generate_latex_table.py` | Table from existing results         | ⚡ < 1s     | ❌ No       |

### Examples

```bash
# Complete benchmark for publication (recommended)
python run_full_benchmark.py --runs 5

# Quick benchmark (test)
python run_full_benchmark.py --runs 3 --algorithms MATILDA SPIDER

# Instant table from existing results
python generate_latex_table.py --detailed

# With configuration file
python run_full_benchmark.py --config benchmark_config.yaml
```

### Complete Documentation

- [benchmark_config.yaml](config/benchmark_config.yaml) - Configuration example

---
