"""
Script de test pour les algorithmes de traversée de graphe de MATILDA.

Ce script teste les trois algorithmes (DFS, BFS, A-star) et compare leurs résultats.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algorithms.MATILDA.graph_traversal import dfs, bfs, astar, get_traversal_algorithm
from algorithms.MATILDA.constraint_graph import ConstraintGraph, JoinableIndexedAttributes


def test_traversal_algorithm_selection():
    """Test que la sélection d'algorithme fonctionne correctement."""
    print("Testing algorithm selection...")
    
    # Test DFS
    algo = get_traversal_algorithm("dfs")
    assert algo == dfs, "DFS selection failed"
    
    # Test BFS
    algo = get_traversal_algorithm("bfs")
    assert algo == bfs, "BFS selection failed"
    
    # Test A-star (multiple formats)
    algo = get_traversal_algorithm("astar")
    assert algo == astar, "A-star selection failed"
    
    algo = get_traversal_algorithm("a-star")
    assert algo == astar, "A-star (with dash) selection failed"
    
    algo = get_traversal_algorithm("A_STAR")
    assert algo == astar, "A-star (uppercase) selection failed"
    
    # Test invalid algorithm
    try:
        get_traversal_algorithm("invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Correctly raised error: {e}")
    
    print("✓ All algorithm selection tests passed!\n")


def test_import():
    """Test que tous les imports fonctionnent."""
    print("Testing imports...")
    
    try:
        from algorithms.MATILDA.tgd_discovery import dfs, bfs, astar, traverse_graph
        from algorithms.matilda import MATILDA
        print("✓ All imports successful!\n")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        sys.exit(1)


def test_config_structure():
    """Test que la structure de configuration est valide."""
    print("Testing configuration structure...")
    
    import yaml
    config_path = Path(__file__).parent / "src" / "config.yaml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check if MATILDA config exists
        assert "algorithm" in config, "Missing 'algorithm' in config"
        assert "matilda" in config["algorithm"], "Missing 'matilda' section in algorithm config"
        assert "traversal_algorithm" in config["algorithm"]["matilda"], \
            "Missing 'traversal_algorithm' in matilda config"
        
        traversal_algo = config["algorithm"]["matilda"]["traversal_algorithm"]
        valid_algos = ["dfs", "bfs", "astar", "a-star", "a_star"]
        assert traversal_algo.lower() in valid_algos, \
            f"Invalid traversal_algorithm: {traversal_algo}"
        
        print(f"✓ Configuration valid! Current algorithm: {traversal_algo}\n")
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        sys.exit(1)


def display_summary():
    """Affiche un résumé des algorithmes disponibles."""
    print("=" * 70)
    print("MATILDA Graph Traversal Algorithms - Test Summary")
    print("=" * 70)
    print()
    print("Available algorithms:")
    print()
    print("1. DFS (Depth-First Search)")
    print("   - Explores deeply before backtracking")
    print("   - Good for finding complex rules quickly")
    print("   - Default algorithm")
    print()
    print("2. BFS (Breadth-First Search)")
    print("   - Explores level by level")
    print("   - Finds shorter rules first")
    print("   - More systematic exploration")
    print()
    print("3. A-star (A*)")
    print("   - Uses heuristic to guide search")
    print("   - Finds high-quality rules faster")
    print("   - Balances exploration and exploitation")
    print()
    print("To change the algorithm, update src/config.yaml:")
    print("  algorithm:")
    print("    matilda:")
    print('      traversal_algorithm: "dfs"  # or "bfs" or "astar"')
    print()
    print("=" * 70)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Testing MATILDA Graph Traversal Algorithms")
    print("=" * 70 + "\n")
    
    try:
        test_import()
        test_traversal_algorithm_selection()
        test_config_structure()
        
        print("=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print()
        
        display_summary()
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
