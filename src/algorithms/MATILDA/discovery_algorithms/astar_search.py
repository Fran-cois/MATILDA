"""
Algorithme de recherche A* pour la découverte de règles.
"""

from collections.abc import Iterator
from queue import PriorityQueue

from algorithms.MATILDA.constraint_graph import (
    AttributeMapper,
    ConstraintGraph,
)
from algorithms.MATILDA.discovery_algorithms.common import (
    CandidateRule,
    PrioritizedRule,
    calculate_path_cost,
    calculate_heuristic_score,
    next_node_test
)
from database.alchemy_utility import AlchemyUtility
from algorithms.MATILDA.rule_types.tgd_discovery import extract_table_occurrences

def a_star_search(
    cg: ConstraintGraph,
    start: CandidateRule,
    pruning_fn: callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int = 3,
    max_vars: int = 6
) -> Iterator[CandidateRule]:
    """
    Implémentation de recherche A* pour la découverte de règles avec élagage branch-and-bound.
    
    :param cg: Graphe de contrainte
    :param start: Nœud de départ
    :param pruning_fn: Fonction pour l'élagage du chemin
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :return: Générateur de règles candidates
    """
    frontier = PriorityQueue()
    visited = set()
    
    # Track best rule found so far
    best_rule = None
    best_score = float('-inf')
    
    # Build initial node if provided
    if start:
        cost = calculate_path_cost(start)
        heuristic = calculate_heuristic_score(start, db_inspector, mapper)
        frontier.put(PrioritizedRule(cost, heuristic, start))
    else:
        # Start from all nodes
        for node in cg.nodes:
            if next_node_test([], node, set(), max_table, max_vars):
                cost = calculate_path_cost([node])
                heuristic = calculate_heuristic_score([node], db_inspector, mapper)
                frontier.put(PrioritizedRule(cost, heuristic, [node]))
    
    while not frontier.empty():
        current_item = frontier.get()
        current = current_item.rule
        current_score = -(current_item.cost + current_item.heuristic)  # Convert back from negative
        
        # Skip if already visited
        current_key = str(current)
        if current_key in visited:
            continue
            
        visited.add(current_key)
        
        # If it's a rule (not just a node), check if it's better than what we've found
        if isinstance(current, list) and len(current) > 0:
            if current_score > best_score:
                best_score = current_score
                best_rule = current
                yield current
        
        # Get neighbors for expansion
        neighbors = []
        if isinstance(current, list):
            # For lists of nodes, find neighbors of the last node
            if len(current) > 0:
                big_neighbours = []
                for node in current:
                    big_neighbours += [e for e in cg.neighbors(node) if str(e) not in visited]
                neighbors = big_neighbours
        else:
            # For single nodes
            neighbors = cg.neighbors(current)
        
        # Expand neighbors
        for neighbor in neighbors:
            # Create new rule candidate by adding neighbor
            if isinstance(current, list):
                new_candidate = current + [neighbor]
            else:
                new_candidate = [current, neighbor]
                
            if (str(new_candidate) not in visited and 
                len(extract_table_occurrences(new_candidate)) <= max_table and 
                len(new_candidate) <= max_vars):
                
                # Branch and bound pruning - skip if can't be better than best
                new_cost = calculate_path_cost(new_candidate, len(new_candidate))
                new_heuristic = calculate_heuristic_score(new_candidate, db_inspector, mapper)
                new_score = -(new_cost + new_heuristic)  # Convert back from negative
                
                # Skip if this branch can't improve on best solution
                if new_score <= best_score and best_rule is not None:
                    continue
                
                # Apply domain-specific pruning
                if pruning_fn(new_candidate, mapper, db_inspector):
                    frontier.put(PrioritizedRule(new_cost, new_heuristic, new_candidate))


def best_first_search(
    cg: ConstraintGraph,
    start: CandidateRule,
    pruning_fn: callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int = 3,
    max_vars: int = 6
) -> Iterator[CandidateRule]:
    """
    Implémentation de recherche meilleur-d'abord pour la découverte de règles.
    
    :param cg: Graphe de contrainte
    :param start: Nœud de départ
    :param pruning_fn: Fonction pour l'élagage du chemin
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :return: Générateur de règles candidates
    """
    frontier = PriorityQueue()
    visited = set()
    best_score = 0

    if start:
        score = calculate_heuristic_score(start, db_inspector, mapper)
        frontier.put(PrioritizedRule(0, score, start))

    while not frontier.empty():
        current = frontier.get().rule
        if str(current) in visited:
            continue
            
        visited.add(str(current))
        yield current

        # Expand neighbors
        for neighbor in cg.neighbors(current):
            if (str(neighbor) not in visited and 
                len(neighbor.tables) <= max_table and 
                len(neighbor.variables) <= max_vars):
                
                if pruning_fn(neighbor, db_inspector, mapper):
                    score = calculate_heuristic_score(neighbor, db_inspector, mapper)
                    if score > best_score:
                        best_score = score
                        frontier.put(PrioritizedRule(0, score, neighbor))
