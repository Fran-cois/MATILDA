import copy
from collections.abc import Callable, Iterator
from itertools import chain, combinations
from statistics import mean
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from queue import PriorityQueue
from typing import Any

from textwrap import indent
from utils.rules import Rule
import json
import re
from utils.rules import Predicate, EGDRule
from tqdm import tqdm
from algorithms.MATILDA.constraint_graph import (
    Attribute,
    AttributeMapper,
    ConstraintGraph,
    IndexedAttribute,
    JoinableIndexedAttributes,
)
from algorithms.MATILDA.candidate_rule_chains import CandidateRuleChains
from database.alchemy_utility import AlchemyUtility
import time
from .tgd_discovery import *
from algorithms.MATILDA.compatibility_checker import CompatibilityChecker

logging.basicConfig(
    filename='logs/fd_computation.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    filemode='w'
)

APPLY_DISJOINT = True
SPLIT_PRUNING_MEAN_THRESHOLD = 0
TableOccurrence = tuple[int, int]
CandidateRule = list[JoinableIndexedAttributes]

def init(
    db_inspector: AlchemyUtility,
    max_nb_occurrence: int = 1,
    max_nb_occurrence_per_table_and_column: dict[str, dict[str, int]] = {},
    results_path: str = None,
    compatibility_mode: str = None,
) -> tuple[ConstraintGraph, AttributeMapper, list[JoinableIndexedAttributes]]:
    """
    Initialize the constraint graph and attribute mapper.
    :param db_inspector: AlchemyUtility instance
    :param max_nb_occurrence: Maximum number of occurrences for each table
    :return: A tuple containing the constraint graph, attribute mapper, and list of compatible indexed attributes
    """
    # FOR FD: 
    #max_nb_occurrence = 3
    compatibility_mode= CompatibilityChecker.MODE_FD

    # Input validation
    if not db_inspector or not hasattr(db_inspector, "base_name"
                                       ):
        raise ValueError("Invalid db_inspector provided.")

    try:
        time_taken_init = time.time()
        # Generate all attributes
        attributes = Attribute.generate_attributes(db_inspector)
        if not attributes:
            logging.warning("No attributes generated. Exiting initialization.")
            return None, None, []


        # Initialiser le vérificateur de compatibilité
        try:
            # Utiliser db_manager.engine comme dans tgd_discovery.py au lieu de get_engine()
            engine = db_inspector.db_manager.engine
            metadata = db_inspector.db_manager.metadata
            compatibility_checker = CompatibilityChecker(engine, metadata)
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation du vérificateur de compatibilité: {e}")
            
            # Afficher la stack trace pour le débogage
            import traceback
            logging.error(f"Stack trace: {traceback.format_exc()}")
            
            # Vérifiez les attributs disponibles
            logging.error(f"Attributs disponibles dans db_inspector: {dir(db_inspector)}")
            
            if hasattr(db_inspector, 'db_manager'):
                logging.error(f"Attributs disponibles dans db_inspector.db_manager: {dir(db_inspector.db_manager)}")
            
            # Continuer avec des valeurs par défaut
            compatibility_checker = None
            compatible_attributes = set()

        # Find compatible attributes en utilisant le mode de compatibilité spécifié
        if compatibility_checker:
            compatible_attributes: set[tuple[Attribute, Attribute]] = set()
            for i, attr1 in enumerate(
                tqdm(attributes, desc="Finding compatible attributes", leave=False)
            ):
                for attr2 in attributes[i:]:
                    try:
                        # Utiliser le vérificateur de compatibilité avec le mode spécifié
                        if compatibility_checker.is_compatible(
                            attr1.table, attr1.name, 
                            attr2.table, attr2.name,
                            mode=compatibility_mode
                        ):
                            compatible_attributes.add((attr1, attr2))
                            compatible_attributes.add((attr2, attr1))

                    except Exception as e:
                        logging.warning(f"Erreur lors de la vérification de compatibilité entre {attr1.table}.{attr1.name} et {attr2.table}.{attr2.name}: {e}")
                        # Continuer avec les autres attributs

        # Export compatible attributes as JSON if results_path is provided
        compatible_dict_to_export = {}
        for attr1, attr2 in compatible_attributes:
            key1 = f"{attr1.table}___sep___{attr1.name}"
            key2 = f"{attr2.table}___sep___{attr2.name}"
            compatible_dict_to_export.setdefault(key1, []).append(key2)
            compatible_dict_to_export.setdefault(key2, []).append(key1)

        if results_path:
            try:
                # Assurer que le répertoire existe
                import os
                os.makedirs(results_path, exist_ok=True)
                
                base_name = db_inspector.base_name
                filepath = os.path.join(results_path, f"compatibility_fd_{base_name}.json")
                
                with open(filepath, "w") as f:
                    json.dump(compatible_dict_to_export, f, indent=4)
                logging.info(f"Attributs compatibles exportés vers {filepath}")
            except Exception as e:
                logging.error(f"Erreur lors de l'exportation des attributs compatibles: {e}")
                # Continuer l'exécution même en cas d'échec de l'exportation

        time_compute_compatible = time.time() - time_taken_init

        # Create indexes for compatible attributes
        try:
            db_inspector.create_composed_indexes(
                [
                    (attr1.table, attr1.name, attr2.table, attr2.name)
                    for attr1, attr2 in compatible_attributes
                ]
            )
        except Exception as e:
            logging.error(f"Error creating composed indexes: {e}")
        time_to_compute_indexed = time.time() - time_taken_init

        # Attribute index mapping
        tables = db_inspector.get_table_names()
        table_name_to_index = {table: i for i, table in enumerate(tables)}
        attribute_name_to_index = {
            table: {attr: i for i, attr in enumerate(db_inspector.get_attribute_names(table))}
            for table in tables
        }

        mapper = AttributeMapper(table_name_to_index, attribute_name_to_index)

        # List creation of compatible indexed attributes
        jia_list: list[JoinableIndexedAttributes] = []
        for table_occurrence1 in range(max_nb_occurrence):
            for table_occurrence2 in range(max_nb_occurrence):
                for attr1, attr2 in compatible_attributes:
                    try:

                        jia = JoinableIndexedAttributes(
                            mapper.attribute_to_indexed(attr1, table_occurrence1),
                            mapper.attribute_to_indexed(attr2, table_occurrence2),
                        )
                        jia_list.append(jia)
                    except Exception as e:
                        logging.warning(f"Erreur lors de la création d'attributs indexés joignables: {e}")
                        # Continuer avec les autres attributs
        jia_list.sort()

        # Create a constraint graph
        cg = ConstraintGraph()
        for i, jia in enumerate(
            tqdm(jia_list, desc="Creating constraint graph", leave=False)
        ):
            try:
                cg.add_node(jia)
                for jia2 in jia_list[i + 1 :]:
                    if jia != jia2 and jia.is_connected(jia2):
                        cg.add_node(jia2)
                        cg.add_edge(jia, jia2)
            except Exception as e:
                logging.warning(f"Erreur lors de la création du graphe de contrainte pour {jia}: {e}")
                # Continuer avec les autres jia
        time_building_cg = time.time() - time_taken_init

        # Export constraint graph metrics if results_path is provided
        if results_path:
            try:
                base_name = db_inspector.base_name
                
                # Export constraint graph metrics
                cg_metrics_path = os.path.join(results_path, f"cg_metrics_fd_{base_name}.json")
                with open(cg_metrics_path, "w") as f:
                    json.dump(str(cg), f)
                
                # Export time metrics
                time_metrics_path = os.path.join(results_path, f"init_time_metrics_fd_{base_name}.json")
                with open(time_metrics_path, "w") as f:
                    json.dump(
                        {
                            "time_compute_compatible": time_compute_compatible,
                            "time_to_compute_indexed": time_to_compute_indexed,
                            "time_building_cg": time_building_cg,
                        },
                        f,
                        indent=4,
                    )
                logging.info(f"Métriques exportées dans {results_path}")
            except Exception as e:
                logging.error(f"Erreur lors de l'exportation des métriques: {e}")
                # Continuer l'exécution même en cas d'échec de l'exportation

        return cg, mapper, jia_list

    except Exception as e:
        logging.error(f"An error occurred during initialization: {e}")
        # Afficher la stack trace pour le débogage
        import traceback
        logging.error(f"Stack trace: {traceback.format_exc()}")
        return None, None, []

