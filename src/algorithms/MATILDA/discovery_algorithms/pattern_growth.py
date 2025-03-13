"""
Algorithme de découverte de règles par croissance de motifs inspiré de FP-Growth.

Cette approche utilise une structure de données compressée similaire à un FP-Tree
pour stocker les informations de couverture des règles et permet d'explorer 
l'espace des règles en profondeur sans énumération complète.
"""

import logging
import time
from collections import defaultdict, Counter, deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Any
from tqdm import tqdm

from algorithms.MATILDA.constraint_graph import (
    AttributeMapper,
    ConstraintGraph, 
    JoinableIndexedAttributes,
    IndexedAttribute
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
    prediction,
    CandidateRuleChains,
    TableOccurrence
)


@dataclass
class RulePatternNode:
    """
    Nœud du Rule-Pattern Tree, une structure inspirée du FP-Tree mais adaptée aux règles.
    """
    attribute: Optional[JoinableIndexedAttributes] = None
    parent: Optional['RulePatternNode'] = None
    children: Dict[str, 'RulePatternNode'] = field(default_factory=dict)
    support_count: int = 0
    rule_indices: Set[int] = field(default_factory=set)
    table_occurrences: Set[TableOccurrence] = field(default_factory=set)
    
    def add_child(self, attribute: JoinableIndexedAttributes, rule_idx: int) -> 'RulePatternNode':
        """Ajoute un enfant au nœud actuel"""
        attr_key = str(attribute)
        if attr_key not in self.children:
            self.children[attr_key] = RulePatternNode(
                attribute=attribute, 
                parent=self, 
                support_count=0
            )
        
        child = self.children[attr_key]
        child.support_count += 1
        child.rule_indices.add(rule_idx)
        
        # Ajouter les occurrences de table
        if attribute:
            for attr in attribute:
                child.table_occurrences.add((attr.i, attr.j))
        
        return child
    
    def get_path_to_root(self) -> List[JoinableIndexedAttributes]:
        """Retourne le chemin de ce nœud jusqu'à la racine"""
        path = []
        current = self
        while current.parent and current.attribute:
            path.append(current.attribute)
            current = current.parent
        return list(reversed(path))


class RulePatternTree:
    """
    Structure de données similaire à un FP-Tree pour stocker des règles de manière compressée.
    """
    def __init__(self, min_support: int = 2):
        self.root = RulePatternNode()  # Nœud racine sans attribut
        self.attribute_nodes: Dict[str, List[RulePatternNode]] = defaultdict(list)
        self.min_support = min_support
        self.rule_count = 0
    
    def add_rule(self, rule: CandidateRule) -> None:
        """
        Ajoute une règle à l'arbre
        
        :param rule: Règle candidate à ajouter
        """
        current = self.root
        rule_idx = self.rule_count
        self.rule_count += 1
        
        for attr in rule:
            current = current.add_child(attr, rule_idx)
            self.attribute_nodes[str(attr)].append(current)
    
    def get_frequent_attributes(self) -> Dict[str, int]:
        """
        Retourne les attributs fréquents avec leur support
        
        :return: Dictionnaire des attributs avec leur support
        """
        attr_support = Counter()
        for attr, nodes in self.attribute_nodes.items():
            # Agréger tous les indices de règles qui contiennent cet attribut
            rule_indices = set()
            for node in nodes:
                rule_indices.update(node.rule_indices)
            
            # Le support est le nombre de règles différentes contenant cet attribut
            support = len(rule_indices)
            if support >= self.min_support:
                attr_support[attr] = support
        
        return attr_support
    
    def get_conditional_pattern_base(self, target_attr: str) -> List[Tuple[List[JoinableIndexedAttributes], int]]:
        """
        Obtient la base de motifs conditionnels pour un attribut cible
        
        :param target_attr: Attribut cible (sous forme de chaîne)
        :return: Liste de tuples (chemin, support)
        """
        conditional_patterns = []
        
        for node in self.attribute_nodes.get(target_attr, []):
            # Obtenir le chemin du nœud jusqu'à la racine (en excluant la racine)
            path = node.get_path_to_root()[:-1]  # Exclure l'attribut cible lui-même
            
            if path:
                # Ajouter le chemin à la base de motifs conditionnels avec le support du nœud
                conditional_patterns.append((path, node.support_count))
        
        return conditional_patterns


