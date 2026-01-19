#!/usr/bin/env python3
"""
Generate scalability visualizations from stress test results.

Creates publication-quality graphs showing:
1. Runtime vs Dataset Size
2. Memory Usage vs Dataset Size
3. Rules Discovered vs Dataset Size
4. Throughput (Rules/sec) vs Dataset Size
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import numpy as np


class ScalabilityVisualizer:
    """Generate scalability visualizations."""
    
    def __init__(self, results_file: str, output_dir: str = None):
        """
        Initialize visualizer.
        
        :param results_file: Path to scalability_summary.json
        :param output_dir: Directory for output graphs
        """
        self.results_file = Path(results_file)
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.results_file.parent
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load results
        with open(self.results_file, 'r') as f:
            self.data = json.load(f)
        
        # Extract data arrays
        self.extract_data()
    
    def extract_data(self):
        """Extract data arrays from results."""
        self.sizes_labels = []
        self.sizes_tuples = []
        self.runtimes = []
        self.num_rules = []
        self.rules_per_sec = []
        self.memory_peak = []
        self.cpu_avg = []
        
        # Sort by tuple count
        datasets = self.data.get('datasets', {})
        sorted_labels = sorted(datasets.keys(), 
                              key=lambda x: datasets[x]['num_tuples'])
        
        for label in sorted_labels:
            dataset = datasets[label]
            results = dataset.get('results', {})
            
            if 'matilda' not in results:
                continue
            
            matilda = results['matilda']
            
            self.sizes_labels.append(label)
            self.sizes_tuples.append(dataset['num_tuples'])
            
            self.runtimes.append(matilda.get('runtime_seconds', 0))
            self.num_rules.append(matilda.get('num_rules', 0))
            self.rules_per_sec.append(matilda.get('rules_per_second', 0))
            
            # Memory (if available from monitoring)
            self.memory_peak.append(matilda.get('memory_peak_mb', 0))
            self.cpu_avg.append(matilda.get('cpu_avg_percent', 0))
    
    def plot_runtime_vs_size(self):
        """Plot runtime vs dataset size."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Convert to millions for readability
        sizes_m = [s / 1_000_000 for s in self.sizes_tuples]
        
        ax.plot(sizes_m, self.runtimes, 'o-', linewidth=2, markersize=8, 
                color='#2E86AB', label='MATILDA (A* + Hybrid)')
        
        # Add linear reference line
        if len(sizes_m) >= 2:
            # Linear fit through origin
            slope = self.runtimes[-1] / sizes_m[-1]
            linear_ref = [slope * s for s in sizes_m]
            ax.plot(sizes_m, linear_ref, '--', color='gray', alpha=0.5, 
                   label='Linear reference')
        
        ax.set_xlabel('Dataset Size (Million Tuples)', fontsize=12)
        ax.set_ylabel('Runtime (seconds)', fontsize=12)
        ax.set_title('Scalability: Runtime vs Dataset Size', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        # Add data labels
        for i, (x, y) in enumerate(zip(sizes_m, self.runtimes)):
            ax.annotate(f'{y:.1f}s', (x, y), textcoords="offset points", 
                       xytext=(0, 10), ha='center', fontsize=9)
        
        plt.tight_layout()
        output_file = self.output_dir / 'scalability_runtime.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Generated: {output_file}")
    
    def plot_memory_vs_size(self):
        """Plot memory usage vs dataset size."""
        if not any(self.memory_peak):
            print("⚠️  No memory data available, skipping memory plot")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        sizes_m = [s / 1_000_000 for s in self.sizes_tuples]
        
        ax.plot(sizes_m, self.memory_peak, 'o-', linewidth=2, markersize=8, 
                color='#A23B72', label='Peak Memory')
        
        ax.set_xlabel('Dataset Size (Million Tuples)', fontsize=12)
        ax.set_ylabel('Memory Usage (MB)', fontsize=12)
        ax.set_title('Scalability: Memory Usage vs Dataset Size', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        # Add data labels
        for i, (x, y) in enumerate(zip(sizes_m, self.memory_peak)):
            ax.annotate(f'{y:.0f}MB', (x, y), textcoords="offset points", 
                       xytext=(0, 10), ha='center', fontsize=9)
        
        plt.tight_layout()
        output_file = self.output_dir / 'scalability_memory.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Generated: {output_file}")
    
    def plot_rules_vs_size(self):
        """Plot rules discovered vs dataset size."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        sizes_m = [s / 1_000_000 for s in self.sizes_tuples]
        
        ax.plot(sizes_m, self.num_rules, 'o-', linewidth=2, markersize=8, 
                color='#F18F01', label='Rules Discovered')
        
        ax.set_xlabel('Dataset Size (Million Tuples)', fontsize=12)
        ax.set_ylabel('Number of Rules', fontsize=12)
        ax.set_title('Scalability: Rules Discovered vs Dataset Size', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        # Add data labels
        for i, (x, y) in enumerate(zip(sizes_m, self.num_rules)):
            ax.annotate(f'{y}', (x, y), textcoords="offset points", 
                       xytext=(0, 10), ha='center', fontsize=9)
        
        plt.tight_layout()
        output_file = self.output_dir / 'scalability_rules.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Generated: {output_file}")
    
    def plot_throughput_vs_size(self):
        """Plot throughput (rules/sec) vs dataset size."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        sizes_m = [s / 1_000_000 for s in self.sizes_tuples]
        
        ax.plot(sizes_m, self.rules_per_sec, 'o-', linewidth=2, markersize=8, 
                color='#06A77D', label='Throughput')
        
        ax.set_xlabel('Dataset Size (Million Tuples)', fontsize=12)
        ax.set_ylabel('Throughput (Rules/second)', fontsize=12)
        ax.set_title('Scalability: Discovery Throughput vs Dataset Size', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        # Add data labels
        for i, (x, y) in enumerate(zip(sizes_m, self.rules_per_sec)):
            ax.annotate(f'{y:.2f}', (x, y), textcoords="offset points", 
                       xytext=(0, 10), ha='center', fontsize=9)
        
        plt.tight_layout()
        output_file = self.output_dir / 'scalability_throughput.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Generated: {output_file}")
    
    def plot_combined_overview(self):
        """Create combined overview with all metrics."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        sizes_m = [s / 1_000_000 for s in self.sizes_tuples]
        
        # Runtime
        axes[0, 0].plot(sizes_m, self.runtimes, 'o-', linewidth=2, markersize=6, color='#2E86AB')
        axes[0, 0].set_xlabel('Dataset Size (M tuples)')
        axes[0, 0].set_ylabel('Runtime (s)')
        axes[0, 0].set_title('Runtime')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Rules
        axes[0, 1].plot(sizes_m, self.num_rules, 'o-', linewidth=2, markersize=6, color='#F18F01')
        axes[0, 1].set_xlabel('Dataset Size (M tuples)')
        axes[0, 1].set_ylabel('Rules Discovered')
        axes[0, 1].set_title('Rules Discovered')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Throughput
        axes[1, 0].plot(sizes_m, self.rules_per_sec, 'o-', linewidth=2, markersize=6, color='#06A77D')
        axes[1, 0].set_xlabel('Dataset Size (M tuples)')
        axes[1, 0].set_ylabel('Rules/second')
        axes[1, 0].set_title('Throughput')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Memory (if available)
        if any(self.memory_peak):
            axes[1, 1].plot(sizes_m, self.memory_peak, 'o-', linewidth=2, markersize=6, color='#A23B72')
            axes[1, 1].set_xlabel('Dataset Size (M tuples)')
            axes[1, 1].set_ylabel('Memory (MB)')
            axes[1, 1].set_title('Peak Memory')
            axes[1, 1].grid(True, alpha=0.3)
        else:
            # Show scalability factor instead
            if 'scalability_metrics' in self.data:
                metrics = self.data['scalability_metrics']
                scaling = metrics.get('avg_scaling_factor', 0)
                interp = metrics.get('interpretation', 'unknown')
                
                axes[1, 1].text(0.5, 0.5, f'Scaling Factor\n{scaling:.2f}\n({interp})',
                              ha='center', va='center', fontsize=14, transform=axes[1, 1].transAxes)
                axes[1, 1].set_title('Scalability Metric')
                axes[1, 1].axis('off')
        
        fig.suptitle('MATILDA Scalability Overview (A* + Hybrid, N=3)', 
                    fontsize=16, fontweight='bold', y=0.995)
        
        plt.tight_layout()
        output_file = self.output_dir / 'scalability_overview.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Generated: {output_file}")
    
    def generate_all_plots(self):
        """Generate all visualization plots."""
        print(f"\n{'='*70}")
        print("GENERATING SCALABILITY VISUALIZATIONS")
        print(f"{'='*70}\n")
        
        print(f"Input: {self.results_file}")
        print(f"Output: {self.output_dir}")
        print()
        
        self.plot_runtime_vs_size()
        self.plot_rules_vs_size()
        self.plot_throughput_vs_size()
        self.plot_memory_vs_size()
        self.plot_combined_overview()
        
        print(f"\n{'='*70}")
        print("✅ ALL VISUALIZATIONS GENERATED")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Generate scalability visualizations from stress test results.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all plots
  python scripts/utils/visualize_scalability.py results/scalability/scalability_summary.json
  
  # Custom output directory
  python scripts/utils/visualize_scalability.py results/scalability/scalability_summary.json \\
    --output-dir figures/
        """
    )
    
    parser.add_argument('results_file', help='Path to scalability_summary.json')
    parser.add_argument('--output-dir', '-o',
                       help='Output directory (default: same as results file)')
    
    args = parser.parse_args()
    
    if not Path(args.results_file).exists():
        print(f"ERROR: Results file not found: {args.results_file}")
        return 1
    
    visualizer = ScalabilityVisualizer(args.results_file, args.output_dir)
    visualizer.generate_all_plots()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
