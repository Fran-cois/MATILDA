#!/usr/bin/env python3
"""
Run all algorithms on Bupa database and compute metrics.
"""

import sys
import os
import subprocess
import json
import yaml
from pathlib import Path
from datetime import datetime

# Add src to path - fix path to point to project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

def run_algorithm(algorithm_name, database_name="Bupa.db"):
    """Run a single algorithm on the database."""
    print(f"\n{'='*80}")
    print(f"🚀 Running {algorithm_name.upper()} on {database_name}")
    print(f"{'='*80}\n")
    
    config = {
        "algorithm": {
            "name": algorithm_name,
            "matilda": {
                "traversal_algorithm": "dfs"
            }
        },
        "database": {
            "name": database_name,
            "path": str(Path(__file__).parent / "data" / "db")
        },
        "results": {
            "output_dir": str(Path(__file__).parent / "data" / "output"),
            "compute_statistics": True,
            "generate_statistical_report": True
        },
        "logging": {
            "log_dir": str(Path(__file__).parent / "logs")
        },
        "monitor": {
            "timeout": 3600
        },
        "mlflow": {
            "use": False
        }
    }
    
    # Save temporary config
    temp_config = Path("temp_config.yaml")
    with open(temp_config, 'w') as f:
        yaml.dump(config, f)
    
    try:
        # Run main.py from src directory to avoid module import issues
        result = subprocess.run(
            [sys.executable, "main.py", "--config", str(temp_config.absolute())],
            cwd=str(project_root / "src"),
            timeout=7200  # 2 hour timeout
        )
        
        if result.returncode == 0:
            print(f"✅ {algorithm_name.upper()} completed successfully")
            return True
        else:
            print(f"❌ {algorithm_name.upper()} failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏱️  {algorithm_name.upper()} timed out")
        return False
    except Exception as e:
        print(f"❌ Error running {algorithm_name.upper()}: {e}")
        return False
    finally:
        # Clean up
        if temp_config.exists():
            temp_config.unlink()


def main():
    """Main execution."""
    algorithms = ["SPIDER", "POPPER", "AMIE3", "ANYBURL"]
    database = "Bupa.db"
    
    print(f"\n{'='*80}")
    print(f"📊 RUNNING BUPA EXPERIMENTS")
    print(f"{'='*80}")
    print(f"Database: {database}")
    print(f"Algorithms: {', '.join(algorithms)}")
    print(f"{'='*80}\n")
    
    results = {}
    for algo in algorithms:
        success = run_algorithm(algo, database)
        results[algo] = "success" if success else "failed"
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📋 SUMMARY")
    print(f"{'='*80}")
    for algo, status in results.items():
        symbol = "✅" if status == "success" else "❌"
        print(f"{symbol} {algo:12s} : {status}")
    print(f"{'='*80}\n")
    
    # Check if all succeeded
    all_success = all(v == "success" for v in results.values())
    if all_success:
        print("🎉 All experiments completed successfully!")
        print("\nNow computing metrics with: python3 compute_all_metrics.py --algorithm all")
    
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
