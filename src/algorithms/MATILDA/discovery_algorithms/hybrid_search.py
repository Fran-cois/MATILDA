"""
Algorithme de recherche hybride BFS-DFS pour la découverte de règles.

Cet algorithme commence par une exploration en largeur (BFS) pour identifier 
rapidement un ensemble diversifié de candidats prometteurs, puis passe à une 
exploration en profondeur (DFS) pour affiner ces candidats.
"""

import logging
import heapq
import copy
from collections import deque
from collections.abc import Callable, Iterator
from typing import List, Set, Dict, Tuple, Optional
from tqdm import tqdm

from algorithms.MATILDA.constraint_graph import (
    AttributeMapper,
    ConstraintGraph,
    JoinableIndexedAttributes,
)
from algorithms.MATILDA.discovery_algorithms.common import (
    CandidateRule,
    next_node_test,
    calculate_beam_score
)
from database.alchemy_utility import AlchemyUtility
from algorithms.MATILDA.rule_types.tgd_discovery import (
    split_candidate_rule,
    split_pruning,
    prediction,
    instantiate_tgd
)

def hybrid_search(
    graph: ConstraintGraph,
    start_node: JoinableIndexedAttributes,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    bfs_levels: int = 2,
    top_k_candidates: int = 10,
    max_table: int = 3,
    max_vars: int = 6,
    quality_threshold: float = 0.2
) -> Iterator[CandidateRule]:
    """
    Effectue une recherche hybride BFS-DFS pour la découverte de règles.
    
    :param graph: Graphe de contraintes
    :param start_node: Nœud de départ ou None pour commencer depuis tous les nœuds
    :param pruning_prediction: Fonction pour déterminer si une règle doit être élaguée
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param bfs_levels: Nombre de niveaux à explorer avec BFS avant de passer à DFS
    :param top_k_candidates: Nombre de meilleurs candidats à sélectionner après BFS
    :param max_table: Nombre maximum de tables dans une règle
    :param max_vars: Nombre maximum de variables dans une règle
    :param quality_threshold: Seuil de qualité pour considérer un candidat comme prometteur
    :yield: Règles candidates découvertes
    """
    logging.info(f"Starting hybrid search with BFS levels={bfs_levels}, top_k={top_k_candidates}")
    
    # Première phase: BFS pour l'exploration initiale
    bfs_candidates = []
    discovered_rules = set()
    
    # Si aucun nœud de départ n'est spécifié, commencer par tous les nœuds possibles
    if start_node is None:
        logging.info("Starting BFS phase from all initial nodes")
        for node in tqdm(graph.nodes, desc="Initial BFS exploration"):
            if next_node_test([], node, set(), max_table, max_vars):
                bfs_results = list(bfs_phase(
                    graph, node, pruning_prediction, db_inspector, mapper,
                    max_levels=bfs_levels, max_table=max_table, max_vars=max_vars
                ))
                bfs_candidates.extend(bfs_results)
    else:
        # Commencer depuis le nœud spécifié
        logging.info(f"Starting BFS phase from specified node")
        bfs_results = list(bfs_phase(
            graph, start_node, pruning_prediction, db_inspector, mapper,
            max_levels=bfs_levels, max_table=max_table, max_vars=max_vars
        ))
        bfs_candidates.extend(bfs_results)
    
    # Éliminer les doublons
    unique_bfs_candidates = []
    for rule in bfs_candidates:
        rule_key = str(rule)
        if rule_key not in discovered_rules:
            discovered_rules.add(rule_key)
            unique_bfs_candidates.append(rule)
    
    logging.info(f"BFS phase completed, found {len(unique_bfs_candidates)} unique candidates")
    
    # Évaluer et classer les candidats BFS
    ranked_candidates = rank_candidates(unique_bfs_candidates, db_inspector, mapper)
    
    # Sélectionner les top_k candidats avec une qualité suffisante
    promising_candidates = [
        rule for score, rule in ranked_candidates 
        if score >= quality_threshold
    ][:top_k_candidates]
    
    logging.info(f"Selected {len(promising_candidates)} promising candidates for DFS phase")
    
    # Deuxième phase: DFS pour l'exploration approfondie
    for candidate in tqdm(promising_candidates, desc="DFS refinement phase"):
        # Commencer DFS à partir de ce candidat
        dfs_results = dfs_phase(
            graph, candidate, pruning_prediction, db_inspector, mapper,
            visited=set(candidate), candidate_rule=candidate.copy(),
            max_table=max_table, max_vars=max_vars
        )
        
        # Yield les résultats de DFS
        for rule in dfs_results:
            rule_key = str(rule)
            if rule_key not in discovered_rules:
                discovered_rules.add(rule_key)
                yield rule
        
        # Également yield le candidat BFS original s'il n'a pas été inclus dans les résultats DFS
        if str(candidate) not in discovered_rules:
            discovered_rules.add(str(candidate))
            yield candidate
    
    logging.info(f"Hybrid search completed, discovered {len(discovered_rules)} unique rules")

