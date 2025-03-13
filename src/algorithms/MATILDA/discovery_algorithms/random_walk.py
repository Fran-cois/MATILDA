"""
Algorithme de marche aléatoire (Random Walk) pour la découverte de règles.

Cet algorithme explore l'espace des règles de manière stochastique en sélectionnant 
aléatoirement des littéraux à ajouter à la règle jusqu'à ce qu'elle soit complète.
"""

import logging
import random
from collections.abc import Callable, Iterator
from typing import List, Set, Dict, Optional, Tuple
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
    extract_table_occurrences,
    split_candidate_rule,
    split_pruning,
    prediction
)


def random_walk_search(
    cg: ConstraintGraph,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    num_walks: int = 100,
    max_walk_length: int = 10,
    max_table: int = 3,
    max_vars: int = 6,
    quality_threshold: float = 0.3,
    restart_probability: float = 0.1
) -> Iterator[CandidateRule]:
    """
    Effectue une recherche par marche aléatoire pour découvrir des règles.
    
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction pour déterminer si une règle doit être élaguée
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param num_walks: Nombre de marches aléatoires à effectuer
    :param max_walk_length: Longueur maximale d'une marche (nombre d'étapes)
    :param max_table: Nombre maximum de tables dans une règle
    :param max_vars: Nombre maximum de variables dans une règle
    :param quality_threshold: Seuil de qualité minimale pour qu'une règle soit retournée
    :param restart_probability: Probabilité de redémarrer la marche à partir d'un nouveau nœud
    :yield: Règles candidates découvertes par marche aléatoire
    """
    discovered_rules = set()
    best_rules: Dict[str, Tuple[CandidateRule, float]] = {}
    
    all_nodes = list(cg.nodes)
    if not all_nodes:
        logging.warning("No nodes found in constraint graph")
        return
    
    logging.info(f"Starting random walk search with {num_walks} walks")
    
    for walk_num in tqdm(range(num_walks), desc="Random Walks"):
        # Créer une nouvelle marche aléatoire
        rule = []
        visited = set()
        
        # Choisir un nœud de départ aléatoire valide
        start_node = select_random_valid_node(cg, rule, visited, all_nodes, max_table, max_vars)
        if not start_node:
            continue
            
        rule.append(start_node)
        visited.add(start_node)
        
        # Validation initiale
        if not pruning_prediction(rule, mapper, db_inspector):
            continue
            
        # Continuer la marche
        for step in range(1, max_walk_length):
            # Décider si on redémarre la marche
            if random.random() < restart_probability and len(rule) > 1:
                # Évaluer la règle actuelle avant de redémarrer
                evaluate_and_store_rule(
                    rule, db_inspector, mapper, 
                    best_rules, discovered_rules, 
                    quality_threshold
                )
                
                # Recommencer avec une nouvelle règle
                rule = []
                visited = set()
                start_node = select_random_valid_node(cg, rule, visited, all_nodes, max_table, max_vars)
                if not start_node:
                    break
                    
                rule.append(start_node)
                visited.add(start_node)
                continue
            
            # Étendre la règle avec un nouveau nœud aléatoire
            next_node = select_random_neighbor(cg, rule, visited, max_table, max_vars)
            
            # Si aucun voisin valide n'est trouvé, terminer cette marche
            if not next_node:
                break
                
            # Ajouter le nœud à la règle
            rule.append(next_node)
            visited.add(next_node)
            
            # Vérifier si la règle est valide
            if not pruning_prediction(rule, mapper, db_inspector):
                # Si la règle n'est pas valide, retirer le dernier nœud
                rule.pop()
                visited.remove(next_node)
                continue
            
            # Évaluer périodiquement des sous-règles
            if len(rule) >= 2 and random.random() < 0.3:
                evaluate_and_store_rule(
                    rule, db_inspector, mapper, 
                    best_rules, discovered_rules, 
                    quality_threshold
                )
        
        # Évaluer la règle finale après la marche
        if rule and len(rule) >= 2:
            evaluate_and_store_rule(
                rule, db_inspector, mapper, 
                best_rules, discovered_rules, 
                quality_threshold
            )
    
    # Retourner les règles découvertes par ordre de qualité décroissante
    sorted_rules = sorted(best_rules.values(), key=lambda x: x[1], reverse=True)
    
    for rule, _ in sorted_rules:
        yield rule