# Reprise de certaines fonctions de base depuis tgd_discovery.py

def split_candidate_rule(
    candidate_rule: CandidateRule,
) -> set[
    tuple[set[TableOccurrence], list[tuple[IndexedAttribute, IndexedAttribute]]]
]:  # where the tuple is a list of equality constraints
    """
    Split a path into a set of table occurrence pairs and equality constraints.
    Pour les FDs, nous voulons uniquement les splits qui correspondent au modèle X → Y
    où X détermine fonctionnellement Y.

    :param candidate_rule: A list of tuples of JoinableIndexedAttributes (representing the candidate_rule)
    :return: A set of (body, equality_constraints) pairs where equality_constraints is a list
    """
    if candidate_rule is None or len(candidate_rule) == 0:
        return set()
    
    # Vérifier que chaque jia contient le même i et k mais j différent
    for jia in candidate_rule:
        attr1, attr2 = jia
        # Les attributs doivent avoir le même i (index de table) 
        # mais des j (occurrence de table) différents
        if attr1.i != attr2.i or attr1.j == attr2.j:
            return set()  # Retourner un ensemble vide si la condition n'est pas satisfaite
        
        # Vérifiez si les attributs ont le même k (index d'attribut)
        # Noter que k n'est pas directement accessible, nous devons l'extraire du nom d'attribut
        # Cette vérification peut être personnalisée selon la structure exacte de IndexedAttribute
        # Si k n'est pas accessible directement, cette vérification peut être omise
    
    valid_splits = set()
    
    # Extraire tous les attributs et leurs occurrences de table
    all_attrs = {}  # {(table_index, table_occurrence): set(IndexedAttribute)}
    table_to_attrs = {}  # {(table_index, table_occurrence): set(IndexedAttribute)}
    
    for jia in candidate_rule:
        attr1, attr2 = jia
        all_attrs[(attr1.i, attr1.j)] = all_attrs.get((attr1.i, attr1.j), set())
        all_attrs[(attr1.i, attr1.j)].add(attr1)
        all_attrs[(attr2.i, attr2.j)] = all_attrs.get((attr2.i, attr2.j), set())
        all_attrs[(attr2.i, attr2.j)].add(attr2)
        
        table_to_attrs[(attr1.i, attr1.j)] = table_to_attrs.get((attr1.i, attr1.j), set())
        table_to_attrs[(attr1.i, attr1.j)].add(attr1)
        table_to_attrs[(attr2.i, attr2.j)] = table_to_attrs.get((attr2.i, attr2.j), set())
        table_to_attrs[(attr2.i, attr2.j)].add(attr2)
    
    # Pour chaque table, essayer de créer des FDs
    for table_occurrence, attributes in table_to_attrs.items():
        if len(attributes) < 2:
            continue  # Besoin d'au moins 2 attributs pour une FD
            
        attributes_list = list(attributes)
        
        # Pour chaque paire d'attributs possible, créer une FD
        for i, attr1 in enumerate(attributes_list):
            for attr2 in attributes_list[i+1:]:
                # FD: attr1 → attr2
                body_set = {table_occurrence}
                eq_constraint = [(attr1, attr2)]
                valid_splits.add((frozenset(body_set), tuple(eq_constraint)))
                
                # FD: attr2 → attr1
                eq_constraint = [(attr2, attr1)]
                valid_splits.add((frozenset(body_set), tuple(eq_constraint)))
    
    return valid_splits

