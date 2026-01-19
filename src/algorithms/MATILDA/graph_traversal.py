"""
Graph traversal algorithms for constraint graph exploration in MATILDA.

This module provides different graph traversal strategies (DFS, BFS, A-star)
to explore the constraint graph and discover candidate rules.
"""

import copy
import heapq
from collections import deque
from collections.abc import Callable, Iterator
from typing import Optional
from algorithms.MATILDA.constraint_graph import (
    ConstraintGraph,
    JoinableIndexedAttributes,
    AttributeMapper,
)
from database.alchemy_utility import AlchemyUtility
from tqdm import tqdm


CandidateRule = list[JoinableIndexedAttributes]


def dfs(
    graph: ConstraintGraph,
    start_node: JoinableIndexedAttributes,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    visited: Optional[set[JoinableIndexedAttributes]] = None,
    candidate_rule: Optional[CandidateRule] = None,
    max_table: int = 3,
    max_vars: int = 4,
    next_node_test_func: Optional[Callable] = None,
) -> Iterator[CandidateRule]:
    """
    Perform a Depth-First Search (DFS) traversal with pruning.
    
    DFS explores as far as possible along each branch before backtracking.
    This strategy is good for finding deep rules quickly but may miss 
    broader patterns initially.

    :param graph: An instance of the ConstraintGraph class.
    :param start_node: The node from which the DFS starts.
    :param pruning_prediction: A function that determines whether to continue exploring.
    :param db_inspector: Database inspector for evaluating rules.
    :param mapper: Attribute mapper for indexed attributes.
    :param visited: A set to keep track of visited nodes to avoid cycles.
    :param candidate_rule: A list to track the current path of nodes being visited.
    :param max_table: Maximum number of tables allowed in a rule.
    :param max_vars: Maximum number of variables allowed in a rule.
    :param next_node_test_func: Function to test if a node can be added.
    :yield: Candidate rules found during traversal.
    """
    if visited is None:
        visited = set()
    if candidate_rule is None:
        candidate_rule = []
    
    if start_node is None:
        for next_node in tqdm(graph.nodes, desc="Initial Nodes (DFS)"):
            if next_node_test_func(candidate_rule, next_node, visited, max_table, max_vars):
                yield from dfs(
                    graph,
                    next_node,
                    pruning_prediction,
                    db_inspector,
                    mapper,
                    visited=set(),
                    candidate_rule=copy.deepcopy(candidate_rule),
                    max_table=max_table,
                    max_vars=max_vars,
                    next_node_test_func=next_node_test_func,
                )
        return
    
    visited.add(start_node)
    candidate_rule.append(start_node)
    
    # Apply pruning
    if not pruning_prediction(candidate_rule, mapper, db_inspector):
        return
    
    yield candidate_rule
    
    # Get neighbors to explore
    big_neighbours = []
    for node in candidate_rule:
        big_neighbours += [e for e in graph.neighbors(node) if e not in visited]
    
    for next_node in big_neighbours:
        if next_node_test_func(candidate_rule, next_node, visited, max_table, max_vars):
            yield from dfs(
                graph,
                next_node,
                pruning_prediction,
                db_inspector,
                mapper,
                visited=visited,
                candidate_rule=candidate_rule,
                max_table=max_table,
                max_vars=max_vars,
                next_node_test_func=next_node_test_func,
            )
            visited.remove(next_node)
            candidate_rule.pop()


