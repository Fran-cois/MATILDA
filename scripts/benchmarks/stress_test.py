#!/usr/bin/env python3
"""
Large-scale stress test for MATILDA scalability validation.

Executes MATILDA TGD discovery on large datasets with comprehensive monitoring:
- Resource usage (CPU, memory, disk)
- Discovery metrics (rules, time, quality)
- Comparison with baselines (AMIE3, AnyBURL, etc.)
"""

import argparse
import json
import time
import sys
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
import traceback

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.utils.monitor_resources import ResourceMonitor


class StressTest:
    """Execute large-scale stress test on MATILDA."""
    
    def __init__(self, db_path: str, output_dir: str = "results/stress_test"):
        """
        Initialize stress test.
        
        :param db_path: Path to large-scale database.
        :param output_dir: Directory to save results.
        """
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = {}
        self.monitor = None
    
    def validate_database(self) -> bool:
        """
        Validate that database exists and is accessible.
        
        :return: True if valid, False otherwise.
        """
        db_file = Path(self.db_path)
        
        if not db_file.exists():
            print(f"❌ ERROR: Database not found: {self.db_path}")
            return False
        
        # Check size
        size_mb = db_file.stat().st_size / (1024 * 1024)
        print(f"✓ Database found: {self.db_path} ({size_mb:.2f} MB)")
        
        # Check tables
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            total_rows = 0
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                total_rows += count
            
            conn.close()
            
            print(f"✓ Tables: {len(tables)}")
            print(f"✓ Total tuples: {total_rows:,}")
            
            self.results['database'] = {
                'path': self.db_path,
                'size_mb': round(size_mb, 2),
                'num_tables': len(tables),
                'total_tuples': total_rows,
                'tables': tables
            }
            
            return True
        
        except Exception as e:
            print(f"❌ ERROR: Could not read database: {e}")
            return False
    
    def run_matilda(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run MATILDA TGD discovery with monitoring.
        
        :param config: MATILDA configuration (algorithm, heuristic, N, etc.).
        :return: Results dictionary.
        """
        print(f"\n{'='*70}")
        print(f"🚀 RUNNING MATILDA")
        print(f"{'='*70}")
        print(f"Algorithm:  {config.get('algorithm', 'dfs')}")
        print(f"Heuristic:  {config.get('heuristic', 'none')}")
        print(f"Max N:      {config.get('max_table', 3)}")
        print(f"Max Vars:   {config.get('max_vars', 6)}")
        print(f"Timeout:    {config.get('timeout', 'none')}")
        print(f"{'='*70}\n")
        
        # Setup monitoring
        monitoring_file = self.output_dir / f"monitoring_{config['algorithm']}.json"
        self.monitor = ResourceMonitor(str(monitoring_file), interval=2.0)
        self.monitor.attach_to_current_process()
        
        # Start monitoring in background
        import threading
        monitor_thread = threading.Thread(
            target=lambda: self.monitor.start_monitoring()
        )
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Run MATILDA
        start_time = time.time()
        
        try:
            # Import MATILDA components
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))
            from algorithms.matilda import MATILDA
            from database.alchemy_utility import AlchemyUtility
            
            # Initialize database connection
            db = AlchemyUtility(f"sqlite:///{self.db_path}")
            
            # Configure MATILDA settings
            matilda_settings = {
                'nb_occurrence': 3,
                'max_table': config.get('max_table', 3),
                'max_vars': config.get('max_vars', 6),
                'timeout': config.get('timeout', 3600)
            }
            
            # Initialize MATILDA
            matilda = MATILDA(database=db, settings=matilda_settings)
            
            # Run discovery
            rules = list(matilda.discover_rules(
                traversal_algorithm=config.get('algorithm', 'astar'),
                heuristic=config.get('heuristic', 'hybrid'),
                max_table=config.get('max_table', 3),
                max_vars=config.get('max_vars', 6)
            ))
            
            elapsed = time.time() - start_time
            
            # Calculate resource peaks from monitoring
            cpu_peak = 0
            memory_peak_mb = 0
            try:
                if self.monitor.samples:
                    cpu_peak = max(s.get('cpu_percent', 0) for s in self.monitor.samples)
                    memory_peak_mb = max(s.get('memory_rss_mb', 0) for s in self.monitor.samples)
            except Exception as monitor_err:
                print(f"Warning: Could not extract monitoring data: {monitor_err}")
                pass
            
            # Results
            result = {
                'success': True,
                'runtime_seconds': round(elapsed, 2),
                'num_rules': len(rules),
                'rules_per_second': round(len(rules) / elapsed, 2) if elapsed > 0 else 0,
                'memory_peak_mb': round(memory_peak_mb, 2),
                'cpu_avg_percent': round(cpu_peak, 2),
                'config': config,
                'monitoring_file': str(monitoring_file)
            }
            
            print(f"\n{'='*70}")
            print(f"✅ MATILDA COMPLETED")
            print(f"{'='*70}")
            print(f"Runtime:         {elapsed:.2f}s")
            print(f"Rules found:     {len(rules)}")
            print(f"Rules/second:    {len(rules)/elapsed:.2f}" if elapsed > 0 else "N/A")
            print(f"Memory peak:     {memory_peak_mb:.2f} MB")
            print(f"CPU peak:        {cpu_peak:.2f}%")
            print(f"{'='*70}")
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ MATILDA FAILED: {e}")
            traceback.print_exc()
            
            result = {
                'success': False,
                'runtime_seconds': round(elapsed, 2),
                'error': str(e),
                'traceback': traceback.format_exc(),
                'config': config
            }
        
        # Stop monitoring
        time.sleep(5)  # Allow final samples
        
        return result
    
    def run_baseline(self, baseline: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run baseline algorithm (AMIE3, AnyBURL, etc.).
        
        :param baseline: Baseline name.
        :param config: Baseline configuration.
        :return: Results dictionary.
        """
        print(f"\n{'='*70}")
        print(f"🔧 RUNNING BASELINE: {baseline.upper()}")
        print(f"{'='*70}\n")
        
        # Placeholder for baseline integration
        # In practice, you would call baseline tools here
        
        result = {
            'baseline': baseline,
            'runtime_seconds': 0,
            'num_rules': 0,
            'note': 'Baseline not yet implemented'
        }
        
        print(f"⚠️  Baseline {baseline} not yet implemented\n")
        
        return result
    
    def compare_algorithms(self, algorithms: list):
        """
        Compare multiple MATILDA algorithm configurations.
        
        :param algorithms: List of algorithm configs to test.
        """
        print(f"\n{'='*80}")
        print(f"🏁 ALGORITHM COMPARISON")
        print(f"{'='*80}")
        
        comparison_results = []
        
        for config in algorithms:
            algo_name = f"{config['algorithm']}"
            if config.get('heuristic'):
                algo_name += f"+{config['heuristic']}"
            
            print(f"\n>>> Testing: {algo_name}")
            result = self.run_matilda(config)
            result['name'] = algo_name
            comparison_results.append(result)
        
        # Save comparison
        comparison_file = self.output_dir / "algorithm_comparison.json"
        with open(comparison_file, 'w') as f:
            json.dump(comparison_results, f, indent=2)
        
        print(f"\n{'='*80}")
        print(f"📊 COMPARISON RESULTS")
        print(f"{'='*80}")
        
        # Sort by runtime
        comparison_results.sort(key=lambda x: x.get('runtime_seconds', float('inf')))
        
        print(f"\n{'Algorithm':<20} {'Time (s)':<12} {'Rules':<10} {'Rules/s':<12} {'Status':<10}")
        print("-" * 80)
        
        for result in comparison_results:
            name = result.get('name', 'unknown')
            time_s = result.get('runtime_seconds', 0)
            rules = result.get('num_rules', 0)
            rules_per_s = result.get('rules_per_second', 0)
            status = "✓" if result.get('success') else "✗"
            
            print(f"{name:<20} {time_s:<12.2f} {rules:<10} {rules_per_s:<12.2f} {status:<10}")
        
        print(f"{'='*80}\n")
        
        return comparison_results
    
    def save_results(self):
        """Save final results to JSON."""
        results_file = self.output_dir / "stress_test_results.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"✓ Results saved: {results_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Large-scale stress test for MATILDA scalability.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic stress test
  python scripts/benchmarks/stress_test.py data/large_scale/dataset_1M.db
  
  # Test specific algorithm
  python scripts/benchmarks/stress_test.py data/large_scale/dataset_5M.db --algorithm astar --heuristic hybrid
  
  # Compare algorithms
  python scripts/benchmarks/stress_test.py data/large_scale/dataset_1M.db --compare-all
  
  # With baselines
  python scripts/benchmarks/stress_test.py data/large_scale/dataset_1M.db --baselines amie3 anyburl
        """
    )
    
    parser.add_argument('database', help='Path to large-scale database')
    parser.add_argument('--output', '-o', default='results/stress_test',
                       help='Output directory (default: results/stress_test)')
    parser.add_argument('--algorithm', default='astar',
                       choices=['dfs', 'bfs', 'astar'],
                       help='MATILDA algorithm (default: astar)')
    parser.add_argument('--heuristic', default='hybrid',
                       choices=['naive', 'table_size', 'join_selectivity', 'hybrid'],
                       help='A-star heuristic (default: hybrid)')
    parser.add_argument('--max-table', '-N', type=int, default=3,
                       help='Max N parameter (default: 3)')
    parser.add_argument('--max-vars', type=int, default=6,
                       help='Max variables (default: 6)')
    parser.add_argument('--timeout', type=int,
                       help='Timeout in seconds')
    parser.add_argument('--compare-all', action='store_true',
                       help='Compare all algorithm configurations')
    parser.add_argument('--baselines', nargs='+',
                       choices=['amie3', 'anyburl', 'popper', 'spider'],
                       help='Run baselines for comparison')
    
    args = parser.parse_args()
    
    # Initialize stress test
    test = StressTest(args.database, args.output)
    
    # Validate database
    if not test.validate_database():
        return 1
    
    # Run tests
    if args.compare_all:
        # Compare all configurations
        algorithms = [
            {'algorithm': 'dfs', 'max_table': args.max_table, 'max_vars': args.max_vars},
            {'algorithm': 'bfs', 'max_table': args.max_table, 'max_vars': args.max_vars},
            {'algorithm': 'astar', 'heuristic': 'naive', 'max_table': args.max_table, 'max_vars': args.max_vars},
            {'algorithm': 'astar', 'heuristic': 'table_size', 'max_table': args.max_table, 'max_vars': args.max_vars},
            {'algorithm': 'astar', 'heuristic': 'join_selectivity', 'max_table': args.max_table, 'max_vars': args.max_vars},
            {'algorithm': 'astar', 'heuristic': 'hybrid', 'max_table': args.max_table, 'max_vars': args.max_vars},
        ]
        
        test.results['comparison'] = test.compare_algorithms(algorithms)
    
    else:
        # Single run
        config = {
            'algorithm': args.algorithm,
            'heuristic': args.heuristic if args.algorithm == 'astar' else None,
            'max_table': args.max_table,
            'max_vars': args.max_vars,
            'timeout': args.timeout
        }
        
        test.results['matilda'] = test.run_matilda(config)
    
    # Run baselines
    if args.baselines:
        test.results['baselines'] = {}
        for baseline in args.baselines:
            test.results['baselines'][baseline] = test.run_baseline(baseline, {})
    
    # Save results
    test.save_results()
    
    print("\n✅ Stress test complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