def is_consistent_constraint_set(eq_pairs):
    """
    Vérifie si un ensemble de contraintes d'égalité est cohérent.
    Les contraintes peuvent être incohérentes si elles créent des cycles transitifs 
    qui conduisent à des égalités contradictoires.
    
    :param eq_pairs: Liste de tuples (attr1, attr2) représentant des contraintes d'égalité
    :return: True si l'ensemble est cohérent, False sinon
    """
    # Construire le graphe d'égalité
    eq_graph = defaultdict(set)
    for attr1, attr2 in eq_pairs:
        eq_graph[attr1].add(attr2)
        eq_graph[attr2].add(attr1)
    
    # Vérifier que chaque attribut n'apparaît pas deux fois dans des contraintes différentes
    # qui pourraient créer des égalités transitives contradictoires
    attr_count = Counter(attr for pair in eq_pairs for attr in pair)
    
    # Un attribut ne peut pas apparaître dans plus de 2 contraintes
    for attr, count in attr_count.items():
        if count > 2:
            # Vérifier si les attributs liés forment un cycle incohérent
            visited = set([attr])
            for neighbor in eq_graph[attr]:
                if has_cycle(eq_graph, neighbor, visited, None):
                    return False
    
    return True

def has_cycle(eq_graph, current, visited, parent):
    """
    Détecte les cycles dans le graphe d'égalité qui pourraient indiquer une incohérence.
    
    :param eq_graph: Graphe d'égalité sous forme de dictionnaire d'adjacence
    :param current: Nœud actuel
    :param visited: Ensemble des nœuds visités
    :param parent: Nœud parent du nœud actuel
    :return: True si un cycle est détecté, False sinon
    """
    visited.add(current)
    
    for neighbor in eq_graph[current]:
        if neighbor != parent:
            if neighbor in visited:
                return True
            if has_cycle(eq_graph, neighbor, visited, current):
                return True
    
    return False