def bfs_phase(
    graph: ConstraintGraph,
    start_node: JoinableIndexedAttributes,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_levels: int = 2,
    max_table: int = 3,
    max_vars: int = 6
) -> Iterator[CandidateRule]:
    """
    Première phase: Recherche en largeur (BFS) jusqu'à une profondeur maximale.
    
    :param graph: Graphe de contraintes
    :param start_node: Nœud de départ
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_levels: Nombre maximum de niveaux BFS
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :yield: Règles candidates jusqu'à max_levels
    """
    queue = deque()
    visited_rules = set()
    
    # Initialiser avec le nœud de départ
    initial_rule = [start_node]
    if pruning_prediction(initial_rule, mapper, db_inspector):
        queue.append((initial_rule, {start_node}, 1))  # (règle, visités, niveau)
        visited_rules.add(str(initial_rule))
        yield initial_rule
    
    # BFS limité par niveau
    while queue:
        current_rule, current_visited, current_level = queue.popleft()
        
        # Si le niveau maximum est atteint, ne pas explorer plus loin
        if current_level >= max_levels:
            continue
        
        # Explorer tous les voisins valides
        neighbors = set()
        for node in current_rule:
            for neighbor in graph.neighbors(node):
                if (neighbor not in current_visited and 
                    next_node_test(current_rule, neighbor, current_visited, max_table, max_vars)):
                    neighbors.add(neighbor)
        
        # Ajouter chaque voisin à la file
        for neighbor in neighbors:
            new_rule = current_rule + [neighbor]
            new_visited = current_visited.union({neighbor})
            
            # Vérifier si cette règle a déjà été vue
            rule_key = str(new_rule)
            if rule_key in visited_rules:
                continue
                
            # Vérifier si la règle est valide selon l'élagage
            if pruning_prediction(new_rule, mapper, db_inspector):
                visited_rules.add(rule_key)
                queue.append((new_rule, new_visited, current_level + 1))
                yield new_rule

def dfs_phase(
    graph: ConstraintGraph,
    start_rule: CandidateRule,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    visited: Set[JoinableIndexedAttributes] = None,
    candidate_rule: CandidateRule = None,
    max_table: int = 3,
    max_vars: int = 6,
) -> Iterator[CandidateRule]:
    """
    Deuxième phase: Recherche en profondeur (DFS) à partir d'un candidat prometteur.
    
    :param graph: Graphe de contraintes
    :param start_rule: Règle candidate à partir de laquelle commencer le DFS
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param visited: Ensemble des nœuds déjà visités
    :param candidate_rule: Règle candidate en cours d'exploration
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :yield: Règles candidates trouvées par DFS
    """
    if visited is None:
        visited = set(start_rule)
    if candidate_rule is None:
        candidate_rule = start_rule.copy()
    
    # Vérifier si la règle est valide
    if pruning_prediction(candidate_rule, mapper, db_inspector):
        yield candidate_rule
    else:
        return
    
    # Explorer tous les voisins valides de tous les nœuds dans la règle
    neighbors = []
    for node in candidate_rule:
        for neighbor in graph.neighbors(node):
            if (neighbor not in visited and 
                next_node_test(candidate_rule, neighbor, visited, max_table, max_vars)):
                neighbors.append(neighbor)
    
    # Trier les voisins pour une exploration plus cohérente
    # (on pourrait intégrer une heuristique ici pour guider l'exploration)
    for neighbor in neighbors:
        # Ajouter le voisin et continuer l'exploration en profondeur
        visited.add(neighbor)
        candidate_rule.append(neighbor)
        
        yield from dfs_phase(
            graph, start_rule, pruning_prediction, db_inspector, mapper,
            visited, candidate_rule, max_table, max_vars
        )
        
        # Retirer le voisin pour backtracking
        candidate_rule.pop()
        visited.remove(neighbor)

def rank_candidates(
    candidates: List[CandidateRule],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper
) -> List[Tuple[float, CandidateRule]]:
    """
    Évalue et classe les candidats selon leur qualité.
    
    :param candidates: Liste des règles candidates à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :return: Liste des tuples (score, règle) triés par score décroissant
    """
    scores = []
    
    for candidate in tqdm(candidates, desc="Ranking candidates"):
        # Calculer un score pour chaque candidat
        score = calculate_candidate_score(candidate, db_inspector, mapper)
        scores.append((score, candidate))
    
    # Trier par score décroissant
    return sorted(scores, key=lambda x: x[0], reverse=True)

def calculate_candidate_score(
    candidate: CandidateRule,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper
) -> float:
    """
    Calcule un score de qualité pour une règle candidate.
    
    :param candidate: Règle candidate à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :return: Score de qualité
    """
    # Utiliser beam_score comme base
    beam_score = calculate_beam_score(candidate, mapper, db_inspector)
    
    # Facteurs supplémentaires pour l'évaluation
    splits = split_candidate_rule(candidate)
    if not splits:
        return 0.0
    
    # Calculer les métriques pour chaque division possible
    split_scores = []
    for split in splits:
        body, head = split
        if not body or not head:
            continue
            
        try:
            valid, support, confidence = split_pruning(candidate, body, head, db_inspector, mapper)
            if valid:
                # Moyenne pondérée de support et confiance
                weighted_score = 0.4 * support + 0.6 * confidence
                split_scores.append(weighted_score)
        except Exception as e:
            logging.debug(f"Error calculating split score: {e}")
    
    # Si aucune division n'a de score valide, retourner 0
    if not split_scores:
        return 0.0
    
    # Prendre le meilleur score de division
    best_split_score = max(split_scores)
    
    # Bonus pour les règles plus complètes mais pas trop complexes
    # (favorise les règles avec 2-4 attributs)
    complexity_factor = 1.0
    if len(candidate) <= 1:
        complexity_factor = 0.5  # Pénaliser les règles trop simples
    elif len(candidate) > 4:
        complexity_factor = 0.7  # Légère pénalité pour les règles très complexes
    
    # Combiner les scores
    final_score = (beam_score + best_split_score) * complexity_factor
    
    return final_score
