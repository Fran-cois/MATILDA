#!/usr/bin/env python3
"""
Démonstration rapide des heuristiques de MATILDA.

Ce script montre comment utiliser les différentes heuristiques sans lancer un benchmark complet.
"""

import sys
from pathlib import Path

# Add src to path
root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root / 'src'))

from heuristics.path_search import PathSearchHeuristics, create_heuristic

# Créer des mocks simples pour la démo
class MockIndexedAttribute:
    def __init__(self, i, j, k):
        self.i = i  # table index
        self.j = j  # occurrence
        self.k = k  # attribute index

class MockMapper:
    def __init__(self):
        self.tables = ['Member', 'Policy', 'Claim']

class MockDB:
    def get_tables(self):
        return ['Member', 'Policy', 'Claim']
    
    def execute_query(self, query):
        if 'Member' in query:
            return [{'cnt': 1000}]
        elif 'Policy' in query:
            return [{'cnt': 5000}]
        elif 'Claim' in query:
            return [{'cnt': 500}]
        return [{'cnt': 0}]


def main():
    print("="*70)
    print("🚀 DEMO: Heuristiques MATILDA Path Search")
    print("="*70)
    
    # Initialiser
    db = MockDB()
    mapper = MockMapper()
    heuristics = PathSearchHeuristics(db, mapper)
    
    print(f"\n📊 Tables mockées:")
    for table, size in heuristics._table_sizes.items():
        print(f"   {table}: {size} tuples")
    
    # Créer des règles candidates de complexité croissante
    rule_1_table = [
        [MockIndexedAttribute(0, 0, 0), MockIndexedAttribute(0, 0, 1)]
    ]
    
    rule_2_tables = [
        [MockIndexedAttribute(0, 0, 0), MockIndexedAttribute(1, 1, 0)]
    ]
    
    rule_3_tables = [
        [MockIndexedAttribute(0, 0, 0), MockIndexedAttribute(1, 1, 0)],
        [MockIndexedAttribute(1, 1, 1), MockIndexedAttribute(2, 2, 0)]
    ]
    
    rules = [
        ("1 table", rule_1_table),
        ("2 tables", rule_2_tables),
        ("3 tables", rule_3_tables),
    ]
    
    # Tester chaque heuristique
    heuristic_names = ['naive', 'table_size', 'join_selectivity', 'hybrid']
    
    print("\n" + "="*70)
    print("📈 Comparaison des Heuristiques")
    print("="*70)
    
    # En-tête du tableau
    header = f"{'Règle':<15}"
    for h_name in heuristic_names:
        header += f"{h_name.capitalize():<20}"
    print(header)
    print("-" * 70)
    
    # Calculer les coûts pour chaque règle
    for rule_name, rule in rules:
        row = f"{rule_name:<15}"
        for h_name in heuristic_names:
            heuristic_func = heuristics.get_heuristic_function(h_name)
            cost = heuristic_func(rule, mapper, db)
            row += f"{cost:<20.2f}"
        print(row)
    
    print("\n💡 Interprétation:")
    print("   - Coûts plus bas = règles plus prometteuses")
    print("   - Naive: Préfère règles courtes")
    print("   - Table Size: Préfère petites tables")
    print("   - Join Selectivity: Évite explosion combinatoire")
    print("   - Hybrid: Compromis équilibré (recommandé)")
    
    print("\n" + "="*70)
    print("✅ Utilisation dans MATILDA:")
    print("="*70)
    print("""
# Dans config.yaml:
algorithm:
  matilda:
    traversal_algorithm: "astar"

# Par code:
from heuristics.path_search import create_heuristic
heuristic = create_heuristic(db_inspector, mapper, 'hybrid')
rules = matilda.discover_rules(
    traversal_algorithm='astar',
    heuristic_func=heuristic
)

# Via CLI:
python cli.py heuristics --algorithm astar --heuristic hybrid
    """)
    
    print("="*70)
    print("✨ Démo terminée ! Lancez un benchmark avec:")
    print("   python cli.py heuristics --quick")
    print("="*70)


if __name__ == '__main__':
    main()
