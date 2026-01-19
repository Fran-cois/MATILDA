#!/usr/bin/env python3
"""
Full Benchmark Runner with Automatic LaTeX Table Generation
Following MLflow-like experiment tracking structure

Executes all algorithms on all datasets with N runs, calculates statistics,
and generates LaTeX tables automatically.

Usage:
    python run_full_benchmark.py --runs 5
    python run_full_benchmark.py --runs 3 --algorithms MATILDA SPIDER
    python run_full_benchmark.py --config my_benchmark.yaml
"""

import subprocess
import json
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
import statistics
import sys
import uuid
import re

class FullBenchmarkRunner:
    """Orchestrates full benchmark with MLflow-like experiment tracking."""
    
    def __init__(
        self,
        runs: int = 5,
        algorithms: Optional[List[str]] = None,
        datasets: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
        timeout: int = 3600,
        verbose: bool = True,
        experiment_name: Optional[str] = None,
        compute_coverage: bool = True
    ):
        self.runs = runs
        self.algorithms = algorithms or ["MATILDA", "SPIDER", "ANYBURL", "POPPER", "AMIE3"]
        self.datasets = datasets or ["Bupa", "BupaImperfect", "ComparisonDataset", "ImperfectTest"]
        self.output_dir = output_dir or Path("data/output")
        self.timeout = timeout
        self.verbose = verbose
        self.compute_coverage = compute_coverage
        
        # MLflow-like structure
        self.experiment_name = experiment_name or f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.experiment_id = str(uuid.uuid4())[:8]
        self.experiment_dir = self.output_dir / "mlruns" / self.experiment_id
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        
        self.runs_data = []  # List of all runs with MLflow structure
        self.results = {}  # algorithm -> dataset -> list of results (legacy)
        self.statistics = {}  # algorithm -> dataset -> stats (legacy)
        
    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def run_single_algorithm(
        self,
        algorithm: str,
        dataset: str,
        run_number: int
    ) -> Optional[Dict[str, Any]]:
        """Run a single algorithm on a single dataset and return MLflow-like run data."""
        run_id = str(uuid.uuid4())[:16]
        start_time = datetime.now()
        
        self.log(f"Running {algorithm} on {dataset} (run {run_number}/{self.runs})...")
        
        # MLflow-like run structure
        run_data = {
            "info": {
                "run_id": run_id,
                "run_name": f"{algorithm}_{dataset}_run{run_number}",
                "experiment_id": self.experiment_id,
                "status": "RUNNING",
                "start_time": start_time.isoformat(),
                "end_time": None,
                "artifact_uri": str(self.experiment_dir / run_id)
            },
            "params": {
                "algorithm": algorithm,
                "dataset": dataset,
                "run_number": run_number,
                "timeout": self.timeout
            },
            "metrics": {},
            "tags": {
                "mlflow.runName": f"{algorithm}_{dataset}_run{run_number}",
                "algorithm": algorithm,
                "dataset": dataset
            }
        }
        
        try:
            # Update config.yaml with algorithm and dataset
            config_path = Path("src/config.yaml")
            if not config_path.exists():
                config_path = Path("config.yaml")
            
            # Read config
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            # Update algorithm and dataset
            config['algorithm']['name'] = algorithm
            config['database']['name'] = f"{dataset}.db"
            
            # Write config
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            # Determine main.py path and working directory
            if Path("src/main.py").exists():
                main_path = Path("src/main.py")
                work_dir = Path.cwd()  # Execute from root
            elif Path("main.py").exists():
                main_path = Path("main.py")
                work_dir = Path.cwd()
            else:
                self.log(f"  ⚠️  main.py not found")
                return None
            
            # Determine python command (use same interpreter as current script)
            import sys
            python_cmd = sys.executable
            
            # Build command - need to cd into src/ directory to run main.py
            if Path("src").exists():
                # If we have a src/ directory, run from inside it
                cmd = [python_cmd, "main.py"]
                work_dir = Path("src").absolute()
            else:
                cmd = [python_cmd, str(main_path)]
                work_dir = Path.cwd()
            
            # Execute with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=work_dir
            )
            
            if result.returncode != 0:
                self.log(f"  ⚠️  Error: {result.stderr[:200]}")
                return None
            
            # Parse results
            result_file = self.output_dir / f"{algorithm}_{dataset}_results.json"
            if result_file.exists():
                with open(result_file) as f:
                    data = json.load(f)
                    
                    # Handle different JSON formats
                    if isinstance(data, list):
                        # Format: list of rules with accuracy/confidence in each
                        if len(data) > 0:
                            # Calculate aggregate metrics from list of rules
                            accuracies = [rule.get('accuracy', 0) or 0 for rule in data if isinstance(rule, dict)]
                            confidences = [rule.get('confidence', 0) or 0 for rule in data if isinstance(rule, dict)]
                            
                            formatted_data = {
                                'rules': data,
                                'accuracy': sum(accuracies) / len(accuracies) if accuracies else 0,
                                'confidence': sum(confidences) / len(confidences) if confidences else 0,
                                'time_total': 0,  # Will be read from time metrics file
                                'time_compat': 0,
                                'time_index': 0,
                                'time_cg': 0
                            }
                        else:
                            formatted_data = {
                                'rules': [],
                                'accuracy': 0,
                                'confidence': 0,
                                'time_total': 0,
                                'time_compat': 0,
                                'time_index': 0,
                                'time_cg': 0
                            }
                    elif isinstance(data, dict):
                        # Format: dict with 'rules' key - ensure time metrics exist
                        formatted_data = data
                        formatted_data.setdefault('time_total', 0)
                        formatted_data.setdefault('time_compat', 0)
                        formatted_data.setdefault('time_index', 0)
                        formatted_data.setdefault('time_cg', 0)
                    else:
                        self.log(f"  ⚠️  Unexpected JSON format")
                        return None
                    
                    # Try to read time metrics
                    time_file = self.output_dir / f"init_time_metrics_{dataset}.json"
                    if time_file.exists():
                        try:
                            with open(time_file) as tf:
                                time_data = json.load(tf)
                                formatted_data['time_compat'] = time_data.get('compatibility_graph', 0) or 0
                                formatted_data['time_index'] = time_data.get('index', 0) or 0
                                formatted_data['time_cg'] = time_data.get('cg_construction', 0) or 0
                                formatted_data['time_total'] = (
                                    formatted_data['time_compat'] + 
                                    formatted_data['time_index'] + 
                                    formatted_data['time_cg']
                                )
                        except:
                            pass
                    
                    self.log(f"  ✓ {algorithm} on {dataset}: {len(formatted_data.get('rules', []))} rules")
                    
                    # Add metrics to MLflow-like structure
                    end_time = datetime.now()
                    run_data["info"]["end_time"] = end_time.isoformat()
                    run_data["info"]["status"] = "FINISHED"
                    run_data["metrics"] = {
                        "num_rules": len(formatted_data.get('rules', [])),
                        "accuracy": formatted_data.get('accuracy', 0) or 0,
                        "confidence": formatted_data.get('confidence', 0) or 0,
                        "time_total": formatted_data.get('time_total', 0) or 0,
                        "time_compat": formatted_data.get('time_compat', 0) or 0,
                        "time_index": formatted_data.get('time_index', 0) or 0,
                        "time_cg": formatted_data.get('time_cg', 0) or 0,
                        "duration_seconds": (end_time - start_time).total_seconds()
                    }
                    
                    # Save run artifacts
                    run_dir = Path(run_data["info"]["artifact_uri"])
                    run_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save metrics as artifact
                    with open(run_dir / "metrics.json", 'w') as f:
                        json.dump(run_data["metrics"], f, indent=2)
                    
                    # Save params as artifact
                    with open(run_dir / "params.json", 'w') as f:
                        json.dump(run_data["params"], f, indent=2)
                    
                    # Save run metadata
                    with open(run_dir / "run_info.json", 'w') as f:
                        json.dump(run_data["info"], f, indent=2)
                    
                    # Save rules as artifact with original metrics
                    rules_with_original_metrics = []
                    for rule in formatted_data.get('rules', []):
                        if isinstance(rule, dict):
                            # Add original metrics (as reported by the algorithm)
                            rule_copy = rule.copy()
                            rule_copy['original_accuracy'] = rule.get('accuracy', 0) or 0
                            rule_copy['original_coverage'] = rule.get('confidence', 0) or 0  # Using confidence as coverage proxy
                            rules_with_original_metrics.append(rule_copy)
                        else:
                            rules_with_original_metrics.append(rule)
                    
                    with open(run_dir / "rules.json", 'w') as f:
                        json.dump(rules_with_original_metrics, f, indent=2)
                    
                    self.runs_data.append(run_data)
                    return formatted_data
            else:
                run_data["info"]["status"] = "FAILED"
                run_data["info"]["end_time"] = datetime.now().isoformat()
                run_data["tags"]["error"] = "Result file not found"
                self.runs_data.append(run_data)
                self.log(f"  ⚠️  Result file not found: {result_file}")
                return None
                
        except subprocess.TimeoutExpired:
            run_data["info"]["status"] = "FAILED"
            run_data["info"]["end_time"] = datetime.now().isoformat()
            run_data["tags"]["error"] = f"Timeout after {self.timeout}s"
            self.runs_data.append(run_data)
            self.log(f"  ⚠️  Timeout after {self.timeout}s")
            return None
        except Exception as e:
            import traceback
            run_data["info"]["status"] = "FAILED"
            run_data["info"]["end_time"] = datetime.now().isoformat()
            run_data["tags"]["error"] = str(e)
            run_data["tags"]["traceback"] = traceback.format_exc()
            self.runs_data.append(run_data)
            self.log(f"  ⚠️  Error: {e}")
            if self.verbose:
                self.log(f"  Traceback:\n{traceback.format_exc()}")
            return None
    
    def run_algorithm_with_repeats(self, algorithm: str, dataset: str) -> List[Dict[str, Any]]:
        """Run algorithm N times and collect results."""
        results = []
        
        for run_num in range(1, self.runs + 1):
            result = self.run_single_algorithm(algorithm, dataset, run_num)
            if result:
                results.append(result)
        
        return results
    
    def calculate_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics from multiple runs."""
        if not results:
            return {
                "num_rules": {"mean": 0, "std": 0},
                "accuracy": {"mean": 0, "std": 0},
                "confidence": {"mean": 0, "std": 0},
                "time_total": {"mean": 0, "std": 0},
                "time_compat": {"mean": 0, "std": 0},
                "time_index": {"mean": 0, "std": 0},
                "time_cg": {"mean": 0, "std": 0},
                "n_runs": 0
            }
        
        # Collect metrics
        num_rules = [len(r.get("rules", [])) for r in results]
        accuracies = [r.get("accuracy", 0) for r in results]
        confidences = [r.get("confidence", 0) for r in results]
        times_total = [r.get("time_total", 0) for r in results]
        times_compat = [r.get("time_compat", 0) for r in results]
        times_index = [r.get("time_index", 0) for r in results]
        times_cg = [r.get("time_cg", 0) for r in results]
        
        def stats(values: List[float]) -> Dict[str, float]:
            if len(values) == 0:
                return {"mean": 0, "std": 0}
            elif len(values) == 1:
                return {"mean": values[0], "std": 0}
            else:
                return {
                    "mean": statistics.mean(values),
                    "std": statistics.stdev(values)
                }
        
        return {
            "num_rules": stats(num_rules),
            "accuracy": stats(accuracies),
            "confidence": stats(confidences),
            "time_total": stats(times_total),
            "time_compat": stats(times_compat),
            "time_index": stats(times_index),
            "time_cg": stats(times_cg),
            "n_runs": len(results)
        }
    
    def run_full_benchmark(self):
        """Run all algorithms on all datasets with N runs."""
        self.log(f"\n{'='*60}")
        self.log(f"FULL BENCHMARK: {len(self.algorithms)} algorithms × {len(self.datasets)} datasets × {self.runs} runs")
        self.log(f"Total runs: {len(self.algorithms) * len(self.datasets) * self.runs}")
        self.log(f"{'='*60}\n")
        
        for algorithm in self.algorithms:
            self.results[algorithm] = {}
            self.statistics[algorithm] = {}
            
            for dataset in self.datasets:
                self.log(f"\n--- {algorithm} on {dataset} ---")
                
                # Run N times
                results = self.run_algorithm_with_repeats(algorithm, dataset)
                
                # Store results
                self.results[algorithm][dataset] = results
                
                # Calculate statistics
                stats = self.calculate_statistics(results)
                self.statistics[algorithm][dataset] = stats
                
                self.log(f"  📊 Stats: {stats['num_rules']['mean']:.1f} ± {stats['num_rules']['std']:.1f} rules")
        
        self.log(f"\n{'='*60}")
        self.log("BENCHMARK COMPLETE!")
        self.log(f"{'='*60}\n")
    
    def save_results(self):
        """Save results and statistics to JSON files with MLflow structure."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save MLflow-like experiment metadata
        experiment_meta = {
            "experiment_id": self.experiment_id,
            "name": self.experiment_name,
            "artifact_location": str(self.experiment_dir),
            "lifecycle_stage": "active",
            "creation_time": timestamp,
            "last_update_time": timestamp,
            "tags": {
                "num_algorithms": len(self.algorithms),
                "num_datasets": len(self.datasets),
                "runs_per_combination": self.runs
            }
        }
        
        experiment_file = self.experiment_dir / "experiment_meta.json"
        with open(experiment_file, 'w') as f:
            json.dump(experiment_meta, f, indent=2)
        self.log(f"✓ Experiment metadata saved: {experiment_file}")
        
        # Save all runs data (MLflow structure)
        runs_file = self.experiment_dir / "runs.json"
        with open(runs_file, 'w') as f:
            json.dump(self.runs_data, f, indent=2)
        self.log(f"✓ All runs saved: {runs_file} ({len(self.runs_data)} runs)")
        
        # Generate summary metrics per algorithm/dataset
        summary = {}
        for run in self.runs_data:
            if run["info"]["status"] == "FINISHED":
                algo = run["params"]["algorithm"]
                dataset = run["params"]["dataset"]
                key = f"{algo}_{dataset}"
                
                if key not in summary:
                    summary[key] = {
                        "algorithm": algo,
                        "dataset": dataset,
                        "runs": [],
                        "metrics": {}
                    }
                
                summary[key]["runs"].append({
                    "run_id": run["info"]["run_id"],
                    "metrics": run["metrics"]
                })
        
        # Calculate statistics for each combination
        for key, data in summary.items():
            if data["runs"]:
                # Aggregate metrics across runs
                all_metrics = [r["metrics"] for r in data["runs"]]
                aggregated = {}
                
                for metric_name in ["num_rules", "accuracy", "confidence", "time_total", 
                                   "time_compat", "time_index", "time_cg", "duration_seconds"]:
                    values = [m.get(metric_name, 0) for m in all_metrics]
                    if len(values) > 1:
                        aggregated[metric_name] = {
                            "mean": statistics.mean(values),
                            "std": statistics.stdev(values),
                            "min": min(values),
                            "max": max(values),
                            "count": len(values)
                        }
                    elif len(values) == 1:
                        aggregated[metric_name] = {
                            "mean": values[0],
                            "std": 0,
                            "min": values[0],
                            "max": values[0],
                            "count": 1
                        }
                
                data["metrics"] = aggregated
        
        # Save summary with statistics
        summary_file = self.experiment_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        self.log(f"✓ Summary with statistics saved: {summary_file}")
        
        # Also save in legacy format for compatibility
        results_file = self.output_dir / f"full_benchmark_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Compute coverage metrics if enabled and MATILDA is present
        if self.compute_coverage and "MATILDA" in self.algorithms:
            coverage_data = self.compute_coverage_metrics()
            if coverage_data:
                self.generate_coverage_table(coverage_data)
        self.log(f"✓ Legacy results saved: {results_file}")
        
        stats_file = self.output_dir / f"full_benchmark_statistics_{timestamp}.json"
        with open(stats_file, 'w') as f:
            json.dump(self.statistics, f, indent=2)
        self.log(f"✓ Legacy statistics saved: {stats_file}")
        
        return experiment_file, runs_file, summary_file
    
    def generate_latex_table(self, table_type: str = "detailed") -> Path:
        """Generate LaTeX table from statistics."""
        self.log("\n--- Generating LaTeX Table ---")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        latex_file = self.experiment_dir / f"benchmark_table_{timestamp}.tex"
        
        # Generate table
        if table_type == "simple":
            content = self._generate_simple_table()
        else:
            content = self._generate_detailed_table()
        
        # Write to file
        with open(latex_file, 'w') as f:
            f.write(content)
        
        # Also save in legacy location
        legacy_latex = self.output_dir / f"benchmark_table_{timestamp}.tex"
        with open(legacy_latex, 'w') as f:
            f.write(content)
        
        self.log(f"✓ LaTeX table saved: {latex_file}")
        self.log(f"✓ LaTeX table (legacy) saved: {legacy_latex}")
        return latex_file
    
    def _generate_simple_table(self) -> str:
        """Generate simple LaTeX table (6 columns)."""
        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            r"\caption{Rule Discovery Performance with Statistics (" + f"{self.runs} runs" + r")}",
            r"\resizebox{\textwidth}{!}{",
            r"\begin{tabular}{llrrrr}",
            r"\toprule",
            r"\textbf{Algorithm} & \textbf{Dataset} & \textbf{\#Rules} & \textbf{Accuracy} & \textbf{Confidence} & \textbf{Time (s)} \\",
            r"\midrule"
        ]
        
        for algorithm in sorted(self.statistics.keys()):
            for dataset in sorted(self.statistics[algorithm].keys()):
                stats = self.statistics[algorithm][dataset]
                
                if stats["n_runs"] == 0:
                    continue
                
                # Format with mean ± std
                num_rules = f"${stats['num_rules']['mean']:.0f} \\pm {stats['num_rules']['std']:.1f}$"
                accuracy = f"${stats['accuracy']['mean']:.3f} \\pm {stats['accuracy']['std']:.3f}$"
                confidence = f"${stats['confidence']['mean']:.3f} \\pm {stats['confidence']['std']:.3f}$"
                time = f"${stats['time_total']['mean']:.3f} \\pm {stats['time_total']['std']:.3f}$"
                
                lines.append(
                    f"{algorithm} & {dataset} & {num_rules} & {accuracy} & {confidence} & {time} \\\\"
                )
        
        lines.extend([
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\end{table}"
        ])
        
        return "\n".join(lines)
    
    def _generate_detailed_table(self) -> str:
        """Generate detailed LaTeX table (8 columns with time breakdown)."""
        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            r"\caption{Detailed Rule Discovery Performance with Statistics (" + f"{self.runs} runs" + r")}",
            r"\resizebox{\textwidth}{!}{",
            r"\begin{tabular}{llrrrrrr}",
            r"\toprule",
            r"\textbf{Algorithm} & \textbf{Dataset} & \textbf{\#Rules} & \textbf{Acc.} & \textbf{Conf.} & \textbf{T\_compat} & \textbf{T\_index} & \textbf{T\_CG} \\",
            r"\midrule"
        ]
        
        for algorithm in sorted(self.statistics.keys()):
            for dataset in sorted(self.statistics[algorithm].keys()):
                stats = self.statistics[algorithm][dataset]
                
                if stats["n_runs"] == 0:
                    continue
                
                # Format with mean ± std
                num_rules = f"${stats['num_rules']['mean']:.0f} \\pm {stats['num_rules']['std']:.1f}$"
                accuracy = f"${stats['accuracy']['mean']:.3f} \\pm {stats['accuracy']['std']:.3f}$"
                confidence = f"${stats['confidence']['mean']:.3f} \\pm {stats['confidence']['std']:.3f}$"
                t_compat = f"${stats['time_compat']['mean']:.4f} \\pm {stats['time_compat']['std']:.4f}$"
                t_index = f"${stats['time_index']['mean']:.4f} \\pm {stats['time_index']['std']:.4f}$"
                t_cg = f"${stats['time_cg']['mean']:.4f} \\pm {stats['time_cg']['std']:.4f}$"
                
                lines.append(
                    f"{algorithm} & {dataset} & {num_rules} & {accuracy} & {confidence} & {t_compat} & {t_index} & {t_cg} \\\\"
                )
        
        lines.extend([
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\end{table}"
        ])
        
        return "\n".join(lines)
    
    def normalize_table_name(self, name: str) -> str:
        """Normalize table names (remove _0 suffix, convert to lowercase)."""
        return name.replace('_0', '').lower().strip()
    
    def extract_tables_from_tgd(self, rule: Dict) -> Set[str]:
        """Extract table names from MATILDA TGD rule."""
        tables = set()
        
        # From body predicates
        for body_pred in rule.get('body', []):
            if 'relation=' in body_pred:
                match = re.search(r"relation='([^']+)'", body_pred)
                if match:
                    tables.add(self.normalize_table_name(match.group(1)))
        
        # From head predicates
        for head_pred in rule.get('head', []):
            if 'relation=' in head_pred:
                match = re.search(r"relation='([^']+)'", head_pred)
                if match:
                    tables.add(self.normalize_table_name(match.group(1)))
        
        return tables
    
    def tgd_matches_ind(self, tgd_rule: Dict, ind_rule: Dict) -> bool:
        """Check if a TGD rule matches an IND rule (SPIDER/IND format)."""
        # Extract IND components
        dep_table = self.normalize_table_name(ind_rule.get('table_dependant', ''))
        ref_table = self.normalize_table_name(ind_rule.get('table_referenced', ''))
        
        # Extract TGD tables
        tgd_tables = self.extract_tables_from_tgd(tgd_rule)
        
        # Check if TGD involves the same tables
        if dep_table in tgd_tables and ref_table in tgd_tables:
            return True
        
        return False
    
    def tgd_matches_tgd(self, tgd1: Dict, tgd2: Dict) -> bool:
        """Check if two TGD/Horn rules match."""
        # Simple approach: compare tables involved
        tables1 = self.extract_tables_from_tgd(tgd1)
        tables2 = self.extract_tables_from_tgd(tgd2)
        
        # Rules match if they share most tables
        if not tables1 or not tables2:
            return False
        
        overlap = len(tables1 & tables2)
        min_size = min(len(tables1), len(tables2))
        
        # At least 80% table overlap
        return overlap / min_size >= 0.8 if min_size > 0 else False
    
    def is_joinable(self, rule: Dict, algorithm: str) -> bool:
        """Check if a rule satisfies joinability constraint."""
        if algorithm.upper() in ['SPIDER', 'IND']:
            # All INDs are potentially joinable
            return True
        
        elif rule.get('type') in ['TGDRule', 'HornRule']:
            # For TGD/Horn rules, check if body and head share variables
            body = rule.get('body', [])
            head = rule.get('head', [])
            
            # Extract variables from body and head
            body_vars = set()
            head_vars = set()
            
            for pred in body:
                vars_found = re.findall(r"variable[12]='([^']+)'", pred)
                body_vars.update(vars_found)
            
            for pred in head:
                vars_found = re.findall(r"variable[12]='([^']+)'", pred)
                head_vars.update(vars_found)
            
            # Rule is joinable if body and head share at least one variable
            return len(body_vars & head_vars) > 0
        
        # Default: assume joinable
        return True
    
    def compute_coverage_metrics(self) -> Dict[str, Any]:
        """Compute MATILDA coverage metrics vs other algorithms."""
        self.log("\n" + "="*60)
        self.log("Computing MATILDA Coverage Metrics")
        self.log("="*60)
        
        coverage_data = {}
        
        for dataset in self.datasets:
            # Load MATILDA rules from summary
            matilda_rules = []
            if "MATILDA" in self.statistics and dataset in self.statistics["MATILDA"]:
                # Get all MATILDA runs for this dataset
                for run_data in self.runs_data:
                    if (run_data["params"]["algorithm"] == "MATILDA" and 
                        run_data["params"]["dataset"] == dataset and
                        run_data["info"]["status"] == "FINISHED"):
                        # Load rules from run artifact
                        run_dir = Path(run_data["info"]["artifact_uri"])
                        rules_file = run_dir / "rules.json"
                        if rules_file.exists():
                            with open(rules_file) as f:
                                matilda_rules = json.load(f)
                            break  # Use first successful run
            
            if not matilda_rules:
                continue
            
            for algorithm in self.algorithms:
                if algorithm == "MATILDA":
                    continue
                
                # Load other algorithm rules
                other_rules = []
                for run_data in self.runs_data:
                    if (run_data["params"]["algorithm"] == algorithm and 
                        run_data["params"]["dataset"] == dataset and
                        run_data["info"]["status"] == "FINISHED"):
                        # Load rules from run artifact
                        run_dir = Path(run_data["info"]["artifact_uri"])
                        rules_file = run_dir / "rules.json"
                        if rules_file.exists():
                            with open(rules_file) as f:
                                other_rules = json.load(f)
                            break  # Use first successful run
                
                if not other_rules:
                    continue
                
                # Compute coverage
                matched_count = 0
                for other_rule in other_rules:
                    for matilda_rule in matilda_rules:
                        is_match = False
                        if other_rule.get('type') == 'InclusionDependency':
                            is_match = self.tgd_matches_ind(matilda_rule, other_rule)
                        elif other_rule.get('type') in ['TGDRule', 'HornRule']:
                            is_match = self.tgd_matches_tgd(matilda_rule, other_rule)
                        
                        if is_match:
                            matched_count += 1
                            break
                
                # Compute completeness (joinable rules)
                joinable_rules = [r for r in other_rules if self.is_joinable(r, algorithm)]
                matilda_recovered = 0
                for other_rule in joinable_rules:
                    for matilda_rule in matilda_rules:
                        is_match = False
                        if other_rule.get('type') == 'InclusionDependency':
                            is_match = self.tgd_matches_ind(matilda_rule, other_rule)
                        else:
                            is_match = self.tgd_matches_tgd(matilda_rule, other_rule)
                        
                        if is_match:
                            matilda_recovered += 1
                            break
                
                key = f"{algorithm}_{dataset}"
                coverage_data[key] = {
                    "algorithm": algorithm,
                    "dataset": dataset,
                    "matilda_total": len(matilda_rules),
                    "other_total": len(other_rules),
                    "rules_match_count": matched_count,
                    "rules_match_percentage": (matched_count / len(other_rules) * 100) if other_rules else 0,
                    "joinable_rules_count": len(joinable_rules),
                    "matilda_recovered_count": matilda_recovered,
                    "completeness_percentage": (matilda_recovered / len(joinable_rules) * 100) if joinable_rules else 0
                }
                
                self.log(f"  {algorithm:10s} vs MATILDA on {dataset:20s}: "
                        f"Match={coverage_data[key]['rules_match_percentage']:5.1f}%  "
                        f"Completeness={coverage_data[key]['completeness_percentage']:5.1f}%")
        
        # Save coverage metrics
        coverage_file = self.experiment_dir / "coverage_metrics.json"
        with open(coverage_file, 'w') as f:
            json.dump(list(coverage_data.values()), f, indent=2)
        
        self.log(f"\n✅ Coverage metrics saved: {coverage_file}")
        
        return coverage_data
    
    def generate_coverage_table(self, coverage_data: Dict[str, Any]) -> Path:
        """Generate LaTeX table with coverage metrics."""
        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            r"\caption{MATILDA Coverage Comparison}",
            r"\label{tab:matilda_coverage}",
            r"\resizebox{\textwidth}{!}{",
            r"\begin{tabular}{llrrrrrr}",
            r"\toprule",
            r"\textbf{Dataset} & \textbf{Algorithm} & ",
            r"\textbf{\#MATILDA} & \textbf{\#Other} & ",
            r"\multicolumn{2}{c}{\textbf{Rules Match}} & ",
            r"\multicolumn{2}{c}{\textbf{Completeness}} \\",
            r"\cmidrule(lr){5-6} \cmidrule(lr){7-8}",
            r" & & & & \textbf{Count} & \textbf{\%} & \textbf{Count} & \textbf{\%} \\",
            r"\midrule"
        ]
        
        # Group by dataset
        by_dataset = {}
        for key, metrics in coverage_data.items():
            dataset = metrics["dataset"]
            if dataset not in by_dataset:
                by_dataset[dataset] = []
            by_dataset[dataset].append(metrics)
        
        for dataset in sorted(by_dataset.keys()):
            metrics_list = by_dataset[dataset]
            for i, m in enumerate(metrics_list):
                if i == 0:
                    dataset_cell = f"\\multirow{{{len(metrics_list)}}}{{*}}{{{dataset}}}"
                else:
                    dataset_cell = ""
                
                lines.append(
                    f"{dataset_cell} & {m['algorithm']} & "
                    f"{m['matilda_total']} & {m['other_total']} & "
                    f"{m['rules_match_count']} & {m['rules_match_percentage']:.1f}\\% & "
                    f"{m['matilda_recovered_count']} & {m['completeness_percentage']:.1f}\\% \\\\"
                )
            
            lines.append(r"\midrule")
        
        lines.extend([
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\end{table}"
        ])
        
        # Save table
        output_file = self.experiment_dir / "coverage_table.tex"
        with open(output_file, 'w') as f:
            f.write("\n".join(lines))
        
        self.log(f"✅ Coverage table saved: {output_file}")
        
        return output_file
    
    def print_summary(self):
        """Print summary of results in MLflow-like format."""
        print("\n" + "="*60)
        print(f"EXPERIMENT: {self.experiment_name}")
        print(f"Experiment ID: {self.experiment_id}")
        print(f"Location: {self.experiment_dir}")
        print("="*60 + "\n")
        
        print(f"Total runs: {len(self.runs_data)}")
        finished = sum(1 for r in self.runs_data if r["info"]["status"] == "FINISHED")
        failed = sum(1 for r in self.runs_data if r["info"]["status"] == "FAILED")
        print(f"  ✓ Finished: {finished}")
        print(f"  ✗ Failed: {failed}")
        
        print("\n" + "-"*60)
        print("SUMMARY BY ALGORITHM/DATASET")
        print("-"*60 + "\n")
        
        for algorithm in sorted(self.statistics.keys()):
            print(f"\n{algorithm}:")
            for dataset in sorted(self.statistics[algorithm].keys()):
                stats = self.statistics[algorithm][dataset]
                if stats["n_runs"] > 0:
                    print(f"  {dataset:20s}: {stats['num_rules']['mean']:5.1f} ± {stats['num_rules']['std']:4.1f} rules "
                          f"({stats['time_total']['mean']:.3f} ± {stats['time_total']['std']:.3f}s)")
                else:
                    print(f"  {dataset:20s}: No results")
        
        print("\n" + "="*60)
        print(f"\n📊 View results: {self.experiment_dir}")
        print(f"   - experiment_meta.json  : Experiment metadata")
        print(f"   - runs.json             : All runs data")
        print(f"   - summary.json          : Aggregated statistics")
        print(f"   - <run_id>/             : Individual run artifacts")
        print("="*60 + "\n")


