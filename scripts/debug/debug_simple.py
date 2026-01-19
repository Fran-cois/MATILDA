#!/usr/bin/env python3
"""
Simplified debug script to trace MATILDA traversal and identify why 0 rules are found.
Uses MATILDA class directly like stress_test.py does.
"""

import sys
import logging
from pathlib import Path

# Setup paths
root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root / 'src'))
sys.path.insert(0, str(root))

from algorithms.matilda import MATILDA
from database.alchemy_utility import AlchemyUtility

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

def main():
    db_path = "data/input/Bupa.db"
    
    print("="*80)
    print("🔍 MATILDA TRAVERSAL DEBUG - Simplified")
    print("="*80)
    
    print(f"\n📂 Database: {db_path}")
    db = AlchemyUtility(f"sqlite:///{db_path}")
    
    print("\n🔧 Initializing MATILDA...")
    settings = {
        'nb_occurrence': 3,
        'max_table': 3,
        'max_vars': 4,
        'timeout': 60
    }
    
    matilda = MATILDA(database=db, settings=settings)
    
    print(f"✅ MATILDA initialized")
    print(f"   Tables: {len(db.get_table_names())}")
    
    # Monkey-patch to add debug logging
    from algorithms.MATILDA import tgd_discovery, graph_traversal
    
    # Stats tracking
    stats = {
        'next_node_test_calls': 0,
        'next_node_test_passed': 0,
        'next_node_test_reasons': {'visited': 0, 'table_occ': 0, 'minimal': 0, 'max_table': 0, 'max_vars': 0},
        'dfs_initial_checked': 0,
        'dfs_initial_accepted': 0,
        'dfs_nodes_explored': 0,
        'dfs_rules_yielded': 0,
        'dfs_pruning_rejected': 0
    }
    
    # Patch next_node_test
    original_next_node_test = tgd_discovery.next_node_test
    
    def logged_next_node_test(candidate_rule, next_node, visited, max_table=10, max_vars=10):
        stats['next_node_test_calls'] += 1
        
        if next_node in visited:
            stats['next_node_test_reasons']['visited'] += 1
            if stats['next_node_test_calls'] <= 5:
                print(f"  ❌ Node #{stats['next_node_test_calls']} rejected: already visited")
            return False
        
        if not tgd_discovery.check_table_occurrences(candidate_rule, next_node):
            stats['next_node_test_reasons']['table_occ'] += 1
            if stats['next_node_test_calls'] <= 5:
                print(f"  ❌ Node #{stats['next_node_test_calls']} rejected: table occurrences not consecutive")
            return False
        
        if not tgd_discovery.check_minimal_candidate_rule(candidate_rule, next_node):
            stats['next_node_test_reasons']['minimal'] += 1
            if stats['next_node_test_calls'] <= 5:
                print(f"  ❌ Node #{stats['next_node_test_calls']} rejected: not minimal")
            return False
        
        if not tgd_discovery.check_max_table(candidate_rule, next_node, max_table):
            stats['next_node_test_reasons']['max_table'] += 1
            if stats['next_node_test_calls'] <= 5:
                print(f"  ❌ Node #{stats['next_node_test_calls']} rejected: max_table exceeded")
            return False
        
        if not tgd_discovery.check_max_vars(candidate_rule, next_node, max_vars):
            stats['next_node_test_reasons']['max_vars'] += 1
            if stats['next_node_test_calls'] <= 5:
                print(f"  ❌ Node #{stats['next_node_test_calls']} rejected: max_vars exceeded")
            return False
        
        stats['next_node_test_passed'] += 1
        if stats['next_node_test_passed'] <= 10:
            print(f"  ✅ Node #{stats['next_node_test_calls']} ACCEPTED")
        return True
    
    tgd_discovery.next_node_test = logged_next_node_test
    
    # Patch DFS to add logging
    original_dfs = graph_traversal.dfs
    
    def logged_dfs(graph, start_node, pruning_prediction, db_inspector, mapper,
                   visited=None, candidate_rule=None, max_table=3, max_vars=4,
                   next_node_test_func=None):
        
        if visited is None:
            visited = set()
        if candidate_rule is None:
            candidate_rule = []
        
        # Initial node phase
        if start_node is None:
            print(f"\n🔍 DFS: Checking {len(graph.nodes)} initial nodes...")
            
            for idx, next_node in enumerate(graph.nodes):
                stats['dfs_initial_checked'] += 1
                
                if idx < 3:
                    print(f"\n  Testing initial node #{idx+1}/{len(graph.nodes)}: {next_node}")
                
                if next_node_test_func(candidate_rule, next_node, visited, max_table, max_vars):
                    stats['dfs_initial_accepted'] += 1
                    if stats['dfs_initial_accepted'] <= 3:
                        print(f"  ✅ Initial node #{idx+1} ACCEPTED - starting DFS from it")
                    
                    import copy
                    yield from logged_dfs(
                        graph, next_node, pruning_prediction, db_inspector, mapper,
                        visited=set(), candidate_rule=copy.deepcopy(candidate_rule),
                        max_table=max_table, max_vars=max_vars,
                        next_node_test_func=next_node_test_func
                    )
            
            print(f"\n📊 Initial phase: {stats['dfs_initial_accepted']}/{stats['dfs_initial_checked']} nodes accepted")
            return
        
        # Regular DFS
        visited.add(start_node)
        candidate_rule.append(start_node)
        stats['dfs_nodes_explored'] += 1
        
        # Pruning check
        if not pruning_prediction(candidate_rule, mapper, db_inspector):
            stats['dfs_pruning_rejected'] += 1
            if stats['dfs_pruning_rejected'] <= 3:
                print(f"  ⚠️  Candidate rejected by pruning (#{stats['dfs_pruning_rejected']})")
            return
        
        # Yield
        stats['dfs_rules_yielded'] += 1
        if stats['dfs_rules_yielded'] <= 5:
            print(f"  🎯 YIELDING rule #{stats['dfs_rules_yielded']} with {len(candidate_rule)} nodes")
        yield candidate_rule
        
        # Neighbors
        big_neighbours = []
        for node in candidate_rule:
            big_neighbours += [e for e in graph.neighbors(node) if e not in visited]
        
        if stats['dfs_rules_yielded'] == 1:
            print(f"  First rule has {len(big_neighbours)} neighbors to explore")
        
        # Explore
        for next_node in big_neighbours:
            if next_node_test_func(candidate_rule, next_node, visited, max_table, max_vars):
                yield from logged_dfs(
                    graph, next_node, pruning_prediction, db_inspector, mapper,
                    visited=visited, candidate_rule=candidate_rule,
                    max_table=max_table, max_vars=max_vars,
                    next_node_test_func=next_node_test_func
                )
                visited.remove(next_node)
                candidate_rule.pop()
    
    graph_traversal.dfs = logged_dfs
    
    # Run discovery
    print("\n" + "="*80)
    print("🚀 STARTING RULE DISCOVERY (DFS)")
    print("="*80 + "\n")
    
    rules = []
    try:
        for idx, rule in enumerate(matilda.discover_rules(
            traversal_algorithm='dfs',
            max_table=3,
            max_vars=4
        )):
            rules.append(rule)
            if idx < 5:
                print(f"\n🎉 RULE #{idx+1} discovered")
            if idx >= 20:  # Limit for debug
                print(f"\n⏸️  Stopping after 20 rules")
                break
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "="*80)
    print("📊 FINAL STATISTICS")
    print("="*80)
    
    print(f"\n🔍 next_node_test() calls:")
    print(f"   Total: {stats['next_node_test_calls']}")
    print(f"   Passed: {stats['next_node_test_passed']}")
    print(f"   Failed: {stats['next_node_test_calls'] - stats['next_node_test_passed']}")
    
    if stats['next_node_test_calls'] > 0:
        print(f"\n❌ Rejection reasons:")
        for reason, count in stats['next_node_test_reasons'].items():
            pct = (count / stats['next_node_test_calls']) * 100
            print(f"   {reason:15s}: {count:5d} ({pct:5.1f}%)")
    
    print(f"\n🌳 DFS traversal:")
    print(f"   Initial nodes checked: {stats['dfs_initial_checked']}")
    print(f"   Initial nodes accepted: {stats['dfs_initial_accepted']}")
    print(f"   Total nodes explored: {stats['dfs_nodes_explored']}")
    print(f"   Rules yielded: {stats['dfs_rules_yielded']}")
    print(f"   Pruning rejections: {stats['dfs_pruning_rejected']}")
    
    print(f"\n🎯 TOTAL RULES: {len(rules)}")
    
    if len(rules) == 0:
        print("\n⚠️  CRITICAL: 0 RULES DISCOVERED!")
        print("\n🔍 Diagnostic:")
        if stats['dfs_initial_accepted'] == 0:
            print("   ❌ NO initial nodes passed next_node_test")
            print("   → Check why all nodes rejected in initial phase")
        elif stats['dfs_nodes_explored'] == 0:
            print("   ❌ No nodes explored (DFS never started)")
            print("   → Bug in DFS initialization?")
        elif stats['dfs_pruning_rejected'] > 0 and stats['dfs_rules_yielded'] == 0:
            print("   ❌ All candidates rejected by pruning")
            print("   → Pruning too strict?")
        else:
            print("   ❓ Unknown issue")

if __name__ == "__main__":
    main()
