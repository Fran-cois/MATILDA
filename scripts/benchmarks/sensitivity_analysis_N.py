#!/usr/bin/env python3
"""
Sensitivity Analysis for N Parameter (max_table) in MATILDA.

This script analyzes how the N parameter (maximum number of tables per rule)
affects:
1. Discovery time (runtime)
2. Number of rules discovered
3. Quality of rules (confidence, support)
4. Pattern coverage

Tests different values of N and compares algorithms (DFS baseline vs A-star optimized).
"""

import argparse
import json
import time
import tracemalloc
from pathlib import Path
from typing import Dict, List, Any, Tuple
import sys
import os
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility
from heuristics.path_search import create_heuristic


def run_discovery_with_N(db_path: str, N: int, algorithm: str = 'dfs',
                         heuristic: str = None, max_vars: int = 6,
                         timeout: int = 600) -> Dict[str, Any]:
    """
    Run rule discovery with specific N parameter.
    
    :param db_path: Path to database.
    :param N: Maximum number of tables per rule.
    :param algorithm: Traversal algorithm ('dfs', 'bfs', 'astar').
    :param heuristic: Heuristic for A-star.
    :param max_vars: Maximum variables per rule.
    :param timeout: Timeout in seconds.
    :return: Dictionary with results.
    """
    print(f"  Running with N={N}, algorithm={algorithm}" + 
          (f", heuristic={heuristic}" if heuristic else ""))
    
    # Initialize database
    db_uri = f"sqlite:///{db_path}"
    db = AlchemyUtility(db_uri)
    
    # Initialize MATILDA
    matilda = MATILDA(db)
    
    # Start monitoring
    tracemalloc.start()
    start_time = time.time()
    
    rules_data = []
    rule_count = 0
    first_rule_time = None
    
    try:
        # Configure discovery
        kwargs = {
            'traversal_algorithm': algorithm,
            'max_table': N,
            'max_vars': max_vars,
        }
        
        # Add heuristic for A-star
        if algorithm == 'astar' and heuristic:
            from algorithms.MATILDA.tgd_discovery import init
            cg, mapper, _ = init(db, max_nb_occurrence=1)
            heuristic_func = create_heuristic(db, mapper, heuristic)
            kwargs['heuristic_func'] = heuristic_func
        
        # Discover rules
        for rule in matilda.discover_rules(**kwargs):
            if first_rule_time is None:
                first_rule_time = time.time() - start_time
            
            # Extract rule metrics
            rules_data.append({
                'rule': str(rule),
                'confidence': getattr(rule, 'confidence', None),
                'support': getattr(rule, 'support', None),
                'num_tables': len(set(str(atom.predicate) for atom in rule.body)),
            })
            rule_count += 1
            
            # Check timeout
            if (time.time() - start_time) > timeout:
                print(f"    Timeout reached at {rule_count} rules")
                break
            
            # Progress
            if rule_count % 20 == 0:
                elapsed = time.time() - start_time
                print(f"    Rules: {rule_count}, Time: {elapsed:.1f}s")
    
    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        end_time = time.time()
        total_time = end_time - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Calculate statistics
        confidences = [r['confidence'] for r in rules_data if r['confidence'] is not None]
        supports = [r['support'] for r in rules_data if r['support'] is not None]
        
        # Count rules by number of tables
        rules_by_tables = defaultdict(int)
        for r in rules_data:
            rules_by_tables[r['num_tables']] += 1
        
        results = {
            'N': N,
            'algorithm': algorithm,
            'heuristic': heuristic,
            'config': {
                'max_table': N,
                'max_vars': max_vars,
                'timeout': timeout,
            },
            'metrics': {
                'total_time_seconds': round(total_time, 3),
                'time_to_first_rule_seconds': round(first_rule_time, 3) if first_rule_time else None,
                'total_rules_discovered': len(rules_data),
                'rules_per_second': round(len(rules_data) / total_time, 3) if total_time > 0 else 0,
                'peak_memory_mb': round(peak / (1024 * 1024), 2),
                'avg_confidence': round(sum(confidences) / len(confidences), 4) if confidences else None,
                'avg_support': round(sum(supports) / len(supports), 4) if supports else None,
                'rules_by_num_tables': dict(rules_by_tables),
            },
            'sample_rules': rules_data[:5],  # Save first 5 as examples
        }
        
        print(f"    ✓ N={N}: {results['metrics']['total_rules_discovered']} rules in "
              f"{results['metrics']['total_time_seconds']}s "
              f"(avg conf={results['metrics']['avg_confidence']})")
        
        return results


