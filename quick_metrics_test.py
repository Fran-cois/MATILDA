#!/usr/bin/env python3
"""
Quick test MATILDA metrics without full benchmark infrastructure.
Bypasses numpy/pandas dependency issues.
"""

import sys
from pathlib import Path
import time
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility

def compute_metrics():
    """Test MATILDA and compute basic metrics."""
    print("\n" + "="*80)
    print("🔬 QUICK MATILDA METRICS TEST")
    print("="*80 + "\n")
    
    # Connect to database
    db_path = Path(__file__).parent / "data" / "input" / "Bupa.db"
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    db_uri = f"sqlite:///{db_path}"
    print(f"📊 Database: {db_uri}")
    
    db = AlchemyUtility(db_uri)
    
    # MATILDA config
    config = {
        'nb_occurrence': 3,
        'max_table': 3,
        'max_vars': 4
    }
    
    print(f"⚙️  Config: {config}")
    print(f"\n{'='*80}\n")
    
    # Run MATILDA
    print("🚀 Discovering rules with MATILDA...")
    matilda = MATILDA(db, config)
    
    start = time.time()
    rules = list(matilda.discover_rules(
        traversal_algorithm='dfs',
        max_table=3,
        max_vars=4
    ))
    runtime = time.time() - start
    
    print(f"\n{'='*80}")
    print("✅ MATILDA RESULTS")
    print(f"{'='*80}\n")
    
    # Basic metrics
    metrics = {
        "algorithm": "MATILDA",
        "dataset": "Bupa",
        "runtime_seconds": round(runtime, 2),
        "rules_discovered": len(rules),
        "rules_per_second": round(len(rules) / runtime, 2) if runtime > 0 else 0
    }
    
    # Display
    for key, value in metrics.items():
        print(f"  {key:20s}: {value}")
    
    # Sample rules
    if rules:
        print(f"\n📝 Sample rules (first 5):")
        for i, rule in enumerate(rules[:5], 1):
            print(f"  {i}. {rule}")
    
    # Rule quality metrics
    if rules:
        confidences = [r.confidence for r in rules if r.confidence is not None]
        accuracies = [r.accuracy for r in rules if r.accuracy is not None]
        
        if confidences:
            metrics["avg_confidence"] = round(sum(confidences) / len(confidences), 4)
            metrics["max_confidence"] = round(max(confidences), 4)
            metrics["min_confidence"] = round(min(confidences), 4)
        
        if accuracies:
            metrics["avg_accuracy"] = round(sum(accuracies) / len(accuracies), 4)
            metrics["max_accuracy"] = round(max(accuracies), 4)
            metrics["min_accuracy"] = round(min(accuracies), 4)
        
        print(f"\n📊 Quality Metrics:")
        if confidences:
            print(f"  Confidence (avg/min/max): {metrics.get('avg_confidence', 'N/A')} / {metrics.get('min_confidence', 'N/A')} / {metrics.get('max_confidence', 'N/A')}")
        if accuracies:
            print(f"  Accuracy (avg/min/max):   {metrics.get('avg_accuracy', 'N/A')} / {metrics.get('min_accuracy', 'N/A')} / {metrics.get('max_accuracy', 'N/A')}")
    
    # Save results
    output_file = Path(__file__).parent / "quick_metrics_results.json"
    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print(f"\n{'='*80}\n")
    
    return metrics

if __name__ == "__main__":
    try:
        compute_metrics()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
