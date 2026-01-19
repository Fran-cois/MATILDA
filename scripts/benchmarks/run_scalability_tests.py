#!/usr/bin/env python3
"""
Run complete scalability stress tests for MATILDA.

This orchestrator script:
1. Generates required datasets (1M, 5M, 10M tuples)
2. Runs stress tests with optimal configuration
3. Collects and aggregates results
4. Generates comparison graphs and reports
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class ScalabilityTestRunner:
    """Orchestrate complete scalability testing suite."""
    
    def __init__(self, output_dir: str = "results/scalability"):
        """
        Initialize test runner.
        
        :param output_dir: Directory for all results.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.root_dir = Path(__file__).parent.parent.parent
        self.data_dir = self.root_dir / "data" / "large_scale"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Test configurations
        self.dataset_sizes = [
            ("1M", 1_000_000),
            ("5M", 5_000_000),
            ("10M", 10_000_000)
        ]
        
        # Optimal configuration from Phase 2
        self.optimal_config = {
            'algorithm': 'astar',
            'heuristic': 'hybrid',
            'max_table': 3,
            'max_vars': 6,
            'timeout': 3600  # 1 hour max per test
        }
        
        self.results = {}
    
    def print_header(self, text: str):
        """Print formatted header."""
        print(f"\n{'='*80}")
        print(f"  {text}")
        print(f"{'='*80}\n")
    
    def print_info(self, text: str):
        """Print info message."""
        print(f"ℹ️  {text}")
    
    def print_success(self, text: str):
        """Print success message."""
        print(f"✅ {text}")
    
    def print_error(self, text: str):
        """Print error message."""
        print(f"❌ {text}")
    
    def generate_dataset(self, label: str, num_tuples: int) -> Path:
        """
        Generate dataset if it doesn't exist.
        
        :param label: Size label (e.g., "1M")
        :param num_tuples: Number of tuples to generate
        :return: Path to dataset
        """
        dataset_path = self.data_dir / f"dataset_{label}.db"
        
        if dataset_path.exists():
            self.print_success(f"Dataset {label} already exists: {dataset_path}")
            return dataset_path
        
        self.print_info(f"Generating dataset {label} ({num_tuples:,} tuples)...")
        
        gen_script = self.root_dir / "scripts" / "utils" / "generate_large_dataset.py"
        
        cmd = [
            sys.executable,
            str(gen_script),
            str(dataset_path),
            '--tuples', str(num_tuples),
            '--tables', '5',
            '--columns', '5',
            '--seed', '42'
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.root_dir)
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            self.print_success(f"Dataset {label} generated in {elapsed:.2f}s")
            return dataset_path
        else:
            self.print_error(f"Failed to generate dataset {label}")
            return None
    
    def run_stress_test(self, dataset_path: Path, label: str) -> Dict[str, Any]:
        """
        Run stress test on dataset.
        
        :param dataset_path: Path to dataset
        :param label: Size label
        :return: Results dictionary
        """
        self.print_info(f"Running stress test on {label} dataset...")
        
        stress_script = self.root_dir / "scripts" / "benchmarks" / "stress_test.py"
        output_subdir = self.output_dir / f"stress_{label}"
        
        cmd = [
            sys.executable,
            str(stress_script),
            str(dataset_path),
            '--output', str(output_subdir),
            '--algorithm', self.optimal_config['algorithm'],
            '--heuristic', self.optimal_config['heuristic'],
            '--max-table', str(self.optimal_config['max_table']),
            '--max-vars', str(self.optimal_config['max_vars']),
            '--timeout', str(self.optimal_config['timeout'])
        ]
        
        # Set PYTHONPATH to include project root
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.root_dir)
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True, env=env)
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            self.print_success(f"Stress test {label} completed in {elapsed:.2f}s")
            
            # Load results
            results_file = output_subdir / "stress_test_results.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    return json.load(f)
            else:
                return {'success': True, 'elapsed': elapsed}
        else:
            self.print_error(f"Stress test {label} failed")
            print(result.stderr)
            return {'success': False, 'error': result.stderr}
    
    def aggregate_results(self):
        """Aggregate all results into summary."""
        self.print_header("AGGREGATING RESULTS")
        
        summary = {
            'test_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'configuration': self.optimal_config,
            'datasets': {},
            'scalability_metrics': {}
        }
        
        # Collect results for each dataset
        for label, num_tuples in self.dataset_sizes:
            result_dir = self.output_dir / f"stress_{label}"
            result_file = result_dir / "stress_test_results.json"
            
            if result_file.exists():
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    summary['datasets'][label] = {
                        'num_tuples': num_tuples,
                        'results': data
                    }
        
        # Calculate scalability metrics
        if len(summary['datasets']) >= 2:
            sizes = sorted(summary['datasets'].keys(), 
                          key=lambda x: summary['datasets'][x]['num_tuples'])
            
            runtimes = []
            tuple_counts = []
            
            for size in sizes:
                data = summary['datasets'][size]
                if 'matilda' in data['results']:
                    runtime = data['results']['matilda'].get('runtime_seconds', 0)
                    runtimes.append(runtime)
                    tuple_counts.append(data['num_tuples'])
            
            if len(runtimes) >= 2:
                # Calculate scaling factor
                scaling_factors = []
                for i in range(1, len(runtimes)):
                    size_ratio = tuple_counts[i] / tuple_counts[i-1]
                    time_ratio = runtimes[i] / runtimes[i-1] if runtimes[i-1] > 0 else 0
                    scaling_factors.append(time_ratio / size_ratio)
                
                avg_scaling = sum(scaling_factors) / len(scaling_factors)
                
                summary['scalability_metrics'] = {
                    'sizes': sizes,
                    'runtimes': runtimes,
                    'tuple_counts': tuple_counts,
                    'scaling_factors': scaling_factors,
                    'avg_scaling_factor': avg_scaling,
                    'interpretation': (
                        'sub-linear' if avg_scaling < 0.8 else
                        'linear' if avg_scaling < 1.2 else
                        'super-linear'
                    )
                }
        
        # Save summary
        summary_file = self.output_dir / "scalability_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.print_success(f"Results aggregated: {summary_file}")
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print human-readable summary."""
        self.print_header("SCALABILITY TEST RESULTS")
        
        print(f"Configuration: {summary['configuration']['algorithm']} + "
              f"{summary['configuration']['heuristic']}, N={summary['configuration']['max_table']}")
        print()
        
        # Results table
        print(f"{'Dataset':<10} {'Tuples':<15} {'Runtime':<12} {'Rules':<10} {'Rules/s':<12}")
        print("-" * 70)
        
        for label in sorted(summary['datasets'].keys(), 
                           key=lambda x: summary['datasets'][x]['num_tuples']):
            data = summary['datasets'][label]
            tuples = f"{data['num_tuples']:,}"
            
            if 'matilda' in data['results']:
                result = data['results']['matilda']
                runtime = result.get('runtime_seconds', 0)
                rules = result.get('num_rules', 0)
                rules_per_s = result.get('rules_per_second', 0)
                
                print(f"{label:<10} {tuples:<15} {runtime:<12.2f} {rules:<10} {rules_per_s:<12.2f}")
        
        print()
        
        # Scalability metrics
        if 'scalability_metrics' in summary and summary['scalability_metrics']:
            metrics = summary['scalability_metrics']
            print(f"Scalability Factor: {metrics['avg_scaling_factor']:.2f} "
                  f"({metrics['interpretation']})")
            print()
            print("Interpretation:")
            print("  < 1.0 = Sub-linear (excellent scaling)")
            print("  ≈ 1.0 = Linear (good scaling)")
            print("  > 1.0 = Super-linear (poor scaling)")
        
        print()
    
    def run_all_tests(self, skip_generation: bool = False):
        """
        Run complete scalability test suite.
        
        :param skip_generation: Skip dataset generation if datasets exist
        """
        self.print_header("SCALABILITY STRESS TEST SUITE")
        
        print(f"Output directory: {self.output_dir}")
        print(f"Optimal config: {self.optimal_config}")
        print()
        
        # Phase 1: Generate datasets
        if not skip_generation:
            self.print_header("PHASE 1: DATASET GENERATION")
            
            for label, num_tuples in self.dataset_sizes:
                dataset_path = self.generate_dataset(label, num_tuples)
                if not dataset_path:
                    self.print_error(f"Cannot proceed without dataset {label}")
                    return 1
        
        # Phase 2: Run stress tests
        self.print_header("PHASE 2: STRESS TESTING")
        
        for label, num_tuples in self.dataset_sizes:
            dataset_path = self.data_dir / f"dataset_{label}.db"
            
            if not dataset_path.exists():
                self.print_error(f"Dataset {label} not found: {dataset_path}")
                continue
            
            result = self.run_stress_test(dataset_path, label)
            self.results[label] = result
        
        # Phase 3: Aggregate and analyze
        self.print_header("PHASE 3: AGGREGATION & ANALYSIS")
        
        summary = self.aggregate_results()
        self.print_summary(summary)
        
        # Phase 4: Generate visualizations (if script exists)
        self.print_header("PHASE 4: VISUALIZATIONS")
        
        # PNG graphs
        viz_script = self.root_dir / "scripts" / "utils" / "visualize_scalability.py"
        if viz_script.exists():
            self.print_info("Generating PNG graphs...")
            cmd = [
                sys.executable,
                str(viz_script),
                str(self.output_dir / "scalability_summary.json"),
                '--output-dir', str(self.output_dir)
            ]
            result = subprocess.run(cmd, cwd=self.root_dir)
            if result.returncode == 0:
                self.print_success("PNG visualizations generated")
        else:
            self.print_info("PNG visualization script not found")
        
        # TikZ/LaTeX graphs
        tikz_script = self.root_dir / "scripts" / "utils" / "generate_tikz_scalability.py"
        if tikz_script.exists():
            self.print_info("Generating TikZ/LaTeX figures...")
            cmd = [
                sys.executable,
                str(tikz_script),
                str(self.output_dir / "scalability_summary.json"),
                '--output-dir', str(self.output_dir)
            ]
            result = subprocess.run(cmd, cwd=self.root_dir)
            if result.returncode == 0:
                self.print_success("TikZ/LaTeX figures generated")
        else:
            self.print_info("TikZ generation script not found")
        
        self.print_header("SCALABILITY TESTS COMPLETE")
        print(f"\nResults saved to: {self.output_dir}")
        
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='Run complete scalability stress tests for MATILDA.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full suite (generate + test)
  python scripts/benchmarks/run_scalability_tests.py
  
  # Skip generation if datasets exist
  python scripts/benchmarks/run_scalability_tests.py --skip-generation
  
  # Custom output directory
  python scripts/benchmarks/run_scalability_tests.py --output results/my_tests
        """
    )
    
    parser.add_argument('--output', '-o', default='results/scalability',
                       help='Output directory (default: results/scalability)')
    parser.add_argument('--skip-generation', action='store_true',
                       help='Skip dataset generation if datasets already exist')
    
    args = parser.parse_args()
    
    runner = ScalabilityTestRunner(args.output)
    return runner.run_all_tests(skip_generation=args.skip_generation)


if __name__ == '__main__':
    sys.exit(main())