def prediction(
    path: CandidateRule,
    mapper: AttributeMapper,
    db_inspector: AlchemyUtility,
    body: set[TableOccurrence] = None,
    equality_constraint = None,  # Peut être un tuple (attr1, attr2) ou un tuple de tuples
    threshold: int = None,
) -> int:
    """
    Calcule l'ensemble des tuples qui satisfont la dépendance générant l'égalité (EGD),
    en tenant compte de la sémantique disjointe pour assurer la non-redondance.

    :param path: Une liste d'instances JoinableIndexedAttributes.
    :param mapper: Une instance d'AttributeMapper pour la correspondance des attributs.
    :param db_inspector: Une instance d'AlchemyUtility pour l'interaction avec la base de données.
    :param body: Ensemble d'occurrences de table représentant le corps de la règle.
    :param equality_constraint: Contrainte d'égalité - peut être un tuple (attr1, attr2) ou un tuple de tuples.
    :param threshold: Seuil pour la vérification.
    :return: Un ensemble ou une liste de tuples qui satisfont les EGDs selon la sémantique disjointe.
    """
    join_conditions: list[tuple[str, int, str, str, int, str]] = []
    if path is None:
        return 0
    
    for indexed_attr1, indexed_attr2 in path:
        attr1 = mapper.indexed_attribute_to_attribute(indexed_attr1)
        attr2 = mapper.indexed_attribute_to_attribute(indexed_attr2)
        join_conditions.append(
            (
                attr1.table,
                indexed_attr1.j,
                attr1.name,
                attr2.table,
                indexed_attr2.j,
                attr2.name,
            )
        )
    
    # Pour les EGDs, nous devons également ajouter la contrainte d'égalité
    if equality_constraint is not None:
        # Déterminer le format de equality_constraint
        if isinstance(equality_constraint, tuple) and len(equality_constraint) == 2:
            # Format simple (attr1, attr2)
            if isinstance(equality_constraint[0], IndexedAttribute):
                eq_attr1, eq_attr2 = equality_constraint
                attr1 = mapper.indexed_attribute_to_attribute(eq_attr1)
                attr2 = mapper.indexed_attribute_to_attribute(eq_attr2)
                # Pour l'EGD, nous voulons trouver les violations de la contrainte d'égalité
                join_conditions.append(
                    (
                        attr1.table,
                        eq_attr1.j,
                        attr1.name,
                        attr2.table,
                        eq_attr2.j,
                        attr2.name,
                    )
                )
        elif isinstance(equality_constraint, tuple) and len(equality_constraint) > 0:
            # Format multiple (tuple de tuples)
            # Pour simplifier, utiliser seulement la première contrainte
            if isinstance(equality_constraint[0], tuple) and len(equality_constraint[0]) == 2:
                eq_attr1, eq_attr2 = equality_constraint[0]
                attr1 = mapper.indexed_attribute_to_attribute(eq_attr1)
                attr2 = mapper.indexed_attribute_to_attribute(eq_attr2)
                join_conditions.append(
                    (
                        attr1.table,
                        eq_attr1.j,
                        attr1.name,
                        attr2.table,
                        eq_attr2.j,
                        attr2.name,
                    )
                )
    
    if threshold is not None:
        return bool(db_inspector.check_threshold(
            join_conditions,
            flag="fd_prediction",
            disjoint_semantics=APPLY_DISJOINT,
            threshold=threshold,
        ))
    
    return db_inspector.get_join_row_count(
        join_conditions, disjoint_semantics=APPLY_DISJOINT, flag="fd_prediction"
    )

def path_pruning(
    path: CandidateRule,
    mapper: AttributeMapper,
    db_inspector: AlchemyUtility,
) -> bool:
    """
    Cette fonction vérifie si un chemin donné (règle candidate) doit être élagué ou non
    en fonction du nombre de prédictions.

    :param path: Une liste d'instances JoinableIndexedAttributes représentant la règle candidate.
    :param mapper: Une instance d'AttributeMapper pour la correspondance des attributs.
    :param db_inspector: Une instance d'AlchemyUtility pour l'interaction avec la base de données.
    :return: Une valeur booléenne indiquant si le chemin doit être élagué ou non.
    """
    if path is None:
        return False
    if len(path) == 0:
        return False
    

    return prediction(path, mapper, db_inspector, threshold=0)

def split_pruning(
    candidate_rule: CandidateRule,
    body: set[TableOccurrence],
    equality_constraint,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
) -> tuple[bool, float, float]:
    """
    Cette fonction vérifie si une règle candidate donnée doit être élaguée en fonction
    de son support et de sa confiance.

    :param candidate_rule: Liste d'instances JoinableIndexedAttributes représentant la règle candidate.
    :param body: Ensemble d'occurrences de table représentant le corps de la règle candidate.
    :param equality_constraint: Contrainte d'égalité - soit un tuple (attr1, attr2) soit un tuple de tuples.
    :param db_inspector: Une instance d'AlchemyUtility pour l'interaction avec la base de données.
    :param mapper: Une instance d'AttributeMapper pour la correspondance des attributs.
    :return: Un tuple contenant un booléen indiquant si la règle candidate doit être élaguée,
             et les valeurs de support et de confiance.
    """
    if len(body) == 0:
        return False, 0, 0  # split invalide
    
    pairs_count = Counter((attr.i, attr.j) for jia in candidate_rule for attr in jia)

    # Gérer différents formats pour equality_constraint
    if isinstance(equality_constraint, tuple) and len(equality_constraint) == 2:
        # Cas simple: une seule contrainte d'égalité sous forme de tuple (attr1, attr2)
        if isinstance(equality_constraint[0], IndexedAttribute) and isinstance(equality_constraint[1], IndexedAttribute):
            eq_attr1, eq_attr2 = equality_constraint
            
            # Vérifier que les attributs de la contrainte d'égalité sont différents
            if eq_attr1 == eq_attr2:
                return False, 0, 0  # contrainte d'égalité triviale
            
            # S'assurer qu'au moins un des attributs de la contrainte d'égalité est dans le corps
            if (eq_attr1.i, eq_attr1.j) not in body and (eq_attr2.i, eq_attr2.j) not in body:
                return False, 0, 0  # aucun des attributs d'égalité n'est dans le corps
            
            # Vérifier si la règle aurait un support non nul
            total_tuple_test = prediction(candidate_rule, mapper, db_inspector, body, equality_constraint, threshold=0)
            if total_tuple_test is False:
                return False, 0, 0  # élaguer si la prédiction est 0

            # Calculer le support et la confiance
            total_tuples = prediction(candidate_rule, mapper, db_inspector, body, equality_constraint)
            
            support = calculate_support(candidate_rule, body, equality_constraint, db_inspector, mapper, total_tuples)
            confidence = calculate_confidence(candidate_rule, body, equality_constraint, db_inspector, mapper, total_tuples)

            if confidence == 0 and support == 0:
                return False, 0, 0
                
            return mean([support, confidence]) > SPLIT_PRUNING_MEAN_THRESHOLD, support, confidence
            
    elif isinstance(equality_constraint, tuple) and len(equality_constraint) > 0:
        # Cas complexe: plusieurs contraintes d'égalité sous forme de tuple de tuples
        # Pour simplifier, nous utilisons seulement la première contrainte pour l'élagage
        if isinstance(equality_constraint[0], tuple) and len(equality_constraint[0]) == 2:
            return split_pruning(candidate_rule, body, equality_constraint[0], db_inspector, mapper)
    
    # Si le format n'est pas reconnu ou si la contrainte est vide
    return False, 0, 0

