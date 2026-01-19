#!/usr/bin/env python3
"""
Quick Start Guide - Graph Traversal Algorithms in MATILDA

This script demonstrates how to use the new graph traversal algorithms.
"""

# Example 1: Using config.yaml (Recommended)
print("=" * 70)
print("Example 1: Using config.yaml")
print("=" * 70)
print("""
Edit src/config.yaml:

algorithm:
  name: "MATILDA"
  matilda:
    traversal_algorithm: "dfs"  # Options: dfs, bfs, astar

Then run:
  python src/main.py
""")

# Example 2: Programmatic usage
print("=" * 70)
print("Example 2: Programmatic Usage")
print("=" * 70)
print("""
from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility

# Initialize database
db_uri = "sqlite:///data/db/Bupa.db"
with AlchemyUtility(db_uri) as db:
    matilda = MATILDA(db)
    
    # Use DFS (default)
    rules_dfs = matilda.discover_rules(
        traversal_algorithm="dfs",
        max_table=3,
        max_vars=6
    )
    
    # Use BFS
    rules_bfs = matilda.discover_rules(
        traversal_algorithm="bfs",
        max_table=3,
        max_vars=6
    )
    
    # Use A-star
    rules_astar = matilda.discover_rules(
        traversal_algorithm="astar",
        max_table=3,
        max_vars=6
    )
""")

# Example 3: Direct usage
print("=" * 70)
print("Example 3: Direct Usage (Advanced)")
print("=" * 70)
print("""
from algorithms.MATILDA.tgd_discovery import (
    init, traverse_graph, path_pruning
)

# Initialize constraint graph
cg, mapper, jia_list = init(db_inspector, max_nb_occurrence=3)

# Use specific algorithm
for candidate_rule in traverse_graph(
    cg,
    None,
    path_pruning,
    db_inspector,
    mapper,
    max_table=3,
    max_vars=6,
    algorithm="bfs"  # or "dfs" or "astar"
):
    # Process candidate_rule
    pass
""")

# Comparison
print("=" * 70)
print("Algorithm Comparison")
print("=" * 70)
print("""
+------------+---------------+------------------+------------------+
| Algorithm  | Memory Usage  | Simple Rules     | Complex Rules    |
+------------+---------------+------------------+------------------+
| DFS        | Low           | Medium speed     | Fast             |
| BFS        | High          | Fast             | Slow             |
| A-star     | Medium        | Very fast        | Fast             |
+------------+---------------+------------------+------------------+

When to use:
- DFS: Default, balanced, low memory
- BFS: Want simple rules first, systematic exploration
- A-star: Want high-quality rules fast
""")

# Testing
print("=" * 70)
print("Testing Your Setup")
print("=" * 70)
print("""
1. Run unit tests:
   python test_traversal.py

2. Run demo comparison:
   python demo_traversal.py

3. Check configuration:
   cat src/config.yaml | grep -A 5 "matilda:"
""")

# More info
print("=" * 70)
print("Documentation")
print("=" * 70)
print("""
- GRAPH_TRAVERSAL_ALGORITHMS.md  - Detailed algorithm documentation
- TRAVERSAL_FEATURE.md           - Feature overview and usage guide
- README_CHANGES.md              - Summary of changes
- test_traversal.py              - Unit tests and examples
- demo_traversal.py              - Comparative demonstration
""")

print("=" * 70)
print("✓ Ready to use!")
print("=" * 70)
