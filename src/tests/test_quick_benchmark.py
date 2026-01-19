#!/usr/bin/env python3
"""
Quick test benchmark with new metrics
"""

import subprocess
import sys
from pathlib import Path

def run_quick_benchmark():
    """Run a quick benchmark test with MATILDA and one other algorithm."""
    
    print("🚀 Running quick benchmark test...")
    print("=" * 60)
    
    # Use only MATILDA and POPPER for a quick test (both are fast)
    cmd = [
        sys.executable,
        "run_full_benchmark.py",
        "--datasets", "Bupa",
        "--algorithms", "MATILDA", "POPPER",
        "--num-runs", "1",
        "--timeout", "30"
    ]
    
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("\n✅ Benchmark completed successfully")
            
            # Now run comparison
            print("\n" + "=" * 60)
            print("🔍 Generating comparison report...\n")
            
            compare_cmd = [sys.executable, "compare_matilda_benchmark.py"]
            compare_result = subprocess.run(
                compare_cmd,
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            print(compare_result.stdout)
            
            if compare_result.returncode == 0:
                print("\n✅ Comparison report generated")
                
                # Run test
                print("\n" + "=" * 60)
                print("🧪 Running validation tests...\n")
                
                test_cmd = [sys.executable, "test_new_metrics.py"]
                test_result = subprocess.run(
                    test_cmd,
                    cwd=Path(__file__).parent,
                    capture_output=True,
                    text=True
                )
                
                print(test_result.stdout)
                
                return test_result.returncode == 0
            else:
                print("\n❌ Comparison failed")
                return False
        else:
            print(f"\n❌ Benchmark failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ Benchmark timed out")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = run_quick_benchmark()
    sys.exit(0 if success else 1)
