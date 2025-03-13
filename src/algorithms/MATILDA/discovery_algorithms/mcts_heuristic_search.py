"""
Algorithme combinant Monte Carlo Tree Search (MCTS) avec élagage heuristique.

Cette approche utilise MCTS pour explorer efficacement l'espace des règles
tout en appliquant des heuristiques d'élagage précoce pour éliminer rapidement
les expansions à faible potentiel.
"""

import logging
import random
import math
import time
from collections.abc import Callable, Iterator
from typing import Optional, Dict, List, Set, Tuple, Any
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
    extract_table_occurrences
)


class MCTSHNode:
    """Nœud de l'arbre de recherche Monte Carlo avec élagage heuristique."""
    
    def __init__(
        self,
        rule: CandidateRule,
        parent: Optional['MCTSHNode'] = None,
        visit_count: int = 0,
        total_score: float = 0.0,
        is_terminal: bool = False,
        heuristic_value: float = 0.0
    ):
        self.rule = rule
        self.parent = parent
        self.visit_count = visit_count
        self.total_score = total_score
        self.is_terminal = is_terminal
        self.heuristic_value = heuristic_value  # Valeur heuristique pour guider l'élagage
        self.children: Dict[str, 'MCTSHNode'] = {}  # Clé = repr du nœud ajouté
        self.untried_actions: List[Tuple[JoinableIndexedAttributes, float]] = []  # Nœuds pas encore essayés avec scores heuristiques
        self.pruned_actions: Set[JoinableIndexedAttributes] = set()  # Actions élaguées par heuristiques


def mcts_heuristic_search(
    cg: ConstraintGraph,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    iterations: int = 1000,
    exploration_weight: float = 1.5,
    max_table: int = 3,
    max_vars: int = 6,
    playout_depth: int = 3,
    heuristic_threshold: float = 0.2,  # Seuil pour l'élagage heuristique
    time_budget: float = 60.0,  # Budget temps en secondes
    early_stopping_threshold: int = 100  # Arrêt anticipé si pas d'amélioration
) -> Iterator[CandidateRule]:
    """
    Monte Carlo Tree Search avec élagage heuristique pour la découverte de règles.
    
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction de base pour l'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param iterations: Nombre maximal d'itérations
    :param exploration_weight: Facteur d'exploration pour UCT (UCB1-Tuned)
    :param max_table: Nombre maximum de tables dans une règle
    :param max_vars: Nombre maximum de variables dans une règle
    :param playout_depth: Profondeur maximale des playouts
    :param heuristic_threshold: Seuil de qualité pour l'élagage heuristique
    :param time_budget: Budget temps maximum en secondes
    :param early_stopping_threshold: Nombre d'itérations sans amélioration avant arrêt
    :yield: Règles candidates découvertes
    """
    start_time = time.time()
    logging.info(f"Starting MCTS with heuristic pruning, max iterations: {iterations}")
    
    # Création du nœud racine
    root = MCTSHNode(rule=[])
    
    # Découvertes uniques pour éviter les doublons
    unique_discoveries = set()
    best_rules = {}  # Dict[str, Tuple[CandidateRule, float]]
    
    # Initialisation des actions possibles pour la racine avec heuristiques
    initialize_actions_with_heuristics(
        root, cg, [], set(), max_table, max_vars, 
        pruning_prediction, db_inspector, mapper, heuristic_threshold
    )
    
    # Métriques pour l'arrêt anticipé
    iterations_without_improvement = 0
    best_score_ever = 0.0
    
    for iteration in tqdm(range(iterations), desc="MCTS-H iterations"):
        # Vérifier le budget temps
        if (time.time() - start_time) > time_budget:
            logging.info(f"Time budget exceeded after {iteration} iterations")
            break
            
        # Vérifier l'arrêt anticipé
        if iterations_without_improvement > early_stopping_threshold:
            logging.info(f"Early stopping after {iteration} iterations without improvement")
            break
            
        # 1. Sélection avec intégration heuristique
        node = select_node_heuristic(root, exploration_weight)
        
        # 2. Expansion guidée par heuristique
        if not node.is_terminal and node.untried_actions:
            node = expand_node_heuristic(
                node, cg, pruning_prediction, db_inspector, 
                mapper, max_table, max_vars
            )
        
        # 3. Simulation avec coupure heuristique
        if node is not None:  # L'expansion peut échouer si toutes les actions sont élaguées
            # Simulation avec limite de profondeur adaptative basée sur la promesse heuristique
            simulation_depth = adjust_playout_depth(node, playout_depth)
            simulation_score = simulate_with_heuristics(
                node.rule, cg, pruning_prediction, db_inspector, mapper, 
                max_table, max_vars, simulation_depth, heuristic_threshold
            )
            
            # 4. Rétropropagation avec poids heuristique
            backpropagate_with_heuristics(node, simulation_score)
            
            # Vérifier si c'est une amélioration pour l'arrêt anticipé
            if simulation_score > best_score_ever:
                best_score_ever = simulation_score
                iterations_without_improvement = 0
            else:
                iterations_without_improvement += 1
            
            # Vérifier si nous avons une nouvelle règle prometteuse à retourner
            if (len(node.rule) >= 2 and node.visit_count > 3 and 
                (node.total_score / node.visit_count) > 0.4):
                rule_str = str(node.rule)
                if rule_str not in unique_discoveries:
                    unique_discoveries.add(rule_str)
                    quality = node.total_score / node.visit_count
                    best_rules[rule_str] = (node.rule, quality)
                    yield node.rule
    
    # À la fin, retourner les meilleures règles trouvées
    best_nodes = get_best_nodes_heuristic(root, 10)  # Obtenir les 10 meilleurs nœuds
    
    for node, score in best_nodes:
        if str(node.rule) not in unique_discoveries and len(node.rule) >= 2:
            unique_discoveries.add(str(node.rule))
            yield node.rule


