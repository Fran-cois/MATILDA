#!/usr/bin/env python3
"""
Quick Test for LaTeX Table Generation

Tests both scripts to ensure they work correctly.
"""

import sys
import subprocess
from pathlib import Path

def test_generate_latex_table():
    """Test generate_latex_table.py script."""
    print("="*70)
    print("Test 1: Generate LaTeX Table (from existing results)")
    print("="*70)
    
    try:
        result = subprocess.run(
            [sys.executable, "generate_latex_table.py", "--detailed"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✓ Script executed successfully")
            
            # Check if table was generated
            output_dir = Path("data/output")
            latex_files = list(output_dir.glob("latex_table_detailed_*.tex"))
            
            if latex_files:
                latest_file = max(latex_files, key=lambda p: p.stat().st_mtime)
                print(f"✓ Table generated: {latest_file.name}")
                
                # Check file content
                with open(latest_file, 'r') as f:
                    content = f.read()
                    if "\\begin{table}" in content and "\\end{table}" in content:
                        print("✓ Valid LaTeX table structure")
                        return True
                    else:
                        print("✗ Invalid LaTeX structure")
                        return False
            else:
                print("✗ No table file found")
                return False
        else:
            print(f"✗ Script failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_results_existence():
    """Check if result files exist."""
    print("\n" + "="*70)
    print("Test 2: Check Existing Results")
    print("="*70)
    
    output_dir = Path("data/output")
    
    if not output_dir.exists():
        print(f"✗ Output directory not found: {output_dir}")
        return False
    
    # Check for result files
    result_files = list(output_dir.glob("*_results.json"))
    time_files = list(output_dir.glob("init_time_metrics_*.json"))
    
    print(f"✓ Output directory: {output_dir}")
    print(f"✓ Result files found: {len(result_files)}")
    print(f"✓ Time metric files found: {len(time_files)}")
    
    if result_files:
        print(f"\nSample result files:")
        for f in result_files[:5]:
            print(f"  - {f.name}")
    
    return len(result_files) > 0


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("Testing LaTeX Table Generation Scripts")
    print("="*70 + "\n")
    
    results = []
    
    # Test 1: Check existing results
    results.append(("Check existing results", test_results_existence()))
    
    # Test 2: Generate LaTeX table
    results.append(("Generate LaTeX table", test_generate_latex_table()))
    
    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n" + "="*70)
        print("✓ All tests passed!")
        print("="*70)
        print("\nYou can now use:")
        print("  python generate_latex_table.py --detailed")
        print("  python run_benchmark.py --runs 5")
    else:
        print("\n" + "="*70)
        print("✗ Some tests failed")
        print("="*70)
        sys.exit(1)


if __name__ == "__main__":
    main()