def run_sensitivity_analysis(db_path: str, 
                            N_values: List[int] = None,
                            algorithms: List[Tuple[str, str]] = None,
                            output_dir: str = 'results/sensitivity_analysis',
                            max_vars: int = 6,
                            timeout: int = 600):
    """
    Run complete sensitivity analysis for N parameter.
    
    :param db_path: Path to database.
    :param N_values: List of N values to test.
    :param algorithms: List of (algorithm, heuristic) tuples to test.
    :param output_dir: Output directory for results.
    :param max_vars: Maximum variables per rule.
    :param timeout: Timeout per run in seconds.
    """
    print("\n" + "="*80)
    print("🔬 SENSITIVITY ANALYSIS - N Parameter (max_table)")
    print("="*80)
    print(f"Database: {db_path}")
    print(f"N values: {N_values}")
    print(f"Algorithms: {algorithms}")
    print(f"Timeout per run: {timeout}s")
    print("="*80 + "\n")
    
    # Default values
    if N_values is None:
        N_values = [1, 2, 3, 4, 5]
    
    if algorithms is None:
        algorithms = [
            ('dfs', None),  # Baseline
            ('astar', 'hybrid'),  # Optimized
        ]
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    all_results = []
    total_runs = len(N_values) * len(algorithms)
    current_run = 0
    
    # Run experiments
    for algo, heur in algorithms:
        algo_name = algo + (f"_{heur}" if heur else "")
        print(f"\n{'='*80}")
        print(f"Testing Algorithm: {algo_name.upper()}")
        print(f"{'='*80}")
        
        for N in N_values:
            current_run += 1
            print(f"\n[{current_run}/{total_runs}] N={N}")
            
            try:
                result = run_discovery_with_N(
                    db_path=db_path,
                    N=N,
                    algorithm=algo,
                    heuristic=heur,
                    max_vars=max_vars,
                    timeout=timeout
                )
                all_results.append(result)
            
            except Exception as e:
                print(f"  FAILED: {e}")
                all_results.append({
                    'N': N,
                    'algorithm': algo,
                    'heuristic': heur,
                    'error': str(e),
                })
    
    # Save results
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'sensitivity_N_{timestamp}.json')
    
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"✅ Analysis complete! Results saved to: {output_file}")
    print(f"{'='*80}")
    
    # Print summary
    print_summary_tables(all_results, algorithms)
    
    # Generate recommendations
    print_recommendations(all_results)
    
    return all_results, output_file


def print_summary_tables(results: List[Dict[str, Any]], algorithms: List[Tuple[str, str]]):
    """Print summary tables for each algorithm."""
    print("\n" + "="*80)
    print("📊 SUMMARY TABLES")
    print("="*80)
    
    for algo, heur in algorithms:
        algo_name = algo + (f" ({heur})" if heur else "")
        algo_results = [r for r in results if r['algorithm'] == algo and 
                       r.get('heuristic') == heur and 'error' not in r]
        
        if not algo_results:
            continue
        
        print(f"\n{algo_name.upper()}")
        print("-" * 80)
        print(f"{'N':<5} {'Rules':<8} {'Time(s)':<10} {'Rules/s':<10} "
              f"{'Avg Conf':<12} {'Avg Supp':<12} {'Memory(MB)':<12}")
        print("-" * 80)
        
        for r in sorted(algo_results, key=lambda x: x['N']):
            m = r['metrics']
            print(f"{r['N']:<5} "
                  f"{m['total_rules_discovered']:<8} "
                  f"{m['total_time_seconds']:<10.2f} "
                  f"{m['rules_per_second']:<10.3f} "
                  f"{m['avg_confidence'] if m['avg_confidence'] else 'N/A':<12} "
                  f"{m['avg_support'] if m['avg_support'] else 'N/A':<12} "
                  f"{m['peak_memory_mb']:<12.2f}")
        print()


