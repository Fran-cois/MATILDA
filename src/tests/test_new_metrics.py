#!/usr/bin/env python3
"""
Test script to verify the new original_accuracy and original_coverage fields
"""

import json
from pathlib import Path

def test_metrics_in_rules():
    """Check if rules have the new original_accuracy and original_coverage fields."""
    
    # Find the most recent experiment
    mlruns_dir = Path("data/output/mlruns")
    
    if not mlruns_dir.exists():
        print("❌ MLflow runs directory not found")
        return False
    
    experiments = [d for d in mlruns_dir.iterdir() if d.is_dir()]
    if not experiments:
        print("❌ No experiments found")
        return False
    
    # Get latest experiment (by modification time)
    latest_exp = max(experiments, key=lambda x: x.stat().st_mtime)
    print(f"✓ Checking latest experiment: {latest_exp.name}")
    
    # Find all run directories
    run_dirs = [d for d in latest_exp.iterdir() if d.is_dir() and (d / "rules.json").exists()]
    
    if not run_dirs:
        print("❌ No run directories with rules.json found")
        return False
    
    print(f"✓ Found {len(run_dirs)} runs to check")
    
    # Check a sample of rules
    success_count = 0
    fail_count = 0
    
    for run_dir in run_dirs[:3]:  # Check first 3 runs
        rules_file = run_dir / "rules.json"
        
        try:
            with open(rules_file) as f:
                rules = json.load(f)
            
            if not rules:
                print(f"  ⚠️  {run_dir.name}: No rules found")
                continue
            
            # Check if first rule has new fields
            first_rule = rules[0] if isinstance(rules, list) else rules
            
            if isinstance(first_rule, dict):
                has_orig_acc = 'original_accuracy' in first_rule
                has_orig_cov = 'original_coverage' in first_rule
                
                if has_orig_acc and has_orig_cov:
                    print(f"  ✓ {run_dir.name}: Has original_accuracy={first_rule['original_accuracy']:.2f}, "
                          f"original_coverage={first_rule['original_coverage']:.2f}")
                    success_count += 1
                else:
                    print(f"  ❌ {run_dir.name}: Missing fields (has_orig_acc={has_orig_acc}, has_orig_cov={has_orig_cov})")
                    fail_count += 1
            else:
                print(f"  ⚠️  {run_dir.name}: Unexpected rule format")
                
        except Exception as e:
            print(f"  ❌ {run_dir.name}: Error reading rules: {e}")
            fail_count += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {success_count} success, {fail_count} failures")
    
    return success_count > 0 and fail_count == 0


def test_comparison_report():
    """Check if comparison report includes original metrics."""
    
    mlruns_dir = Path("data/output/mlruns")
    experiments = [d for d in mlruns_dir.iterdir() if d.is_dir()]
    
    if not experiments:
        print("❌ No experiments found")
        return False
    
    latest_exp = max(experiments, key=lambda x: x.stat().st_mtime)
    report_file = latest_exp / "MATILDA_COMPARISON_REPORT.md"
    
    if not report_file.exists():
        print(f"⚠️  Comparison report not found at {report_file}")
        return False
    
    with open(report_file) as f:
        content = f.read()
    
    has_quality_section = "Quality Metrics" in content or "Original Accuracy" in content
    
    if has_quality_section:
        print(f"✓ Comparison report contains quality metrics section")
        return True
    else:
        print(f"❌ Comparison report missing quality metrics section")
        return False


if __name__ == "__main__":
    print("Testing new original_accuracy and original_coverage fields...\n")
    
    print("\n1. Testing rules.json files:")
    print("-" * 60)
    rules_ok = test_metrics_in_rules()
    
    print("\n2. Testing comparison report:")
    print("-" * 60)
    report_ok = test_comparison_report()
    
    print("\n" + "=" * 60)
    if rules_ok and report_ok:
        print("✅ All tests passed!")
    elif rules_ok:
        print("⚠️  Rules have new fields, but report needs regeneration")
        print("   Run: python compare_matilda_benchmark.py")
    else:
        print("❌ Tests failed - new metrics not found in rules")
        print("   Need to run a new benchmark to generate rules with new fields")
