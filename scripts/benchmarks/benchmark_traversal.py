#!/usr/bin/env python3
"""
Benchmark script to compare traversal algorithms and heuristics in MATILDA.

This script compares:
1. Naive DFS (baseline)
2. BFS
3. A-star with different heuristics (naive, table_size, join_selectivity, hybrid)

Metrics measured:
- Total runtime
- Number of rules discovered
- Time to first rule
- Memory usage
- Rules per second
"""

import argparse
import json
import time
import tracemalloc
from pathlib import Path
from typing import Dict, List, Any
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility
from heuristics.path_search import create_heuristic


def benchmark_algorithm(db_path: str, algorithm: str, heuristic: str = None, 
                       max_table: int = 3, max_vars: int = 6,
                       max_rules: int = None, timeout: int = 300) -> Dict[str, Any]:
    """
    Benchmark a single algorithm configuration.
    
    :param db_path: Path to database file.
    :param algorithm: Algorithm name ('dfs', 'bfs', 'astar').
    :param heuristic: Heuristic name for A-star (None for dfs/bfs).
    :param max_table: Maximum number of tables per rule.
    :param max_vars: Maximum number of variables per rule.
    :param max_rules: Maximum number of rules to discover (None = unlimited).
    :param timeout: Maximum time in seconds (None = no timeout).
    :return: Dictionary with benchmark results.
    """
    print(f"\n{'='*60}")
    print(f"Benchmarking: {algorithm.upper()}" + (f" with {heuristic} heuristic" if heuristic else ""))
    print(f"{'='*60}")
    
    # Initialize database
    db_uri = f"sqlite:///{db_path}"
    db = AlchemyUtility(db_uri)
    
    # Initialize MATILDA
    matilda = MATILDA(db)
    
    # Start monitoring
    tracemalloc.start()
    start_time = time.time()
    first_rule_time = None
    rules_discovered = []
    
    try:
        # Configure discovery parameters
        kwargs = {
            'traversal_algorithm': algorithm,
            'max_table': max_table,
            'max_vars': max_vars,
        }
        
        # Add heuristic for A-star
        if algorithm == 'astar' and heuristic:
            from algorithms.MATILDA.tgd_discovery import init
            cg, mapper, _ = init(db, max_nb_occurrence=1)
            heuristic_func = create_heuristic(db, mapper, heuristic)
            kwargs['heuristic_func'] = heuristic_func
        
        # Discover rules
        rule_count = 0
        for rule in matilda.discover_rules(**kwargs):
            if first_rule_time is None:
                first_rule_time = time.time() - start_time
            
            rules_discovered.append({
                'rule': str(rule),
                'confidence': getattr(rule, 'confidence', None),
                'support': getattr(rule, 'support', None),
            })
            rule_count += 1
            
            # Check limits
            if max_rules and rule_count >= max_rules:
                print(f"Reached max rules limit ({max_rules})")
                break
            
            if timeout and (time.time() - start_time) > timeout:
                print(f"Reached timeout ({timeout}s)")
                break
            
            # Progress update
            if rule_count % 10 == 0:
                elapsed = time.time() - start_time
                print(f"  Rules: {rule_count}, Time: {elapsed:.2f}s, Rate: {rule_count/elapsed:.2f} rules/s")
    
    except Exception as e:
        print(f"ERROR during discovery: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Collect metrics
        end_time = time.time()
        total_time = end_time - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        results = {
            'algorithm': algorithm,
            'heuristic': heuristic,
            'config': {
                'max_table': max_table,
                'max_vars': max_vars,
                'max_rules': max_rules,
                'timeout': timeout,
            },
            'metrics': {
                'total_time_seconds': round(total_time, 3),
                'time_to_first_rule_seconds': round(first_rule_time, 3) if first_rule_time else None,
                'total_rules_discovered': len(rules_discovered),
                'rules_per_second': round(len(rules_discovered) / total_time, 3) if total_time > 0 else 0,
                'peak_memory_mb': round(peak / (1024 * 1024), 2),
                'current_memory_mb': round(current / (1024 * 1024), 2),
            },
            'rules': rules_discovered[:10],  # Save first 10 rules as examples
        }
        
        print(f"\nResults:")
        print(f"  Total Time: {results['metrics']['total_time_seconds']}s")
        print(f"  Rules Discovered: {results['metrics']['total_rules_discovered']}")
        print(f"  Rules/Second: {results['metrics']['rules_per_second']}")
        print(f"  Peak Memory: {results['metrics']['peak_memory_mb']} MB")
        if first_rule_time:
            print(f"  Time to First Rule: {results['metrics']['time_to_first_rule_seconds']}s")
        
        return results


def run_benchmark_suite(db_path: str, output_dir: str = 'results/benchmarks',
                       max_table: int = 3, max_vars: int = 6,
                       max_rules: int = 50, timeout: int = 300):
    """
    Run a complete benchmark suite comparing all algorithms.
    
    :param db_path: Path to database file.
    :param output_dir: Directory to save results.
    :param max_table: Maximum number of tables per rule.
    :param max_vars: Maximum number of variables per rule.
    :param max_rules: Maximum number of rules to discover per algorithm.
    :param timeout: Maximum time in seconds per algorithm.
    """
    print("\n" + "="*80)
    print("MATILDA BENCHMARK SUITE - Traversal Algorithms Comparison")
    print("="*80)
    print(f"Database: {db_path}")
    print(f"Config: max_table={max_table}, max_vars={max_vars}")
    print(f"Limits: max_rules={max_rules}, timeout={timeout}s")
    print("="*80)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Define benchmark configurations
    configs = [
        ('dfs', None, 'Depth-First Search (baseline)'),
        ('bfs', None, 'Breadth-First Search'),
        ('astar', 'naive', 'A-star with Naive Heuristic'),
        ('astar', 'table_size', 'A-star with Table Size Heuristic'),
        ('astar', 'join_selectivity', 'A-star with Join Selectivity Heuristic'),
        ('astar', 'hybrid', 'A-star with Hybrid Heuristic'),
    ]
    
    all_results = []
    
    # Run each configuration
    for i, (algo, heur, desc) in enumerate(configs, 1):
        print(f"\n[{i}/{len(configs)}] {desc}")
        
        try:
            result = benchmark_algorithm(
                db_path=db_path,
                algorithm=algo,
                heuristic=heur,
                max_table=max_table,
                max_vars=max_vars,
                max_rules=max_rules,
                timeout=timeout
            )
            all_results.append(result)
        
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
            all_results.append({
                'algorithm': algo,
                'heuristic': heur,
                'error': str(e),
            })
    
    # Save results
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'traversal_benchmark_{timestamp}.json')
    
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Benchmark complete! Results saved to: {output_file}")
    print(f"{'='*80}")
    
    # Print summary comparison
    print_comparison_table(all_results)
    
    return all_results