def extract_table_occurrences(
    candidate_rule: CandidateRule,
) -> set[TableOccurrence]:
    """
    Extracts the set of table occurrences from a candidate rule.
    :param candidate_rule: List of JoinableIndexedAttributes representing the candidate rule.
    :return: Set of tuples representing table occurrences (i, j).
    """
    table_occurrences = set()
    for attr1, attr2 in candidate_rule:
        table_occurrences.add((attr1.i, attr1.j))
        table_occurrences.add((attr2.i, attr2.j))
    return table_occurrences

def calculate_support(
    candidate_rule: CandidateRule,
    body: set[TableOccurrence],
    equality_constraint,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    total_tuples: int = None,
) -> float:
    """
    Calcule le support d'une règle candidate fd.
    Le support est défini comme la proportion de tuples satisfaisant à la fois le corps et 
    la contrainte d'égalité par rapport à la population totale de tuples pertinents.
    
    :param candidate_rule: La règle candidate pour laquelle calculer le support.
    :param body: La partie corps de la règle candidate pour laquelle calculer le support.
    :param equality_constraint: Contrainte d'égalité - peut être un tuple (attr1, attr2) ou un tuple de tuples.
    :param db_inspector: Une instance fournissant des fonctionnalités d'inspection de la base de données.
    :param mapper: Une instance d'AttributeMapper pour la correspondance des attributs.
    :param total_tuples: Le nombre total de tuples satisfaisant la règle (si déjà calculé).
    :return: La valeur du support sous forme de nombre décimal.
    """
    # Si total_tuples n'est pas fourni, le calculer
    if total_tuples is None:
        # Calculer le nombre de tuples satisfaisant à la fois le corps et la contrainte d'égalité
        equality_constraint_copy = equality_constraint
        if isinstance(equality_constraint, tuple) and len(equality_constraint) > 0 and isinstance(equality_constraint[0], tuple):
            # Si c'est un tuple de tuples, prendre seulement le premier tuple
            equality_constraint_copy = equality_constraint[0]
            
        total_tuples = prediction(candidate_rule, mapper, db_inspector, body, equality_constraint_copy)
    
    # Calculer le nombre total de tuples dans les relations concernées
    tables_in_rule = set()
    for jia in candidate_rule:
        attr1, attr2 = jia
        tables_in_rule.add((attr1.i, mapper.index_to_table_name[attr1.i]))
        # Correction de l'erreur : utiliser la syntaxe d'accès par clé au lieu d'appel de fonction
        tables_in_rule.add((attr2.i, mapper.index_to_table_name[attr2.i]))
    
    # Calculer le produit cartésien total
    total_population = 1
    for _, table_name in tables_in_rule:
        try:
            row_count = db_inspector.get_row_count(table_name)
            # Éviter les multiplications par zéro simplement en ignorant les tables vides
            if row_count > 0:
                total_population *= row_count
        except Exception as e:
            logging.warning(f"Couldn't get row count for {table_name}: {e}")
            # Estimer une valeur raisonnable sans utiliser max()
            if total_population > 0:  # Si déjà des lignes comptées
                # Utiliser une valeur typique basée sur les autres tables
                total_population *= 100
    
    # Si aucun tuple satisfait la règle ou pas de population, le support est 0
    if total_tuples == 0 or total_population == 0:
        return 0.0
    
    # Support = # tuples satisfaisant la règle / # tuples dans la population
    # Ne pas limiter à 1.0 pour permettre la détection d'erreurs
    support = total_tuples / total_population
    return support

