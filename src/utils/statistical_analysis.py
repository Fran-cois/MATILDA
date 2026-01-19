"""
Statistical analysis module for MATILDA performance results.

This module provides functions to compute statistics (mean, standard deviation)
and perform significance tests on rule discovery performance metrics.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from scipy import stats


@dataclass
class PerformanceStats:
    """Statistics for a set of performance metrics."""
    metric_name: str
    mean: float
    std: float
    median: float
    min: float
    max: float
    count: int
    confidence_interval_95: Tuple[float, float]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "metric": self.metric_name,
            "mean": self.mean,
            "std": self.std,
            "median": self.median,
            "min": self.min,
            "max": self.max,
            "count": self.count,
            "ci_95_lower": self.confidence_interval_95[0],
            "ci_95_upper": self.confidence_interval_95[1],
        }


@dataclass
class SignificanceTest:
    """Results of a statistical significance test."""
    test_name: str
    metric: str
    group1_name: str
    group2_name: str
    statistic: float
    p_value: float
    is_significant: bool
    effect_size: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "test": self.test_name,
            "metric": self.metric,
            "group1": self.group1_name,
            "group2": self.group2_name,
            "statistic": float(self.statistic),
            "p_value": float(self.p_value),
            "is_significant": bool(self.is_significant),
            "effect_size": float(self.effect_size) if self.effect_size is not None else None,
        }


def compute_statistics(values: List[float], metric_name: str = "metric") -> PerformanceStats:
    """
    Compute descriptive statistics for a list of values.
    
    :param values: List of numerical values
    :param metric_name: Name of the metric being analyzed
    :return: PerformanceStats object with computed statistics
    """
    if not values:
        raise ValueError("Cannot compute statistics on empty list")
    
    arr = np.array(values)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1) if len(arr) > 1 else 0.0)
    median_val = float(np.median(arr))
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))
    count = len(arr)
    
    # Compute 95% confidence interval
    if len(arr) > 1:
        ci = stats.t.interval(
            confidence=0.95,
            df=len(arr) - 1,
            loc=mean_val,
            scale=stats.sem(arr)
        )
        ci_95 = (float(ci[0]), float(ci[1]))
    else:
        ci_95 = (mean_val, mean_val)
    
    return PerformanceStats(
        metric_name=metric_name,
        mean=mean_val,
        std=std_val,
        median=median_val,
        min=min_val,
        max=max_val,
        count=count,
        confidence_interval_95=ci_95
    )


def perform_t_test(
    group1: List[float],
    group2: List[float],
    metric_name: str,
    group1_name: str = "Group 1",
    group2_name: str = "Group 2",
    alpha: float = 0.05
) -> SignificanceTest:
    """
    Perform independent samples t-test.
    
    :param group1: First group of values
    :param group2: Second group of values
    :param metric_name: Name of the metric being tested
    :param group1_name: Name of first group
    :param group2_name: Name of second group
    :param alpha: Significance level (default 0.05)
    :return: SignificanceTest object with results
    """
    if len(group1) < 2 or len(group2) < 2:
        raise ValueError("Both groups must have at least 2 samples for t-test")
    
    statistic, p_value = stats.ttest_ind(group1, group2)
    
    # Compute Cohen's d effect size
    mean1, mean2 = np.mean(group1), np.mean(group2)
    std1, std2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
    n1, n2 = len(group1), len(group2)
    
    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))
    cohen_d = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0.0
    
    return SignificanceTest(
        test_name="Independent t-test",
        metric=metric_name,
        group1_name=group1_name,
        group2_name=group2_name,
        statistic=float(statistic),
        p_value=float(p_value),
        is_significant=p_value < alpha,
        effect_size=float(abs(cohen_d))
    )


def perform_mannwhitneyu_test(
    group1: List[float],
    group2: List[float],
    metric_name: str,
    group1_name: str = "Group 1",
    group2_name: str = "Group 2",
    alpha: float = 0.05
) -> SignificanceTest:
    """
    Perform Mann-Whitney U test (non-parametric alternative to t-test).
    
    :param group1: First group of values
    :param group2: Second group of values
    :param metric_name: Name of the metric being tested
    :param group1_name: Name of first group
    :param group2_name: Name of second group
    :param alpha: Significance level (default 0.05)
    :return: SignificanceTest object with results
    """
    if len(group1) < 1 or len(group2) < 1:
        raise ValueError("Both groups must have at least 1 sample")
    
    statistic, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
    
    # Compute rank-biserial correlation as effect size
    n1, n2 = len(group1), len(group2)
    r = 1 - (2 * statistic) / (n1 * n2)
    
    return SignificanceTest(
        test_name="Mann-Whitney U test",
        metric=metric_name,
        group1_name=group1_name,
        group2_name=group2_name,
        statistic=float(statistic),
        p_value=float(p_value),
        is_significant=p_value < alpha,
        effect_size=float(abs(r))
    )


def analyze_rules_performance(
    rules_file: Path,
    metrics: Optional[List[str]] = None
) -> Dict[str, PerformanceStats]:
    """
    Analyze performance metrics from a rules JSON file.
    
    :param rules_file: Path to the rules JSON file
    :param metrics: List of metric names to analyze (default: accuracy, confidence)
    :return: Dictionary mapping metric names to PerformanceStats
    """
    if metrics is None:
        metrics = ["accuracy", "confidence"]
    
    with open(rules_file, 'r') as f:
        rules = json.load(f)
    
    results = {}
    
    for metric in metrics:
        values = []
        for rule in rules:
            if metric in rule and rule[metric] is not None:
                values.append(rule[metric])
        
        if values:
            results[metric] = compute_statistics(values, metric)
    
    return results


def analyze_time_metrics(
    time_metrics_file: Path,
    metrics: Optional[List[str]] = None
) -> Dict[str, PerformanceStats]:
    """
    Analyze time metrics from a time_metrics JSON file.
    
    Time metrics files contain compute times for different operations:
    - time_compute_compatible: Time to compute compatible attributes
    - time_to_compute_indexed: Time to compute indexed attributes
    - time_building_cg: Time to build constraint graph
    
    :param time_metrics_file: Path to the time metrics JSON file
    :param metrics: List of time metric names to analyze (default: all available)
    :return: Dictionary mapping metric names to PerformanceStats (with single value)
    """
    if not time_metrics_file.exists():
        return {}
    
    with open(time_metrics_file, 'r') as f:
        time_data = json.load(f)
    
    if metrics is None:
        metrics = list(time_data.keys())
    
    results = {}
    
    for metric in metrics:
        if metric in time_data:
            # For time metrics, we have single values, but we create stats for consistency
            value = time_data[metric]
            results[metric] = compute_statistics([value], metric)
    
    return results


def compare_algorithms(
    algorithm1_file: Path,
    algorithm2_file: Path,
    algorithm1_name: str,
    algorithm2_name: str,
    metrics: Optional[List[str]] = None,
    use_parametric: bool = True
) -> Dict[str, SignificanceTest]:
    """
    Compare performance between two algorithms.
    
    :param algorithm1_file: Path to first algorithm's results
    :param algorithm2_file: Path to second algorithm's results
    :param algorithm1_name: Name of first algorithm
    :param algorithm2_name: Name of second algorithm
    :param metrics: List of metrics to compare
    :param use_parametric: Use t-test (True) or Mann-Whitney U (False)
    :return: Dictionary mapping metric names to SignificanceTest results
    """
    if metrics is None:
        metrics = ["accuracy", "confidence"]
    
    with open(algorithm1_file, 'r') as f:
        rules1 = json.load(f)
    with open(algorithm2_file, 'r') as f:
        rules2 = json.load(f)
    
    results = {}
    
    for metric in metrics:
        values1 = [r[metric] for r in rules1 if metric in r and r[metric] is not None]
        values2 = [r[metric] for r in rules2 if metric in r and r[metric] is not None]
        
        if not values1 or not values2:
            continue
        
        try:
            if use_parametric and len(values1) >= 2 and len(values2) >= 2:
                test_result = perform_t_test(
                    values1, values2, metric,
                    algorithm1_name, algorithm2_name
                )
            else:
                test_result = perform_mannwhitneyu_test(
                    values1, values2, metric,
                    algorithm1_name, algorithm2_name
                )
            
            results[metric] = test_result
        except Exception as e:
            print(f"Warning: Could not perform test for {metric}: {e}")
    
    return results


def compare_time_metrics(
    algorithm1_file: Path,
    algorithm2_file: Path,
    algorithm1_name: str,
    algorithm2_name: str,
    metrics: Optional[List[str]] = None
) -> Dict[str, Dict[str, float]]:
    """
    Compare time metrics between two algorithms.
    
    Since time metrics are single values per run (not distributions),
    this returns the raw values and their differences.
    
    :param algorithm1_file: Path to first algorithm's time metrics file
    :param algorithm2_file: Path to second algorithm's time metrics file
    :param algorithm1_name: Name of first algorithm
    :param algorithm2_name: Name of second algorithm
    :param metrics: List of time metrics to compare (default: all available)
    :return: Dictionary with comparisons
    """
    if not algorithm1_file.exists() or not algorithm2_file.exists():
        return {}
    
    with open(algorithm1_file, 'r') as f:
        times1 = json.load(f)
    with open(algorithm2_file, 'r') as f:
        times2 = json.load(f)
    
    if metrics is None:
        metrics = list(set(times1.keys()) & set(times2.keys()))
    
    results = {}
    
    for metric in metrics:
        if metric in times1 and metric in times2:
            value1 = times1[metric]
            value2 = times2[metric]
            difference = value1 - value2
            percent_diff = (difference / value2 * 100) if value2 != 0 else float('inf')
            
            results[metric] = {
                "metric": metric,
                f"{algorithm1_name}_time": value1,
                f"{algorithm2_name}_time": value2,
                "difference": difference,
                "percent_difference": percent_diff,
                "faster_algorithm": algorithm1_name if value1 < value2 else algorithm2_name
            }
    
    return results


def generate_statistical_report(
    results_dir: Path,
    output_file: Optional[Path] = None,
    algorithms: Optional[List[str]] = None,
    datasets: Optional[List[str]] = None,
    include_time_metrics: bool = True
) -> Dict[str, Any]:
    """
    Generate a comprehensive statistical report for all results.
    
    :param results_dir: Directory containing result files
    :param output_file: Optional path to save the report
    :param algorithms: List of algorithm names to analyze
    :param datasets: List of dataset names to analyze
    :param include_time_metrics: Whether to include time metrics analysis
    :return: Dictionary containing all statistical analyses
    """
    if algorithms is None:
        algorithms = ["MATILDA", "SPIDER", "ANYBURL", "POPPER"]
    
    report = {
        "statistics": {},
        "comparisons": {},
        "time_metrics": {},
        "time_comparisons": {},
        "summary": {}
    }
    
    # Collect all result files
    result_files = {}
    time_files = {}
    for algo in algorithms:
        result_files[algo] = {}
        time_files[algo] = {}
        
        # Rule result files
        pattern = f"{algo}_*_results.json"
        for file_path in results_dir.glob(pattern):
            dataset_name = file_path.stem.replace(f"{algo}_", "").replace("_results", "")
            result_files[algo][dataset_name] = file_path
        
        # Time metrics files
        if include_time_metrics:
            time_pattern = f"init_time_metrics_*.json"
            for file_path in results_dir.glob(time_pattern):
                dataset_name = file_path.stem.replace("init_time_metrics_", "")
                if dataset_name in result_files[algo]:  # Only include if we have results for this dataset
                    time_files[algo][dataset_name] = file_path
    
    # Compute statistics for each algorithm and dataset
    for algo, datasets_dict in result_files.items():
        report["statistics"][algo] = {}
        for dataset, file_path in datasets_dict.items():
            try:
                stats = analyze_rules_performance(file_path)
                report["statistics"][algo][dataset] = {
                    metric: stat.to_dict() for metric, stat in stats.items()
                }
            except Exception as e:
                print(f"Warning: Could not analyze {algo}/{dataset}: {e}")
    
    # Analyze time metrics
    if include_time_metrics:
        for algo, datasets_dict in time_files.items():
            if algo not in report["time_metrics"]:
                report["time_metrics"][algo] = {}
            for dataset, file_path in datasets_dict.items():
                try:
                    time_stats = analyze_time_metrics(file_path)
                    report["time_metrics"][algo][dataset] = {
                        metric: stat.to_dict() for metric, stat in time_stats.items()
                    }
                except Exception as e:
                    print(f"Warning: Could not analyze time metrics for {algo}/{dataset}: {e}")
    
    # Perform pairwise comparisons
    algo_list = list(result_files.keys())
    for i, algo1 in enumerate(algo_list):
        for algo2 in algo_list[i+1:]:
            # Find common datasets
            common_datasets = set(result_files[algo1].keys()) & set(result_files[algo2].keys())
            
            for dataset in common_datasets:
                try:
                    comparisons = compare_algorithms(
                        result_files[algo1][dataset],
                        result_files[algo2][dataset],
                        algo1, algo2
                    )
                    
                    comparison_key = f"{algo1}_vs_{algo2}_{dataset}"
                    report["comparisons"][comparison_key] = {
                        metric: test.to_dict() for metric, test in comparisons.items()
                    }
                except Exception as e:
                    print(f"Warning: Could not compare {algo1} vs {algo2} on {dataset}: {e}")
                
                # Compare time metrics
                if include_time_metrics and dataset in time_files.get(algo1, {}) and dataset in time_files.get(algo2, {}):
                    try:
                        time_comparisons = compare_time_metrics(
                            time_files[algo1][dataset],
                            time_files[algo2][dataset],
                            algo1, algo2
                        )
                        
                        time_comparison_key = f"{algo1}_vs_{algo2}_{dataset}_time"
                        report["time_comparisons"][time_comparison_key] = time_comparisons
                    except Exception as e:
                        print(f"Warning: Could not compare time metrics for {algo1} vs {algo2} on {dataset}: {e}")
    
    # Generate summary
    report["summary"]["total_algorithms"] = len(algo_list)
    report["summary"]["total_datasets"] = len(set(
        dataset for datasets_dict in result_files.values() for dataset in datasets_dict.keys()
    ))
    report["summary"]["total_comparisons"] = len(report["comparisons"])
    report["summary"]["total_time_comparisons"] = len(report["time_comparisons"])
    
    # Save report if output file specified
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Statistical report saved to {output_file}")
    
    return report


def format_statistics_markdown(stats: PerformanceStats) -> str:
    """
    Format PerformanceStats as a markdown table row.
    
    :param stats: PerformanceStats object
    :return: Markdown formatted string
    """
    return (
        f"| {stats.metric_name} | {stats.mean:.4f} | {stats.std:.4f} | "
        f"{stats.median:.4f} | {stats.min:.4f} | {stats.max:.4f} | "
        f"({stats.confidence_interval_95[0]:.4f}, {stats.confidence_interval_95[1]:.4f}) |"
    )


def format_significance_test_markdown(test: SignificanceTest) -> str:
    """
    Format SignificanceTest as a markdown table row.
    
    :param test: SignificanceTest object
    :return: Markdown formatted string
    """
    sig_indicator = "✓" if test.is_significant else "✗"
    return (
        f"| {test.metric} | {test.group1_name} vs {test.group2_name} | "
        f"{test.test_name} | {test.statistic:.4f} | {test.p_value:.4f} | "
        f"{sig_indicator} | {test.effect_size:.4f if test.effect_size else 'N/A'} |"
    )
