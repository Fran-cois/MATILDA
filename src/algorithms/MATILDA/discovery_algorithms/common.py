"""
Types et fonctions communes partagés par les différents algorithmes de découverte.
"""

from dataclasses import dataclass
from typing import List, Set, Dict, Any, Tuple, Optional

from algorithms.MATILDA.constraint_graph import (
    AttributeMapper,
    IndexedAttribute,
    JoinableIndexedAttributes,
)
from database.alchemy_utility import AlchemyUtility

# Type définitions
CandidateRule = List[JoinableIndexedAttributes]
TableOccurrence = Tuple[int, int]

@dataclass
class PrioritizedRule:
    """Structure pour une règle avec priorité pour les files d'attente prioritaires."""
    cost: float  # Coût réel du chemin jusqu'ici (g)
    heuristic: float  # Coût estimé jusqu'au but (h)
    rule: CandidateRule  # La règle candidate
    
    def __lt__(self, other: 'PrioritizedRule') -> bool:
        """Compare deux règles prioritaires pour les tris."""
        # On utilise le négatif pour avoir un tri décroissant (meilleur score = plus prioritaire)
        return (self.cost + self.heuristic) > (other.cost + other.heuristic)

def next_node_test(
    candidate_rule: CandidateRule,
    next_node: JoinableIndexedAttributes,
    visited: Set[JoinableIndexedAttributes],
    max_table: int = 10,
    max_vars: int = 10,
) -> bool:
    """
    Vérifie si le nœud suivant peut être ajouté à la règle candidate.
    
    :param candidate_rule: Liste d'instances JoinableIndexedAttributes représentant la règle candidate actuelle.
    :param next_node: La prochaine instance JoinableIndexedAttributes à ajouter à la règle candidate.
    :param visited: Ensemble d'instances JoinableIndexedAttributes qui ont été visitées.
    :param max_table: Nombre maximum de tables autorisées dans une règle.
    :param max_vars: Nombre maximum de variables autorisées dans une règle.
    :return: Une valeur booléenne indiquant si le nœud suivant peut être ajouté à la règle candidate.
    """
    # Éviter les cycles
    if next_node in visited:
        return False
    
    # Vérifier les limites de taille
    if len(candidate_rule) + 1 > max_vars:
        return False
    
    # Vérifier si le nœud est connecté à au moins un nœud dans la règle candidate
    if candidate_rule:
        is_connected = False
        for node in candidate_rule:
            if node.is_connected(next_node):
                is_connected = True
                break
        if not is_connected:
            return False
    
    # Vérifier le nombre de tables impliquées
    table_occurrences = extract_table_occurrences(candidate_rule + [next_node])
    if len(table_occurrences) > max_table:
        return False
    
    # Vérifier la cohérence des tables (occurrences consécutives)
    if not has_consecutive_occurrences(table_occurrences):
        return False
    
    return True

def extract_table_occurrences(rule: CandidateRule) -> Set[TableOccurrence]:
    """
    Extrait l'ensemble des occurrences de table à partir d'une règle candidate.
    
    :param rule: Liste des JoinableIndexedAttributes représentant la règle candidate.
    :return: Ensemble de tuples représentant les occurrences de table (i, j).
    """
    table_occurrences = set()
    for jia in rule:
        for attr in jia:  # JoinableIndexedAttributes est itérable sur ses deux attributs
            table_occurrences.add((attr.i, attr.j))
    return table_occurrences

def has_consecutive_occurrences(table_occurrences: Set[TableOccurrence]) -> bool:
    """
    Vérifie si les occurrences de table sont consécutives pour chaque table.
    
    :param table_occurrences: Ensemble de tuples représentant les occurrences de table (i, j).
    :return: True si les occurrences sont consécutives, False sinon.
    """
    # Grouper les occurrences par table (i)
    tables_dict = {}
    for i, j in table_occurrences:
        if i not in tables_dict:
            tables_dict[i] = []
        tables_dict[i].append(j)
    
    # Vérifier que pour chaque table, les occurrences sont consécutives (0, 1, 2, ...)
    for table_id, occurrences in tables_dict.items():
        occurrences.sort()
        expected = list(range(occurrences[0], occurrences[-1] + 1))
        if occurrences != expected:
            return False
    
    return True