def calculate_confidence(
    candidate_rule: CandidateRule,
    body: set[TableOccurrence],
    equality_constraint,  # Modifié pour accepter les deux formats
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    total_tuples: int = None,
) -> float:
    """
    Calcule la confiance d'une règle candidate fd.
    La confiance est définie comme la proportion de tuples satisfaisant la contrainte d'égalité
    parmi ceux qui satisfont le corps de la règle.
    
    :param candidate_rule: La règle candidate pour laquelle calculer la confiance.
    :param body: La partie corps de la règle candidate.
    :param equality_constraint: Contrainte d'égalité - peut être un tuple (attr1, attr2) ou un tuple de tuples.
    :param db_inspector: Une instance fournissant des fonctionnalités d'inspection de la base de données.
    :param mapper: Une instance d'AttributeMapper pour la correspondance des attributs.
    :param total_tuples: Le nombre total de tuples satisfaisant la règle (si déjà calculé).
    :return: La valeur de la confiance sous forme de nombre décimal.
    """
    # Normaliser le format de la contrainte d'égalité
    if isinstance(equality_constraint, tuple) and len(equality_constraint) == 2:
        if isinstance(equality_constraint[0], IndexedAttribute):
            # Format simple (attr1, attr2)
            eq_attr1, eq_attr2 = equality_constraint
        else:
            # Format non reconnu
            return 0
    elif isinstance(equality_constraint, tuple) and len(equality_constraint) > 0:
        # Format multiple (tuple de tuples)
        if isinstance(equality_constraint[0], tuple) and len(equality_constraint[0]) == 2:
            # Utiliser seulement la première contrainte
            eq_attr1, eq_attr2 = equality_constraint[0]
        else:
            # Format non reconnu
            return 0
        
    # Le calcul correct de la confiance pour une fd doit mesurer:
    # 1. Le nombre de tuples satisfaisant le corps (dénominateur)
    # 2. Parmi ces tuples, combien satisfont également la condition d'égalité (numérateur)
    
    # Construction des conditions de jointure pour le corps de la règle
    body_conditions = []
    for jia in candidate_rule:
        attr1, attr2 = jia
        if (attr1.i, attr1.j) in body or (attr2.i, attr2.j) in body:
            attr1_obj = mapper.indexed_attribute_to_attribute(attr1)
            attr2_obj = mapper.indexed_attribute_to_attribute(attr2)
            body_conditions.append(
                (
                    attr1_obj.table,
                    attr1.j,
                    attr1_obj.name,
                    attr2_obj.table,
                    attr2.j,
                    attr2_obj.name,
                )
            )
    
    # Vérifier s'il y a des tuples qui satisfont le corps
    if not body_conditions or not db_inspector.check_threshold(
        body_conditions, 
        flag="fd_confidence_body",
        disjoint_semantics=APPLY_DISJOINT, 
        threshold=0
    ):
        return 0
    
    # Nombre de tuples qui satisfont le corps de la règle
    body_tuples_count = db_inspector.get_join_row_count(
        body_conditions, 
        flag="fd_confidence_body",
        disjoint_semantics=APPLY_DISJOINT
    )
    
    if body_tuples_count == 0:
        return 0
    
    # Pour calculer les tuples qui satisfont le corps ET l'égalité, nous devons compter
    # les tuples où les deux côtés de la contrainte d'égalité sont effectivement égaux
    
    # Récupérer les attributs pour la contrainte d'égalité
    attr1_obj = mapper.indexed_attribute_to_attribute(eq_attr1)
    attr2_obj = mapper.indexed_attribute_to_attribute(eq_attr2)
    
    # On récupère les deux valeurs pour les vérifier, sans imposer leur égalité
    query_attrs = [
        (f"{attr1_obj.table}_{eq_attr1.j}.{attr1_obj.name}", f"val1"),
        (f"{attr2_obj.table}_{eq_attr2.j}.{attr2_obj.name}", f"val2")
    ]
    
    # Compter les tuples où les valeurs sont égales
    try:
        # Obtenir d'abord tous les tuples qui satisfont le corps
        body_tuples = db_inspector.get_join_content_custom(
            body_conditions,
            query_attrs,
            flag="fd_confidence_full"
        )
        
        # Parmi ces tuples, compter ceux où val1 == val2
        equal_tuples = sum(1 for row in body_tuples if row[0] == row[1])
        
        if equal_tuples == 0:
            return 0
            
        # Calculer la confiance comme le rapport entre les tuples égaux et tous les tuples du corps
        # Ne pas limiter la valeur pour permettre de détecter les erreurs potentielles
        confidence = equal_tuples / body_tuples_count
        return confidence
        
    except Exception as e:
        logging.error(f"Error computing confidence: {e}")
        
        # Si la méthode ci-dessus échoue, essayer une approche alternative
        extended_conditions = body_conditions.copy()
        extended_conditions.append(
            (
                attr1_obj.table,
                eq_attr1.j,
                attr1_obj.name,
                attr2_obj.table,
                eq_attr2.j,
                attr2_obj.name,
            )
        )
        
        # Compter les tuples qui satisfont à la fois le corps et la contrainte d'égalité
        equal_tuples = db_inspector.get_join_row_count(
            extended_conditions, 
            flag="fd_confidence_fallback",
            disjoint_semantics=APPLY_DISJOINT
        )
        
        # Calculer la confiance, sans limitation pour détecter les anomalies
        if equal_tuples == 0:
            return 0
            
        confidence = equal_tuples / body_tuples_count
        return confidence

