#!/usr/bin/env python3
"""
Parse existing ANYBURL output file and generate JSON results
"""
import sys
import os
import json
import re

# Configuration
RULES_FILE = '/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/2026-01-12_00-08-08_anyburl/-100'
OUTPUT_JSON = '/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/ANYBURL_BupaImperfect_results.json'


class Predicate:
    def __init__(self, variable1, relation, variable2):
        self.variable1 = variable1
        self.relation = relation
        self.variable2 = variable2
    
    def __repr__(self):
        return f"Predicate(variable1='{self.variable1}', relation='{self.relation}', variable2='{self.variable2}')"


class TGDRule:
    def __init__(self, body, head, confidence=None, support=None):
        self.body = body  # list of Predicate
        self.head = head  # list of Predicate
        self.confidence = confidence
        self.support = support
    
    def __repr__(self):
        body_str = ", ".join(str(p) for p in self.body)
        head_str = ", ".join(str(p) for p in self.head)
        return f"{body_str} => {head_str}"


def _parse_predicate_token(token):
    """Parse a single predicate token like 'drinks.arg2(X,"6.000")'"""
    pattern = r'\s*([A-Za-z0-9_:/.-]+)\s*\(\s*([^,\)]+)\s*,\s*([^\)]+)\s*\)\s*'
    m = re.match(pattern, token.strip())
    if m:
        rel = m.group(1)
        v1 = m.group(2).strip()
        v2 = m.group(3).strip()
        return Predicate(variable1=v1, relation=rel, variable2=v2)
    return None


def _parse_literals(part):
    """Parse comma-separated predicates, respecting parentheses"""
    tokens = []
    current = []
    depth = 0
    
    for char in part:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            tokens.append(''.join(current).strip())
            current = []
            continue
        current.append(char)
    
    if current:
        tokens.append(''.join(current).strip())
    
    predicates = []
    for tok in tokens:
        tok = tok.strip()
        if tok:
            pred = _parse_predicate_token(tok)
            if pred:
                predicates.append(pred)
    
    return predicates


def parse_anyburl_rules(file_path):
    """Parse ANYBURL output file"""
    rules = []
    
    pat_le = re.compile(r"^(.+?)\s*<=\s*(.+?)$")
    pat_ge = re.compile(r"^(.+?)\s*>=\s*(.+?)$")
    
    with open(file_path, 'r') as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            
            parts = s.split('\t')
            
            if len(parts) >= 4:
                # Tab-separated format
                support_str = parts[0].strip()
                correct_str = parts[1].strip()
                conf_str = parts[2].strip()
                rule_str = parts[3].strip()
                
                try:
                    support = int(float(support_str))
                    confidence = float(conf_str)
                except:
                    continue
            else:
                # Non-tab format
                support = None
                confidence = None
                rule_str = s
            
            # Parse rule string
            m = pat_le.match(rule_str)
            if m:
                head_part = m.group(1).strip()
                body_part = m.group(2).strip()
            else:
                m = pat_ge.match(rule_str)
                if m:
                    body_part = m.group(1).strip()
                    head_part = m.group(2).strip()
                else:
                    continue
            
            body_preds = _parse_literals(body_part)
            head_preds = _parse_literals(head_part)
            
            if not body_preds or not head_preds:
                continue
            
            rule = TGDRule(
                body=body_preds,
                head=head_preds,
                confidence=confidence,
                support=support
            )
            rules.append(rule)
    
    return rules

def main():
    print(f"Parsing ANYBURL rules from: {RULES_FILE}")
    print(f"Output will be saved to: {OUTPUT_JSON}")
    
    # Parse the rules file
    rules = parse_anyburl_rules(RULES_FILE)
    
    print(f"\nParsed {len(rules)} rules")
    
    # Convert to JSON format
    results = []
    for i, rule in enumerate(rules, 1):
        rule_dict = {
            "id": i,
            "body": [
                {
                    "variable1": pred.variable1,
                    "relation": pred.relation,
                    "variable2": pred.variable2
                }
                for pred in rule.body
            ],
            "head": [
                {
                    "variable1": pred.variable1,
                    "relation": pred.relation,
                    "variable2": pred.variable2
                }
                for pred in rule.head
            ],
            "confidence": rule.confidence,
            "support": rule.support
        }
        results.append(rule_dict)
    
    # Save to JSON
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nSuccessfully saved {len(results)} rules to {OUTPUT_JSON}")
    
    # Show first 3 rules
    print("\nFirst 3 rules:")
    for i, rule in enumerate(rules[:3], 1):
        print(f"\n{i}. {rule}")
        print(f"   Confidence: {rule.confidence:.4f}")
        print(f"   Support: {rule.support}")

if __name__ == "__main__":
    main()
