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
    tuple[frozenset[JoinableIndexedAttributes], frozenset[JoinableIndexedAttributes]]
]:  
    """
    Génère toutes les partitions possibles (powerset) d'une règle candidate pour former des FDs.
    Pour chaque sous-ensemble possible de la règle candidate, crée un split où ce sous-ensemble
    est le corps et le reste est la tête.

    :param candidate_rule: Une liste de JoinableIndexedAttributes (représentant le candidat)
    :return: Un ensemble de tuples (body, head) où body et head sont des sous-ensembles de candidate_rule
    """
    if candidate_rule is None or len(candidate_rule) == 0:
        return set()
    
    valid_splits = set()
    
    # Convertir candidate_rule en frozenset pour permettre les opérations d'ensemble
    candidate_set = frozenset(candidate_rule)
    
    # Générer tous les sous-ensembles possibles pour le corps (body)
    for r in range(len(candidate_rule) + 1):
        for body_items in combinations(candidate_rule, r):
            # Convertir en frozenset pour l'unicité et l'immuabilité
            body = frozenset(body_items)
            # La tête est le complément du corps par rapport à l'ensemble complet
            head = candidate_set - body
            
            # Ajouter le split à l'ensemble des splits valides
            # Ne pas ajouter le split si le body ou le head est vide
            if body and head:
                valid_splits.add((body, head))
    
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
    body: set[JoinableIndexedAttributes],
    head: set[JoinableIndexedAttributes],
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
    
    # check that the FD is not trivial
    if len(candidate_rule) == 1:
        # Si la règle candidate n'a qu'un seul attribut, elle est triviale
        return False, 0, 0
    if body == head:
        # Si le corps et la tête sont identiques, la règle candidate est triviale
        return False, 0, 0 
    for element in head: 
        if element in body:
            # Si un élément de la tête est également dans le corps, la règle candidate est triviale
            return False, 0, 0
    # TODO: check the FD metrics 
    # compute the support and confidence
    total_tuples = prediction(candidate_rule, mapper, db_inspector, body, head)
    support = calculate_support(
        candidate_rule,
        body,
        head,
        db_inspector=db_inspector,
        mapper=mapper,
        total_tuples=total_tuples,
    )
    confidence = calculate_confidence(
        candidate_rule,
        body,
        head,
        db_inspector=db_inspector,
        mapper=mapper,
        total_tuples=total_tuples,

    )
    if support < 0.01 or confidence < 0.01:
        logger.info(
            f"Candidate rule {candidate_rule} is pruned due to low support ({support}) or confidence ({confidence})."
        )
        # Si le support ou la confiance est inférieur à 0.01, élaguer la règle candidate
        return False, support, confidence
    else: 
        # Si le support et la confiance sont suffisants, ne pas élaguer
        return True, support, confidence
    return False , 0, 0 # debug 


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
    head: set[TableOccurrence],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    total_tuples: int = None,
) -> float:
    """
    Calculate the support of a candidate rule.
    :param candidate_rule: The candidate rule for which to calculate support.
    :param body: The body part of the candidate rule for which to calculate support.
    :param db_inspector: An instance of a class that provides database inspection functionalities.
    :param mapper: An instance of AttributeMapper for mapping indexed attributes to actual database attributes.
    :return: The support value as a float.
    """
    # cr_chains = CandidateRuleChains(candidate_rule).cr_chains

    # x_chains = CandidateRuleChains(candidate_rule).get_x_chains(
    #     body, head, mapper, select_body=True
    # )


    if total_tuples == 0:
       return 0

    support_condition: list[tuple[str, int, str, str, int, str]] = []
    # First, add the constraints from the body
    for jia in body:
        attr1, attr2 = jia

        support_condition.append(
            (
                mapper.indexed_attribute_to_attribute(attr2).table,
                attr2.j,
                mapper.indexed_attribute_to_attribute(attr2).name,
                mapper.indexed_attribute_to_attribute(attr1).table,
                attr1.j,
                mapper.indexed_attribute_to_attribute(attr1).name,
            )
        )
    # # add other constraints for each respective chain in the cr_chains
    # for jia in candidate_rule:
    #     for attr11 in jia:
    #         for chain in cr_chains:
    #             if attr11 in chain:
    #                 for attr22 in chain:
    #                     if (
    #                             attr11 != attr22
    #                             and attr22 not in jia
    #                             and (attr11.i, attr11.j) in body
    #                             and (attr22.i, attr22.j) in body
    #                     ):
    #                         support_condition.append(
    #                             (
    #                                 mapper.indexed_attribute_to_attribute(attr22).table,
    #                                 attr22.j,
    #                                 mapper.indexed_attribute_to_attribute(attr22).name,
    #                                 mapper.indexed_attribute_to_attribute(attr11).table,
    #                                 attr11.j,
    #                                 mapper.indexed_attribute_to_attribute(attr11).name,
    #                             )
    #                         )
    support_condition = list(set(support_condition))
    is_body_tuples_emtpy = db_inspector.check_threshold(
        support_condition,  flag="support", disjoint_semantics=True, threshold=0
    )
    if not(bool( is_body_tuples_emtpy)):
        return 0 
    total_tuples_satisfying_body = db_inspector.get_join_row_count(
        support_condition, flag="support", disjoint_semantics=True
    )
    # logger.info(
        # f"Candidate Rule: {candidate_rule}, Body: {body}, Head: {head}, is_body_tuples_emtpy: {bool(is_body_tuples_emtpy)}        , total_tuples_satisfying_body: {total_tuples_satisfying_body}"
    # )
    # raise ValueError(
    #     f"Candidate Rule: {candidate_rule}, Body: {body}, Head: {head}, is_body_tuples_emtpy: {is_body_tuples_emtpy}        , total_tuples_satisfying_body: {total_tuples_satisfying_body}"
    # )

    # if not  bool(is_body_tuples_emtpy):
    #     return 0
    # total_tuples_satisfying_body = db_inspector.get_join_row_count(
    #     support_condition, flag="support", disjoint_semantics=True
    # )
    # raise ValueError(    f"iam here {support_condition} {body} {head}")
    if total_tuples_satisfying_body == 0 :
        return 0
    support = total_tuples / total_tuples_satisfying_body
    return support