def print_comparison_table(results: List[Dict[str, Any]]):
    """Print a comparison table of all benchmark results."""
    print("\n" + "="*100)
    print("COMPARISON TABLE")
    print("="*100)
    
    # Header
    print(f"{'Algorithm':<25} {'Rules':<8} {'Time (s)':<10} {'Rules/s':<10} {'Memory (MB)':<12} {'First Rule (s)':<15}")
    print("-" * 100)
    
    # Data rows
    for result in results:
        if 'error' in result:
            algo_name = f"{result['algorithm']}" + (f" ({result['heuristic']})" if result['heuristic'] else "")
            print(f"{algo_name:<25} {'ERROR':<8} {'-':<10} {'-':<10} {'-':<12} {'-':<15}")
            continue
        
        algo_name = result['algorithm']
        if result['heuristic']:
            algo_name += f" ({result['heuristic']})"
        
        metrics = result['metrics']
        print(f"{algo_name:<25} "
              f"{metrics['total_rules_discovered']:<8} "
              f"{metrics['total_time_seconds']:<10.2f} "
              f"{metrics['rules_per_second']:<10.3f} "
              f"{metrics['peak_memory_mb']:<12.2f} "
              f"{metrics['time_to_first_rule_seconds'] if metrics['time_to_first_rule_seconds'] else 'N/A':<15}")
    
    print("="*100)
    
    # Find best performers
    valid_results = [r for r in results if 'error' not in r]
    if valid_results:
        fastest = min(valid_results, key=lambda r: r['metrics']['total_time_seconds'])
        most_rules = max(valid_results, key=lambda r: r['metrics']['total_rules_discovered'])
        fastest_first = min(
            [r for r in valid_results if r['metrics']['time_to_first_rule_seconds']],
            key=lambda r: r['metrics']['time_to_first_rule_seconds'],
            default=None
        )
        
        print("\nBEST PERFORMERS:")
        print(f"  ⚡ Fastest Total Time: {fastest['algorithm']}" + 
              (f" ({fastest['heuristic']})" if fastest['heuristic'] else "") +
              f" - {fastest['metrics']['total_time_seconds']:.2f}s")
        print(f"  📊 Most Rules: {most_rules['algorithm']}" + 
              (f" ({most_rules['heuristic']})" if most_rules['heuristic'] else "") +
              f" - {most_rules['metrics']['total_rules_discovered']} rules")
        if fastest_first:
            print(f"  🎯 Fastest First Rule: {fastest_first['algorithm']}" + 
                  (f" ({fastest_first['heuristic']})" if fastest_first['heuristic'] else "") +
                  f" - {fastest_first['metrics']['time_to_first_rule_seconds']:.2f}s")
        print("="*100)


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark MATILDA traversal algorithms and heuristics.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full benchmark suite on Bupa database
  python scripts/benchmarks/benchmark_traversal.py data/db/BupaImperfect.db
  
  # Quick benchmark with limits
  python scripts/benchmarks/benchmark_traversal.py data/db/BupaImperfect.db --max-rules 20 --timeout 60
  
  # Benchmark single algorithm
  python scripts/benchmarks/benchmark_traversal.py data/db/BupaImperfect.db --algorithm astar --heuristic hybrid
        """
    )
    
    parser.add_argument('database', help='Path to SQLite database file')
    parser.add_argument('--output-dir', default='results/benchmarks', 
                       help='Output directory for results (default: results/benchmarks)')
    parser.add_argument('--max-table', type=int, default=3,
                       help='Maximum tables per rule (default: 3)')
    parser.add_argument('--max-vars', type=int, default=6,
                       help='Maximum variables per rule (default: 6)')
    parser.add_argument('--max-rules', type=int, default=50,
                       help='Maximum rules to discover per algorithm (default: 50)')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Timeout in seconds per algorithm (default: 300)')
    parser.add_argument('--algorithm', choices=['dfs', 'bfs', 'astar'],
                       help='Run only specific algorithm (default: all)')
    parser.add_argument('--heuristic', choices=['naive', 'table_size', 'join_selectivity', 'hybrid'],
                       help='Heuristic for A-star (only with --algorithm astar)')
    
    args = parser.parse_args()
    
    # Validate database path
    if not os.path.exists(args.database):
        print(f"ERROR: Database file not found: {args.database}")
        return 1
    
    # Run benchmark
    if args.algorithm:
        # Single algorithm benchmark
        result = benchmark_algorithm(
            db_path=args.database,
            algorithm=args.algorithm,
            heuristic=args.heuristic,
            max_table=args.max_table,
            max_vars=args.max_vars,
            max_rules=args.max_rules,
            timeout=args.timeout
        )
        
        # Save result
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(
            args.output_dir, 
            f'{args.algorithm}_{args.heuristic or "default"}_{timestamp}.json'
        )
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    else:
        # Full benchmark suite
        run_benchmark_suite(
            db_path=args.database,
            output_dir=args.output_dir,
            max_table=args.max_table,
            max_vars=args.max_vars,
            max_rules=args.max_rules,
            timeout=args.timeout
        )
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
