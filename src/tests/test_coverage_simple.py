#!/usr/bin/env python3
"""
Test simple de coverage metrics
"""

import json
from pathlib import Path

# Charger les données existantes
output_dir = Path("data/output")

# MATILDA BupaImperfect
matilda_file = output_dir / "MATILDA_BupaImperfect_results.json"
spider_file = output_dir / "SPIDER_BupaImperfect_results.json"

if matilda_file.exists() and spider_file.exists():
    with open(matilda_file) as f:
        matilda_rules = json.load(f)
    with open(spider_file) as f:
        spider_rules = json.load(f)
    
    print(f"MATILDA rules: {len(matilda_rules)}")
    print(f"SPIDER rules: {len(spider_rules)}")
    
    # Simple matching
    import re
    
    def extract_tables_from_tgd(rule):
        tables = set()
        for body_pred in rule.get('body', []):
            if 'relation=' in body_pred:
                match = re.search(r"relation='([^']+)'", body_pred)
                if match:
                    tables.add(match.group(1).replace('_0', '').lower())
        for head_pred in rule.get('head', []):
            if 'relation=' in head_pred:
                match = re.search(r"relation='([^']+)'", head_pred)
                if match:
                    tables.add(match.group(1).replace('_0', '').lower())
        return tables
    
    # Count matches
    matches = 0
    for spider_rule in spider_rules:
        dep_table = spider_rule.get('table_dependant', '').lower()
        ref_table = spider_rule.get('table_referenced', '').lower()
        
        for matilda_rule in matilda_rules:
            tgd_tables = extract_tables_from_tgd(matilda_rule)
            if dep_table in tgd_tables and ref_table in tgd_tables:
                matches += 1
                break
    
    print(f"\nMatches: {matches}/{len(spider_rules)} ({matches/len(spider_rules)*100:.1f}%)")
    print(f"Coverage: {matches}/{len(spider_rules)} règles SPIDER correspondantes dans MATILDA")
else:
    print("❌ Fichiers de résultats introuvables")
