#!/usr/bin/env python3
"""
Generate Statistical Analysis Report for MATILDA Results

This script analyzes performance results from multiple algorithms and datasets,
computing descriptive statistics and performing significance tests.

Usage:
    python generate_statistics_report.py [--results-dir PATH] [--output FILE]
    
Examples:
    # Analyze all results in default directory
    python generate_statistics_report.py
    
    # Specify custom directory
    python generate_statistics_report.py --results-dir data/output
    
    # Save to specific file
    python generate_statistics_report.py --output my_report.json
"""

import argparse
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.statistical_analysis import (
    generate_statistical_report,
    analyze_rules_performance,
    format_statistics_markdown,
    format_significance_test_markdown,
)


def create_markdown_report(json_report: dict, output_file: Path):
    """
    Create a human-readable markdown report from JSON statistics.
    
    :param json_report: Dictionary containing statistical analyses
    :param output_file: Path to save the markdown report
    """
    md_content = []
    
    md_content.append("# Statistical Analysis Report\n")
    md_content.append(f"**Generated:** {json_report.get('timestamp', 'N/A')}\n")
    md_content.append("---\n\n")
    
    # Summary
    summary = json_report.get("summary", {})
    md_content.append("## Summary\n\n")
    md_content.append(f"- **Total Algorithms:** {summary.get('total_algorithms', 0)}\n")
    md_content.append(f"- **Total Datasets:** {summary.get('total_datasets', 0)}\n")
    md_content.append(f"- **Total Comparisons:** {summary.get('total_comparisons', 0)}\n")
    md_content.append(f"- **Total Time Comparisons:** {summary.get('total_time_comparisons', 0)}\n\n")
    
    # Descriptive Statistics
    md_content.append("## Descriptive Statistics\n\n")
    
    statistics = json_report.get("statistics", {})
    for algo, datasets in statistics.items():
        md_content.append(f"### {algo}\n\n")
        
        for dataset, metrics in datasets.items():
            md_content.append(f"#### Dataset: {dataset}\n\n")
            md_content.append("| Metric | Mean | Std Dev | Median | Min | Max | 95% CI |\n")
            md_content.append("|--------|------|---------|--------|-----|-----|--------|\n")
            
            for metric_name, stat in metrics.items():
                md_content.append(
                    f"| {stat['metric']} | {stat['mean']:.4f} | {stat['std']:.4f} | "
                    f"{stat['median']:.4f} | {stat['min']:.4f} | {stat['max']:.4f} | "
                    f"({stat['ci_95_lower']:.4f}, {stat['ci_95_upper']:.4f}) |\n"
                )
            
            md_content.append("\n")
    
    # Time Metrics
    time_metrics = json_report.get("time_metrics", {})
    if time_metrics:
        md_content.append("## Compute Time Metrics\n\n")
        
        for algo, datasets in time_metrics.items():
            md_content.append(f"### {algo}\n\n")
            
            for dataset, metrics in datasets.items():
                md_content.append(f"#### Dataset: {dataset}\n\n")
                md_content.append("| Metric | Time (seconds) |\n")
                md_content.append("|--------|----------------|\n")
                
                for metric_name, stat in metrics.items():
                    md_content.append(f"| {stat['metric']} | {stat['mean']:.6f} |\n")
                
                md_content.append("\n")
    
    # Significance Tests
    md_content.append("## Significance Tests\n\n")
    
    comparisons = json_report.get("comparisons", {})
    if comparisons:
        md_content.append("| Metric | Comparison | Test | Statistic | p-value | Significant | Effect Size |\n")
        md_content.append("|--------|------------|------|-----------|---------|-------------|-------------|\n")
        
        for comparison_name, metrics in comparisons.items():
            for metric_name, test in metrics.items():
                sig_indicator = "✓" if test['is_significant'] else "✗"
                effect = test.get('effect_size', 'N/A')
                effect_str = f"{effect:.4f}" if isinstance(effect, (int, float)) else effect
                
                md_content.append(
                    f"| {test['metric']} | {test['group1']} vs {test['group2']} | "
                    f"{test['test']} | {test['statistic']:.4f} | {test['p_value']:.4f} | "
                    f"{sig_indicator} | {effect_str} |\n"
                )
        
        md_content.append("\n")
    else:
        md_content.append("*No significance tests performed.*\n\n")
    
    # Time Comparisons
    time_comparisons = json_report.get("time_comparisons", {})
    if time_comparisons:
        md_content.append("## Compute Time Comparisons\n\n")
        
        for comparison_name, metrics in time_comparisons.items():
            parts = comparison_name.split("_vs_")
            if len(parts) >= 2:
                algo1 = parts[0]
                rest = parts[1].rsplit("_time", 1)[0]
                parts2 = rest.rsplit("_", 1)
                algo2 = parts2[0] if len(parts2) > 1 else rest
                dataset = parts2[1] if len(parts2) > 1 else ""
                
                md_content.append(f"### {algo1} vs {algo2} - {dataset}\n\n")
                md_content.append("| Metric | Time (s) | Faster Algorithm | Difference (s) | % Difference |\n")
                md_content.append("|--------|----------|------------------|----------------|-------------|\n")
                
                for metric_name, comp in metrics.items():
                    time1_key = [k for k in comp.keys() if k.endswith("_time") and algo1 in k]
                    time2_key = [k for k in comp.keys() if k.endswith("_time") and algo2 in k]
                    
                    time1 = comp[time1_key[0]] if time1_key else "N/A"
                    time2 = comp[time2_key[0]] if time2_key else "N/A"
                    
                    time1_str = f"{time1:.6f}" if isinstance(time1, (int, float)) else time1
                    time2_str = f"{time2:.6f}" if isinstance(time2, (int, float)) else time2
                    
                    md_content.append(
                        f"| {comp['metric']} | {algo1}: {time1_str}, {algo2}: {time2_str} | "
                        f"{comp.get('faster_algorithm', 'N/A')} | "
                        f"{comp.get('difference', 0):.6f} | "
                        f"{comp.get('percent_difference', 0):.2f}% |\n"
                    )
                
                md_content.append("\n")
    
    # Interpretation Guide
    md_content.append("## Interpretation Guide\n\n")
    md_content.append("### Effect Size (Cohen's d)\n\n")
    md_content.append("- **Small:** d = 0.2\n")
    md_content.append("- **Medium:** d = 0.5\n")
    md_content.append("- **Large:** d = 0.8\n\n")
    md_content.append("### Significance Level\n\n")
    md_content.append("- **p < 0.05:** Statistically significant ✓\n")
    md_content.append("- **p ≥ 0.05:** Not statistically significant ✗\n\n")
    md_content.append("### Confidence Interval (95% CI)\n\n")
    md_content.append("The range within which the true population mean is likely to fall with 95% confidence.\n\n")
    
    # Write to file
    with open(output_file, 'w') as f:
        f.writelines(md_content)
    
    print(f"Markdown report saved to {output_file}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate statistical analysis report for MATILDA results",
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
        help="Output file path for JSON report (default: results-dir/statistical_analysis_report.json)"
    )
    
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=None,
        help="List of algorithm names to analyze (default: all found)"
    )
    
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Also generate markdown version of the report"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate results directory
    if not args.results_dir.exists():
        print(f"Error: Results directory does not exist: {args.results_dir}")
        sys.exit(1)
    
    # Set output file
    if args.output is None:
        args.output = args.results_dir / "statistical_analysis_report.json"
    
    print(f"Analyzing results from: {args.results_dir}")
    print(f"Output will be saved to: {args.output}")
    
    # Generate report
    try:
        import datetime
        report = generate_statistical_report(
            args.results_dir,
            args.output,
            algorithms=args.algorithms
        )
        
        # Add timestamp
        report["timestamp"] = datetime.datetime.now().isoformat()
        
        # Save JSON report
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ JSON report saved to {args.output}")
        
        # Generate markdown report if requested
        if args.markdown:
            md_output = args.output.with_suffix('.md')
            create_markdown_report(report, md_output)
            print(f"✓ Markdown report saved to {md_output}")
        
        # Print summary
        print("\n" + "="*70)
        print("Summary")
        print("="*70)
        print(f"Algorithms analyzed: {report['summary']['total_algorithms']}")
        print(f"Datasets analyzed: {report['summary']['total_datasets']}")
        print(f"Comparisons performed: {report['summary']['total_comparisons']}")
        print(f"Time comparisons performed: {report['summary']['total_time_comparisons']}")
        
        # Print statistics summary if verbose
        if args.verbose and report.get("statistics"):
            print("\n" + "="*70)
            print("Statistics Overview")
            print("="*70)
            
            for algo, datasets in report["statistics"].items():
                print(f"\n{algo}:")
                for dataset, metrics in datasets.items():
                    print(f"  {dataset}:")
                    for metric_name, stat in metrics.items():
                        print(f"    {stat['metric']}: μ={stat['mean']:.4f}, σ={stat['std']:.4f}")
        
        # Print time metrics if verbose
        if args.verbose and report.get("time_metrics"):
            print("\n" + "="*70)
            print("Compute Time Metrics")
            print("="*70)
            
            for algo, datasets in report["time_metrics"].items():
                print(f"\n{algo}:")
                for dataset, metrics in datasets.items():
                    print(f"  {dataset}:")
                    for metric_name, stat in metrics.items():
                        print(f"    {stat['metric']}: {stat['mean']:.6f}s")
        
        # Print significant differences
        if report.get("comparisons"):
            significant_tests = []
            for comp_name, metrics in report["comparisons"].items():
                for metric_name, test in metrics.items():
                    if test['is_significant']:
                        significant_tests.append((comp_name, test))
            
            if significant_tests:
                print("\n" + "="*70)
                print(f"Significant Differences Found ({len(significant_tests)})")
                print("="*70)
                
                for comp_name, test in significant_tests[:10]:  # Show first 10
                    print(f"  {test['group1']} vs {test['group2']} ({test['metric']})")
                    print(f"    p-value: {test['p_value']:.4f}, effect size: {test.get('effect_size', 'N/A')}")
                
                if len(significant_tests) > 10:
                    print(f"  ... and {len(significant_tests) - 10} more (see report for details)")
        
        # Print time comparisons if verbose
        if args.verbose and report.get("time_comparisons"):
            print("\n" + "="*70)
            print("Compute Time Comparisons")
            print("="*70)
            
            for comp_name, metrics in report["time_comparisons"].items():
                print(f"\n{comp_name}:")
                for metric_name, comp in metrics.items():
                    faster = comp.get('faster_algorithm', 'N/A')
                    diff = comp.get('difference', 0)
                    percent = comp.get('percent_difference', 0)
                    print(f"  {comp['metric']}: {faster} is faster by {abs(diff):.6f}s ({abs(percent):.2f}%)")
        
        print("\n" + "="*70)
        print("✓ Analysis complete!")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Error during analysis: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
