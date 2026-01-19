#!/usr/bin/env python3
"""
Test script for statistical analysis module.

This script tests the statistical analysis functionality with sample data.
"""

import sys
import json
from pathlib import Path
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.statistical_analysis import (
    compute_statistics,
    perform_t_test,
    perform_mannwhitneyu_test,
    analyze_rules_performance,
    PerformanceStats,
    SignificanceTest,
)


def test_compute_statistics():
    """Test computation of descriptive statistics."""
    print("Testing compute_statistics...")
    
    values = [0.8, 0.85, 0.9, 0.75, 0.88, 0.92, 0.78]
    stats = compute_statistics(values, "test_metric")
    
    assert abs(stats.mean - np.mean(values)) < 0.001
    assert abs(stats.std - np.std(values, ddof=1)) < 0.001
    assert stats.count == len(values)
    
    print(f"  Mean: {stats.mean:.4f}")
    print(f"  Std: {stats.std:.4f}")
    print(f"  Median: {stats.median:.4f}")
    print(f"  95% CI: ({stats.confidence_interval_95[0]:.4f}, {stats.confidence_interval_95[1]:.4f})")
    print("  ✓ Passed!\n")


def test_t_test():
    """Test t-test functionality."""
    print("Testing t-test...")
    
    # Create two groups with different means
    group1 = [0.8, 0.82, 0.85, 0.83, 0.81]
    group2 = [0.9, 0.92, 0.88, 0.91, 0.89]
    
    result = perform_t_test(group1, group2, "accuracy", "Algorithm A", "Algorithm B")
    
    assert result.is_significant == (result.p_value < 0.05)
    assert result.effect_size >= 0
    
    print(f"  Group 1 mean: {np.mean(group1):.4f}")
    print(f"  Group 2 mean: {np.mean(group2):.4f}")
    print(f"  t-statistic: {result.statistic:.4f}")
    print(f"  p-value: {result.p_value:.4f}")
    print(f"  Significant: {result.is_significant}")
    print(f"  Effect size (Cohen's d): {result.effect_size:.4f}")
    print("  ✓ Passed!\n")


def test_mannwhitneyu():
    """Test Mann-Whitney U test."""
    print("Testing Mann-Whitney U test...")
    
    group1 = [0.7, 0.75, 0.8, 0.72, 0.78]
    group2 = [0.85, 0.9, 0.88, 0.92, 0.87]
    
    result = perform_mannwhitneyu_test(group1, group2, "confidence", "Method X", "Method Y")
    
    assert result.is_significant == (result.p_value < 0.05)
    
    print(f"  Group 1 median: {np.median(group1):.4f}")
    print(f"  Group 2 median: {np.median(group2):.4f}")
    print(f"  U-statistic: {result.statistic:.4f}")
    print(f"  p-value: {result.p_value:.4f}")
    print(f"  Significant: {result.is_significant}")
    print(f"  Effect size: {result.effect_size:.4f}")
    print("  ✓ Passed!\n")


def test_analyze_rules_performance():
    """Test analysis of rules from JSON file."""
    print("Testing analyze_rules_performance...")
    
    # Check if sample results file exists
    sample_files = [
        Path("data/output/MATILDA_Bupa_results.json"),
        Path("data/output/MATILDA_BupaImperfect_results.json"),
    ]
    
    found_file = None
    for file_path in sample_files:
        if file_path.exists():
            found_file = file_path
            break
    
    if found_file:
        print(f"  Analyzing {found_file}...")
        stats = analyze_rules_performance(found_file)
        
        print(f"  Metrics found: {list(stats.keys())}")
        for metric, stat in stats.items():
            print(f"    {metric}:")
            print(f"      Mean: {stat.mean:.4f} ± {stat.std:.4f}")
            print(f"      Range: [{stat.min:.4f}, {stat.max:.4f}]")
            print(f"      Count: {stat.count}")
        
        print("  ✓ Passed!\n")
    else:
        print("  ⚠ No sample files found, skipping this test\n")


def test_json_serialization():
    """Test JSON serialization of results."""
    print("Testing JSON serialization...")
    
    values = [0.8, 0.85, 0.9]
    stats = compute_statistics(values, "test")
    stats_dict = stats.to_dict()
    
    # Should be JSON serializable
    json_str = json.dumps(stats_dict, indent=2)
    assert json_str
    
    group1 = [0.8, 0.85]
    group2 = [0.9, 0.95]
    test_result = perform_t_test(group1, group2, "metric", "A", "B")
    test_dict = test_result.to_dict()
    
    json_str = json.dumps(test_dict, indent=2)
    assert json_str
    
    print("  Statistics dict keys:", list(stats_dict.keys()))
    print("  Test result dict keys:", list(test_dict.keys()))
    print("  ✓ Passed!\n")


def run_all_tests():
    """Run all tests."""
    print("="*70)
    print("Testing Statistical Analysis Module")
    print("="*70)
    print()
    
    try:
        test_compute_statistics()
        test_t_test()
        test_mannwhitneyu()
        test_json_serialization()
        test_analyze_rules_performance()
        
        print("="*70)
        print("✓ All tests passed!")
        print("="*70)
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