def pattern_growth_search(
    cg: ConstraintGraph,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    initial_rule_count: int = 100,
    min_support: int = 2,
    max_table: int = 3,
    max_vars: int = 6,
    support_threshold: float = 0.3,
    confidence_threshold: float = 0.3
) -> Iterator[CandidateRule]:
    """
    Algorithme de découverte de règles par croissance de motifs, inspiré de FP-Growth.
    
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction pour déterminer si une règle doit être élaguée
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param initial_rule_count: Nombre de règles initiales à générer
    :param min_support: Support minimum pour considérer un motif comme fréquent
    :param max_table: Nombre maximum de tables dans une règle
    :param max_vars: Nombre maximum de variables dans une règle
    :param support_threshold: Seuil de support minimal pour qu'une règle soit valide
    :param confidence_threshold: Seuil de confiance minimal pour qu'une règle soit valide
    :yield: Règles candidates découvertes
    """
    logging.info("Initializing pattern growth search")
    start_time = time.time()
    
    # 1. Générer un ensemble initial de règles
    initial_rules = generate_initial_rules(
        cg, pruning_prediction, db_inspector, mapper, 
        initial_rule_count, max_table, max_vars
    )
    logging.info(f"Generated {len(initial_rules)} initial rules in {time.time() - start_time:.2f}s")
    
    # 2. Construire le Rule-Pattern Tree
    tree = build_pattern_tree(initial_rules, min_support)
    logging.info(f"Built pattern tree in {time.time() - start_time:.2f}s")
    
    # 3. Trouver les attributs fréquents
    frequent_attributes = tree.get_frequent_attributes()
    logging.info(f"Found {len(frequent_attributes)} frequent attributes")
    
    # 4. Construire les règles candidates par croissance de motifs
    discovered_rules = set()
    
    # Trier les attributs fréquents par support décroissant
    sorted_attrs = sorted(
        frequent_attributes.items(), 
        key=lambda item: item[1], 
        reverse=True
    )
    
    for attr_str, support in tqdm(sorted_attrs, desc="Mining patterns"):
        # Trouver les nœuds de l'arbre correspondant à cet attribut
        for node in tree.attribute_nodes.get(attr_str, []):
            # Obtenir la règle actuelle (chemin depuis la racine)
            current_rule = node.get_path_to_root()
            
            if not current_rule or len(current_rule) < 2:
                continue
                
            # Vérifier si cette règle a déjà été découverte
            rule_str = str(current_rule)
            if rule_str in discovered_rules:
                continue
            
            discovered_rules.add(rule_str)
            
            # Vérifier si la règle est valide
            if len(current_rule) <= max_vars and len(node.table_occurrences) <= max_table:
                if pruning_prediction(current_rule, mapper, db_inspector):
                    # Évaluer la qualité de la règle
                    splits = split_candidate_rule(current_rule)
                    for split in splits:
                        body, head = split
                        if not body or not head:
                            continue
                        
                        try:
                            valid, support, confidence = split_pruning(
                                current_rule, body, head, db_inspector, mapper
                            )
                            
                            if (valid and 
                                support >= support_threshold and 
                                confidence >= confidence_threshold):
                                yield current_rule
                                break  # Une seule split valide suffit
                        except Exception as e:
                            logging.error(f"Error evaluating rule: {e}")
            
            # Explorer les patterns conditionnels
            conditional_base = tree.get_conditional_pattern_base(attr_str)
            for pattern, pattern_support in conditional_base:
                if pattern_support >= min_support and len(pattern) >= 2:
                    # Créer une nouvelle règle en combinant ce pattern avec d'autres attributs
                    extended_rules = grow_rules_from_pattern(
                        pattern, cg, pruning_prediction, db_inspector, mapper, 
                        max_table, max_vars
                    )
                    
                    for extended_rule in extended_rules:
                        rule_str = str(extended_rule)
                        if rule_str in discovered_rules:
                            continue
                        
                        discovered_rules.add(rule_str)
                        
                        # Vérifier la validité et la qualité
                        if pruning_prediction(extended_rule, mapper, db_inspector):
                            # Évaluer la qualité
                            if evaluate_rule_quality(
                                extended_rule, db_inspector, mapper,
                                support_threshold, confidence_threshold
                            ):
                                yield extended_rule

    logging.info(f"Pattern growth search completed in {time.time() - start_time:.2f}s")


