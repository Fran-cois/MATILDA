"""
Algorithme combinant recherche par faisceau (beam search) avec raffinement DFS local.

Cette approche maintient un faisceau des meilleurs candidats et effectue une 
exploration en profondeur limitée pour chacun d'eux, permettant de trouver 
un équilibre optimal entre exploration large et exploitation profonde.
"""

import logging
import copy
from collections.abc import Callable, Iterator
from typing import List, Set, Dict, Tuple
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
    prediction
)


def beam_dfs_search(
    cg: ConstraintGraph,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    beam_width: int = 10,
    dfs_depth: int = 2,
    max_iterations: int = 5,
    max_table: int = 3,
    max_vars: int = 6,
    quality_threshold: float = 0.3
) -> Iterator[CandidateRule]:
    """
    Algorithme combinant beam search avec raffinement DFS local.
    
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction pour déterminer si une règle doit être élaguée
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param beam_width: Largeur du faisceau (nombre de candidats à maintenir)
    :param dfs_depth: Profondeur maximale pour l'exploration DFS locale
    :param max_iterations: Nombre maximal d'itérations de l'algorithme
    :param max_table: Nombre maximum de tables dans une règle
    :param max_vars: Nombre maximum de variables dans une règle
    :param quality_threshold: Seuil de qualité minimal pour les règles
    :yield: Règles candidates de haute qualité
    """
    logging.info(f"Starting beam-DFS search with beam width={beam_width}, DFS depth={dfs_depth}")
    
    # Initialiser le faisceau avec des règles de départ prometteuses
    beam = initialize_beam(cg, pruning_prediction, db_inspector, mapper, beam_width, max_table, max_vars)
    logging.info(f"Initialized beam with {len(beam)} candidates")
    
    # Garder trace des règles déjà découvertes pour éviter les doublons
    discovered_rules = set()
    
    # Produire les règles initiales du faisceau
    for score, rule in beam:
        rule_str = str(rule)
        if rule_str not in discovered_rules and len(rule) >= 2:
            discovered_rules.add(rule_str)
            yield rule
    
    # Itérer le processus beam-DFS
    for iteration in range(max_iterations):
        logging.info(f"Beam-DFS iteration {iteration+1}/{max_iterations}")
        
        # Collecter de nouveaux candidats par DFS local depuis chaque règle du faisceau
        new_candidates = []
        
        for score, rule in tqdm(beam, desc="DFS refinement"):
            # Effectuer une recherche DFS limitée depuis cette règle
            local_candidates = explore_dfs_locally(
                cg, rule, pruning_prediction, db_inspector, mapper, 
                dfs_depth, max_table, max_vars
            )
            
            # Évaluer et ajouter les candidats trouvés
            for candidate in local_candidates:
                candidate_str = str(candidate)
                if candidate_str not in discovered_rules:
                    candidate_score = evaluate_rule(candidate, db_inspector, mapper)
                    if candidate_score >= quality_threshold:
                        new_candidates.append((candidate_score, candidate))
                        discovered_rules.add(candidate_str)
                        yield candidate
        
        # Mettre à jour le faisceau en combinant les anciens et les nouveaux candidats
        all_candidates = beam + new_candidates
        all_candidates.sort(reverse=True)  # Trier par score décroissant
        beam = all_candidates[:beam_width]  # Garder les beam_width meilleurs
        
        # Sortir si aucun nouveau candidat n'est trouvé
        if not new_candidates:
            logging.info("No new candidates found, stopping iterations")
            break
    
    logging.info(f"Beam-DFS search completed, discovered {len(discovered_rules)} unique rules")


def initialize_beam(
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    beam_width: int,
    max_table: int,
    max_vars: int
) -> List[Tuple[float, CandidateRule]]:
    """
    Initialise le faisceau avec des règles candidates prometteuses.
    
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param beam_width: Largeur du faisceau à initialiser
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :return: Liste de tuples (score, règle) triés par score décroissant
    """
    # Collecter les candidats initiaux (règles de longueur 1 ou 2)
    initial_candidates = []
    visited_rules = set()
    
    # Commencer par des nœuds uniques (règles de longueur 1)
    for node in tqdm(cg.nodes, desc="Initializing beam"):
        if next_node_test([], node, set(), max_table, max_vars):
            rule = [node]
            if pruning_prediction(rule, mapper, db_inspector):
                score = evaluate_rule(rule, db_inspector, mapper)
                initial_candidates.append((score, rule))
                visited_rules.add(str(rule))
                
                # Essayer d'étendre à une règle de longueur 2
                for neighbor in cg.neighbors(node):
                    if next_node_test(rule, neighbor, {node}, max_table, max_vars):
                        extended_rule = rule + [neighbor]
                        rule_str = str(extended_rule)
                        if rule_str not in visited_rules and pruning_prediction(extended_rule, mapper, db_inspector):
                            score = evaluate_rule(extended_rule, db_inspector, mapper)
                            initial_candidates.append((score, extended_rule))
                            visited_rules.add(rule_str)
    
    # Trier et limiter à beam_width candidats
    initial_candidates.sort(reverse=True)
    return initial_candidates[:beam_width]


