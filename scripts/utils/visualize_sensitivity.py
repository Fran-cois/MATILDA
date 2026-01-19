#!/usr/bin/env python3
"""
Visualization tool for sensitivity analysis results.

Generates plots showing:
1. N vs Runtime
2. N vs Number of Rules
3. N vs Quality (confidence/support)
4. Trade-off curves
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Install with: pip install matplotlib")


def load_results(result_file: str) -> List[Dict[str, Any]]:
    """Load sensitivity analysis results from JSON file."""
    with open(result_file, 'r') as f:
        return json.load(f)


def plot_runtime_vs_n(results: List[Dict], output_file: str):
    """Plot N vs Runtime for different algorithms."""
    if not HAS_MATPLOTLIB:
        print("Skipping runtime plot (matplotlib not available)")
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Group by algorithm
    algorithms = {}
    for r in results:
        if 'error' in r:
            continue
        algo_key = f"{r['algorithm']}" + (f"_{r['heuristic']}" if r['heuristic'] else "")
        if algo_key not in algorithms:
            algorithms[algo_key] = {'N': [], 'time': []}
        algorithms[algo_key]['N'].append(r['N'])
        algorithms[algo_key]['time'].append(r['metrics']['total_time_seconds'])
    
    # Plot each algorithm
    for algo_name, data in algorithms.items():
        sorted_pairs = sorted(zip(data['N'], data['time']))
        N_sorted, time_sorted = zip(*sorted_pairs)
        ax.plot(N_sorted, time_sorted, marker='o', label=algo_name, linewidth=2)
    
    ax.set_xlabel('N (max_table)', fontsize=12)
    ax.set_ylabel('Runtime (seconds)', fontsize=12)
    ax.set_title('Impact of N on Discovery Time', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_rules_vs_n(results: List[Dict], output_file: str):
    """Plot N vs Number of Rules discovered."""
    if not HAS_MATPLOTLIB:
        print("Skipping rules plot (matplotlib not available)")
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    algorithms = {}
    for r in results:
        if 'error' in r:
            continue
        algo_key = f"{r['algorithm']}" + (f"_{r['heuristic']}" if r['heuristic'] else "")
        if algo_key not in algorithms:
            algorithms[algo_key] = {'N': [], 'rules': []}
        algorithms[algo_key]['N'].append(r['N'])
        algorithms[algo_key]['rules'].append(r['metrics']['total_rules_discovered'])
    
    for algo_name, data in algorithms.items():
        sorted_pairs = sorted(zip(data['N'], data['rules']))
        N_sorted, rules_sorted = zip(*sorted_pairs)
        ax.plot(N_sorted, rules_sorted, marker='s', label=algo_name, linewidth=2)
    
    ax.set_xlabel('N (max_table)', fontsize=12)
    ax.set_ylabel('Number of Rules Discovered', fontsize=12)
    ax.set_title('Impact of N on Rule Discovery', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_quality_vs_n(results: List[Dict], output_file: str):
    """Plot N vs Quality metrics (confidence/support)."""
    if not HAS_MATPLOTLIB:
        print("Skipping quality plot (matplotlib not available)")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Confidence
    algorithms_conf = {}
    for r in results:
        if 'error' in r or not r['metrics'].get('avg_confidence'):
            continue
        algo_key = f"{r['algorithm']}" + (f"_{r['heuristic']}" if r['heuristic'] else "")
        if algo_key not in algorithms_conf:
            algorithms_conf[algo_key] = {'N': [], 'conf': []}
        algorithms_conf[algo_key]['N'].append(r['N'])
        algorithms_conf[algo_key]['conf'].append(r['metrics']['avg_confidence'])
    
    for algo_name, data in algorithms_conf.items():
        sorted_pairs = sorted(zip(data['N'], data['conf']))
        N_sorted, conf_sorted = zip(*sorted_pairs)
        ax1.plot(N_sorted, conf_sorted, marker='o', label=algo_name, linewidth=2)
    
    ax1.set_xlabel('N (max_table)', fontsize=12)
    ax1.set_ylabel('Average Confidence', fontsize=12)
    ax1.set_title('Impact of N on Rule Confidence', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Support
    algorithms_supp = {}
    for r in results:
        if 'error' in r or not r['metrics'].get('avg_support'):
            continue
        algo_key = f"{r['algorithm']}" + (f"_{r['heuristic']}" if r['heuristic'] else "")
        if algo_key not in algorithms_supp:
            algorithms_supp[algo_key] = {'N': [], 'supp': []}
        algorithms_supp[algo_key]['N'].append(r['N'])
        algorithms_supp[algo_key]['supp'].append(r['metrics']['avg_support'])
    
    for algo_name, data in algorithms_supp.items():
        sorted_pairs = sorted(zip(data['N'], data['supp']))
        N_sorted, supp_sorted = zip(*sorted_pairs)
        ax2.plot(N_sorted, supp_sorted, marker='s', label=algo_name, linewidth=2)
    
    ax2.set_xlabel('N (max_table)', fontsize=12)
    ax2.set_ylabel('Average Support', fontsize=12)
    ax2.set_title('Impact of N on Rule Support', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def plot_tradeoff(results: List[Dict], output_file: str):
    """Plot trade-off between runtime and number of rules."""
    if not HAS_MATPLOTLIB:
        print("Skipping tradeoff plot (matplotlib not available)")
        return
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    algorithms = {}
    for r in results:
        if 'error' in r:
            continue
        algo_key = f"{r['algorithm']}" + (f"_{r['heuristic']}" if r['heuristic'] else "")
        if algo_key not in algorithms:
            algorithms[algo_key] = {'time': [], 'rules': [], 'N': []}
        algorithms[algo_key]['time'].append(r['metrics']['total_time_seconds'])
        algorithms[algo_key]['rules'].append(r['metrics']['total_rules_discovered'])
        algorithms[algo_key]['N'].append(r['N'])
    
    for algo_name, data in algorithms.items():
        scatter = ax.scatter(data['time'], data['rules'], 
                           s=100, alpha=0.7, label=algo_name)
        # Add N labels
        for i, n in enumerate(data['N']):
            ax.annotate(f'N={n}', 
                       (data['time'][i], data['rules'][i]),
                       textcoords="offset points",
                       xytext=(5,5), ha='left', fontsize=8)
    
    ax.set_xlabel('Runtime (seconds)', fontsize=12)
    ax.set_ylabel('Number of Rules', fontsize=12)
    ax.set_title('Trade-off: Runtime vs Coverage', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def generate_all_plots(result_file: str, output_dir: str = None):
    """Generate all visualization plots."""
    print(f"\n{'='*60}")
    print("📊 Generating Visualizations")
    print(f"{'='*60}")
    
    if not HAS_MATPLOTLIB:
        print("\n❌ matplotlib not installed. Install with:")
        print("   pip install matplotlib")
        return
    
    # Load results
    results = load_results(result_file)
    print(f"Loaded {len(results)} results from {result_file}")
    
    # Determine output directory
    if output_dir is None:
        output_dir = Path(result_file).parent
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate plots
    print("\nGenerating plots...")
    base_name = Path(result_file).stem
    
    plot_runtime_vs_n(results, f"{output_dir}/{base_name}_runtime.png")
    plot_rules_vs_n(results, f"{output_dir}/{base_name}_rules.png")
    plot_quality_vs_n(results, f"{output_dir}/{base_name}_quality.png")
    plot_tradeoff(results, f"{output_dir}/{base_name}_tradeoff.png")
    
    print(f"\n{'='*60}")
    print(f"✅ All plots saved to: {output_dir}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='Visualize sensitivity analysis results.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visualize results
  python scripts/utils/visualize_sensitivity.py results/sensitivity_analysis/sensitivity_N_20260119_143022.json
  
  # Specify output directory
  python scripts/utils/visualize_sensitivity.py results/sensitivity_analysis/sensitivity_N_20260119_143022.json \
    --output-dir figures/
        """
    )
    
    parser.add_argument('result_file', help='Path to sensitivity analysis JSON result file')
    parser.add_argument('--output-dir', help='Output directory for plots (default: same as result file)')
    
    args = parser.parse_args()
    
    if not Path(args.result_file).exists():
        print(f"ERROR: Result file not found: {args.result_file}")
        return 1
    
    generate_all_plots(args.result_file, args.output_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