def select_random_valid_node(
    cg: ConstraintGraph,
    rule: CandidateRule,
    visited: Set[JoinableIndexedAttributes],
    all_nodes: List[JoinableIndexedAttributes],
    max_table: int,
    max_vars: int
) -> Optional[JoinableIndexedAttributes]:
    """
    Sélectionne aléatoirement un nœud valide comme point de départ.
    
    :param cg: Graphe de contraintes
    :param rule: Règle actuelle
    :param visited: Nœuds déjà visités
    :param all_nodes: Liste de tous les nœuds disponibles
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :return: Un nœud aléatoire valide ou None si aucun n'est trouvé
    """
    # Si la règle a déjà atteint la limite, ne rien retourner
    if len(rule) >= max_vars:
        return None
    
    # Mélanger les nœuds pour la sélection aléatoire
    random.shuffle(all_nodes)
    
    # Essayer jusqu'à 30 nœuds aléatoires
    for _ in range(min(30, len(all_nodes))):
        candidate = random.choice(all_nodes)
        if candidate not in visited and next_node_test(rule, candidate, visited, max_table, max_vars):
            return candidate
    
    return None


def select_random_neighbor(
    cg: ConstraintGraph,
    rule: CandidateRule,
    visited: Set[JoinableIndexedAttributes],
    max_table: int,
    max_vars: int
) -> Optional[JoinableIndexedAttributes]:
    """
    Sélectionne aléatoirement un nœud voisin valide pour étendre la règle.
    
    :param cg: Graphe de contraintes
    :param rule: Règle actuelle
    :param visited: Nœuds déjà visités
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :return: Un voisin aléatoire valide ou None si aucun n'est trouvé
    """
    valid_neighbors = []
    
    # Collecter tous les voisins valides de tous les nœuds dans la règle
    for node in rule:
        for neighbor in cg.neighbors(node):
            if neighbor not in visited and next_node_test(rule, neighbor, visited, max_table, max_vars):
                valid_neighbors.append(neighbor)
    
    # S'il n'y a pas de voisins valides, retourner None
    if not valid_neighbors:
        return None
    
    # Sélectionner aléatoirement un voisin valide
    return random.choice(valid_neighbors)


def evaluate_and_store_rule(
    rule: CandidateRule,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    best_rules: Dict[str, Tuple[CandidateRule, float]],
    discovered_rules: Set[str],
    quality_threshold: float
) -> None:
    """
    Évalue une règle et la stocke si elle est de bonne qualité.
    
    :param rule: Règle à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param best_rules: Dictionnaire des meilleures règles trouvées jusqu'à présent
    :param discovered_rules: Ensemble des règles déjà découvertes (pour éviter les doublons)
    :param quality_threshold: Seuil de qualité minimale
    """
    rule_str = str(rule)
    
    # Éviter de réévaluer les règles déjà découvertes
    if rule_str in discovered_rules:
        return
    
    discovered_rules.add(rule_str)
    
    # Calculer le score de la règle
    quality = evaluate_rule_quality(rule, db_inspector, mapper)
    
    # Stocker la règle si elle dépasse le seuil de qualité
    if quality > quality_threshold:
        best_rules[rule_str] = (rule.copy(), quality)


def evaluate_rule_quality(
    rule: CandidateRule,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper
) -> float:
    """
    Évalue la qualité d'une règle générée par marche aléatoire.
    
    :param rule: Règle à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :return: Score de qualité de la règle
    """
    # Utiliser le score de beam comme base
    base_score = calculate_beam_score(rule, mapper, db_inspector)
    
    # Facteurs supplémentaires à considérer
    splits = split_candidate_rule(rule)
    if not splits:
        return 0.0
    
    # Calculer la moyenne des scores pour toutes les divisions possibles
    split_scores = []
    for split in splits:
        body, head = split
        if not body or not head:
            continue
        
        try:
            valid, support, confidence = split_pruning(rule, body, head, db_inspector, mapper)
            if valid:
                # Équilibrer support et confiance
                split_scores.append((support + confidence) / 2)
        except Exception:
            pass
    
    # Si aucune division n'est valide, retourner 0
    if not split_scores:
        return 0.0
    
    # Calculer la moyenne des scores de division
    avg_split_score = sum(split_scores) / len(split_scores)
    
    # Bonus pour les règles concises
    conciseness_bonus = 0.1 * (1.0 / len(rule)) if len(rule) > 0 else 0
    
    # Score final
    return base_score + avg_split_score + conciseness_bonus
