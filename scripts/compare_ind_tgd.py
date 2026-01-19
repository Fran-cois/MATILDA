"""
Analyze and compare Inclusion Dependencies vs MATILDA TGD Rules on BupaImperfect dataset.
"""

import sqlite3
import json
from typing import List, Dict

def analyze_inclusion_dependencies(db_path: str) -> List[Dict]:
    """Analyze inclusion dependencies in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    inclusion_deps = []
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]
        
        if row_count == 0:
            continue
        
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        
        for col in cols:
            col_name = col[1]
            
            for target_table in tables:
                if target_table == table:
                    continue
                
                cursor.execute(f"PRAGMA table_info({target_table})")
                target_cols = cursor.fetchall()
                
                for target_col in target_cols:
                    target_col_name = target_col[1]
                    
                    # Count total non-null values
                    cursor.execute(f"""
                        SELECT COUNT(DISTINCT {col_name})
                        FROM {table}
                        WHERE {col_name} IS NOT NULL
                    """)
                    total = cursor.fetchone()[0]
                    
                    if total == 0:
                        continue
                    
                    # Count matching values
                    cursor.execute(f"""
                        SELECT COUNT(DISTINCT s.{col_name})
                        FROM {table} s
                        INNER JOIN {target_table} t ON s.{col_name} = t.{target_col_name}
                        WHERE s.{col_name} IS NOT NULL
                    """)
                    matching = cursor.fetchone()[0]
                    
                    coverage = matching / total if total > 0 else 0
                    
                    if coverage >= 0.70:  # At least 70% coverage
                        inclusion_deps.append({
                            "source_table": table,
                            "source_column": col_name,
                            "target_table": target_table,
                            "target_column": target_col_name,
                            "total_values": total,
                            "matching_values": matching,
                            "confidence": coverage,
                            "ind": f"{table}.{col_name} ⊆ {target_table}.{target_col_name}"
                        })
    
    conn.close()
    return sorted(inclusion_deps, key=lambda x: x['confidence'], reverse=True)


def load_matilda_rules(results_file: str) -> List[Dict]:
    """Load MATILDA TGD rules from results file."""
    try:
        with open(results_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def tgd_to_ind_format(tgd_rule: Dict) -> str:
    """
    Try to convert a simple TGD rule to IND format.
    Example: ∀ x0: bupa_0(arg2=x0) ⇒ bupa_type_0(arg1=x0)
    Converts to: bupa.arg2 ⊆ bupa_type.arg1
    """
    import re
    
    # Extract body and head predicates
    display = tgd_rule['display']
    
    # Pattern for simple unary TGD: ∀ x: P(col=x) ⇒ Q(col=x)
    pattern = r'∀ (\w+): (\w+)\((\w+)=\1\) ⇒ (\w+)\((\w+)=\1\)'
    match = re.search(pattern, display)
    
    if match:
        var, body_rel, body_col, head_rel, head_col = match.groups()
        # Extract table names (remove _0 suffix)
        body_table = body_rel.rsplit('_', 1)[0]
        head_table = head_rel.rsplit('_', 1)[0]
        return f"{body_table}.{body_col} ⊆ {head_table}.{head_col}"
    
    return None


def compare_results(inds: List[Dict], tgds: List[Dict]):
    """Compare Inclusion Dependencies with MATILDA TGD rules."""
    
    print("=" * 100)
    print("COMPARISON: INCLUSION DEPENDENCIES vs MATILDA TGD RULES")
    print("=" * 100)
    
    print(f"\n📊 Summary:")
    print(f"  • Inclusion Dependencies found: {len(inds)}")
    print(f"  • MATILDA TGD rules found: {len(tgds)}")
    
    # Group INDs by confidence
    print(f"\n{'='*100}")
    print(f"INCLUSION DEPENDENCIES (sorted by confidence)")
    print(f"{'='*100}")
    
    for i, ind in enumerate(inds, 1):
        print(f"\n{i}. {ind['ind']}")
        print(f"   Confidence: {ind['confidence']*100:.1f}% ({ind['matching_values']}/{ind['total_values']} values)")
    
    # Show MATILDA rules
    print(f"\n{'='*100}")
    print(f"MATILDA TGD RULES")
    print(f"{'='*100}")
    
    if tgds:
        for i, tgd in enumerate(tgds, 1):
            print(f"\n{i}. {tgd['display']}")
            print(f"   Accuracy: {tgd['accuracy']:.3f}, Confidence: {tgd['confidence']:.3f}")
            
            # Try to convert to IND format
            ind_format = tgd_to_ind_format(tgd)
            if ind_format:
                print(f"   ≈ IND: {ind_format}")
    else:
        print("\n❌ No TGD rules discovered by MATILDA")
    
    # Matching analysis
    print(f"\n{'='*100}")
    print(f"MATCHING ANALYSIS")
    print(f"{'='*100}")
    
    if tgds:
        print("\n🔍 Attempting to match TGD rules with Inclusion Dependencies...")
        
        # Convert TGDs to IND-like format and compare
        tgd_as_inds = {}
        for tgd in tgds:
            ind_format = tgd_to_ind_format(tgd)
            if ind_format:
                tgd_as_inds[ind_format] = tgd
        
        matched = []
        unmatched_inds = []
        unmatched_tgds = list(tgd_as_inds.keys())
        
        for ind in inds:
            ind_str = ind['ind']
            if ind_str in tgd_as_inds:
                matched.append((ind, tgd_as_inds[ind_str]))
                unmatched_tgds.remove(ind_str)
            else:
                unmatched_inds.append(ind)
        
        print(f"\n✅ Matched (IND ≈ TGD): {len(matched)}")
        for ind, tgd in matched:
            print(f"  • {ind['ind']}")
            print(f"    IND confidence: {ind['confidence']*100:.1f}%")
            print(f"    TGD confidence: {tgd['confidence']*100:.1f}%")
            diff = abs(ind['confidence'] - tgd['confidence'])
            if diff < 0.01:
                print(f"    ✓ Very similar confidence!")
            elif diff < 0.05:
                print(f"    ~ Similar confidence (diff: {diff*100:.1f}%)")
            else:
                print(f"    ⚠ Different confidence (diff: {diff*100:.1f}%)")
        
        print(f"\n⚠️  INDs without matching TGD: {len(unmatched_inds)}")
        for ind in unmatched_inds[:5]:  # Show first 5
            print(f"  • {ind['ind']} ({ind['confidence']*100:.1f}%)")
        
        print(f"\n⚠️  TGDs without matching IND: {len(unmatched_tgds)}")
        for tgd_ind in unmatched_tgds[:5]:  # Show first 5
            print(f"  • {tgd_ind}")
    else:
        print("\n⚠️  Cannot perform matching: No MATILDA TGD rules to compare")
    
    print(f"\n{'='*100}")
    print("CONCLUSION")
    print(f"{'='*100}")
    
    print("\nKey observations:")
    print("1. Inclusion Dependencies are a subset of TGD rules")
    print("   - IND: A.col ⊆ B.col means every value in A.col exists in B.col")
    print("   - TGD: ∀x: A(col=x) ⇒ B(col=x) expresses the same constraint")
    
    print("\n2. TGD rules are more expressive:")
    print("   - Can express complex multi-column dependencies")
    print("   - Can have multiple predicates in body and head")
    print("   - INDs are simple unary TGDs")
    
    if tgds and len(matched) > 0:
        print(f"\n3. In this dataset:")
        print(f"   - {len(matched)}/{len(inds)} INDs have corresponding TGD rules")
        print(f"   - Confidence values are similar (MATILDA validates INDs)")
    else:
        print(f"\n3. In this dataset:")
        print(f"   - MATILDA discovered {len(tgds)} rules")
        print(f"   - {len(inds)} INDs were found by direct analysis")


# Main execution
if __name__ == "__main__":
    db_path = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/db/BupaImperfect.db"
    matilda_file = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/MATILDA_BupaImperfect_results.json"
    
    print("Analyzing BupaImperfect dataset...")
    print(f"Database: {db_path}")
    print(f"MATILDA results: {matilda_file}\n")
    
    # Analyze inclusion dependencies
    inds = analyze_inclusion_dependencies(db_path)
    
    # Load MATILDA rules
    tgds = load_matilda_rules(matilda_file)
    
    # Compare results
    compare_results(inds, tgds)
    
    # Save INDs to file
    output_file = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/IND_BupaImperfect_results.json"
    with open(output_file, 'w') as f:
        json.dump(inds, f, indent=2)
    
    print(f"\n\n✅ Inclusion dependencies saved to: {output_file}")