def generate_initial_rules(
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    count: int,
    max_table: int,
    max_vars: int
) -> List[CandidateRule]:
    """
    Génère un ensemble initial de règles variées pour construire l'arbre de patterns
    
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param count: Nombre de règles à générer
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :return: Liste de règles candidates initiales
    """
    initial_rules = []
    visited = set()
    
    # Utiliser une approche BFS pour générer rapidement un ensemble de règles variées
    queue = deque()
    all_nodes = list(cg.nodes)
    
    # Ajouter quelques nœuds de départ
    for i, node in enumerate(all_nodes):
        if i >= min(20, len(all_nodes)):
            break
        if next_node_test([], node, set(), max_table, max_vars):
            queue.append(([node], {node}))
    
    # BFS limité pour générer des règles initiales
    while queue and len(initial_rules) < count:
        current_rule, current_visited = queue.popleft()
        
        # Vérifier si la règle est valide
        if pruning_prediction(current_rule, mapper, db_inspector):
            initial_rules.append(current_rule)
            
            # Arrêter si nous avons assez de règles
            if len(initial_rules) >= count:
                break
        
        # Éviter de créer des règles trop longues
        if len(current_rule) >= max_vars // 2:
            continue
        
        # Explorer les voisins
        for node in current_rule:
            neighbors = [
                n for n in cg.neighbors(node) 
                if n not in current_visited and 
                next_node_test(current_rule, n, current_visited, max_table, max_vars)
            ]
            
            # Ajouter les premiers voisins valides à la queue
            for neighbor in neighbors[:3]:  # Limiter à 3 voisins par nœud
                new_rule = current_rule + [neighbor]
                new_visited = current_visited.union({neighbor})
                
                rule_str = str(new_rule)
                if rule_str not in visited:
                    visited.add(rule_str)
                    queue.append((new_rule, new_visited))
    
    return initial_rules


def build_pattern_tree(rules: List[CandidateRule], min_support: int) -> RulePatternTree:
    """
    Construit un Rule-Pattern Tree à partir d'un ensemble de règles
    
    :param rules: Liste de règles candidates
    :param min_support: Support minimum pour les motifs fréquents
    :return: Arbre de patterns de règles
    """
    tree = RulePatternTree(min_support=min_support)
    
    for rule in rules:
        tree.add_rule(rule)
    
    return tree


def grow_rules_from_pattern(
    pattern: List[JoinableIndexedAttributes],
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int,
    max_vars: int,
    max_extensions: int = 5
) -> List[CandidateRule]:
    """
    Étend un motif pour créer de nouvelles règles candidates
    
    :param pattern: Motif de base à étendre
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :param max_extensions: Nombre maximum d'extensions à générer
    :return: Liste de nouvelles règles candidates
    """
    if not pattern or len(pattern) >= max_vars:
        return []
    
    extended_rules = []
    visited = set(pattern)
    
    # Trouver les voisins possibles pour étendre le motif
    neighbors = []
    for node in pattern:
        for neighbor in cg.neighbors(node):
            if (neighbor not in visited and 
                next_node_test(pattern, neighbor, visited, max_table, max_vars)):
                neighbors.append(neighbor)
    
    # Générer des extensions en ajoutant jusqu'à deux voisins
    extensions_count = 0
    base_rule = pattern.copy()
    
    # Extensions avec 1 nœud supplémentaire
    for neighbor in neighbors[:min(10, len(neighbors))]:
        new_rule = base_rule + [neighbor]
        if pruning_prediction(new_rule, mapper, db_inspector):
            extended_rules.append(new_rule)
            extensions_count += 1
            
            if extensions_count >= max_extensions:
                break
    
    # Si nous n'avons pas atteint le maximum, essayer des extensions avec 2 nœuds
    if extensions_count < max_extensions and len(base_rule) + 2 <= max_vars:
        for i, n1 in enumerate(neighbors[:5]):
            for n2 in neighbors[i+1:5]:
                if extensions_count >= max_extensions:
                    break
                    
                # Vérifier si les deux nœuds peuvent être ajoutés ensemble
                test_rule = base_rule + [n1]
                if next_node_test(test_rule, n2, set(test_rule), max_table, max_vars):
                    new_rule = base_rule + [n1, n2]
                    if pruning_prediction(new_rule, mapper, db_inspector):
                        extended_rules.append(new_rule)
                        extensions_count += 1
    
    return extended_rules


def evaluate_rule_quality(
    rule: CandidateRule,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    support_threshold: float,
    confidence_threshold: float
) -> bool:
    """
    Évalue la qualité d'une règle candidate
    
    :param rule: Règle à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param support_threshold: Seuil de support minimal
    :param confidence_threshold: Seuil de confiance minimal
    :return: True si la règle est de bonne qualité, False sinon
    """
    # Évaluer les différentes divisions possibles
    splits = split_candidate_rule(rule)
    if not splits:
        return False
    
    for split in splits:
        body, head = split
        if not body or not head:
            continue
        
        try:
            valid, support, confidence = split_pruning(rule, body, head, db_inspector, mapper)
            if (valid and 
                support >= support_threshold and 
                confidence >= confidence_threshold):
                return True
        except Exception:
            continue
    
    return False
