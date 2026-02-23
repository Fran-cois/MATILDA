# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Agreements

- **Plan First:** If a change touches more than 2 files, list a concise "Proposed Changes" before editing.
- **Verification Required:** Never claim completion without running the relevant verification commands and confirming exit code 0.
- **Incrementalism:** Prefer small, atomic modifications over broad refactors.
- **Root Cause Discipline:** If a test, lint, or type check fails, inspect logs and config before modifying code.
- **No Tool Churn:** Do not replace existing tooling unless explicitly requested.

## Toolchain

`uv` + `ruff` + `pyright` + `pre-commit` + `pytest`. Do not introduce pip-tools, Poetry, Black, or isort.

**Setup:**
```bash
uv sync --extra dev
```

## Verification Loop

Run after any Python edit and confirm all exit 0 before marking work done.

```bash
uv run ruff check --fix .
uv run ruff format .
uv run pyright
uv run pytest
```

If pre-commit is configured:
```bash
uv run pre-commit run -a
```

## Commands

**Setup:**
```bash
uv sync --extra dev
```

**Run the application** (must `cd src` first, as imports are relative to `src/`):
```bash
cd src
uv run python main.py --config config.yaml
```

**Tests:**
```bash
# All tests (testpaths and pythonpath configured in pyproject.toml)
uv run pytest

# Single test file
uv run pytest src/tests/algorithms/matilda/test_matilda_main.py -v

# With coverage
uv run pytest --cov=src --cov-report=html
```

**Benchmarking:**
```bash
# Full benchmark (all algos × all datasets × N runs → LaTeX table)
uv run python scripts/benchmarks/run_full_benchmark.py --runs 5

# Single algorithm benchmark
uv run python cli.py benchmark --algorithm MATILDA

# Generate LaTeX table from existing results
uv run python cli.py report --latex
```

**CLI utility commands:**
```bash
uv run python cli.py validate --auto     # Validate metric consistency
uv run python cli.py metrics --all       # Calculate metrics
uv run python cli.py clean --cache       # Clean artifacts
uv run python cli.py info --scripts --results
```

## Architecture

### Import path convention
All source code assumes `src/` is the working directory and Python path root. Imports look like `from algorithms.matilda import MATILDA`, not `from src.algorithms...`. When running scripts outside `src/`, set `PYTHONPATH=src`.

### Algorithm plugin pattern
Every algorithm implements `BaseAlgorithm` (`src/algorithms/base_algorithm.py`) with a single `discover_rules(**kwargs) -> Generator[Rule, None, None]` method. `src/main.py` selects the algorithm by name from config and calls `discover_rules()`. Adding a new algorithm means subclassing `BaseAlgorithm` and registering it in `main.py`.

External algorithms (SPIDER, AMIE3, AnyBURL) run via Docker; their wrappers handle container lifecycle. AnyBURL additionally requires a JAR at `src/algorithms/bins/anyburl/*.jar` or the `ANYBURL_JAR` env variable.

### MATILDA core pipeline
`src/algorithms/matilda.py` (the wrapper) calls into `src/algorithms/MATILDA/` in this order:
1. `tgd_discovery.init()` — builds a `ConstraintGraph` of joinable attribute pairs from the database schema. Two attributes are "compatible" (joinable) if they share foreign-key relationships or have sufficient value overlap (Jaccard/count thresholds).
2. `traverse_graph()` — explores the constraint graph with DFS, BFS, or A* (selected via `traversal_algorithm` config key) to produce `CandidateRuleChains`.
3. For each candidate: `split_candidate_rule()` generates body/head splits → `split_pruning()` tests validity via support/confidence queries → `instantiate_tgd()` converts the winner to a `TGDRule`.

### Database layer
`AlchemyUtility` (`src/database/alchemy_utility.py`) is the single access point for all database operations. It composes:
- `DatabaseConnectionManager` — SQLAlchemy engine creation for SQLite/MySQL/Oracle
- `IndexManager` — SQLite index creation
- `DataExporter` — CSV/TSV export
- `TripleConverter` — RDF triple export for AMIE3/AnyBURL
- `QueryUtility` — shared query helpers

Pass an `AlchemyUtility` instance to every algorithm constructor.

### Rule types
`src/utils/rules.py` defines the canonical rule dataclasses: `InclusionDependency`, `TGDRule`, `HornRule`, `FunctionalDependency`, `DenialConstraint`. `TGDRuleFactory.str_to_tgd()` parses MATILDA's string format back into a typed `TGDRule`. `RuleIO` handles JSON serialization.

### Configuration
YAML config is loaded by `src/utils/config_loader.py`. The main keys are:
- `algorithm.name` — which algorithm to run; `algorithm.matilda.traversal_algorithm` — `dfs`/`bfs`/`astar`
- `database.name` / `database.path` — SQLite file location
- `monitor.memory_threshold` (bytes) / `monitor.timeout` (seconds) — enforced by `ResourceMonitor`
- `results.output_dir` — where JSON results are written

The `src/config.yaml` contains hardcoded absolute paths from the original developer's machine — **always override `database.path` and `results.output_dir`** when running locally.

### Studies pipeline
`studies/main/steps/` is a numbered 6-step pipeline (0–5) for reproducing the published benchmark. Run steps in order; each step reads outputs from the previous one. Step 2 calls `src/main.py` for each algorithm/dataset combination.

## Lessons Learned

<!-- Append concise bullets here when corrected, to prevent recurrence. -->
