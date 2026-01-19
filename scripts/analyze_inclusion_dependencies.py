"""
Analyze inclusion dependencies in the ComparisonDataset and compare with MATILDA results.
"""

import sqlite3
import json
from collections import defaultdict

# Connect to database
db_path = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/db/ComparisonDataset.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("INCLUSION DEPENDENCIES ANALYSIS")
print("=" * 80)

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

print(f"\nTables found: {', '.join(tables)}")

# Analyze each table for foreign key relationships
inclusion_deps = []

for table in tables:
    # Get table structure
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    row_count = cursor.fetchone()[0]
    
    if row_count == 0:
        continue
    
    print(f"\n{'='*80}")
    print(f"Table: {table} ({row_count} rows)")
    print(f"{'='*80}")
    
    # Check each column for potential foreign key relationships
    cursor.execute(f"PRAGMA table_info({table})")
    cols = cursor.fetchall()
    
    for col in cols:
        col_name = col[1]
        
        # Try to find matching columns in other tables
        for target_table in tables:
            if target_table == table:
                continue
            
            cursor.execute(f"PRAGMA table_info({target_table})")
            target_cols = cursor.fetchall()
            
            for target_col in target_cols:
                target_col_name = target_col[1]
                
                # Check inclusion dependency: table.col_name ⊆ target_table.target_col_name
                # Count how many values in source are in target
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT s.{col_name}) as total
                    FROM {table} s
                    WHERE s.{col_name} IS NOT NULL
                """)
                total_non_null = cursor.fetchone()[0]
                
                if total_non_null == 0:
                    continue
                
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT s.{col_name}) as matching
                    FROM {table} s
                    INNER JOIN {target_table} t ON s.{col_name} = t.{target_col_name}
                    WHERE s.{col_name} IS NOT NULL
                """)
                matching = cursor.fetchone()[0]
                
                coverage = matching / total_non_null if total_non_null > 0 else 0
                
                # Only report high coverage (potential INDs)
                if coverage >= 0.75:  # At least 75% coverage
                    dep = {
                        "source": f"{table}.{col_name}",
                        "target": f"{target_table}.{target_col_name}",
                        "total_values": total_non_null,
                        "matching_values": matching,
                        "coverage": coverage,
                        "confidence": coverage
                    }
                    inclusion_deps.append(dep)
                    
                    print(f"\n  ✓ {table}.{col_name} ⊆ {target_table}.{target_col_name}")
                    print(f"    Coverage: {matching}/{total_non_null} = {coverage*100:.1f}%")

print(f"\n{'='*80}")
print(f"SUMMARY: Found {len(inclusion_deps)} Inclusion Dependencies")
print(f"{'='*80}")

# Sort by coverage
inclusion_deps.sort(key=lambda x: x['coverage'], reverse=True)

print("\nAll Inclusion Dependencies (sorted by confidence):")
for i, dep in enumerate(inclusion_deps, 1):
    print(f"{i}. {dep['source']} ⊆ {dep['target']}")
    print(f"   Confidence: {dep['confidence']*100:.1f}% ({dep['matching_values']}/{dep['total_values']})")

# Try to load MATILDA results
print(f"\n{'='*80}")
print("MATILDA RESULTS COMPARISON")
print(f"{'='*80}")

matilda_file = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/MATILDA_ComparisonDataset_results.json"
try:
    with open(matilda_file, 'r') as f:
        matilda_rules = json.load(f)
    
    print(f"\nMATILDA discovered {len(matilda_rules)} TGD rules")
    
    if len(matilda_rules) > 0:
        print("\nMATILDA Rules:")
        for i, rule in enumerate(matilda_rules, 1):
            print(f"{i}. {rule['display']}")
            print(f"   Accuracy: {rule['accuracy']}, Confidence: {rule['confidence']}")
        
        # Try to match TGD rules with inclusion dependencies
        print(f"\n{'='*80}")
        print("MAPPING: Inclusion Dependencies ↔ TGD Rules")
        print(f"{'='*80}")
        
        print("\nNote: TGD rules are more expressive than inclusion dependencies.")
        print("A simple IND like 'students.dept_id ⊆ departments.id' corresponds to:")
        print("  ∀x: students(dept_id=x) ⇒ departments(id=x)")
        
        # Extract simple binary TGD rules that look like INDs
        simple_tgds = []
        for rule in matilda_rules:
            if len(rule['body']) == 1 and len(rule['head']) == 1:
                simple_tgds.append(rule)
        
        if simple_tgds:
            print(f"\nFound {len(simple_tgds)} simple binary TGD rules (potential INDs):")
            for tgd in simple_tgds:
                print(f"  • {tgd['display']}")
                print(f"    Confidence: {tgd['confidence']*100:.1f}%")
    else:
        print("\n❌ No MATILDA rules discovered (likely due to high violation rates)")
        print("   MATILDA may require lower violation rates or different parameters")
        
except FileNotFoundError:
    print(f"\n❌ MATILDA results file not found: {matilda_file}")
    print("   Run MATILDA first with: algorithm: name: \"MATILDA\"")

# Save inclusion dependencies to JSON
output_file = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/IND_ComparisonDataset_results.json"
with open(output_file, 'w') as f:
    json.dump(inclusion_deps, f, indent=2)

print(f"\n✅ Inclusion dependencies saved to: {output_file}")

conn.close()

print(f"\n{'='*80}")
print("ANALYSIS COMPLETE")
print(f"{'='*80}")
