#!/usr/bin/env python3
"""
Quick Precision/Recall test for MATILDA rules.
Tests discovered rules against Bupa ground truth (Inclusion Dependencies).
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility


def normalize_rule_to_id(rule_str: str) -> str:
    """
    Normalize a TGD rule to an Inclusion Dependency representation.
    
    Example:
    "∀ x0: bupa_0(arg1=x0) ⇒ mcv_0(arg1=x0)" 
    becomes
    "bupa_0.arg1 -> mcv_0.arg1"
    """
    # Simple parsing for unary predicates with arg1
    if '⇒' not in rule_str:
        return None
    
    parts = rule_str.split('⇒')
    if len(parts) != 2:
        return None
    
    body = parts[0].strip()
    head = parts[1].strip()
    
    # Extract table and column from predicates
    # Format: table_0(arg1=x0)
    def extract_table_col(pred: str) -> Tuple[str, str]:
        if '(' not in pred or '=' not in pred:
            return None, None
        
        table_part = pred.split('(')[0].strip()
        col_part = pred.split('(')[1].split('=')[0].strip()
        
        # Remove _0, _1, etc suffixes from table names
        table = '_'.join(table_part.split('_')[:-1]) if '_' in table_part else table_part
        
        return table, col_part
    
    # Handle single predicate body (most common case for IDs)
    body_cleaned = body.split(':')[1].strip() if ':' in body else body
    head_cleaned = head.strip()
    
    # Remove conjunction symbols
    if '∧' in body_cleaned:
        # Multi-predicate body - skip for now (not simple IDs)
        return None
    
    body_table, body_col = extract_table_col(body_cleaned)
    head_table, head_col = extract_table_col(head_cleaned)
    
    if not all([body_table, body_col, head_table, head_col]):
        return None
    
    # Format: table1.col1 -> table2.col2
    return f"{body_table}.{body_col} -> {head_table}.{head_col}"


def load_ground_truth(gt_file: Path) -> Set[str]:
    """Load ground truth IDs from JSON file."""
    with open(gt_file) as f:
        data = json.load(f)
    
    ground_truth = set()
    for item in data:
        if item['type'] == 'InclusionDependency':
            left_table, left_col = item['left']
            right_table, right_col = item['right']
            id_str = f"{left_table}.{left_col} -> {right_table}.{right_col}"
            ground_truth.add(id_str)
    
    return ground_truth


def compute_precision_recall(discovered: Set[str], ground_truth: Set[str]) -> Dict:
    """Compute P/R metrics."""
    true_positives = discovered & ground_truth
    false_positives = discovered - ground_truth
    false_negatives = ground_truth - discovered
    
    tp_count = len(true_positives)
    fp_count = len(false_positives)
    fn_count = len(false_negatives)
    
    precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 0
    recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'true_positives': tp_count,
        'false_positives': fp_count,
        'false_negatives': fn_count,
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1_score': round(f1, 4),
        'matched_rules': sorted(list(true_positives)),
        'extra_rules': sorted(list(false_positives)),
        'missing_rules': sorted(list(false_negatives))
    }


def main():
    """Main test."""
    print("\n" + "="*80)
    print("🎯 PRECISION/RECALL TEST - MATILDA vs Ground Truth")
    print("="*80 + "\n")
    
    # Load ground truth
    gt_file = Path(__file__).parent / "data" / "ground_truth_bupa_real.json"
    if not gt_file.exists():
        print(f"❌ Ground truth file not found: {gt_file}")
        return
    
    print(f"📋 Ground truth: {gt_file}")
    ground_truth = load_ground_truth(gt_file)
    print(f"   Ground truth IDs: {len(ground_truth)}\n")
    
    # Discover rules with MATILDA
    db_path = Path(__file__).parent / "data" / "input" / "Bupa.db"
    db_uri = f"sqlite:///{db_path}"
    
    print(f"🔍 Discovering rules with MATILDA...")
    db = AlchemyUtility(db_uri)
    matilda = MATILDA(db, {'nb_occurrence': 3, 'max_table': 3, 'max_vars': 4})
    
    rules = list(matilda.discover_rules(traversal_algorithm='dfs', max_table=3, max_vars=4))
    print(f"   Total rules discovered: {len(rules)}\n")
    
    # Convert rules to ID format
    print("🔄 Converting rules to Inclusion Dependencies...")
    discovered_ids = set()
    for rule in rules:
        id_str = normalize_rule_to_id(rule.display)
        if id_str:
            discovered_ids.add(id_str)
    
    print(f"   Convertible IDs: {len(discovered_ids)}\n")
    
    # Compute P/R
    print("="*80)
    print("📊 PRECISION/RECALL RESULTS")
    print("="*80 + "\n")
    
    metrics = compute_precision_recall(discovered_ids, ground_truth)
    
    print(f"True Positives:  {metrics['true_positives']}")
    print(f"False Positives: {metrics['false_positives']}")
    print(f"False Negatives: {metrics['false_negatives']}")
    print()
    print(f"Precision: {metrics['precision']:.2%}")
    print(f"Recall:    {metrics['recall']:.2%}")
    print(f"F1-Score:  {metrics['f1_score']:.2%}")
    
    # Details
    if metrics['matched_rules']:
        print(f"\n✅ Matched rules ({len(metrics['matched_rules'])}):")
        for rule in metrics['matched_rules'][:10]:  # Show first 10
            print(f"   - {rule}")
        if len(metrics['matched_rules']) > 10:
            print(f"   ... and {len(metrics['matched_rules']) - 10} more")
    
    if metrics['missing_rules']:
        print(f"\n❌ Missing from discovered ({len(metrics['missing_rules'])}):")
        for rule in metrics['missing_rules']:
            print(f"   - {rule}")
    
    if metrics['extra_rules']:
        print(f"\n🔍 Extra rules discovered ({min(10, len(metrics['extra_rules']))}/{len(metrics['extra_rules'])}):")
        for rule in metrics['extra_rules'][:10]:
            print(f"   - {rule}")
        if len(metrics['extra_rules']) > 10:
            print(f"   ... and {len(metrics['extra_rules']) - 10} more")
    
    # Save results
    output_file = Path(__file__).parent / "precision_recall_results.json"
    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
