#!/usr/bin/env python3
"""
Benchmark Runner for MATILDA

This script runs MATILDA multiple times on specified datasets to collect
performance statistics (number of rules, execution time) and generates
a LaTeX table with mean and standard deviation.

Usage:
    python run_benchmark.py [--runs N] [--datasets DATASET1 DATASET2 ...] [--algorithms ALG1 ALG2 ...]
    
Examples:
    # Run 5 times on all datasets
    python run_benchmark.py --runs 5
    
    # Run 3 times on specific datasets
    python run_benchmark.py --runs 3 --datasets Bupa BupaImperfect
    
    # Run with specific algorithms
    python run_benchmark.py --runs 5 --algorithms MATILDA SPIDER
"""

import argparse
import json
import sys
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.config_loader import load_config


class BenchmarkRunner:
    """Runs multiple benchmark iterations and collects statistics."""
    
    def __init__(self, config_file: str = "config.yaml", num_runs: int = 5):
        self.config_file = Path(config_file)
        self.num_runs = num_runs
        self.results = {}
        self.config = load_config(str(self.config_file))
        
    def run_single_iteration(self, dataset: str, algorithm: str) -> Tuple[int, float, Dict[str, float]]:
        """
        Run a single iteration of the algorithm on a dataset.
        
        :param dataset: Dataset name (e.g., "Bupa")
        :param algorithm: Algorithm name (e.g., "MATILDA")
        :return: Tuple of (num_rules, total_time, time_metrics)
        """
        # Modify config for this run
        config = self.config.copy()
        config['database']['name'] = f"{dataset}.db"
        config['algorithm']['name'] = algorithm
        
        # Save temporary config
        temp_config = Path(f"temp_config_{dataset}_{algorithm}.yaml")
        import yaml
        with open(temp_config, 'w') as f:
            yaml.dump(config, f)
        
        try:
            # Run main.py with temporary config
            start_time = time.time()
            result = subprocess.run(
                [sys.executable, "src/main.py", "--config", str(temp_config)],
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # Parse results
            results_dir = Path(config.get("results", {}).get("output_dir", "data/results"))
            results_file = results_dir / f"{algorithm}_{dataset}_results.json"
            
            num_rules = 0
            if results_file.exists():
                with open(results_file, 'r') as f:
                    rules = json.load(f)
                    num_rules = len(rules)
            
            # Get time metrics
            time_metrics_file = results_dir / f"init_time_metrics_{dataset}.json"
            time_metrics = {}
            if time_metrics_file.exists():
                with open(time_metrics_file, 'r') as f:
                    time_metrics = json.load(f)
            
            return num_rules, total_time, time_metrics
            
        except subprocess.TimeoutExpired:
            print(f"⚠️  Timeout for {algorithm} on {dataset}")
            return 0, 3600.0, {}
        except Exception as e:
            print(f"✗ Error running {algorithm} on {dataset}: {e}")
            return 0, 0.0, {}
        finally:
            # Clean up temp config
            if temp_config.exists():
                temp_config.unlink()
    
    def run_benchmark(self, datasets: List[str], algorithms: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Run benchmark for all combinations of datasets and algorithms.
        
        :param datasets: List of dataset names
        :param algorithms: List of algorithm names
        :return: Dictionary with benchmark results
        """
        results = {}
        
        for algorithm in algorithms:
            results[algorithm] = {}
            
            for dataset in datasets:
                print(f"\n{'='*70}")
                print(f"Benchmarking: {algorithm} on {dataset}")
                print(f"{'='*70}")
                
                runs_data = {
                    'num_rules': [],
                    'total_time': [],
                    'time_compute_compatible': [],
                    'time_to_compute_indexed': [],
                    'time_building_cg': []
                }
                
                for run in range(1, self.num_runs + 1):
                    print(f"\nRun {run}/{self.num_runs}...", end=" ")
                    
                    num_rules, total_time, time_metrics = self.run_single_iteration(dataset, algorithm)
                    
                    runs_data['num_rules'].append(num_rules)
                    runs_data['total_time'].append(total_time)
                    
                    if time_metrics:
                        runs_data['time_compute_compatible'].append(time_metrics.get('time_compute_compatible', 0))
                        runs_data['time_to_compute_indexed'].append(time_metrics.get('time_to_compute_indexed', 0))
                        runs_data['time_building_cg'].append(time_metrics.get('time_building_cg', 0))
                    
                    print(f"✓ (Rules: {num_rules}, Time: {total_time:.2f}s)")
                
                # Calculate statistics
                stats = {}
                for key, values in runs_data.items():
                    if values and any(v > 0 for v in values):
                        stats[key] = {
                            'mean': float(np.mean(values)),
                            'std': float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                            'min': float(np.min(values)),
                            'max': float(np.max(values)),
                            'values': values
                        }
                
                results[algorithm][dataset] = stats
                
                print(f"\n📊 Statistics for {algorithm} on {dataset}:")
                print(f"  Rules: {stats['num_rules']['mean']:.1f} ± {stats['num_rules']['std']:.1f}")
                print(f"  Total Time: {stats['total_time']['mean']:.2f} ± {stats['total_time']['std']:.2f}s")
        
        self.results = results
        return results
    
    def save_results(self, output_file: Path):
        """Save benchmark results to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✓ Results saved to {output_file}")
    
    def generate_latex_table(self, output_file: Path):
        """
        Generate LaTeX table with benchmark results.
        
        :param output_file: Path to save the LaTeX table
        """
        latex_lines = []
        
        # Table header
        latex_lines.append("% LaTeX Table: Benchmark Results")
        latex_lines.append("% Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        latex_lines.append("")
        latex_lines.append("\\begin{table}[htbp]")
        latex_lines.append("\\centering")
        latex_lines.append("\\caption{Performance Comparison: Number of Rules and Execution Time}")
        latex_lines.append("\\label{tab:benchmark_results}")
        latex_lines.append("\\begin{tabular}{llrrr}")
        latex_lines.append("\\toprule")
        latex_lines.append("\\textbf{Algorithm} & \\textbf{Dataset} & \\textbf{\\#Rules} & \\textbf{Time (s)} & \\textbf{Time Building CG (s)} \\\\")
        latex_lines.append("\\midrule")
        
        # Table content
        for algorithm, datasets in sorted(self.results.items()):
            first_row = True
            for dataset, stats in sorted(datasets.items()):
                # Extract statistics
                num_rules_mean = stats.get('num_rules', {}).get('mean', 0)
                num_rules_std = stats.get('num_rules', {}).get('std', 0)
                
                time_mean = stats.get('total_time', {}).get('mean', 0)
                time_std = stats.get('total_time', {}).get('std', 0)
                
                cg_time_mean = stats.get('time_building_cg', {}).get('mean', 0)
                cg_time_std = stats.get('time_building_cg', {}).get('std', 0)
                
                # Format numbers
                if first_row:
                    algo_name = algorithm
                    first_row = False
                else:
                    algo_name = ""
                
                rules_str = f"${num_rules_mean:.0f} \\pm {num_rules_std:.1f}$" if num_rules_std > 0 else f"${num_rules_mean:.0f}$"
                time_str = f"${time_mean:.2f} \\pm {time_std:.2f}$" if time_std > 0 else f"${time_mean:.2f}$"
                cg_time_str = f"${cg_time_mean:.4f} \\pm {cg_time_std:.4f}$" if cg_time_std > 0 else f"${cg_time_mean:.4f}$"
                
                latex_lines.append(f"{algo_name} & {dataset} & {rules_str} & {time_str} & {cg_time_str} \\\\")
            
            latex_lines.append("\\midrule")
        
        # Remove last midrule and add bottomrule
        latex_lines[-1] = "\\bottomrule"
        
        # Table footer
        latex_lines.append("\\end{tabular}")
        latex_lines.append("\\end{table}")
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(latex_lines))
        
        print(f"\n✓ LaTeX table saved to {output_file}")
        
        # Also print to console
        print("\n" + "="*70)
        print("LaTeX Table:")
        print("="*70)
        print('\n'.join(latex_lines))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run benchmark experiments and generate LaTeX table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of runs per dataset/algorithm (default: 5)"
    )
    
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["Bupa", "BupaImperfect", "ComparisonDataset"],
        help="List of datasets to benchmark (default: Bupa BupaImperfect ComparisonDataset)"
    )
    
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=["MATILDA"],
        help="List of algorithms to benchmark (default: MATILDA)"
    )
    
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/output"),
        help="Directory for output files (default: data/output)"
    )
    
    parser.add_argument(
        "--no-latex",
        action="store_true",
        help="Skip LaTeX table generation"
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("MATILDA Benchmark Runner")
    print("="*70)
    print(f"Configuration:")
    print(f"  Runs per experiment: {args.runs}")
    print(f"  Datasets: {', '.join(args.datasets)}")
    print(f"  Algorithms: {', '.join(args.algorithms)}")
    print(f"  Config file: {args.config}")
    print(f"  Output directory: {args.output_dir}")
    print("="*70)
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run benchmark
    runner = BenchmarkRunner(config_file=args.config, num_runs=args.runs)
    
    try:
        results = runner.run_benchmark(args.datasets, args.algorithms)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_output = args.output_dir / f"benchmark_results_{timestamp}.json"
        runner.save_results(json_output)
        
        # Generate LaTeX table
        if not args.no_latex:
            latex_output = args.output_dir / f"benchmark_table_{timestamp}.tex"
            runner.generate_latex_table(latex_output)
        
        print("\n" + "="*70)
        print("✓ Benchmark completed successfully!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during benchmark: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