def bfs(
    graph: ConstraintGraph,
    start_node: JoinableIndexedAttributes,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int = 3,
    max_vars: int = 4,
    next_node_test_func: Optional[Callable] = None,
) -> Iterator[CandidateRule]:
    """
    Perform a Breadth-First Search (BFS) traversal with pruning.
    
    BFS explores all neighbors at the current depth before moving to nodes
    at the next depth level. This strategy finds shorter rules first and
    provides a more systematic exploration of the search space.

    :param graph: An instance of the ConstraintGraph class.
    :param start_node: The node from which the BFS starts (None for all nodes).
    :param pruning_prediction: A function that determines whether to continue exploring.
    :param db_inspector: Database inspector for evaluating rules.
    :param mapper: Attribute mapper for indexed attributes.
    :param max_table: Maximum number of tables allowed in a rule.
    :param max_vars: Maximum number of variables allowed in a rule.
    :param next_node_test_func: Function to test if a node can be added.
    :yield: Candidate rules found during traversal.
    """
    if start_node is None:
        # Initialize BFS from all nodes
        for initial_node in tqdm(graph.nodes, desc="Initial Nodes (BFS)"):
            # Each starting node begins its own BFS
            queue = deque([(initial_node, [], set())])
            
            while queue:
                current_node, candidate_rule, visited = queue.popleft()
                
                if current_node in visited:
                    continue
                
                # Create new state
                new_visited = visited.copy()
                new_visited.add(current_node)
                new_candidate_rule = candidate_rule + [current_node]
                
                # Apply pruning
                if not pruning_prediction(new_candidate_rule, mapper, db_inspector):
                    continue
                
                yield new_candidate_rule
                
                # Get all neighbors from all nodes in current candidate rule
                big_neighbours = []
                for node in new_candidate_rule:
                    big_neighbours += [e for e in graph.neighbors(node) if e not in new_visited]
                
                # Add valid neighbors to queue
                for next_node in big_neighbours:
                    if next_node_test_func(new_candidate_rule, next_node, new_visited, max_table, max_vars):
                        queue.append((next_node, new_candidate_rule, new_visited))
    else:
        # BFS from a specific start node
        queue = deque([(start_node, [], set())])
        
        while queue:
            current_node, candidate_rule, visited = queue.popleft()
            
            if current_node in visited:
                continue
            
            # Create new state
            new_visited = visited.copy()
            new_visited.add(current_node)
            new_candidate_rule = candidate_rule + [current_node]
            
            # Apply pruning
            if not pruning_prediction(new_candidate_rule, mapper, db_inspector):
                continue
            
            yield new_candidate_rule
            
            # Get all neighbors
            big_neighbours = []
            for node in new_candidate_rule:
                big_neighbours += [e for e in graph.neighbors(node) if e not in new_visited]
            
            # Add valid neighbors to queue
            for next_node in big_neighbours:
                if next_node_test_func(new_candidate_rule, next_node, new_visited, max_table, max_vars):
                    queue.append((next_node, new_candidate_rule, new_visited))


