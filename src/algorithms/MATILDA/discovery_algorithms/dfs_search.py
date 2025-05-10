"""
Algorithme de recherche en profondeur (DFS) pour la découverte de règles.
"""

import copy
from collections.abc import Callable, Iterator
from tqdm import tqdm

from algorithms.MATILDA.constraint_graph import (
    AttributeMapper,
    ConstraintGraph,
    JoinableIndexedAttributes,
)
from algorithms.MATILDA.discovery_algorithms.common import (
    CandidateRule,
    next_node_test
)
from database.alchemy_utility import AlchemyUtility

def dfs(
    graph: ConstraintGraph,
    start_node: JoinableIndexedAttributes,
    pruning_prediction: Callable[
        [CandidateRule, AttributeMapper, AlchemyUtility],
        bool,
    ],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    visited: set[JoinableIndexedAttributes] = None,
    candidate_rule: CandidateRule = None,
    max_table: int = 3,
    max_vars: int = 6,
) -> Iterator[CandidateRule]:
    """
    Effectue un parcours en profondeur (DFS) avec une heuristique basée sur le chemin,
    en produisant la règle candidate menant à un arrêt déterminé par l'heuristique.

    :param graph: Une instance de la classe ConstraintGraph.
    :param start_node: Le nœud à partir duquel le DFS commence (ou None pour démarrer de tous les nœuds).
    :param pruning_prediction: Une fonction qui prend le chemin actuel et décide s'il faut continuer.
    :param db_inspector: Une instance d'AlchemyUtility pour l'interaction avec la base de données.
    :param mapper: Une instance d'AttributeMapper pour la correspondance des attributs.
    :param visited: Un ensemble pour garder trace des nœuds visités pour éviter les cycles.
    :param candidate_rule: Une liste pour suivre le chemin actuel des nœuds visités.
    :param max_table: Nombre maximum de tables dans une règle.
    :param max_vars: Nombre maximum de variables dans une règle.
    :yield: Les chemins valides jusqu'à, mais n'incluant pas, le nœud qui fait que l'heuristique retourne False.
    """
    if visited is None:
        visited = set()
    if candidate_rule is None:
        candidate_rule = []
        
    # Si aucun nœud de départ n'est spécifié, démarrer à partir de chaque nœud du graphe
    if start_node is None:
        for node in tqdm(graph.nodes, desc="Initial Nodes"):
            # Tester si le nœud est valide pour commencer une règle
            if next_node_test([], node, set(), max_table, max_vars):
                # Effectuer DFS à partir de ce nœud
                yield from dfs(
                        graph,
                        node,
                        pruning_prediction,
                        db_inspector,
                        mapper,
                        visited=set(),  # Nouvel ensemble de visites pour chaque départ
                        candidate_rule=[],  # Nouvelle règle vide
                        max_table=max_table,
                        max_vars=max_vars
                    )
        return
        
    # Marquer le nœud actuel comme visité et l'ajouter à la règle candidate
    visited.add(start_node)
    candidate_rule.append(start_node)
    
    # Appliquer la fonction d'élagage pour déterminer si on continue
    if not pruning_prediction(candidate_rule, mapper, db_inspector):
       return
        
    # Produire la règle candidate actuelle si elle contient au moins deux nœuds
    if len(candidate_rule) >= 1:
        yield copy.deepcopy(candidate_rule)

    # Explorer tous les voisins valides
    # Pour chaque nœud dans la règle candidate, explorer ses voisins
    big_neighbours = []
    for node in candidate_rule:
        for neighbor in graph.neighbors(node):
            if neighbor not in visited:
                big_neighbours.append(neighbor)
    
    # Explorer chaque voisin valide
    for next_node in big_neighbours:
        if next_node_test(candidate_rule, next_node, visited, max_table, max_vars) :
            # Récursion pour explorer ce chemin
            yield from dfs(
                graph,
                next_node,
                pruning_prediction,
                db_inspector,
                mapper,
                visited=visited,  # Utiliser le même ensemble de visites
                candidate_rule=candidate_rule,  # Utiliser la même règle
                max_table=max_table,
                max_vars=max_vars
            )
            
            # Retirer le nœud après avoir exploré son sous-arbre (backtracking)
            visited.remove(next_node)
            candidate_rule.pop()
