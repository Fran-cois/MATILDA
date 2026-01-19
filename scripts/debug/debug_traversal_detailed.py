#!/usr/bin/env python3
"""
Detailed debug script for MATILDA graph traversal.
This script adds extensive logging to identify exactly where the traversal fails.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from algorithms.MATILDA.tgd_discovery import init, discover, next_node_test
from algorithms.MATILDA import tgd_discovery as tgd_module
from database.alchemy_utility import AlchemyUtility

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def patch_next_node_test():
    """Patch next_node_test to add logging"""
    original_next_node_test = tgd_module.next_node_test
    
    call_count = {"total": 0, "passed": 0, "failed": 0}
    failure_reasons = {
        "visited": 0,
        "table_occurrences": 0,
        "minimal": 0,
        "max_table": 0,
        "max_vars": 0
    }
    
    def logged_next_node_test(candidate_rule, next_node, visited, max_table=10, max_vars=10):
        call_count["total"] += 1
        
        # Check 1: Already visited
        if next_node in visited:
            failure_reasons["visited"] += 1
            if call_count["total"] <= 10:  # Log first 10
                logger.debug(f"❌ Node REJECTED (visited): {next_node}")
            return False
        
        # Check 2: Table occurrences
        if not tgd_module.check_table_occurrences(candidate_rule, next_node):
            failure_reasons["table_occurrences"] += 1
            if call_count["total"] <= 10:
                logger.debug(f"❌ Node REJECTED (table_occ): {next_node}")
            return False
        
        # Check 3: Minimal candidate rule
        if not tgd_module.check_minimal_candidate_rule(candidate_rule, next_node):
            failure_reasons["minimal"] += 1
            if call_count["total"] <= 10:
                logger.debug(f"❌ Node REJECTED (minimal): {next_node}")
            return False
        
        # Check 4: Max table
        if not tgd_module.check_max_table(candidate_rule, next_node, max_table):
            failure_reasons["max_table"] += 1
            if call_count["total"] <= 10:
                logger.debug(f"❌ Node REJECTED (max_table): {next_node}")
            return False
        
        # Check 5: Max vars
        if not tgd_module.check_max_vars(candidate_rule, next_node, max_vars):
            failure_reasons["max_vars"] += 1
            if call_count["total"] <= 10:
                logger.debug(f"❌ Node REJECTED (max_vars): {next_node}")
            return False
        
        # All checks passed
        call_count["passed"] += 1
        if call_count["passed"] <= 20:  # Log first 20 successes
            logger.info(f"✅ Node ACCEPTED: {next_node}")
        return True
    
    # Replace function
    tgd_module.next_node_test = logged_next_node_test
    
    return call_count, failure_reasons


def patch_dfs_traversal():
    """Patch DFS to add logging"""
    from algorithms.MATILDA import graph_traversal as gt_module
    
    original_dfs = gt_module.dfs
    
    stats = {
        "initial_nodes_checked": 0,
        "initial_nodes_accepted": 0,
        "paths_explored": 0,
        "paths_yielded": 0,
        "pruning_rejected": 0
    }
    
    def logged_dfs(graph, start_node, pruning_prediction, db_inspector, mapper,
                   visited=None, candidate_rule=None, max_table=3, max_vars=4,
                   next_node_test_func=None):
        
        if visited is None:
            visited = set()
        if candidate_rule is None:
            candidate_rule = []
        
        # Initial node selection phase
        if start_node is None:
            logger.info(f"🔍 Starting DFS with {len(graph.nodes)} total nodes")
            
            for idx, next_node in enumerate(graph.nodes):
                stats["initial_nodes_checked"] += 1
                
                if idx < 5:  # Log first 5 nodes
                    logger.info(f"  Checking initial node #{idx}: {next_node}")
                
                if next_node_test_func(candidate_rule, next_node, visited, max_table, max_vars):
                    stats["initial_nodes_accepted"] += 1
                    logger.info(f"✅ Initial node #{idx} ACCEPTED - starting DFS from it")
                    
                    # Recurse with this node
                    import copy
                    yield from logged_dfs(
                        graph, next_node, pruning_prediction, db_inspector, mapper,
                        visited=set(), candidate_rule=copy.deepcopy(candidate_rule),
                        max_table=max_table, max_vars=max_vars,
                        next_node_test_func=next_node_test_func
                    )
                else:
                    if idx < 5:
                        logger.debug(f"  Initial node #{idx} rejected by next_node_test")
            
            logger.info(f"📊 Initial phase complete: {stats['initial_nodes_accepted']}/{stats['initial_nodes_checked']} nodes accepted")
            return
        
        # Regular DFS exploration
        visited.add(start_node)
        candidate_rule.append(start_node)
        stats["paths_explored"] += 1
        
        # Apply pruning
        if not pruning_prediction(candidate_rule, mapper, db_inspector):
            stats["pruning_rejected"] += 1
            return
        
        # Yield this candidate
        stats["paths_yielded"] += 1
        if stats["paths_yielded"] <= 5:
            logger.info(f"🎯 YIELDING candidate rule #{stats['paths_yielded']}: {len(candidate_rule)} nodes")
        yield candidate_rule
        
        # Get neighbors
        big_neighbours = []
        for node in candidate_rule:
            big_neighbours += [e for e in graph.neighbors(node) if e not in visited]
        
        if stats["paths_yielded"] == 1 and len(big_neighbours) > 0:
            logger.info(f"  First rule has {len(big_neighbours)} neighbors to explore")
        
        # Explore neighbors
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
    
    gt_module.dfs = logged_dfs
    return stats


def main():
    db_path = "data/input/Bupa.db"
    
    logger.info("="*80)
    logger.info("MATILDA TRAVERSAL DEBUG - DETAILED LOGGING")
    logger.info("="*80)
    
    # Initialize
    logger.info(f"\n📂 Database: {db_path}")
    db_inspector = AlchemyUtility(f"sqlite:///{db_path}")
    
    logger.info("\n🔧 Initializing MATILDA...")
    # Use init() from tgd_discovery
    constraint_graph, jia_list, mapper = init(
        db_inspector,
        max_table=3,
        max_vars=4
    )
    
    # Patch functions to add logging
    logger.info("\n🔌 Patching functions with logging...")
    call_count, failure_reasons = patch_next_node_test()
    dfs_stats = patch_dfs_traversal()
    
    # Check initialization
    logger.info(f"\n✅ Initialization complete:")
    logger.info(f"   - Constraint graph nodes: {len(constraint_graph.nodes)}")
    logger.info(f"   - JIA list size: {len(jia_list)}")
    
    if len(constraint_graph.nodes) == 0:
        logger.error("❌ PROBLEM: Graph has 0 nodes!")
        return
    
    # Sample nodes
    logger.info(f"\n📋 Sample graph nodes (first 3):")
    for i, node in enumerate(list(constraint_graph.nodes)[:3]):
        logger.info(f"   {i+1}. {node}")
    
    # Start discovery
    logger.info("\n" + "="*80)
    logger.info("🚀 STARTING RULE DISCOVERY")
    logger.info("="*80)
    
    rules = []
    try:
        # Call discover() with proper parameters
        for idx, rule in enumerate(discover(
            constraint_graph=constraint_graph,
            jia_list=jia_list,
            mapper=mapper,
            db_inspector=db_inspector,
            algorithm='dfs',
            max_table=3,
            max_vars=4
        )):
            rules.append(rule)
            logger.info(f"\n🎉 DISCOVERED RULE #{idx+1}: {rule}")
            if idx >= 10:  # Stop after 10 rules for debug
                logger.info("\n⏸️  Stopping after 10 rules (debug limit)")
                break
    except Exception as e:
        logger.error(f"\n❌ Exception during discovery: {e}", exc_info=True)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("📊 FINAL STATISTICS")
    logger.info("="*80)
    
    logger.info(f"\n🔍 next_node_test() calls:")
    logger.info(f"   - Total calls: {call_count['total']}")
    logger.info(f"   - Passed: {call_count['passed']}")
    logger.info(f"   - Failed: {call_count['failed']}")
    
    if call_count['total'] > 0:
        logger.info(f"\n❌ Failure breakdown:")
        for reason, count in failure_reasons.items():
            pct = (count / call_count['total']) * 100
            logger.info(f"   - {reason}: {count} ({pct:.1f}%)")
    
    logger.info(f"\n🌳 DFS traversal:")
    logger.info(f"   - Initial nodes checked: {dfs_stats['initial_nodes_checked']}")
    logger.info(f"   - Initial nodes accepted: {dfs_stats['initial_nodes_accepted']}")
    logger.info(f"   - Paths explored: {dfs_stats['paths_explored']}")
    logger.info(f"   - Paths yielded: {dfs_stats['paths_yielded']}")
    logger.info(f"   - Pruning rejected: {dfs_stats['pruning_rejected']}")
    
    logger.info(f"\n🎯 Rules discovered: {len(rules)}")
    
    if len(rules) == 0:
        logger.error("\n⚠️  CRITICAL: 0 RULES DISCOVERED")
        logger.error("   Root cause analysis needed:")
        logger.error(f"   - Were initial nodes accepted? {dfs_stats['initial_nodes_accepted'] > 0}")
        logger.error(f"   - Was pruning too strict? {dfs_stats['pruning_rejected']} rejected")
        logger.error(f"   - Did next_node_test pass anything? {call_count['passed'] > 0}")


if __name__ == "__main__":
    main()
