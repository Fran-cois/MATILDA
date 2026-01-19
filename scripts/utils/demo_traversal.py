"""
Script de démonstration pour comparer les algorithmes de traversée.

Ce script exécute MATILDA avec les trois algorithmes et montre les différences.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from database.alchemy_utility import AlchemyUtility
from algorithms.matilda import MATILDA


def test_algorithm(db_path: str, algorithm: str, max_rules: int = 5):
    """
    Test un algorithme de traversée et retourne les résultats.
    
    :param db_path: Chemin vers la base de données
    :param algorithm: Nom de l'algorithme ('dfs', 'bfs', 'astar')
    :param max_rules: Nombre maximum de règles à découvrir
    :return: Liste des règles et temps d'exécution
    """
    print(f"\n{'='*70}")
    print(f"Testing with {algorithm.upper()}")
    print(f"{'='*70}")
    
    db_uri = f"sqlite:///{db_path}"
    
    try:
        with AlchemyUtility(db_uri, create_index=False) as db_util:
            matilda = MATILDA(db_util)
            
            rules = []
            start_time = time.time()
            
            print(f"Discovering rules with {algorithm.upper()}...")
            
            for i, rule in enumerate(matilda.discover_rules(
                traversal_algorithm=algorithm,
                max_table=2,
                max_vars=4,
                nb_occurrence=2,
            )):
                rules.append(rule)
                print(f"  {i+1}. {rule.display[:100]}...")
                
                if i + 1 >= max_rules:
                    print(f"\n  (Stopping after {max_rules} rules for demo)")
                    break
            
            elapsed_time = time.time() - start_time
            
            print(f"\nSummary:")
            print(f"  - Algorithm: {algorithm.upper()}")
            print(f"  - Rules found: {len(rules)}")
            print(f"  - Time: {elapsed_time:.2f}s")
            
            if rules:
                avg_confidence = sum(r.confidence for r in rules) / len(rules)
                avg_support = sum(r.accuracy for r in rules) / len(rules)
                print(f"  - Avg confidence: {avg_confidence:.3f}")
                print(f"  - Avg support: {avg_support:.3f}")
            
            return rules, elapsed_time
            
    except Exception as e:
        print(f"Error with {algorithm}: {e}")
        import traceback
        traceback.print_exc()
        return [], 0


def main():
    """Fonction principale pour comparer les algorithmes."""
    
    # Trouver une base de données de test
    db_paths = [
        Path("data/db/Bupa.db"),
        Path("data/db/BupaImperfect.db"),
        Path("data/db/ComparisonDataset.db"),
    ]
    
    db_path = None
    for path in db_paths:
        if path.exists():
            db_path = path
            break
    
    if not db_path:
        print("No test database found. Please ensure a database exists in data/db/")
        print("Looking for: Bupa.db, BupaImperfect.db, or ComparisonDataset.db")
        sys.exit(1)
    
    print(f"\nUsing database: {db_path}")
    print("Note: This is a quick demo with limited rules for comparison.")
    print("For full rule discovery, use the main.py script.\n")
    
    results = {}
    
    # Test each algorithm
    for algo in ["dfs", "bfs", "astar"]:
        rules, exec_time = test_algorithm(str(db_path), algo, max_rules=3)
        results[algo] = {
            "rules": rules,
            "time": exec_time,
            "count": len(rules)
        }
    
    # Display comparison
    print(f"\n{'='*70}")
    print("COMPARISON SUMMARY")
    print(f"{'='*70}")
    print(f"{'Algorithm':<15} {'Rules Found':<15} {'Time (s)':<15}")
    print(f"{'-'*70}")
    
    for algo, data in results.items():
        print(f"{algo.upper():<15} {data['count']:<15} {data['time']:<15.2f}")
    
    print(f"{'='*70}")
    print("\nNotes:")
    print("- DFS explores deeply, finding complex rules quickly")
    print("- BFS explores breadth-first, finding simpler rules first")
    print("- A-star uses heuristics to find quality rules efficiently")
    print("\nThe actual performance differences become more apparent with:")
    print("  - Larger databases")
    print("  - More complex schemas")
    print("  - Higher max_table and max_vars settings")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
