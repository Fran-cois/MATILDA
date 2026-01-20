#!/usr/bin/env python3
"""Quick scalability test with logging disabled."""
import sys
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility

# Test configurations
TESTS = [
    ("Bupa-345", "data/input/Bupa.db", 3, 4),  # baseline
    ("Bupa-1K", "data/scalability/Bupa-1K.db", 2, 3),  # reduced complexity
    ("Bupa-5K", "data/scalability/Bupa-5K.db", 2, 3),
    ("Bupa-10K", "data/scalability/Bupa-10K.db", 2, 3),
]

results = []

print("\n" + "="*80)
print("🚀 SCALABILITY TEST - MATILDA (Logging Disabled)")
print("="*80 + "\n")

for name, db_path, max_table, max_vars in TESTS:
    print(f"\n{'='*80}")
    print(f"📊 Testing: {name} (max_table={max_table}, max_vars={max_vars})")
    print(f"{'='*80}")
    
    db_file = Path(__file__).parent / db_path
    if not db_file.exists():
        print(f"❌ Database not found: {db_file}")
        continue
    
    try:
        # Connect
        db_uri = f"sqlite:///{db_file}"
        db = AlchemyUtility(db_uri)
        
        # Configure MATILDA
        config = {
            'nb_occurrence': 3,
            'max_table': max_table,
            'max_vars': max_vars
        }
        
        matilda = MATILDA(db, config)
        
        # Run discovery
        print(f"🔍 Discovering rules...")
        start = time.time()
        rules = list(matilda.discover_rules(
            traversal_algorithm='dfs',
            max_table=max_table,
            max_vars=max_vars
        ))
        runtime = time.time() - start
        
        # Calculate metrics
        throughput = len(rules) / runtime if runtime > 0 else 0
        
        result = {
            "dataset": name,
            "rules": len(rules),
            "runtime_sec": round(runtime, 2),
            "throughput_rps": round(throughput, 2),
            "max_table": max_table,
            "max_vars": max_vars
        }
        
        results.append(result)
        
        print(f"\n✅ {name}: {len(rules)} rules in {runtime:.2f}s ({throughput:.2f} r/s)")
        
    except Exception as e:
        print(f"\n❌ Error testing {name}: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            "dataset": name,
            "error": str(e),
            "max_table": max_table,
            "max_vars": max_vars
        })

# Summary
print("\n" + "="*80)
print("📈 SCALABILITY RESULTS SUMMARY")
print("="*80 + "\n")

for r in results:
    if "error" not in r:
        print(f"{r['dataset']:12s}: {r['rules']:5d} rules | {r['runtime_sec']:7.2f}s | {r['throughput_rps']:7.2f} r/s")
    else:
        print(f"{r['dataset']:12s}: ERROR - {r['error']}")

# Save results
output_file = Path(__file__).parent / "scalability_results.json"
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n💾 Results saved to: {output_file}")
print("\n" + "="*80 + "\n")
