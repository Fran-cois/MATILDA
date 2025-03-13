"""
Algorithme de recherche en largeur (BFS) pour la découverte de règles.
"""

import copy
from collections import deque
import logging
from collections.abc import Callable, Iterator
from tqdm import tqdm

from algorithms.MATILDA.constraint_graph import (
    AttributeMapper,
    ConstraintGraph,
    JoinableIndexedAttributes,
)
from algorithms.MATILDA.discovery_algorithms.common import (
    CandidateRule, next_node_test
)
from database.alchemy_utility import AlchemyUtility

def bfs(
    graph: ConstraintGraph,
    start_node: JoinableIndexedAttributes,
    pruning_prediction: Callable[
        [CandidateRule, AttributeMapper, AlchemyUtility],
        bool,
    ],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int = 3,
    max_vars: int = 6
) -> Iterator[CandidateRule]:
    """
    Effectue une recherche en largeur (BFS) pour découvrir des règles candidates.
    Explore le graphe niveau par niveau, en commençant par le nœud initial ou tous les nœuds.

    :param graph: Une instance de la classe ConstraintGraph.
    :param start_node: Le nœud à partir duquel la BFS démarre, ou None pour commencer depuis tous les nœuds.
    :param pruning_prediction: Fonction qui prend une règle candidate et décide si elle doit être élaguée.
    :param db_inspector: Instance d'AlchemyUtility pour l'interaction avec la base de données.
    :param mapper: Instance d'AttributeMapper pour la correspondance des attributs.
    :param max_table: Nombre maximum de tables autorisées dans une règle.
    :param max_vars: Nombre maximum de variables autorisées dans une règle.
    :yield: Les règles candidates valides explorées niveau par niveau.
    """
    # Si aucun nœud de départ n'est fourni, commencer par tous les nœuds
    if start_node is None:
        logging.info("Starting BFS from all nodes")
        for node in tqdm(graph.nodes, desc="Initial Nodes"):
            if next_node_test([], node, set(), max_table, max_vars):
                yield from bfs_from_node(
                    graph, node, pruning_prediction, db_inspector, mapper, 
                    max_table, max_vars
                )
        return
    
    # Sinon, commencer par le nœud spécifié
    yield from bfs_from_node(
        graph, start_node, pruning_prediction, db_inspector, mapper, 
        max_table, max_vars
    )

def bfs_from_node(
    graph: ConstraintGraph,
    start_node: JoinableIndexedAttributes,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int = 3,
    max_vars: int = 6
) -> Iterator[CandidateRule]:
    """
    Implémente la recherche en largeur à partir d'un nœud spécifique.
    
    :param graph: Graphe de contraintes
    :param start_node: Nœud de départ
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :yield: Règles candidates valides
    """
    queue = deque()
    visited_rules = set()
    
    # Créer la règle candidate initiale avec le nœud de départ
    initial_candidate = [start_node]
    if pruning_prediction(initial_candidate, mapper, db_inspector):
        queue.append((initial_candidate, {start_node}))
        visited_rules.add(str(initial_candidate))
        yield initial_candidate
    
    while queue:
        current_candidate, current_visited = queue.popleft()
        
        # Si la longueur maximale est atteinte, ne pas explorer plus loin
        if len(current_candidate) >= max_vars:
            continue
        
        # Trouver tous les voisins valides
        neighbors = []
        for node in current_candidate:
            for neighbor in graph.neighbors(node):
                if neighbor not in current_visited and next_node_test(current_candidate, neighbor, current_visited, max_table, max_vars):
                    neighbors.append(neighbor)
        
        # Ajouter chaque voisin valide à la file
        for neighbor in neighbors:
            new_candidate = current_candidate + [neighbor]
            new_visited = current_visited.union({neighbor})
            
            # Éviter les règles déjà visitées
            candidate_key = str(new_candidate)
            if candidate_key in visited_rules:
                continue
            
            # Appliquer l'élagage
            if pruning_prediction(new_candidate, mapper, db_inspector):
                visited_rules.add(candidate_key)
                queue.append((new_candidate, new_visited))
                yield new_candidate