def initialize_actions_with_heuristics(
    node: MCTSHNode,
    cg: ConstraintGraph,
    rule: CandidateRule,
    visited: Set[JoinableIndexedAttributes],
    max_table: int,
    max_vars: int,
    pruning_fn: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    threshold: float
) -> None:
    """
    Initialise les actions possibles pour un nœud avec scores heuristiques.
    
    :param node: Nœud pour lequel initialiser les actions
    :param cg: Graphe de contraintes
    :param rule: Règle candidate actuelle
    :param visited: Nœuds déjà visités
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :param pruning_fn: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param threshold: Seuil pour l'élagage heuristique
    """
    potential_actions = []
    
    if node.rule:
        # Si nous avons déjà des nœuds dans la règle, trouver les voisins valides
        for existing_node in node.rule:
            for neighbor in cg.neighbors(existing_node):
                if (neighbor not in visited and 
                    next_node_test(rule, neighbor, visited, max_table, max_vars)):
                    # Évaluer le potentiel de cette action avec une heuristique
                    potential_rule = rule + [neighbor]
                    heuristic_score = quick_heuristic_evaluation(
                        potential_rule, db_inspector, mapper
                    )
                    
                    # Élagage heuristique précoce
                    if heuristic_score >= threshold:
                        potential_actions.append((neighbor, heuristic_score))
                    else:
                        node.pruned_actions.add(neighbor)
    else:
        # Pour le nœud racine, considérer un échantillon de nœuds de départ
        sample_size = min(50, len(cg.nodes))  # Limiter à 50 nœuds de départ pour l'efficacité
        sampled_nodes = random.sample(list(cg.nodes), sample_size)
        
        for graph_node in sampled_nodes:
            if next_node_test([], graph_node, set(), max_table, max_vars):
                # Évaluer le potentiel de chaque nœud de départ
                potential_rule = [graph_node]
                heuristic_score = quick_heuristic_evaluation(
                    potential_rule, db_inspector, mapper
                )
                
                if heuristic_score >= threshold:
                    potential_actions.append((graph_node, heuristic_score))
                else:
                    node.pruned_actions.add(graph_node)
    
    # Trier par score heuristique décroissant pour privilégier les actions prometteuses
    potential_actions.sort(key=lambda x: x[1], reverse=True)
    node.untried_actions = potential_actions