def astar(
    graph: ConstraintGraph,
    start_node: JoinableIndexedAttributes,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int = 3,
    max_vars: int = 4,
    next_node_test_func: Optional[Callable] = None,
    heuristic_func: Optional[Callable[[CandidateRule, AttributeMapper, AlchemyUtility], float]] = None,
) -> Iterator[CandidateRule]:
    """
    Perform an A-star search traversal with pruning.
    
    A-star uses a heuristic function to guide the search towards more promising
    candidate rules. It prioritizes exploring rules that have higher estimated quality
    (based on support/confidence metrics).

    :param graph: An instance of the ConstraintGraph class.
    :param start_node: The node from which the A-star starts (None for all nodes).
    :param pruning_prediction: A function that determines whether to continue exploring.
    :param db_inspector: Database inspector for evaluating rules.
    :param mapper: Attribute mapper for indexed attributes.
    :param max_table: Maximum number of tables allowed in a rule.
    :param max_vars: Maximum number of variables allowed in a rule.
    :param next_node_test_func: Function to test if a node can be added.
    :param heuristic_func: Heuristic function to estimate rule quality (lower is better).
                          If None, uses a default heuristic based on rule length.
    :yield: Candidate rules found during traversal.
    """
    if heuristic_func is None:
        # Default heuristic: prefer shorter rules (simple heuristic)
        heuristic_func = lambda cr, m, db: len(cr)
    
    if start_node is None:
        # Initialize A-star from all nodes
        for initial_node in tqdm(graph.nodes, desc="Initial Nodes (A*)"):
            # Priority queue: (priority, counter, node, candidate_rule, visited)
            # Counter ensures stable ordering for equal priorities
            counter = 0
            priority_queue = [(0, counter, initial_node, [], set())]
            
            while priority_queue:
                priority, _, current_node, candidate_rule, visited = heapq.heappop(priority_queue)
                
                if current_node in visited:
                    continue
                
                # Create new state
                new_visited = visited.copy()
                new_visited.add(current_node)
                new_candidate_rule = candidate_rule + [current_node]
                
                # Apply pruning
                if not pruning_prediction(new_candidate_rule, mapper, db_inspector):
                    continue
                
                yield new_candidate_rule
                
                # Get all neighbors
                big_neighbours = []
                for node in new_candidate_rule:
                    big_neighbours += [e for e in graph.neighbors(node) if e not in new_visited]
                
                # Add valid neighbors to priority queue
                for next_node in big_neighbours:
                    if next_node_test_func(new_candidate_rule, next_node, new_visited, max_table, max_vars):
                        # Calculate priority (cost + heuristic)
                        # Negate heuristic if higher quality should have lower cost
                        test_rule = new_candidate_rule + [next_node]
                        cost = len(test_rule)  # g(n): actual cost (path length)
                        heuristic = heuristic_func(test_rule, mapper, db_inspector)  # h(n)
                        
                        # For A-star, we want to explore better rules first
                        # If heuristic returns quality (higher is better), negate it
                        priority = cost - heuristic  # Lower priority = explored first
                        
                        counter += 1
                        heapq.heappush(
                            priority_queue,
                            (priority, counter, next_node, new_candidate_rule, new_visited)
                        )
    else:
        # A-star from a specific start node
        counter = 0
        priority_queue = [(0, counter, start_node, [], set())]
        
        while priority_queue:
            priority, _, current_node, candidate_rule, visited = heapq.heappop(priority_queue)
            
            if current_node in visited:
                continue
            
            # Create new state
            new_visited = visited.copy()
            new_visited.add(current_node)
            new_candidate_rule = candidate_rule + [current_node]
            
            # Apply pruning
            if not pruning_prediction(new_candidate_rule, mapper, db_inspector):
                continue
            
            yield new_candidate_rule
            
            # Get all neighbors
            big_neighbours = []
            for node in new_candidate_rule:
                big_neighbours += [e for e in graph.neighbors(node) if e not in new_visited]
            
            # Add valid neighbors to priority queue
            for next_node in big_neighbours:
                if next_node_test_func(new_candidate_rule, next_node, new_visited, max_table, max_vars):
                    test_rule = new_candidate_rule + [next_node]
                    cost = len(test_rule)
                    heuristic = heuristic_func(test_rule, mapper, db_inspector)
                    priority = cost - heuristic
                    
                    counter += 1
                    heapq.heappush(
                        priority_queue,
                        (priority, counter, next_node, new_candidate_rule, new_visited)
                    )


def get_traversal_algorithm(algorithm_name: str):
    """
    Factory function to get the appropriate traversal algorithm.
    
    :param algorithm_name: Name of the algorithm ('dfs', 'bfs', or 'astar').
    :return: The traversal function.
    :raises ValueError: If algorithm_name is not recognized.
    """
    algorithms = {
        'dfs': dfs,
        'bfs': bfs,
        'astar': astar,
        'a-star': astar,
        'a_star': astar,
    }
    
    algorithm_name_lower = algorithm_name.lower()
    if algorithm_name_lower not in algorithms:
        raise ValueError(
            f"Unknown traversal algorithm: {algorithm_name}. "
            f"Available algorithms: {', '.join(set(algorithms.keys()))}"
        )
    
    return algorithms[algorithm_name_lower]
