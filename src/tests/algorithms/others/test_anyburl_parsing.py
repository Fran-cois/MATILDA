#!/usr/bin/env python3
"""Test ANYBURL parsing with existing file"""
import sys
import re
sys.path.insert(0, '/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/src')

from utils.rules import Predicate, TGDRule

def parse_predicate_token(token: str):
    """Parse a single token like relation(X,Y) or relation(X,"value")"""
    # Updated regex to handle quoted strings and dots in values
    m = re.match(r'\s*([A-Za-z0-9_:/.-]+)\s*\(\s*([^,\)]+)\s*,\s*([^\)]+)\s*\)\s*', token)
    if not m:
        return None
    rel, v1, v2 = m.group(1), m.group(2).strip(), m.group(3).strip()
    return Predicate(variable1=v1, relation=rel, variable2=v2)

def parse_literals(part: str):
    """Parse comma-separated literals or single literal"""
    literals = []
    # Don't split by comma if it's inside parentheses
    # For now, try to parse the whole thing as one literal if no comma outside parens
    if ',' not in part or (part.count('(') == part.count(')') and part.index('(') < part.rindex(')')):
        # Single predicate or comma is inside parentheses
        # Try to split smartly
        depth = 0
        current = []
        tokens = []
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
        
        for tok in tokens:
            p = parse_predicate_token(tok)
            if p:
                literals.append(p)
    else:
        for tok in part.split(','):
            p = parse_predicate_token(tok)
            if p:
                literals.append(p)
    return literals

def parse_anyburl_rules(rules_str: str):
    """Parse ANYBURL rules"""
    rules = []
    
    # Updated regex to not stop at parentheses  
    pat_le = re.compile(r"^(.+?)\s*<=\s*(.+?)$")
    pat_ge = re.compile(r"^(.+?)\s*=>\s*(.+?)$")
    
    for line_no, line in enumerate(rules_str.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        
        # Try tab-separated format
        parts = s.split('\t')
        if len(parts) >= 4:
            try:
                support = int(parts[0].strip())
                correct_preds = int(parts[1].strip())
                confidence = float(parts[2].strip())
                rule_str = parts[3].strip()
                
                if line_no <= 3:
                    print(f"DEBUG Line {line_no}: rule_str = '{rule_str}'")
                
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
                        m = None
                
                if m:
                    if line_no <= 3:
                        print(f"  Head: '{head_part}'")
                        print(f"  Body: '{body_part}'")
                    
                    body_preds = parse_literals(body_part)
                    head_preds = parse_literals(head_part)
                    
                    if line_no <= 3:
                        print(f"  Body preds: {body_preds}")
                        print(f"  Head preds: {head_preds}")
                    
                    if body_preds and head_preds:
                        display = f"{', '.join(map(str, body_preds))} => {', '.join(map(str, head_preds))}"
                        rules.append({
                            'body': body_preds,
                            'head': head_preds,
                            'display': display,
                            'confidence': confidence,
                            'support': support
                        })
                        continue
                    elif line_no <= 3:
                        print(f"  -> Failed: body_preds or head_preds empty")
                elif line_no <= 3:
                    print(f"  -> No regex match")
            except (ValueError, IndexError) as e:
                if line_no <= 3:
                    print(f"  -> Exception: {e}")
                pass
    
    return rules

# Read the existing file
rule_file = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/output/2026-01-12_00-08-08_anyburl/-100"
with open(rule_file, 'r') as f:
    raw_rules = f.read()

print(f"Reading file: {rule_file}")
print(f"File size: {len(raw_rules)} bytes")
print(f"Number of lines: {len(raw_rules.splitlines())}\n")

# Parse rules
rules = parse_anyburl_rules(raw_rules)

print(f"Parsed {len(rules)} rules\n")

if rules:
    print("First 5 rules:")
    for i, rule in enumerate(rules[:5]):
        print(f"\n{i+1}. {rule['display']}")
        print(f"   Confidence: {rule['confidence']:.4f}")
        print(f"   Support: {rule['support']}")
        print(f"   Body: {len(rule['body'])} predicates")
        print(f"   Head: {len(rule['head'])} predicates")
else:
    print("No rules parsed! Check the parsing logic.")
    print("\nFirst 10 lines of file:")
    for i, line in enumerate(raw_rules.splitlines()[:10]):
        print(f"{i+1}: {line}")