def select_node_heuristic(node: MCTSHNode, exploration_weight: float) -> MCTSHNode:
    """
    Sélectionne un nœud à explorer en utilisant UCT avec bonus heuristique.
    
    :param node: Nœud à partir duquel commencer la sélection
    :param exploration_weight: Poids pour le terme d'exploration
    :return: Nœud sélectionné pour expansion ou simulation
    """
    # Si le nœud a des actions non essayées, on le retourne pour expansion
    if node.untried_actions or node.is_terminal:
        return node
    
    # Sinon, on utilise UCT avec bonus heuristique pour équilibrer exploitation et exploration
    best_score = float('-inf')
    best_child = None
    
    # Facteur de normalisation pour les scores heuristiques
    heuristic_factor = 0.2
    
    for child in node.children.values():
        # Éviter division par zéro
        if child.visit_count == 0:
            ucb_score = float('inf')
        else:
            # Exploitation (Q-value)
            exploitation = child.total_score / child.visit_count
            
            # Exploration (UCT)
            exploration = exploration_weight * math.sqrt(
                2.0 * math.log(node.visit_count) / child.visit_count
            )
            
            # Bonus heuristique
            heuristic_bonus = heuristic_factor * child.heuristic_value
            
            # Score UCT combiné
            ucb_score = exploitation + exploration + heuristic_bonus
        
        if ucb_score > best_score:
            best_score = ucb_score
            best_child = child
    
    # Poursuivre la sélection récursivement
    if best_child:
        return select_node_heuristic(best_child, exploration_weight)
    return node


def expand_node_heuristic(
    node: MCTSHNode,
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int,
    max_vars: int
) -> Optional[MCTSHNode]:
    """
    Étend le nœud actuel en choisissant une action basée sur son score heuristique.
    
    :param node: Nœud à étendre
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :return: Nouveau nœud enfant créé, ou None si aucune expansion n'est possible
    """
    if not node.untried_actions:
        return None
    
    # Sélectionner l'action avec le meilleur score heuristique (déjà triée lors de l'initialisation)
    action, heuristic_score = node.untried_actions.pop(0)
    
    # Créer la nouvelle règle en ajoutant l'action à la règle actuelle
    new_rule = node.rule + [action]
    visited = set(node.rule) | {action}
    
    # Vérifier si la règle est valide après élagage
    if pruning_prediction(new_rule, mapper, db_inspector):
        # Créer le nouveau nœud enfant avec la valeur heuristique
        child = MCTSHNode(
            rule=new_rule, 
            parent=node, 
            heuristic_value=heuristic_score
        )
        
        # Vérifier si le nœud est terminal (a atteint les limites max)
        child.is_terminal = (len(new_rule) >= max_vars or 
                            len({attr.i for jia in new_rule for attr in jia}) >= max_table)
        
        # Initialiser les actions possibles pour ce nouvel enfant avec élagage heuristique
        if not child.is_terminal:
            initialize_actions_with_heuristics(
                child, cg, new_rule, visited, max_table, max_vars,
                pruning_prediction, db_inspector, mapper, 0.1  # Seuil plus bas pour enfants
            )
        
        # Stocker l'enfant dans le parent
        node.children[str(action)] = child
        return child
    
    # Si l'action était invalide, la marquer comme élaguée
    node.pruned_actions.add(action)
    return None