def validate_perfect_rule(
    candidate_rule: CandidateRule,
    body: set[TableOccurrence],
    equality_constraint,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
) -> bool:
    """
    Valide qu'une règle parfaite (100% support, 100% confiance) est légitime et non due à une erreur.
    
    :param candidate_rule: La règle candidate à valider
    :param body: Le corps de la règle
    :param equality_constraint: La contrainte d'égalité
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :return: True si la règle est légitime, False sinon
    """
    # Extraire les attributs de la contrainte d'égalité
    if isinstance(equality_constraint, tuple) and len(equality_constraint) == 2:
        if isinstance(equality_constraint[0], IndexedAttribute):
            eq_attr1, eq_attr2 = equality_constraint
        else:
            return False
    elif isinstance(equality_constraint, tuple) and len(equality_constraint) > 0:
        if isinstance(equality_constraint[0], tuple) and len(equality_constraint[0]) == 2:
            eq_attr1, eq_attr2 = equality_constraint[0]
        else:
            return False
    else:
        return False
        
    # Convertir en objets Attribute
    attr1_obj = mapper.indexed_attribute_to_attribute(eq_attr1)
    attr2_obj = mapper.indexed_attribute_to_attribute(eq_attr2)
    
    # Vérifier s'il s'agit d'attributs liés par une clé étrangère
    is_foreign_key = db_inspector.are_foreign_keys(
        attr1_obj.table, attr1_obj.name, attr2_obj.table, attr2_obj.name
    )
    
    # Vérifier si les attributs ont des noms identiques ou très similaires
    name_similarity = attr1_obj.name.lower() == attr2_obj.name.lower()
    
    # Vérifier si les tables ont des noms similaires ou liés
    table_related = (attr1_obj.table.lower() in attr2_obj.table.lower() or 
                     attr2_obj.table.lower() in attr1_obj.table.lower())
    
    # Vérifier si le nombre de tuples impliqués est significatif
    body_condition = []
    for jia in candidate_rule:
        a1, a2 = jia
        if (a1.i, a1.j) in body or (a2.i, a2.j) in body:
            a1_obj = mapper.indexed_attribute_to_attribute(a1)
            a2_obj = mapper.indexed_attribute_to_attribute(a2)
            body_condition.append(
                (a1_obj.table, a1.j, a1_obj.name, a2_obj.table, a2.j, a2_obj.name)
            )
    
    tuples_count = db_inspector.get_join_row_count(body_condition, disjoint_semantics=APPLY_DISJOINT)
    # Seuil fixe au lieu d'utiliser max()
    significant_data = tuples_count > 10
    
    # Une règle légitime de 100% devrait généralement être:
    # - Une contrainte de clé étrangère, OU
    # - Des attributs avec des noms identiques entre tables liées, OU
    # - Une règle portant sur un nombre significatif de tuples
    return is_foreign_key or (name_similarity and table_related) or significant_data

def has_common_elements_above_threshold_percentage(self, db_inspector: AlchemyUtility, table1: str, col1: str,
                                                   table2: str,
                                                   col2: str, threshold: int) -> bool:
    # Fetch data directly from the database using db_inspector
    df1_values = db_inspector.get_attribute_values(table1, col1)
    df2_values = db_inspector.get_attribute_values(table2, col2)

    # Convert lists to sets (drop None and convert to string)
    set1 = set(filter(None, map(str, df1_values)))
    set2 = set(filter(None, map(str, df2_values)))

    # Find common elements and union of the sets
    common_values = set1.intersection(set2)
    union_values = set1.union(set2)
    
    # Vérifier si l'union est vide pour éviter une division par zéro
    if len(union_values) == 0:
        return False
        
    # Check if the ratio of common elements to the union is above the thresholdSupporte également le nouvel attribut head qui stocke les contraintes d'égalité.
    return len(common_values) / len(union_values) > threshold

