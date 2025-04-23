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
    filename='logs/egd_computation.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    filemode='w'
)

APPLY_DISJOINT = False
SPLIT_PRUNING_MEAN_THRESHOLD = 0
TableOccurrence = tuple[int, int]
CandidateRule = list[JoinableIndexedAttributes]

def init(
    db_inspector: AlchemyUtility,
    max_nb_occurrence: int = 3,
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
    # Input validation
    if not db_inspector or not hasattr(db_inspector, "base_name"):
        raise ValueError("Invalid db_inspector provided.")

    try:
        time_taken_init = time.time()
        # Generate all attributes
        attributes = Attribute.generate_attributes(db_inspector)
        if not attributes:
            logging.warning("No attributes generated. Exiting initialization.")
            return None, None, []

        # Utiliser le mode de compatibilité spécifié ou le mode par défaut
        try:
            compatibility_mode = compatibility_mode or CompatibilityChecker.MODE_HYBRID
        except AttributeError:
            compatibility_mode = "hybrid"  # Valeur par défaut si l'attribut MODE_HYBRID n'existe pas
        
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
                filepath = os.path.join(results_path, f"compatibility_egd_{base_name}.json")
                
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
                        if (
                            max_nb_occurrence_per_table_and_column.get(attr1.table, {}).get(
                                attr1.name, max_nb_occurrence
                            )
                            < table_occurrence1
                        ):
                            continue
                        if (
                            max_nb_occurrence_per_table_and_column.get(attr2.table, {}).get(
                                attr2.name, max_nb_occurrence
                            )
                            < table_occurrence2
                        ):
                            continue
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
                cg_metrics_path = os.path.join(results_path, f"cg_metrics_egd_{base_name}.json")
                with open(cg_metrics_path, "w") as f:
                    json.dump(str(cg), f)
                
                # Export time metrics
                time_metrics_path = os.path.join(results_path, f"init_time_metrics_egd_{base_name}.json")
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
    Pour les EGDs, nous cherchons à identifier les contraintes d'égalité possibles 
    entre attributs différents, en séparant le chemin en corps et tête.
    Supporte désormais plusieurs contraintes d'égalité dans la tête.

    :param candidate_rule: A list of tuples of JoinableIndexedAttributes (representing the candidate_rule)
    :return: A set of (body, equality_constraints) pairs where equality_constraints is a list
    """
    if candidate_rule is None or len(candidate_rule) == 0:
        return set()
    
    valid_splits = set()
    
    # Pour chaque taille possible du corps (de 1 à n-1)
    for body_size in range(1, len(candidate_rule)):
        # Générer toutes les combinaisons possibles de chemins pour le corps
        for body_indices in combinations(range(len(candidate_rule)), body_size):
            # Construire le corps
            body_rule = [candidate_rule[i] for i in body_indices]
            body_table_occurrences = extract_table_occurrences(body_rule)
            
            # Construire la tête (reste du chemin)
            head_indices = [i for i in range(len(candidate_rule)) if i not in body_indices]
            head_rule = [candidate_rule[i] for i in head_indices]
            head_table_occurrences = extract_table_occurrences(head_rule)
            
            # Trouver toutes les paires d'attributs compatibles (un du corps, un de la tête)
            all_body_attrs = set()
            for jia in body_rule:
                attr1, attr2 = jia
                all_body_attrs.add(attr1)
                all_body_attrs.add(attr2)
            
            all_head_attrs = set()
            for jia in head_rule:
                attr1, attr2 = jia
                all_head_attrs.add(attr1)
                all_head_attrs.add(attr2)
            
            # Générer toutes les combinaisons possibles de contraintes d'égalité
            # Pour 1 à k contraintes d'égalité (limité à 3 pour la performance)
            for eq_count in range(1, min(4, len(all_body_attrs) * len(all_head_attrs) + 1)):
                # Générer toutes les paires d'attributs possibles pour les contraintes d'égalité
                all_eq_pairs = []
                for attr1 in all_body_attrs:
                    for attr2 in all_head_attrs:
                        if attr1 != attr2:  # Évite les règles triviales
                            all_eq_pairs.append((attr1, attr2))
                
                # Générer toutes les combinaisons possibles de paires d'égalité
                for eq_pairs in combinations(all_eq_pairs, eq_count):
                    # Vérifier que les paires sont cohérentes (pas de transitivité contradictoire)
                    if is_consistent_constraint_set(eq_pairs):
                        combined_body = body_table_occurrences.union(head_table_occurrences)
                        # Convertir en tuple pour hashabilité
                        equality_constraints = tuple(sorted(eq_pairs))
                        valid_splits.add((frozenset(combined_body), equality_constraints))
    
    # Ajouter également les splits traditionnels (tout le chemin dans le corps)
    table_occurrences = extract_table_occurrences(candidate_rule)
    all_attributes = set()
    for jia in candidate_rule:
        attr1, attr2 = jia
        all_attributes.add(attr1)
        all_attributes.add(attr2)
    
    # Générer des ensembles de contraintes d'égalité pour tout le corps
    # Pour 1 à k contraintes d'égalité (limité à 3 pour la performance)
    attr_list = list(all_attributes)
    for eq_count in range(1, min(4, len(attr_list) * (len(attr_list) - 1) // 2 + 1)):
        # Générer toutes les paires d'attributs possibles
        all_eq_pairs = []
        for i, attr1 in enumerate(attr_list):
            for attr2 in attr_list[i+1:]:
                if attr1 != attr2:  # Évite les règles triviales
                    all_eq_pairs.append((attr1, attr2))
        
        # Générer toutes les combinaisons possibles de paires d'égalité
        for eq_pairs in combinations(all_eq_pairs, eq_count):
            # Vérifier que les paires sont cohérentes (pas de transitivité contradictoire)
            if is_consistent_constraint_set(eq_pairs):
                equality_constraints = tuple(sorted(eq_pairs))
                valid_splits.add((frozenset(table_occurrences), equality_constraints))
    
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

def instantiate_egd(
    candidate_rule: CandidateRule,
    split: tuple[set[TableOccurrence], tuple[tuple[IndexedAttribute, IndexedAttribute], ...]],
    mapper: AttributeMapper,
) -> str:
    """
    Cette fonction instancie une dépendance générant l'égalité (EGD) avec plusieurs contraintes d'égalité.
    
    :param candidate_rule: Une liste d'instances JoinableIndexedAttributes représentant la règle candidate.
    :param split: Un tuple contenant un ensemble d'occurrences de table (le body) et un tuple de contraintes d'égalité.
    :param mapper: Une instance d'AttributeMapper pour la correspondance des attributs.
    :return: Une chaîne représentant l'EGD instanciée.
    """
    # Étape 1: Déterminer les classes d'équivalence à partir de la règle candidate
    cr_chains = CandidateRuleChains(candidate_rule).cr_chains
    
    # Étape 2: Assigner des variables à chaque classe d'équivalence
    body, equality_constraints = split
    
    # Si equality_constraints n'est pas un tuple de tuples, le convertir en tuple d'un seul élément
    if len(equality_constraints) > 0 and not isinstance(equality_constraints[0], tuple):
        equality_constraints = (equality_constraints,)
    
    variable_assignment = assign_variables_for_multiple_egd(cr_chains, body, equality_constraints, mapper)
    
    # Étape 3: Construire les prédicats pour le corps
    body_predicates = construct_predicates_egd(variable_assignment, candidate_rule, mapper, body)
    
    # Étape 4: Construire la liste des contraintes d'égalité
    equality_strings = []
    equality_pairs = []  # Pour stocker les paires de variables pour l'attribut head
    
    for eq_attr1, eq_attr2 in equality_constraints:
        var1 = variable_assignment.get(eq_attr1)
        var2 = variable_assignment.get(eq_attr2)
        
        # Vérifier que les variables sont présentes et différentes
        if var1 and var2 and var1 != var2:
            equality_strings.append(f"{var1} = {var2}")
            equality_pairs.append((var1, var2))
    
    # Si aucune contrainte d'égalité valide n'a été trouvée, retourner une chaîne vide
    if not equality_strings:
        return ""
    
    # Pour plusieurs contraintes d'égalité, les joindre avec une conjonction
    if len(equality_strings) > 1:
        equality_constraint = " ∧ ".join(equality_strings)
    else:
        equality_constraint = equality_strings[0]
    
    # Retourner l'EGD instanciée sous forme de chaîne, et stocker les paires d'égalité
    egd_string = construct_egd_string(body_predicates, equality_constraint, variable_assignment)
    
    # Stocker également les paires d'égalité pour pouvoir les utiliser lors de la création de l'EGDRule
    return egd_string

def assign_variables_for_multiple_egd(
    equivalence_classes: list[set[IndexedAttribute]],
    body: set[TableOccurrence],
    equality_constraints: tuple[tuple[IndexedAttribute, IndexedAttribute], ...],
    mapper: AttributeMapper
) -> dict[IndexedAttribute, str]:
    """
    Assigner des variables aux attributs dans les classes d'équivalence pour les EGDs.
    Gère plusieurs contraintes d'égalité et s'assure que les variables sont correctement assignées.
    
    :param equivalence_classes: Une liste d'ensembles d'IndexedAttribute, chaque ensemble représente une classe d'équivalence.
    :param body: Un ensemble d'occurrences de table représentant le corps de l'EGD.
    :param equality_constraints: Un tuple de tuples, chaque tuple interne représente une contrainte d'égalité (attr1, attr2).
    :param mapper: Une instance d'AttributeMapper pour la correspondance des attributs.
    :return: Un dictionnaire associant chaque IndexedAttribute à un nom de variable.
    """
    variables_assignment = {}
    
    # Extraire tous les attributs de contraintes d'égalité
    equality_attrs = set()
    for eq_attr1, eq_attr2 in equality_constraints:
        equality_attrs.add(eq_attr1)
        equality_attrs.add(eq_attr2)
    
    # Extraire tous les attributs indexés pertinents pour le corps
    body_attributes = set()
    for ec in equivalence_classes:
        for attr in ec:
            if (attr.i, attr.j) in body:
                body_attributes.add(attr)
    
    # Ajouter tous les attributs de contrainte d'égalité à l'ensemble des attributs du corps
    body_attributes.update(equality_attrs)
    
    # Convention de nommage des variables
    variable_counter = 0
    
    # Étape 1: Assigner des variables aux attributs des contraintes d'égalité
    for eq_attr1, eq_attr2 in equality_constraints:
        # Si les attributs n'ont pas encore de variable assignée, leur en assigner une
        if eq_attr1 not in variables_assignment:
            variables_assignment[eq_attr1] = f"x{variable_counter}"
            variable_counter += 1
            
        if eq_attr2 not in variables_assignment:
            variables_assignment[eq_attr2] = f"x{variable_counter}"
            variable_counter += 1
    
    # Étape 2: Assigner des variables aux attributs des classes d'équivalence
    for ec in equivalence_classes:
        # Trouver les attributs de cette classe qui sont dans le corps
        ec_body_attrs = [attr for attr in ec if attr in body_attributes]
        if not ec_body_attrs:
            continue
            
        # Vérifier si certains attributs de cette classe ont déjà des variables assignées
        assigned_attrs = [attr for attr in ec_body_attrs if attr in variables_assignment]
        
        if assigned_attrs:
            # Si des attributs ont déjà une variable, utiliser cette variable pour tous les attributs non assignés
            existing_variable = variables_assignment[assigned_attrs[0]]
            for attr in ec_body_attrs:
                if attr not in variables_assignment:
                    variables_assignment[attr] = existing_variable
        else:
            # Sinon, créer une nouvelle variable pour cette classe
            variable_name = f"x{variable_counter}"
            variable_counter += 1
            for attr in ec_body_attrs:
                variables_assignment[attr] = variable_name
    
    # Étape 3: Vérification finale pour s'assurer que les variables des contraintes d'égalité sont différentes
    # Ceci est particulièrement important pour éviter les contraintes d'égalité triviales comme x0 = x0
    for eq_attr1, eq_attr2 in equality_constraints:
        if eq_attr1 in variables_assignment and eq_attr2 in variables_assignment:
            if variables_assignment[eq_attr1] == variables_assignment[eq_attr2]:
                # Si deux attributs d'une contrainte d'égalité ont la même variable, réassigner
                variables_assignment[eq_attr2] = f"x{variable_counter}"
                variable_counter += 1
    
    return variables_assignment

def construct_predicates_egd(
    variable_assignment: dict[IndexedAttribute, str],
    candidate_rule: CandidateRule,
    mapper: AttributeMapper,
    body: set[TableOccurrence]
) -> str:
    """
    Cette fonction construit les prédicats pour le corps d'une EGD.
    S'assure que toutes les variables apparaissant dans les prédicats sont définies
    dans variable_assignment pour éviter les variables orphelines.
    
    :param variable_assignment: Un dictionnaire associant chaque IndexedAttribute à un nom de variable.
    :param candidate_rule: Une liste d'instances JoinableIndexedAttributes représentant la règle candidate.
    :param mapper: Une instance d'AttributeMapper pour la correspondance des attributs.
    :param body: Un ensemble d'occurrences de table représentant le corps de l'EGD.
    :return: Une chaîne représentant les prédicats pour le corps.
    """
    # Initialiser les composants des prédicats
    body_predicates = []  # Pour le corps de l'EGD
    
    # Identifier les attributs qui devraient être dans le corps
    body_attributes = set()
    for pair in candidate_rule:
        for indexed_attr in pair:
            if (indexed_attr.i, indexed_attr.j) in body:
                body_attributes.add(indexed_attr)
    
    # Regrouper par occurrences de table
    attr_by_table_occurrence = {}
    for indexed_attr in body_attributes:
        # Vérifier si l'attribut a une variable assignée
        if indexed_attr not in variable_assignment:
            # Si non, on ne l'inclut pas pour éviter les variables orphelines
            continue
            
        # Convertir IndexedAttribute en Attribute pour une représentation lisible
        attribute = mapper.indexed_attribute_to_attribute(indexed_attr)
        attr_name = attribute.name
        # Utiliser la variable assignée
        variable = variable_assignment[indexed_attr]
        
        table_occurrence = (indexed_attr.i, indexed_attr.j)
        if table_occurrence not in attr_by_table_occurrence:
            attr_by_table_occurrence[table_occurrence] = []
            
        attr_str = f"{attr_name}={variable}"
        if attr_str not in attr_by_table_occurrence[table_occurrence]:
            attr_by_table_occurrence[table_occurrence].append(attr_str)
    
    # Construire les prédicats pour chaque occurrence de table
    for table_occurrence, attr_list in attr_by_table_occurrence.items():
        # Convertir IndexedAttribute en Attribute pour une représentation lisible
        table = mapper.index_to_table_name[table_occurrence[0]]
        attr_list_str = ", ".join(attr_list)
        predicate = f"{table}_{table_occurrence[1]}({attr_list_str})"
        # Ajouter le prédicat au corps
        body_predicates.append(predicate)
    
    # Combiner les composants du prédicat en une chaîne
    body_str = " ∧ ".join(body_predicates)
    return body_str

def construct_egd_string(
    body_predicates: str,
    equality_constraint: str,
    variable_assignment: dict[IndexedAttribute, str]
) -> str:
    """
    Cette fonction construit une représentation en chaîne d'une dépendance générant l'égalité (EGD).
    
    :param body_predicates: Une chaîne représentant les prédicats pour le corps.
    :param equality_constraint: Une chaîne représentant la contrainte d'égalité.
    :param variable_assignment: Un dictionnaire associant chaque IndexedAttribute à un nom de variable.
    :return: Une chaîne représentant l'EGD instanciée.
    """
    # Extraire les variables uniques de variable_assignment
    variables = set(variable_assignment.values())
    
    # Formater les variables pour les inclure dans la chaîne EGD
    variables_str = ", ".join(sorted(variables))
    
    # Construire la chaîne EGD complète
    if variables_str and body_predicates:
        egd_string = f"∀ {variables_str}: {body_predicates} ⇒ {equality_constraint}"
    elif body_predicates:
        egd_string = f"{body_predicates} ⇒ {equality_constraint}"
    else:
        egd_string = f"⊤ ⇒ {equality_constraint}"
    
    return egd_string

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
            flag="egd_prediction",
            disjoint_semantics=APPLY_DISJOINT,
            threshold=threshold,
        ))
    
    return db_inspector.get_join_row_count(
        join_conditions, disjoint_semantics=APPLY_DISJOINT, flag="egd_prediction"
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
    Calcule le support d'une règle candidate EGD.
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
    Calcule la confiance d'une règle candidate EGD.
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
        
    # Le calcul correct de la confiance pour une EGD doit mesurer:
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
        flag="egd_confidence_body", 
        disjoint_semantics=APPLY_DISJOINT, 
        threshold=0
    ):
        return 0
    
    # Nombre de tuples qui satisfont le corps de la règle
    body_tuples_count = db_inspector.get_join_row_count(
        body_conditions, 
        flag="egd_confidence_body", 
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
            flag="egd_confidence_full"
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
            flag="egd_confidence_fallback", 
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

def instantiate_egd_object(candidate_rule, split, mapper, support=1.0, confidence=1.0):
    """
    Crée directement un objet EGDRule à partir d'un candidat et d'un split.
    
    :param candidate_rule: Le candidat de règle (liste de JoinableIndexedAttributes)
    :param split: La division du candidat en corps/tête (body, equality_constraints)
    :param mapper: Le mappeur d'attributs
    :param support: Le support de la règle
    :param confidence: La confiance de la règle
    :return: Un objet EGDRule ou None si l'instanciation échoue
    """
    try:
        from utils.rules import EGDRule
        
        # Extraire le corps et les contraintes d'égalité
        body, equality_constraints = split
                # Créer la liste des variables du corps (body_variables)
        body_variables = set()

        # Obtenir les attributs du corps
        body_tuples = []
        for jia in candidate_rule:
            # Accéder aux attributs via l'interface indexable
            body_pairs=[]
            for attr in jia:  # Parcourir les deux attributs
                if (attr.i, attr.j) in body:
                    attribute = mapper.indexed_attribute_to_attribute(attr)
                    if attribute:
                        body_pairs.append((attribute.table, attr.j, attribute.name))
                if len(body_pairs)==2:
                    body_tuples.append(body_pairs)
        



        # Obtenir les contraintes d'égalité pour la tête de la règle
        head_equalities = []
        eq_var_dict = {}  # Pour collecter les variables associées aux attributs
        
        if isinstance(equality_constraints, tuple):
            # Gérer le cas où equality_constraints est un tuple de tuples
            if equality_constraints and isinstance(equality_constraints[0], tuple):
                for eq_attr1, eq_attr2 in equality_constraints:
                    attr1 = mapper.indexed_attribute_to_attribute(eq_attr1)
                    attr2 = mapper.indexed_attribute_to_attribute(eq_attr2)
                    if attr1 and attr2:
                        head_equalities.append(
                            ((attr1.table, attr1.name, eq_attr1.k),
                             (attr2.table, attr2.name, eq_attr2.k))
                        )
                        # Générer des noms de variables pour ces attributs (pour body_variables)
                        var1_name = f"x{len(eq_var_dict)}"
                        var2_name = f"x{len(eq_var_dict)+1}"
                        eq_var_dict[eq_attr1] = var1_name
                        eq_var_dict[eq_attr2] = var2_name
            
            # Gérer le cas où equality_constraints est un tuple simple (eq_attr1, eq_attr2)
            elif len(equality_constraints) == 2 and isinstance(equality_constraints[0], IndexedAttribute):
                eq_attr1, eq_attr2 = equality_constraints
                attr1 = mapper.indexed_attribute_to_attribute(eq_attr1)
                attr2 = mapper.indexed_attribute_to_attribute(eq_attr2)
                if attr1 and attr2:
                    head_equalities.append(
                        ((attr1.table, attr1.name, eq_attr1.k),
                         (attr2.table, attr2.name, eq_attr2.k))
                    )
                    # Générer des noms de variables pour ces attributs (pour body_variables)
                    var1_name = f"x0"
                    var2_name = f"x1"
                    eq_var_dict[eq_attr1] = var1_name
                    eq_var_dict[eq_attr2] = var2_name
        

        
        # Ajouter également les variables associées aux attributs du corps
        var_counter = len(eq_var_dict)
        for jia in candidate_rule:
            for attr in jia:
                if (attr.i, attr.j) in body and attr not in eq_var_dict:
                    var_name = f"x{var_counter}"
                    eq_var_dict[attr] = var_name
                    body_variables.add(var_name)
                    var_counter += 1
        
        # Extraire les head_variables (paires de variables égales)
        head_variables = []
        for eq_attr1, eq_attr2 in equality_constraints:
            if isinstance(eq_attr1, IndexedAttribute) and isinstance(eq_attr2, IndexedAttribute):
                var1 = eq_var_dict.get(eq_attr1)
                var2 = eq_var_dict.get(eq_attr2)
                if var1 and var2:
                    head_variables.append((var1, var2))
        
        # Générer la représentation textuelle de la règle
        display = instantiate_egd(candidate_rule, split, mapper)
        
        if body_tuples and head_equalities:
            # Créer l'objet EGDRule avec les nouveaux attributs

            # Créer l'objet EGDRule avec tous les attributs nécessaires
            return EGDRule(
                body=body_tuples,  # Remplacer par les vrais prédicats si nécessaire
                head=tuple(head_equalities),  # Remplacer par les vrais prédicats si nécessaire
                display=display,
                accuracy=support,
                support=support,
                confidence=confidence,
                head_variables=tuple(head_variables),
                body_variables=tuple(sorted(body_variables))
            )
        else:
            return None
                
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(f"Error instantiating EGD object: {e}")
        return None