def simulate_with_heuristics(
    rule: CandidateRule,
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int,
    max_vars: int,
    playout_depth: int,
    quality_threshold: float
) -> float:
    """
    Effectue une simulation avec coupure heuristique.
    
    :param rule: Règle candidate à partir de laquelle simuler
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :param playout_depth: Profondeur maximale de la simulation
    :param quality_threshold: Seuil de qualité pour les coupes heuristiques
    :return: Score de la règle après simulation
    """
    current_rule = rule.copy()
    visited = set(current_rule)
    
    # Évaluer la qualité initiale de la règle
    current_quality = evaluate_rule_with_heuristics(current_rule, db_inspector, mapper)
    best_quality = current_quality
    best_rule = current_rule.copy()
    
    # Simulation: étendre aléatoirement la règle avec élagage heuristique
    depth = 0
    consecutive_fails = 0
    max_consecutive_fails = 3  # Arrêt si trop d'échecs consécutifs
    
    while depth < playout_depth and len(current_rule) < max_vars and consecutive_fails < max_consecutive_fails:
        # Collecter et évaluer les voisins valides
        potential_neighbors = []
        
        for node in current_rule:
            for neighbor in cg.neighbors(node):
                if neighbor not in visited and next_node_test(current_rule, neighbor, visited, max_table, max_vars):
                    # Estimation rapide de la qualité potentielle
                    test_rule = current_rule + [neighbor]
                    potential_quality = quick_heuristic_evaluation(test_rule, db_inspector, mapper)
                    
                    # Ajouter seulement si la qualité dépasse le seuil
                    if potential_quality >= quality_threshold:
                        potential_neighbors.append((neighbor, potential_quality))
        
        # S'il n'y a pas de voisins prometteurs, incrémenter les échecs consécutifs
        if not potential_neighbors:
            consecutive_fails += 1
            continue
        
        # Sélection biaisée vers les meilleurs voisins (roulette wheel)
        total_quality = sum(q for _, q in potential_neighbors)
        if total_quality > 0:
            # Sélection probabiliste basée sur la qualité
            r = random.random() * total_quality
            cumulative = 0
            selected_neighbor = None
            
            for neighbor, quality in potential_neighbors:
                cumulative += quality
                if cumulative >= r:
                    selected_neighbor = neighbor
                    break
            
            if not selected_neighbor:  # Fallback si problème numérique
                selected_neighbor, _ = random.choice(potential_neighbors)
        else:
            # Fallback: choix uniforme
            selected_neighbor, _ = random.choice(potential_neighbors)
        
        # Ajouter le voisin sélectionné
        current_rule.append(selected_neighbor)
        visited.add(selected_neighbor)
        depth += 1
        consecutive_fails = 0
        
        # Vérifier si la règle reste valide
        if not pruning_prediction(current_rule, mapper, db_inspector):
            current_rule.pop()
            visited.remove(selected_neighbor)
            consecutive_fails += 1
            continue
        
        # Évaluer la nouvelle règle
        new_quality = evaluate_rule_with_heuristics(current_rule, db_inspector, mapper)
        
        # Garder trace de la meilleure règle trouvée pendant la simulation
        if new_quality > best_quality:
            best_quality = new_quality
            best_rule = current_rule.copy()
    
    # Retourner le score de la meilleure règle trouvée
    return best_quality


def backpropagate_with_heuristics(node: MCTSHNode, score: float) -> None:
    """
    Propage le score avec une pondération heuristique.
    
    :param node: Nœud à partir duquel commence la rétropropagation
    :param score: Score à propager
    """
    # Facteur de discount pour atténuer l'effet des nœuds éloignés
    discount_factor = 0.95
    current_discount = 1.0
    
    while node:
        node.visit_count += 1
        
        # Appliquer le facteur de discount pour la rétropropagation
        adjusted_score = score * current_discount
        
        # Pondérer par la valeur heuristique du nœud
        heuristic_weight = 1.0 + 0.2 * node.heuristic_value  # 20% max de bonus
        
        # Mettre à jour le score avec pondération
        node.total_score += adjusted_score * heuristic_weight
        
        # Passer au parent avec discount
        current_discount *= discount_factor
        node = node.parent


def adjust_playout_depth(node: MCTSHNode, base_depth: int) -> int:
    """
    Ajuste dynamiquement la profondeur du playout selon la promesse du nœud.
    
    :param node: Nœud actuel
    :param base_depth: Profondeur de base
    :return: Profondeur ajustée
    """
    # Profondeur additionnelle basée sur la valeur heuristique
    depth_bonus = int(node.heuristic_value * 3)  # +0 à +3 selon la valeur heuristique
    
    # Considérer l'historique des visites
    if node.visit_count > 0 and node.parent:
        avg_score = node.total_score / node.visit_count
        parent_avg = node.parent.total_score / node.parent.visit_count if node.parent.visit_count > 0 else 0
        
        # Si le nœud est meilleur que son parent, explorer plus en profondeur
        if avg_score > parent_avg:
            depth_bonus += 1
    
    return base_depth + depth_bonus