def calculate_confidence(
    candidate_rule: CandidateRule,
    body: set[TableOccurrence],
    head: set[TableOccurrence],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    total_tuples: int = None,

) -> float:
    """
    Calculate the confidence of a candidate rule.

    :param candidate_rule: The candidate rule for which to calculate confidence.
    :param head: The head part of the candidate rule for which to calculate confidence.
    :param db_inspector: An instance of a class that provides database inspection functionalities.
    :param mapper: An instance of AttributeMapper for mapping indexed attributes to actual database attributes.
    :return: The confidence value as a float.
    """
    # total_tuples = prediction(candidate_rule, mapper, db_inspector, body, head)
    # x_chains = CandidateRuleChains(candidate_rule).get_x_chains(
        # body, head, mapper, select_head=True
    # )
    # cr_chains = CandidateRuleChains(candidate_rule).cr_chains

    #confidence_conditions: list[tuple[str, int, str, str, int, str]] = []
    # add constraints in head
    head_conditions = []
    for jia in head:
        attr1, attr2 = jia

        head_conditions.append(
            (
                mapper.indexed_attribute_to_attribute(attr2).table,
                attr2.j,
                mapper.indexed_attribute_to_attribute(attr2).name,
                mapper.indexed_attribute_to_attribute(attr1).table,
                attr1.j,
                mapper.indexed_attribute_to_attribute(attr1).name,
            )
        )
    # for jia in candidate_rule:
    #     for attr11 in jia:
    #         for chain in cr_chains:
    #             if attr11 in chain:
    #                 for attr22 in chain:
    #                     if (
    #                             attr11 != attr22
    #                             and attr22 not in jia
    #                             and (attr11.i, attr11.j) in head
    #                             and (attr22.i, attr22.j) in head
    #                     ):
    #                         head_conditions.append(
    #                             (
    #                                 mapper.indexed_attribute_to_attribute(attr22).table,
    #                                 attr22.j,
    #                                 mapper.indexed_attribute_to_attribute(attr22).name,
    #                                 mapper.indexed_attribute_to_attribute(attr11).table,
    #                                 attr11.j,
    #                                 mapper.indexed_attribute_to_attribute(attr11).name,
    #                             )
    #                         )
    is_head_tuples_emtpy = db_inspector.check_threshold(
        head_conditions, flag="head", disjoint_semantics=APPLY_DISJOINT, threshold=0
    )
    if not bool(is_head_tuples_emtpy):
        return 0
    # logger.info(
    #     f"Candidate Rule: {candidate_rule}, Body: {body}, Head: {head}, is_body_tuples_emtpy: {is_body_tuples_emtpy}"
    # )
    # if not  bool(is_body_tuples_emtpy):
    #     return 0

    total_tuples_satisfying_head = db_inspector.get_join_row_count(
        head_conditions, flag="head", disjoint_semantics=APPLY_DISJOINT
    )
    if total_tuples_satisfying_head == 0:
        return 0
    support = total_tuples / total_tuples_satisfying_head
    # logger.info(
    #     f"Candidate Rule: {candidate_rule}, Body: {body}, Head: {head}, Support: {support}"
    # )
    return support

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
        body, head = split
        #logger.info(f"Body: {body}, Head: {head}")
        # Informations de table et colonnes
        table_name = None
        table_names = set()  # Pour stocker tous les noms de tables rencontrés
        determinant_cols = []
        dependent_cols = []
        
        # Obtenir les attributs du corps (déterminants)
        for jia in candidate_rule:
            attr1, attr2 = jia
            attr = attr1 
            attribute = mapper.indexed_attribute_to_attribute(attr)

            if jia in body:

                if attribute:
                    # Collecter les noms de tables
                    table_names.add(attribute.table)
                        # Ajouter le nom de la colonne comme déterminant
                    determinant_cols.append(attribute.name)
            else :
                if attribute:
                    # Collecter les noms de tables
                    table_names.add(attribute.table)
                        # Ajouter le nom de la colonne comme déterminant
                    dependent_cols.append(attribute.name)
                    
        


        table_name = table_names.pop() if len(table_names) >= 1 else None  # Prendre le dernier nom de table si unique
        
        # Créer l'objet FD avec les déterminants et les dépendants
        if table_name:# and determinant_cols and dependent_cols:
            # Utiliser confidence comme valeur pour accuracy pour éviter les None
            accuracy = confidence  
            
            # Créer un représentation formatée pour l'affichage
            display_str = f"{table_name}: {', '.join(determinant_cols)} → {', '.join(dependent_cols)}"
            
            return FunctionalDependency(
                table=table_name,  # Utiliser uniquement la table principale identifiée
                determinant=tuple(determinant_cols),
                dependent=tuple(dependent_cols),
                support=support,
                confidence=confidence,
                accuracy=accuracy,
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