def print_recommendations(results: List[Dict[str, Any]]):
    """Analyze results and print recommendations."""
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)
    
    valid_results = [r for r in results if 'error' not in r]
    
    if not valid_results:
        print("No valid results to analyze.")
        return
    
    # Find optimal N for different criteria
    best_time = min(valid_results, key=lambda r: r['metrics']['total_time_seconds'])
    best_rules = max(valid_results, key=lambda r: r['metrics']['total_rules_discovered'])
    
    quality_results = [r for r in valid_results if r['metrics']['avg_confidence']]
    best_quality = max(quality_results, key=lambda r: r['metrics']['avg_confidence']) if quality_results else None
    
    print(f"\n⚡ Fastest Discovery:")
    print(f"   N={best_time['N']}, {best_time['algorithm']}" + 
          (f" ({best_time['heuristic']})" if best_time['heuristic'] else ""))
    print(f"   Time: {best_time['metrics']['total_time_seconds']:.2f}s")
    
    print(f"\n📊 Most Rules:")
    print(f"   N={best_rules['N']}, {best_rules['algorithm']}" + 
          (f" ({best_rules['heuristic']})" if best_rules['heuristic'] else ""))
    print(f"   Rules: {best_rules['metrics']['total_rules_discovered']}")
    
    if best_quality:
        print(f"\n⭐ Best Quality:")
        print(f"   N={best_quality['N']}, {best_quality['algorithm']}" + 
              (f" ({best_quality['heuristic']})" if best_quality['heuristic'] else ""))
        print(f"   Avg Confidence: {best_quality['metrics']['avg_confidence']:.4f}")
    
    # Find sweet spot (balance)
    print(f"\n🎯 Recommended Configuration:")
    # N=3 is often a good balance for TGD discovery
    n3_results = [r for r in valid_results if r['N'] == 3]
    if n3_results:
        best_n3 = max(n3_results, key=lambda r: r['metrics']['total_rules_discovered'])
        print(f"   N=3 (balanced complexity)")
        print(f"   Algorithm: {best_n3['algorithm']}" + 
              (f" with {best_n3['heuristic']} heuristic" if best_n3['heuristic'] else ""))
        print(f"   Expected: ~{best_n3['metrics']['total_rules_discovered']} rules " +
              f"in ~{best_n3['metrics']['total_time_seconds']:.1f}s")
    
    print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Sensitivity Analysis for N parameter in MATILDA.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full analysis N=1 to N=5
  python scripts/benchmarks/sensitivity_analysis_N.py data/db/BupaImperfect.db
  
  # Quick test N=1,2,3
  python scripts/benchmarks/sensitivity_analysis_N.py data/db/BupaImperfect.db --quick
  
  # Extended analysis N=1 to N=8
  python scripts/benchmarks/sensitivity_analysis_N.py data/db/BupaImperfect.db \
    --n-min 1 --n-max 8
  
  # Compare more algorithms
  python scripts/benchmarks/sensitivity_analysis_N.py data/db/BupaImperfect.db \
    --algorithms dfs bfs astar
        """
    )
    
    parser.add_argument('database', help='Path to SQLite database file')
    parser.add_argument('--quick', action='store_true',
                       help='Quick test (N=1,2,3, 120s timeout)')
    parser.add_argument('--n-min', type=int, default=1,
                       help='Minimum N value (default: 1)')
    parser.add_argument('--n-max', type=int, default=5,
                       help='Maximum N value (default: 5)')
    parser.add_argument('--algorithms', nargs='+', 
                       choices=['dfs', 'bfs', 'astar'],
                       default=['dfs', 'astar'],
                       help='Algorithms to test (default: dfs astar)')
    parser.add_argument('--heuristic', default='hybrid',
                       choices=['naive', 'table_size', 'join_selectivity', 'hybrid'],
                       help='Heuristic for A-star (default: hybrid)')
    parser.add_argument('--max-vars', type=int, default=6,
                       help='Maximum variables per rule (default: 6)')
    parser.add_argument('--timeout', type=int, default=600,
                       help='Timeout per run in seconds (default: 600)')
    parser.add_argument('--output-dir', default='results/sensitivity_analysis',
                       help='Output directory (default: results/sensitivity_analysis)')
    
    args = parser.parse_args()
    
    # Validate database
    if not os.path.exists(args.database):
        print(f"ERROR: Database not found: {args.database}")
        return 1
    
    # Configure N values
    if args.quick:
        N_values = [1, 2, 3]
        timeout = 120
    else:
        N_values = list(range(args.n_min, args.n_max + 1))
        timeout = args.timeout
    
    # Configure algorithms
    algorithms = []
    for algo in args.algorithms:
        if algo == 'astar':
            algorithms.append((algo, args.heuristic))
        else:
            algorithms.append((algo, None))
    
    # Run analysis
    run_sensitivity_analysis(
        db_path=args.database,
        N_values=N_values,
        algorithms=algorithms,
        output_dir=args.output_dir,
        max_vars=args.max_vars,
        timeout=timeout
    )
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