def get_best_nodes_heuristic(root: MCTSHNode, n: int) -> List[Tuple[MCTSHNode, float]]:
    """
    Retourne les n meilleurs nœuds selon un score combinant visites, valeur et heuristique.
    
    :param root: Nœud racine de l'arbre MCTS
    :param n: Nombre de meilleurs nœuds à retourner
    :return: Liste des meilleurs nœuds avec leurs scores
    """
    all_nodes = collect_all_nodes_heuristic(root)
    
    # Calcul des scores combinés
    scored_nodes = []
    for node in all_nodes:
        if node.visit_count > 0 and len(node.rule) >= 2:
            # Score basé sur la moyenne + bonus heuristique + bonus exploration
            avg_value = node.total_score / node.visit_count
            exploration_bonus = math.sqrt(math.log(root.visit_count + 1) / (node.visit_count + 1))
            combined_score = avg_value + 0.2 * node.heuristic_value + 0.1 * exploration_bonus
            scored_nodes.append((node, combined_score))
    
    # Tri par score décroissant
    scored_nodes.sort(key=lambda x: x[1], reverse=True)
    return scored_nodes[:n]


def collect_all_nodes_heuristic(node: MCTSHNode) -> List[MCTSHNode]:
    """
    Collecte tous les nœuds de l'arbre MCTS.
    
    :param node: Nœud racine
    :return: Liste de tous les nœuds
    """
    result = [node]
    for child in node.children.values():
        result.extend(collect_all_nodes_heuristic(child))
    return result


def quick_heuristic_evaluation(
    rule: CandidateRule,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper
) -> float:
    """
    Effectue une évaluation heuristique rapide d'une règle.
    
    :param rule: Règle candidate à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :return: Score heuristique entre 0 et 1
    """
    # Pour les règles trop courtes, estimation simple basée sur la structure
    if len(rule) <= 1:
        return 0.3  # Valeur de base modérée
    
    # Évaluer les métriques structurelles
    table_occurrences = extract_table_occurrences(rule)
    unique_tables = {occurrence[0] for occurrence in table_occurrences}
    
    # Pénaliser les règles avec trop ou trop peu de tables
    table_factor = 1.0
    if len(unique_tables) > 3:
        table_factor = 0.8  # Légère pénalité pour beaucoup de tables
    
    # Pénaliser les règles trop longues ou trop courtes
    length_factor = 1.0
    rule_length = len(rule)
    if rule_length < 2:
        length_factor = 0.5  # Forte pénalité pour les règles trop courtes
    elif rule_length > 5:
        length_factor = 0.7  # Pénalité pour les règles très complexes
    
    # Estimation basée sur les splits possibles
    splits = split_candidate_rule(rule)
    if not splits:
        return 0.1
    
    # Prendre en compte le nombre de splits possibles
    split_factor = min(1.0, len(splits) / 5.0)  # Normaliser à max 1.0
    
    # Score combiné
    return 0.4 + 0.2 * table_factor + 0.2 * length_factor + 0.2 * split_factor


def evaluate_rule_with_heuristics(
    rule: CandidateRule,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper
) -> float:
    """
    Évaluation complète d'une règle combinant score beam et heuristiques.
    
    :param rule: Règle à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :return: Score combiné
    """
    if not rule or len(rule) < 2:
        return 0.0
    
    # Utiliser le score beam standard
    beam_score = calculate_beam_score(rule, mapper, db_inspector)
    
    # Facteurs supplémentaires pour affiner l'évaluation
    rule_length = len(rule)
    complexity_bonus = 0.0
    
    # Préférence pour les règles de complexité moyenne
    if 2 <= rule_length <= 4:
        complexity_bonus = 0.1
    
    # Vérifier la couverture des tables de la base de données
    table_occurrences = extract_table_occurrences(rule)
    unique_tables = {occurrence[0] for occurrence in table_occurrences}
    table_coverage_bonus = 0.05 * len(unique_tables) / 3.0  # Normaliser à ~0.05 max
    
    # Vérifier la qualité des divisions possibles
    splits = split_candidate_rule(rule)
    split_quality = 0.0
    
    if splits:
        split_scores = []
        for split in list(splits)[:3]:  # Limiter à 3 splits pour l'efficacité
            body, head = split
            if not body or not head:
                continue
                
            try:
                valid, support, confidence = split_pruning(rule, body, head, db_inspector, mapper)
                if valid:
                    split_scores.append((support + confidence) / 2)
            except Exception:
                pass
        
        if split_scores:
            split_quality = max(split_scores)
    
    # Score final combinant tous les facteurs
    final_score = (0.5 * beam_score + 0.3 * split_quality + 
                   complexity_bonus + table_coverage_bonus)
    
    return final_score
