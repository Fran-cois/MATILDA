#!/usr/bin/env python3
"""
Compare ANYBURL results with MATILDA and POPPER
"""
import json
import re

# Read ANYBURL rules
anyburl_file = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/2026-01-12_00-08-08_anyburl/-100"
anyburl_rules = []

print("=== ANYBURL RULES ===\n")
with open(anyburl_file, 'r') as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) >= 4:
            support = int(parts[0])
            correct_preds = int(parts[1])
            confidence = float(parts[2])
            rule_str = parts[3]
            anyburl_rules.append({
                'rule': rule_str,
                'support': support,
                'correct_predictions': correct_preds,
                'confidence': confidence
            })

print(f"Total ANYBURL rules: {len(anyburl_rules)}\n")
print("Sample rules (first 10):")
for i, rule in enumerate(anyburl_rules[:10]):
    print(f"{i+1}. {rule['rule']}")
    print(f"   Support: {rule['support']}, Confidence: {rule['confidence']:.4f}\n")

# Read MATILDA results
matilda_file = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/MATILDA_BupaImperfect_results.json"
with open(matilda_file, 'r') as f:
    matilda_rules = json.load(f)

print(f"\n=== MATILDA RULES ===\n")
print(f"Total MATILDA rules: {len(matilda_rules)}\n")

# Focus on the bupa -> bupa_name rule similar to POPPER
matilda_bupa_rule = None
for rule in matilda_rules:
    if 'bupa_0' in rule['display'] and 'bupa_name_0' in rule['display']:
        matilda_bupa_rule = rule
        break

if matilda_bupa_rule:
    print("MATILDA rule (bupa -> bupa_name):")
    print(f"  {matilda_bupa_rule['display']}")
    print(f"  Confidence: {matilda_bupa_rule['confidence']:.4f}")
    if 'support' in matilda_bupa_rule:
        print(f"  Support: {matilda_bupa_rule['support']:.4f}")
    print(f"  Accuracy: {matilda_bupa_rule['accuracy']:.4f}\n")

# Read POPPER results
popper_file = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/POPPER_BupaImperfect_results.json"
with open(popper_file, 'r') as f:
    popper_rules = json.load(f)

print(f"=== POPPER RULES ===\n")
print(f"Total POPPER rules: {len(popper_rules)}\n")

if popper_rules:
    popper_rule = popper_rules[0]
    print("POPPER rule:")
    print(f"  {popper_rule['display']}")
    print(f"  Accuracy: {popper_rule['accuracy']:.4f}\n")

# Find similar ANYBURL rules
print("=== ANYBURL RULES (related to bupa/bupa_name) ===\n")
bupa_related = [r for r in anyburl_rules if 'bupa.arg1' in r['rule'] or 'bupa_name.arg1' in r['rule']]
print(f"Found {len(bupa_related)} bupa-related rules\n")

for i, rule in enumerate(bupa_related[:5]):
    print(f"{i+1}. {rule['rule']}")
    print(f"   Support: {rule['support']}, Confidence: {rule['confidence']:.4f}\n")

# Summary comparison
print("\n=== SUMMARY COMPARISON ===\n")
print(f"ANYBURL: {len(anyburl_rules)} rules discovered")
print(f"MATILDA: {len(matilda_rules)} rules discovered")
print(f"POPPER:  {len(popper_rules)} rules discovered")

print("\n=== METRICS FOR bupa -> bupa_name RULE ===\n")
if popper_rule:
    print(f"POPPER Accuracy:    {popper_rule['accuracy']:.4f} ({popper_rule['accuracy']*100:.2f}%)")
if matilda_bupa_rule:
    print(f"MATILDA Confidence: {matilda_bupa_rule['confidence']:.4f} ({matilda_bupa_rule['confidence']*100:.2f}%)")

# Look for the most similar ANYBURL rule
# The closest would be something like: bupa_name.arg1(X,Y) <= bupa.arg1(X,A)
print("\n=== CLOSEST ANYBURL RULE ===")
for rule in anyburl_rules:
    if ('bupa_name.arg1' in rule['rule'] and '<= bupa.arg1' in rule['rule']) or \
       ('bupa_name.arg2' in rule['rule'] and '<= bupa.arg2' in rule['rule']):
        print(f"\nRule: {rule['rule']}")
        print(f"Support: {rule['support']}, Confidence: {rule['confidence']:.4f} ({rule['confidence']*100:.2f}%)")
        break
else:
    print("\nNo direct bupa -> bupa_name implication found in ANYBURL rules.")
    print("ANYBURL discovers different types of rules (forward chaining with variables).")