def load_config(config_file: Path) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_file) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Run full benchmark with all algorithms and generate LaTeX table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run 5 times each algorithm on all datasets
  python run_full_benchmark.py --runs 5
  
  # Run only MATILDA and SPIDER
  python run_full_benchmark.py --runs 3 --algorithms MATILDA SPIDER
  
  # Run on specific datasets
  python run_full_benchmark.py --runs 5 --datasets Bupa BupaImperfect
  
  # Use custom configuration file
  python run_full_benchmark.py --config my_benchmark.yaml
  
  # Generate simple table instead of detailed
  python run_full_benchmark.py --runs 5 --table-type simple
        """
    )
    
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of runs per algorithm/dataset (default: 5)"
    )
    
    parser.add_argument(
        "--algorithms",
        nargs="+",
        choices=["MATILDA", "SPIDER", "ANYBURL", "POPPER", "AMIE3"],
        help="Algorithms to benchmark (default: all)"
    )
    
    parser.add_argument(
        "--datasets",
        nargs="+",
        help="Datasets to use (default: all from config)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/output"),
        help="Output directory for results (default: data/output)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Timeout per run in seconds (default: 3600)"
    )
    
    parser.add_argument(
        "--table-type",
        choices=["simple", "detailed"],
        default="detailed",
        help="Type of LaTeX table to generate (default: detailed)"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Configuration file (YAML)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )
    
    parser.add_argument(
        "--experiment-name",
        type=str,
        help="Name for this experiment (default: benchmark_YYYYMMDD_HHMMSS)"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage metrics computation"
    )
    
    args = parser.parse_args()
    
    # Load config if provided
    config = {}
    if args.config and args.config.exists():
        config = load_config(args.config)
    
    # Create runner
    runner = FullBenchmarkRunner(
        runs=config.get("runs", args.runs),
        algorithms=config.get("algorithms", args.algorithms),
        datasets=config.get("datasets", args.datasets),
        output_dir=Path(config.get("output_dir", args.output_dir)),
        timeout=config.get("timeout", args.timeout),
        verbose=not args.quiet,
        experiment_name=args.experiment_name,
        compute_coverage=not args.no_coverage
    )
    
    # Run benchmark
    print("\n🚀 Starting full benchmark...\n")
    start_time = datetime.now()
    
    try:
        runner.run_full_benchmark()
        runner.save_results()
        latex_file = runner.generate_latex_table(args.table_type)
        runner.print_summary()
        
        # Print LaTeX table content
        print("\n📄 LaTeX Table Preview:")
        print("-" * 60)
        with open(latex_file) as f:
            print(f.read())
        print("-" * 60)
        
        elapsed = datetime.now() - start_time
        print(f"\n✅ Benchmark completed in {elapsed.total_seconds():.1f} seconds")
        print(f"   LaTeX table: {latex_file}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