def instantiate_fd_object(candidate_rule, split, mapper, support=1.0, confidence=1.0):
    """
    Crée directement un objet FunctionalDependency à partir d'un candidat et d'un split.
    
    :param candidate_rule: Le candidat de règle (liste de JoinableIndexedAttributes)
    :param split: La division du candidat en corps/tête (body, equality_constraints)
    :param mapper: Le mappeur d'attributs
    :param support: Le support de la règle
    :param confidence: La confiance de la règle
    :return: Un objet FunctionalDependency ou None si l'instanciation échoue
    """
    try:
        from utils.rules_classes.functional_dependency import FunctionalDependency
        
        if FunctionalDependency is None:
            import logging
            logging.getLogger(__name__).error("FunctionalDependency class not available")
            return None
        
        # Extraire le corps et les contraintes d'égalité
        body, equality_constraints = split
        
        # Informations de table et colonnes
        table_name = None
        determinant_cols = []
        dependent_cols = []
        
        # Obtenir les attributs du corps (déterminants)
        for jia in candidate_rule:
            for attr in jia:
                if (attr.i, attr.j) in body:
                    attribute = mapper.indexed_attribute_to_attribute(attr)
                    if attribute:
                        # Enregistrer la table si pas encore définie
                        if table_name is None:
                            table_name = attribute.table
                            
                        # Ajouter le nom de la colonne comme déterminant
                        if attribute.name not in determinant_cols:
                            determinant_cols.append(attribute.name)
        
        # Obtenir les attributs dépendants
        if isinstance(equality_constraints, tuple):
            # Gérer le cas où equality_constraints est un tuple de tuples
            if equality_constraints and isinstance(equality_constraints[0], tuple):
                for eq_attr1, eq_attr2 in equality_constraints:
                    # Pour les FDs, le deuxième attribut est généralement l'attribut dépendant
                    attr = mapper.indexed_attribute_to_attribute(eq_attr2)
                    if attr:
                        if table_name is None:
                            table_name = attr.table
                        if attr.name not in dependent_cols:
                            dependent_cols.append(attr.name)
            # Gérer le cas où equality_constraints est un tuple simple (eq_attr1, eq_attr2)
            elif len(equality_constraints) == 2 and isinstance(equality_constraints[0], IndexedAttribute):
                _, eq_attr2 = equality_constraints  # Le second est l'attribut dépendant
                attr = mapper.indexed_attribute_to_attribute(eq_attr2)
                if attr:
                    if table_name is None:
                        table_name = attr.table
                    dependent_cols.append(attr.name)
        
        # Créer l'objet FD avec les déterminants et les dépendants
        if table_name and determinant_cols and dependent_cols:
            # Utiliser confidence comme valeur pour accuracy pour éviter les None
            accuracy = confidence  # Dans le contexte des FDs, la précision est souvent égale à la confiance
            
            # Créer un représentation formatée pour l'affichage
            display_str = f"{table_name}: {', '.join(determinant_cols)} → {', '.join(dependent_cols)}"
            
            return FunctionalDependency(
                table=table_name,
                determinant=tuple(determinant_cols),
                dependent=tuple(dependent_cols),
                support=support,
                confidence=confidence,
                accuracy=accuracy,  # Initialiser accuracy avec la valeur de confidence
                converted_from_egd=True,  # Indique que cette FD a été découverte via notre algorithme
                display=display_str  # Ajouter la représentation formatée
            )
        else:
            return None
                
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(f"Error instantiating FD object: {e}")
        return None

import logging
from typing import Dict, List, Set, Tuple, Any, Optional
import time

from utils.rules import FunctionalDependency



logger = logging.getLogger('MATILDA.FDDiscovery')

def instantiate_fd(db_inspector, min_occurrences=2, **kwargs):
    """
    Initialise les structures de données nécessaires pour la découverte de dépendances fonctionnelles (FD).
    Version simplifiée qui identifie rapidement les candidats potentiels.
    
    :param db_inspector: L'inspecteur de base de données
    :param min_occurrences: Nombre minimum d'occurrences pour considérer une dépendance
    :param kwargs: Paramètres supplémentaires
    :return: Dictionnaire contenant les structures initialisées pour la découverte de FD
    """
    logger.info("Initialisation du module de découverte de dépendances fonctionnelles (version simplifiée)...")
    
    # Récupérer la liste des tables
    tables = db_inspector.get_table_names()
    
    # Structure pour stocker les attributs et candidats FD
    table_attributes = {}
    fd_candidates = []
    
    # Pour chaque table
    for table in tables:
        try:
            # Récupérer ses attributs
            attributes = db_inspector.get_attribute_names(table)
            table_attributes[table] = attributes
            
            # Pour chaque paire d'attributs, créer un candidat FD
            for attr1 in attributes:
                for attr2 in attributes:
                    # Ne pas considérer les FDs de type A → A
                    if attr1 != attr2:
                        fd_candidates.append({
                            'table': table,
                            'lhs': [attr1],  # Déterminant (partie gauche)
                            'rhs': attr2,    # Dépendant (partie droite)
                            'priority': 1.0   # Priorité uniforme
                        })
        except Exception as e:
            logger.warning(f"Erreur lors de l'analyse de la table {table}: {e}")
            continue
    
    logger.info(f"Initialisation terminée. Identifié {len(fd_candidates)} candidats FD potentiels.")
    
    return {
        'table_attributes': table_attributes,
        'fd_candidates': fd_candidates,
        'min_occurrences': min_occurrences,
        'initialized': True
    }
