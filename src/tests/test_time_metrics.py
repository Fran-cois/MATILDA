#!/usr/bin/env python3
"""
Test Time Metrics Analysis

This script tests the new time metrics analysis functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.statistical_analysis import (
    analyze_time_metrics,
    compare_time_metrics,
)


def test_analyze_time_metrics():
    """Test analyzing time metrics from a file."""
    print("="*70)
    print("Test 1: Analyze Time Metrics")
    print("="*70)
    
    time_file = Path("data/output/init_time_metrics_Bupa.json")
    
    if not time_file.exists():
        print(f"✗ Time metrics file not found: {time_file}")
        return False
    
    try:
        stats = analyze_time_metrics(time_file)
        
        print(f"\n✓ Successfully analyzed time metrics from {time_file.name}")
        print(f"  Metrics found: {len(stats)}")
        
        for metric, stat in stats.items():
            print(f"\n  {metric}:")
            print(f"    Value: {stat.mean:.6f}s")
            print(f"    Min: {stat.min:.6f}s")
            print(f"    Max: {stat.max:.6f}s")
        
        return True
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compare_time_metrics():
    """Test comparing time metrics between two algorithms."""
    print("\n" + "="*70)
    print("Test 2: Compare Time Metrics")
    print("="*70)
    
    # For this test, we'll compare the same file to itself (just for testing)
    # In real usage, you'd compare different algorithms
    time_file1 = Path("data/output/init_time_metrics_Bupa.json")
    time_file2 = Path("data/output/init_time_metrics_BupaImperfect.json")
    
    if not time_file1.exists() or not time_file2.exists():
        print(f"✗ Time metrics files not found")
        return False
    
    try:
        comparisons = compare_time_metrics(
            time_file1,
            time_file2,
            "Bupa",
            "BupaImperfect"
        )
        
        print(f"\n✓ Successfully compared time metrics")
        print(f"  Metrics compared: {len(comparisons)}")
        
        for metric, comp in comparisons.items():
            print(f"\n  {comp['metric']}:")
            print(f"    Bupa: {comp['Bupa_time']:.6f}s")
            print(f"    BupaImperfect: {comp['BupaImperfect_time']:.6f}s")
            print(f"    Difference: {comp['difference']:.6f}s")
            print(f"    % Difference: {comp['percent_difference']:.2f}%")
            print(f"    Faster: {comp['faster_algorithm']}")
        
        return True
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("Testing Time Metrics Analysis Module")
    print("="*70 + "\n")
    
    results = []
    
    # Test 1: Analyze time metrics
    results.append(("Analyze time metrics", test_analyze_time_metrics()))
    
    # Test 2: Compare time metrics
    results.append(("Compare time metrics", test_compare_time_metrics()))
    
    # Summary
    print("\n" + "="*70)
    print("Test Results")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ Passed" if passed else "✗ Failed"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n" + "="*70)
        print("✓ All tests passed!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("✗ Some tests failed!")
        print("="*70)
        sys.exit(1)


if __name__ == "__main__":
    main()