def explore_dfs_locally(
    cg: ConstraintGraph,
    rule: CandidateRule,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_depth: int,
    max_table: int,
    max_vars: int
) -> List[CandidateRule]:
    """
    Effectue une exploration DFS locale à partir d'une règle donnée.
    
    :param cg: Graphe de contraintes
    :param rule: Règle à partir de laquelle faire l'exploration
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_depth: Profondeur maximale de l'exploration DFS
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :return: Liste des règles candidates découvertes
    """
    if not rule or len(rule) >= max_vars:
        return []
        
    discovered = []
    visited = set()
    
    def dfs_recursive(
        current_rule: CandidateRule,
        current_visited: Set[JoinableIndexedAttributes],
        current_depth: int
    ):
        # Ajouter la règle actuelle aux découvertes si elle est valide
        if len(current_rule) >= 2 and pruning_prediction(current_rule, mapper, db_inspector):
            discovered.append(current_rule.copy())
        
        # Arrêter si la profondeur max est atteinte
        if current_depth >= max_depth or len(current_rule) >= max_vars:
            return
            
        # Explorer tous les voisins valides
        neighbors = set()
        for node in current_rule:
            for neighbor in cg.neighbors(node):
                if (neighbor not in current_visited and 
                    next_node_test(current_rule, neighbor, current_visited, max_table, max_vars)):
                    neighbors.add(neighbor)
        
        # Explorations récursives pour chaque voisin valide
        for neighbor in neighbors:
            current_visited.add(neighbor)
            current_rule.append(neighbor)
            
            # Uniquement continuer l'exploration si la règle est valide
            if pruning_prediction(current_rule, mapper, db_inspector):
                dfs_recursive(current_rule, current_visited, current_depth + 1)
            
            # Retirer le voisin pour le backtracking
            current_rule.pop()
            current_visited.remove(neighbor)
    
    # Démarrer l'exploration récursive
    initial_visited = set(rule)
    dfs_recursive(rule.copy(), initial_visited, 0)
    
    return discovered


def evaluate_rule(
    rule: CandidateRule,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper
) -> float:
    """
    Évalue une règle candidate et retourne un score de qualité.
    
    :param rule: Règle candidate à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :return: Score de qualité entre 0 et 1
    """
    # Calcul basé sur le beam score existant
    base_score = calculate_beam_score(rule, mapper, db_inspector)
    
    # Facteurs supplémentaires pour affiner le score
    splits = split_candidate_rule(rule)
    if not splits:
        return 0.0
    
    split_scores = []
    for split in splits:
        body, head = split
        if not body or not head:
            continue
        
        try:
            valid, support, confidence = split_pruning(rule, body, head, db_inspector, mapper)
            if valid:
                # Calculer un score combiné pour cette division
                coverage_score = 0.0
                try:
                    # Obtenir une estimation de la couverture
                    coverage = prediction(rule, mapper, db_inspector)
                    if isinstance(coverage, (int, float)) and coverage > 0:
                        # Normaliser la couverture
                        coverage_score = min(0.2, coverage / 1000.0)
                except Exception:
                    pass
                
                # Score combiné: 40% support, 40% confiance, 20% couverture
                combined_score = 0.4 * support + 0.4 * confidence + coverage_score
                split_scores.append(combined_score)
        except Exception:
            continue
    
    # Si aucune division n'a de score valide
    if not split_scores:
        return 0.0
    
    # Utiliser le score de la meilleure division
    best_split_score = max(split_scores)
    
    # Balance entre le score de base et le score de division
    final_score = 0.5 * base_score + 0.5 * best_split_score
    
    # Ajuster selon la complexité de la règle (préférer des règles de taille moyenne)
    rule_length = len(rule)
    if rule_length <= 1:
        # Pénaliser les règles trop simples
        final_score *= 0.5
    elif rule_length > 4:
        # Pénaliser légèrement les règles très complexes
        final_score *= 0.8
    
    return final_score
