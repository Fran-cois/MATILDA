"""
Algorithme de recherche par arbre de Monte Carlo (MCTS) pour la découverte de règles.

MCTS utilise des simulations aléatoires (playouts) pour explorer efficacement
l'espace de recherche des règles possibles, en équilibrant exploration et exploitation.
"""

import logging
import random
import math
from collections.abc import Callable, Iterator
from typing import Optional, Dict, List, Set
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


class MCTSNode:
    """Nœud de l'arbre de recherche Monte Carlo."""
    
    def __init__(
        self,
        rule: CandidateRule,
        parent: Optional['MCTSNode'] = None,
        visit_count: int = 0,
        total_score: float = 0.0,
        is_terminal: bool = False
    ):
        self.rule = rule
        self.parent = parent
        self.visit_count = visit_count
        self.total_score = total_score
        self.is_terminal = is_terminal
        self.children: Dict[str, 'MCTSNode'] = {}  # Clé = repr du nœud ajouté
        self.untried_actions: Set[JoinableIndexedAttributes] = set()  # Nœuds pas encore essayés


def mcts_search(
    cg: ConstraintGraph,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    iterations: int = 1000,
    exploration_weight: float = 1.0,
    max_table: int = 3,
    max_vars: int = 6,
    playout_depth: int = 3,
) -> Iterator[CandidateRule]:
    """
    Effectue une recherche par arbre de Monte Carlo pour découvrir des règles.
    
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction pour déterminer si une règle doit être élaguée
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param iterations: Nombre d'itérations MCTS
    :param exploration_weight: Poids pour l'exploration (facteur C dans UCB1)
    :param max_table: Nombre maximum de tables dans une règle
    :param max_vars: Nombre maximum de variables dans une règle
    :param playout_depth: Profondeur maximale des playouts aléatoires
    :yield: Règles candidates prometteuses
    """
    # Création du nœud racine
    root = MCTSNode(rule=[])
    
    # Découvertes uniques pour éviter les doublons
    unique_discoveries = set()
    
    # Initialisation des actions possibles pour la racine
    initialize_actions(root, cg, [], set(), max_table, max_vars)
    
    for iteration in tqdm(range(iterations), desc="MCTS iterations"):
        # 1. Sélection: naviguer depuis la racine jusqu'à un nœud à explorer
        node = select_node(root, exploration_weight)
        
        # 2. Expansion: ajouter un nouvel enfant au nœud sélectionné
        if not node.is_terminal and node.untried_actions:
            node = expand_node(node, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
        
        # 3. Simulation: faire un playout aléatoire depuis ce nœud
        if node is not None:  # L'expansion peut échouer si toutes les actions sont élaguées
            simulation_score = simulate(
                node.rule, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars, playout_depth
            )
            
            # 4. Rétropropagation: mettre à jour les statistiques des nœuds
            backpropagate(node, simulation_score)
            
            # Vérifier si nous avons une nouvelle règle prometteuse à retourner
            if (len(node.rule) > 1 and node.visit_count > 5 and 
                (node.total_score / node.visit_count) > 0.6):
                rule_repr = str(node.rule)
                if rule_repr not in unique_discoveries:
                    unique_discoveries.add(rule_repr)
                    yield node.rule
    
    # À la fin, renvoyer les meilleures règles trouvées selon UCB
    best_nodes = get_best_nodes(root, 5)
    for node in best_nodes:
        if str(node.rule) not in unique_discoveries and len(node.rule) > 1:
            unique_discoveries.add(str(node.rule))
            yield node.rule


def initialize_actions(
    node: MCTSNode,
    cg: ConstraintGraph,
    rule: CandidateRule,
    visited: Set[JoinableIndexedAttributes],
    max_table: int,
    max_vars: int
) -> None:
    """
    Initialise les actions possibles pour un nœud.
    
    :param node: Nœud pour lequel initialiser les actions
    :param cg: Graphe de contraintes
    :param rule: Règle candidate actuelle
    :param visited: Nœuds déjà visités
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    """
    if node.rule:
        # Si nous avons déjà des nœuds dans la règle, trouver les voisins valides
        for existing_node in node.rule:
            for neighbor in cg.neighbors(existing_node):
                if (neighbor not in visited and 
                    next_node_test(rule, neighbor, visited, max_table, max_vars)):
                    node.untried_actions.add(neighbor)
    else:
        # Pour le nœud racine, considérer tous les nœuds comme possibles actions de départ
        for graph_node in cg.nodes:
            if next_node_test([], graph_node, set(), max_table, max_vars):
                node.untried_actions.add(graph_node)


def select_node(node: MCTSNode, exploration_weight: float) -> MCTSNode:
    """
    Sélectionne un nœud à explorer en utilisant la stratégie UCB1.
    
    :param node: Nœud à partir duquel commencer la sélection
    :param exploration_weight: Poids pour le terme d'exploration
    :return: Nœud sélectionné pour expansion ou simulation
    """
    # Si le nœud a des actions non essayées, on le retourne pour expansion
    if node.untried_actions or node.is_terminal:
        return node
    
    # Sinon, on utilise UCB1 pour équilibrer exploitation et exploration
    best_score = float('-inf')
    best_child = None
    
    # Exploration UCB1
    for child in node.children.values():
        # Éviter division par zéro
        if child.visit_count == 0:
            ucb_score = float('inf')
        else:
            # Formule UCB1: exploitation + exploration
            exploitation = child.total_score / child.visit_count
            exploration = exploration_weight * math.sqrt(
                math.log(node.visit_count) / child.visit_count
            )
            ucb_score = exploitation + exploration
        
        if ucb_score > best_score:
            best_score = ucb_score
            best_child = child
    
    # Poursuivre la sélection récursivement
    if best_child:
        return select_node(best_child, exploration_weight)
    return node  # Fallback si aucun enfant n'est disponible


def expand_node(
    node: MCTSNode,
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int,
    max_vars: int
) -> Optional[MCTSNode]:
    """
    Étend le nœud actuel en ajoutant un enfant pour une action non-essayée.
    
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
    
    # Choisir aléatoirement une action non-essayée
    action = random.choice(list(node.untried_actions))
    node.untried_actions.remove(action)
    
    # Créer la nouvelle règle en ajoutant l'action à la règle actuelle
    new_rule = node.rule + [action]
    visited = set(node.rule) | {action}
    
    # Vérifier si la règle est valide après élagage
    if pruning_prediction(new_rule, mapper, db_inspector):
        # Créer le nouveau nœud enfant
        child = MCTSNode(rule=new_rule, parent=node)
        
        # Vérifier si le nœud est terminal (a atteint les limites max)
        child.is_terminal = (len(new_rule) >= max_vars or 
                            len({attr.i for jia in new_rule for attr in jia}) >= max_table)
        
        # Initialiser les actions possibles pour ce nouvel enfant
        if not child.is_terminal:
            initialize_actions(child, cg, new_rule, visited, max_table, max_vars)
        
        # Stocker l'enfant dans le parent
        node.children[str(action)] = child
        return child
    
    return None


def simulate(
    rule: CandidateRule,
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int,
    max_vars: int,
    playout_depth: int
) -> float:
    """
    Effectue une simulation (playout) aléatoire à partir de la règle actuelle.
    
    :param rule: Règle candidate à partir de laquelle simuler
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :param playout_depth: Profondeur maximale de la simulation
    :return: Score de la règle après simulation
    """
    current_rule = rule.copy()
    visited = set(current_rule)
    
    # Simulation: étendre aléatoirement la règle jusqu'à playout_depth étapes
    depth = 0
    while depth < playout_depth and len(current_rule) < max_vars:
        # Collecter les voisins valides
        valid_actions = []
        for node in current_rule:
            for neighbor in cg.neighbors(node):
                if (neighbor not in visited and 
                    next_node_test(current_rule, neighbor, visited, max_table, max_vars)):
                    valid_actions.append(neighbor)
        
        # S'il n'y a pas d'action valide, arrêter la simulation
        if not valid_actions:
            break
        
        # Choisir une action aléatoire
        action = random.choice(valid_actions)
        current_rule.append(action)
        visited.add(action)
        depth += 1
        
        # Vérifier si la règle reste valide
        if not pruning_prediction(current_rule, mapper, db_inspector):
            current_rule.pop()  # Annuler la dernière action
            break
    
    # Évaluer la règle finale
    if current_rule and len(current_rule) > 0:
        return calculate_beam_score(current_rule, mapper, db_inspector)
    return 0.0


def backpropagate(node: MCTSNode, score: float) -> None:
    """
    Propage le score de la simulation vers le haut de l'arbre.
    
    :param node: Nœud à partir duquel commence la rétropropagation
    :param score: Score à propager
    """
    while node:
        node.visit_count += 1
        node.total_score += score
        node = node.parent


def get_best_nodes(root: MCTSNode, n: int) -> List[MCTSNode]:
    """
    Retourne les n meilleurs nœuds selon leur score moyen.
    
    :param root: Nœud racine de l'arbre MCTS
    :param n: Nombre de meilleurs nœuds à retourner
    :return: Liste des meilleurs nœuds
    """
    # Collecte de tous les nœuds de l'arbre
    all_nodes = collect_all_nodes(root)
    
    # Filtrer les nœuds avec suffisamment de visites et les trier par score moyen
    qualified_nodes = [
        node for node in all_nodes if node.visit_count > 5 and len(node.rule) > 1
    ]
    qualified_nodes.sort(
        key=lambda x: (x.total_score / x.visit_count if x.visit_count > 0 else 0), 
        reverse=True
    )
    
    return qualified_nodes[:n]


def collect_all_nodes(node: MCTSNode) -> List[MCTSNode]:
    """
    Collecte tous les nœuds de l'arbre MCTS.
    
    :param node: Nœud racine
    :return: Liste de tous les nœuds
    """
    result = [node]
    for child in node.children.values():
        result.extend(collect_all_nodes(child))
    return result
