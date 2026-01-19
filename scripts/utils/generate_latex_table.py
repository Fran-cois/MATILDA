#!/usr/bin/env python3
"""
Generate LaTeX Table from Existing Results

This script analyzes existing MATILDA results and generates a LaTeX table
without re-running experiments. Useful for quick table generation.

Usage:
    python generate_latex_table.py [--results-dir DIR] [--output FILE]
    
Examples:
    # Use default results directory
    python generate_latex_table.py
    
    # Specify custom directory and output
    python generate_latex_table.py --results-dir data/output --output my_table.tex
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


class LatexTableGenerator:
    """Generates LaTeX tables from existing results."""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.data = {}
        
    def collect_results(self, algorithms: List[str], datasets: List[str]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Collect results from existing result files.
        
        :param algorithms: List of algorithm names
        :param datasets: List of dataset names
        :return: Dictionary with collected results
        """
        data = {}
        
        for algorithm in algorithms:
            data[algorithm] = {}
            
            for dataset in datasets:
                # Results file
                results_file = self.results_dir / f"{algorithm}_{dataset}_results.json"
                time_file = self.results_dir / f"init_time_metrics_{dataset}.json"
                
                if not results_file.exists():
                    continue
                
                # Load results
                with open(results_file, 'r') as f:
                    rules = json.load(f)
                
                num_rules = len(rules)
                
                # Load time metrics
                time_metrics = {}
                if time_file.exists():
                    with open(time_file, 'r') as f:
                        time_metrics = json.load(f)
                
                # Calculate average metrics from rules
                accuracy_values = [r.get('accuracy', 0) for r in rules if r.get('accuracy') is not None]
                confidence_values = [r.get('confidence', 0) for r in rules if r.get('confidence') is not None]
                
                data[algorithm][dataset] = {
                    'num_rules': num_rules,
                    'avg_accuracy': sum(accuracy_values) / len(accuracy_values) if accuracy_values else 0,
                    'avg_confidence': sum(confidence_values) / len(confidence_values) if confidence_values else 0,
                    'time_compute_compatible': time_metrics.get('time_compute_compatible', 0),
                    'time_to_compute_indexed': time_metrics.get('time_to_compute_indexed', 0),
                    'time_building_cg': time_metrics.get('time_building_cg', 0),
                }
        
        self.data = data
        return data
    
    def generate_simple_table(self, output_file: Path):
        """
        Generate a simple LaTeX table (no statistics, single run data).
        
        :param output_file: Path to save the LaTeX table
        """
        latex_lines = []
        
        # Table header
        latex_lines.append("% LaTeX Table: MATILDA Results")
        latex_lines.append("% Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        latex_lines.append("")
        latex_lines.append("\\begin{table}[htbp]")
        latex_lines.append("\\centering")
        latex_lines.append("\\caption{Rule Discovery Results}")
        latex_lines.append("\\label{tab:results}")
        latex_lines.append("\\begin{tabular}{llrrrr}")
        latex_lines.append("\\toprule")
        latex_lines.append("\\textbf{Algorithm} & \\textbf{Dataset} & \\textbf{\\#Rules} & \\textbf{Accuracy} & \\textbf{Confidence} & \\textbf{Time (s)} \\\\")
        latex_lines.append("\\midrule")
        
        # Table content
        for algorithm, datasets in sorted(self.data.items()):
            first_row = True
            for dataset, metrics in sorted(datasets.items()):
                # Extract metrics
                num_rules = metrics.get('num_rules', 0)
                accuracy = metrics.get('avg_accuracy', 0)
                confidence = metrics.get('avg_confidence', 0)
                time_cg = metrics.get('time_building_cg', 0)
                
                # Algorithm name only on first row
                algo_name = algorithm if first_row else ""
                first_row = False
                
                latex_lines.append(
                    f"{algo_name} & {dataset} & {num_rules} & "
                    f"{accuracy:.4f} & {confidence:.4f} & {time_cg:.4f} \\\\"
                )
            
            latex_lines.append("\\midrule")
        
        # Remove last midrule and add bottomrule
        if latex_lines[-1] == "\\midrule":
            latex_lines[-1] = "\\bottomrule"
        else:
            latex_lines.append("\\bottomrule")
        
        # Table footer
        latex_lines.append("\\end{tabular}")
        latex_lines.append("\\end{table}")
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(latex_lines))
        
        print(f"\n✓ LaTeX table saved to {output_file}")
        
        # Print to console
        print("\n" + "="*70)
        print("LaTeX Table:")
        print("="*70)
        print('\n'.join(latex_lines))
        print("="*70)
    
    def generate_detailed_table(self, output_file: Path):
        """
        Generate a detailed LaTeX table with all time metrics.
        
        :param output_file: Path to save the LaTeX table
        """
        latex_lines = []
        
        # Table header
        latex_lines.append("% LaTeX Table: Detailed MATILDA Results")
        latex_lines.append("% Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        latex_lines.append("")
        latex_lines.append("\\begin{table}[htbp]")
        latex_lines.append("\\centering")
        latex_lines.append("\\caption{Detailed Rule Discovery Performance}")
        latex_lines.append("\\label{tab:detailed_results}")
        latex_lines.append("\\resizebox{\\textwidth}{!}{%")
        latex_lines.append("\\begin{tabular}{llrrrrrr}")
        latex_lines.append("\\toprule")
        latex_lines.append("\\textbf{Algorithm} & \\textbf{Dataset} & \\textbf{\\#Rules} & "
                          "\\textbf{Acc.} & \\textbf{Conf.} & \\textbf{T\\textsubscript{compat}} & "
                          "\\textbf{T\\textsubscript{index}} & \\textbf{T\\textsubscript{CG}} \\\\")
        latex_lines.append("\\midrule")
        
        # Table content
        for algorithm, datasets in sorted(self.data.items()):
            first_row = True
            for dataset, metrics in sorted(datasets.items()):
                # Extract metrics
                num_rules = metrics.get('num_rules', 0)
                accuracy = metrics.get('avg_accuracy', 0)
                confidence = metrics.get('avg_confidence', 0)
                t_compat = metrics.get('time_compute_compatible', 0)
                t_index = metrics.get('time_to_compute_indexed', 0)
                t_cg = metrics.get('time_building_cg', 0)
                
                # Algorithm name only on first row
                algo_name = algorithm if first_row else ""
                first_row = False
                
                latex_lines.append(
                    f"{algo_name} & {dataset} & {num_rules} & "
                    f"{accuracy:.3f} & {confidence:.3f} & "
                    f"{t_compat:.4f} & {t_index:.4f} & {t_cg:.4f} \\\\"
                )
            
            latex_lines.append("\\midrule")
        
        # Remove last midrule and add bottomrule
        if latex_lines[-1] == "\\midrule":
            latex_lines[-1] = "\\bottomrule"
        else:
            latex_lines.append("\\bottomrule")
        
        # Table footer
        latex_lines.append("\\end{tabular}}")
        latex_lines.append("\\end{table}")
        latex_lines.append("")
        latex_lines.append("% Legend:")
        latex_lines.append("% Acc. = Average Accuracy")
        latex_lines.append("% Conf. = Average Confidence")
        latex_lines.append("% T_compat = Time to compute compatible attributes (seconds)")
        latex_lines.append("% T_index = Time to compute indexed attributes (seconds)")
        latex_lines.append("% T_CG = Time to build constraint graph (seconds)")
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(latex_lines))
        
        print(f"\n✓ Detailed LaTeX table saved to {output_file}")
        
        # Print to console
        print("\n" + "="*70)
        print("Detailed LaTeX Table:")
        print("="*70)
        print('\n'.join(latex_lines))
        print("="*70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate LaTeX table from existing results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("data/output"),
        help="Directory containing result files (default: data/output)"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file for LaTeX table (default: results-dir/latex_table.tex)"
    )
    
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=["MATILDA", "SPIDER", "ANYBURL", "POPPER"],
        help="List of algorithms to include (default: all found)"
    )
    
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["Bupa", "BupaImperfect", "ComparisonDataset", "ImperfectTest"],
        help="List of datasets to include (default: all found)"
    )
    
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Generate detailed table with all time metrics"
    )
    
    args = parser.parse_args()
    
    # Set default output file
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        table_type = "detailed" if args.detailed else "simple"
        args.output = args.results_dir / f"latex_table_{table_type}_{timestamp}.tex"
    
    print("="*70)
    print("LaTeX Table Generator")
    print("="*70)
    print(f"Results directory: {args.results_dir}")
    print(f"Output file: {args.output}")
    print(f"Table type: {'Detailed' if args.detailed else 'Simple'}")
    print("="*70)
    
    # Check if results directory exists
    if not args.results_dir.exists():
        print(f"\n✗ Error: Results directory not found: {args.results_dir}")
        sys.exit(1)
    
    # Generate table
    generator = LatexTableGenerator(args.results_dir)
    
    try:
        print("\nCollecting results...")
        data = generator.collect_results(args.algorithms, args.datasets)
        
        if not data:
            print("\n⚠️  No results found. Please check:")
            print(f"  - Results directory: {args.results_dir}")
            print(f"  - Expected file pattern: ALGORITHM_DATASET_results.json")
            sys.exit(1)
        
        print(f"✓ Found results for:")
        for algo, datasets in data.items():
            print(f"  - {algo}: {', '.join(datasets.keys())}")
        
        # Generate appropriate table
        if args.detailed:
            generator.generate_detailed_table(args.output)
        else:
            generator.generate_simple_table(args.output)
        
        print("\n" + "="*70)
        print("✓ Table generation completed!")
        print("="*70)
        print(f"\nTo use in LaTeX, add to your document preamble:")
        print("  \\usepackage{booktabs}")
        print("  \\usepackage{graphicx}  % For resizebox in detailed table")
        print(f"\nThen include the table:")
        print(f"  \\input{{{args.output.name}}}")
        
    except Exception as e:
        print(f"\n✗ Error generating table: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