def calculate_path_cost(rule: CandidateRule, length_penalty: float = 0.1) -> float:
    """
    Calcule le coût réel (g) d'une règle candidate.
    Un coût plus faible est meilleur.
    
    :param rule: La règle candidate.
    :param length_penalty: Pénalité par nœud dans la règle.
    :return: Le coût calculé.
    """
    if not rule:
        return 0.0
    
    # Pénalité basée sur la longueur de la règle
    base_cost = len(rule) * length_penalty
    
    # Retourner le négatif pour avoir une priorité décroissante
    return -base_cost  # Plus le coût est faible (négatif important), plus la priorité est élevée

def calculate_heuristic_score(
    rule: CandidateRule, 
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper
) -> float:
    """
    Calcule un score heuristique (h) pour une règle candidate.
    Plus le score est élevé, meilleure est la règle.
    
    :param rule: La règle candidate.
    :param db_inspector: Instance d'AlchemyUtility pour l'accès à la base de données.
    :param mapper: Instance d'AttributeMapper pour la correspondance des attributs.
    :return: Le score heuristique calculé.
    """
    if not rule or len(rule) < 2:
        return -100.0  # Règle trop courte, score très bas
    
    # Évaluer le degré de connectivité de la règle
    connectivity = 0.0
    for i, jia1 in enumerate(rule[:-1]):
        for jia2 in rule[i+1:]:
            if jia1.is_connected(jia2):
                connectivity += 1.0
    
    # Normaliser la connectivité
    max_possible = (len(rule) * (len(rule) - 1)) / 2
    if max_possible > 0:
        connectivity = connectivity / max_possible
    
    # Estimer la qualité basée sur la diversité des tables/attributs
    table_occurrences = extract_table_occurrences(rule)
    table_diversity = len(table_occurrences) / (2.0 * len(rule))  # Normaliser
    
    # Combiner les facteurs pour le score final
    # Utiliser le négatif pour avoir une priorité décroissante
    return -(0.7 * connectivity + 0.3 * table_diversity)

def calculate_beam_score(
    rule: CandidateRule, 
    mapper: AttributeMapper, 
    db_inspector: AlchemyUtility
) -> float:
    """
    Calcule un score pour la recherche en faisceau.
    Plus le score est élevé, meilleure est la règle.
    
    :param rule: La règle candidate.
    :param mapper: Instance d'AttributeMapper pour la correspondance des attributs.
    :param db_inspector: Instance d'AlchemyUtility pour l'accès à la base de données.
    :return: Le score calculé.
    """
    if not rule or len(rule) < 2:
        return 0.0  # Règle trop courte, score nul
    
    # Facteurs de score de base
    length_score = min(1.0, len(rule) / 5.0)  # Favoriser les règles de taille moyenne
    table_occurrences = extract_table_occurrences(rule)
    diversity_score = min(1.0, len(table_occurrences) / 6.0)  # Favoriser la diversité des tables
    
    # Score de connectivité
    connected_pairs = 0
    for i, jia1 in enumerate(rule[:-1]):
        for jia2 in rule[i+1:]:
            if jia1.is_connected(jia2):
                connected_pairs += 1
    max_pairs = (len(rule) * (len(rule) - 1)) / 2
    connectivity_score = connected_pairs / max_pairs if max_pairs > 0 else 0
    
    # Combiner les facteurs (régler les poids selon les priorités)
    score = (0.3 * length_score + 0.4 * diversity_score + 0.3 * connectivity_score)
    
    return score
