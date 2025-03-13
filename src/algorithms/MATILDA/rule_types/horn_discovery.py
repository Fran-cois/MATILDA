"""
Module pour la découverte des règles de Horn dans MATILDA.
Une règle de Horn est une clause disjonctive avec au plus un littéral positif,
souvent représentée sous la forme (p1 ∧ p2 ∧ ... ∧ pn → q).
"""

import logging
import time
import os
from typing import List, Dict, Set, Tuple, Any, Optional, Union
import itertools
import copy
import numpy as np
import pandas as pd
from sqlalchemy import select, and_, func, or_, not_

from database.alchemy_utility import AlchemyUtility
from algorithms.MATILDA.constraint_graph import (
    Attribute, AttributeMapper, IndexedAttribute, JoinableIndexedAttributes, ConstraintGraph
)
from algorithms.MATILDA.discovery_algorithms.common import CandidateRule, TableOccurrence, extract_table_occurrences

logger = logging.getLogger(__name__)

def init(db_inspector: AlchemyUtility, max_nb_occurrence: int = 3, results_path: str = None) -> Tuple[ConstraintGraph, AttributeMapper, List[JoinableIndexedAttributes]]:
    """
    Initialise le graphe de contraintes et le mappage d'attributs pour la découverte de règles de Horn.
    
    :param db_inspector: Inspecteur de base de données
    :param max_nb_occurrence: Nombre maximum d'occurrences de table
    :param results_path: Chemin pour sauvegarder les résultats intermédiaires
    :return: Tuple contenant le graphe de contraintes, le mappeur d'attributs et la liste des attributs indexés joinables
    """
    logger.info("Initialisation pour la découverte de règles de Horn...")
    
    # Récupération des tables et métadonnées
    tables = db_inspector.get_tables()
    metadata = db_inspector.get_metadata()
    
    # Création du mappeur d'attributs
    mapper = AttributeMapper()
    
    # Construction du graphe de contraintes
    constraint_graph = ConstraintGraph()
    
    # Liste pour stocker les attributs indexés joinables
    jia_list = []
    
    # Pour les règles de Horn, nous nous intéressons particulièrement aux attributs booléens et catégoriels
    # car ils peuvent être naturellement représentés comme des littéraux dans les clauses de Horn
    
    # Traitement de chaque table
    for table in tables:
        # Création des nœuds pour chaque colonne de la table
        columns = db_inspector.get_columns(table)
        for col in columns:
            indexed_attr = mapper.get_indexed_attribute(table, col)
            constraint_graph.add_node(indexed_attr)
            
            # Pour les règles de Horn, nous pourrions donner une priorité plus élevée 
            # aux colonnes booléennes ou à faible cardinalité
            col_info = db_inspector.get_column_info(table, col)
            col_type = str(col_info.get('type', '')).lower()
            
            # On peut ajouter des métadonnées aux nœuds pour les utiliser plus tard
            if 'bool' in col_type:
                constraint_graph.add_node_attribute(indexed_attr, 'is_boolean', True)
            else:
                constraint_graph.add_node_attribute(indexed_attr, 'is_boolean', False)
    
    # Établir les relations entre les attributs
    for table1 in tables:
        columns1 = db_inspector.get_columns(table1)
        
        # Ajouter des arêtes entre les colonnes de la même table
        for i, col1 in enumerate(columns1):
            for j, col2 in enumerate(columns1):
                if i != j:
                    attr1 = mapper.get_indexed_attribute(table1, col1)
                    attr2 = mapper.get_indexed_attribute(table1, col2)
                    # Poids standard pour les relations intra-table
                    constraint_graph.add_edge(attr1, attr2, weight=0.8)
                    
                    # Ajouter aux attributs joinables
                    jia_pair = JoinableIndexedAttributes(attr1, attr2)
                    jia_list.append(jia_pair)
        
        # Récupérer les relations de clé étrangère
        fks = db_inspector.get_foreign_keys(table1)
        for fk in fks:
            ref_table = fk['referred_table']
            for i, col in enumerate(fk['constrained_columns']):
                ref_col = fk['referred_columns'][i]
                
                # Créer les attributs indexés
                attr1 = mapper.get_indexed_attribute(table1, col)
                attr2 = mapper.get_indexed_attribute(ref_table, ref_col)
                
                # Ajouter les relations au graphe
                constraint_graph.add_edge(attr1, attr2, weight=0.9)
                
                # Ajouter les attributs joinables
                jia_pair = JoinableIndexedAttributes(attr1, attr2)
                jia_list.append(jia_pair)
                
        # Pour les règles de Horn, on peut également chercher des relations sémantiques
        # basées sur les noms des colonnes et leur contenu
        for table2 in tables:
            if table1 == table2:
                continue
                
            columns2 = db_inspector.get_columns(table2)
            
            for col1 in columns1:
                for col2 in columns2:
                    # Vérifier la similarité des noms et des types
                    column_info1 = db_inspector.get_column_info(table1, col1)
                    column_info2 = db_inspector.get_column_info(table2, col2)
                    
                    # Vérifier les correspondances potentielles
                    name_similarity = 0.0
                    if col1.lower() == col2.lower():
                        name_similarity = 1.0
                    elif col1.lower() in col2.lower() or col2.lower() in col1.lower():
                        name_similarity = 0.6
                        
                    # Vérifier la compatibilité des types
                    type_match = 0.0
                    if str(column_info1['type']) == str(column_info2['type']):
                        type_match = 1.0
                    
                    # Combiner les deux scores
                    combined_score = (name_similarity * 0.7 + type_match * 0.3) * 0.7
                    
                    if combined_score > 0.3:  # Seuil minimal pour établir une relation
                        attr1 = mapper.get_indexed_attribute(table1, col1)
                        attr2 = mapper.get_indexed_attribute(table2, col2)
                        
                        constraint_graph.add_edge(attr1, attr2, weight=combined_score)
                        
                        # Ajouter aux attributs joinables
                        jia_pair = JoinableIndexedAttributes(attr1, attr2)
                        jia_list.append(jia_pair)
    
    logger.info(f"Graphe de contraintes créé avec {constraint_graph.number_of_nodes()} nœuds et {constraint_graph.number_of_edges()} arêtes")
    logger.info(f"Liste JIA contient {len(jia_list)} paires d'attributs")
    
    return constraint_graph, mapper, jia_list

def path_pruning(candidate_rule: CandidateRule, 
                db_inspector: AlchemyUtility, 
                mapper: AttributeMapper,
                compatibility_mode: str = None,
                compatibility_checker: Any = None,
                **kwargs) -> bool:
    """
    Détermine si un chemin candidat doit être élagué pour les règles de Horn.
    
    :param candidate_rule: Règle candidate à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param compatibility_mode: Mode de vérification de la compatibilité
    :param compatibility_checker: Vérificateur de compatibilité
    :return: True si le chemin doit être poursuivi, False sinon
    """
    # Vérifier si nous avons au moins deux attributs (pour former une règle de Horn)
    if len(candidate_rule.indexed_attributes) < 2:
        return True
    
    # Extraire les occurrences de tables
    table_occurrences = extract_table_occurrences(candidate_rule.indexed_attributes)
    
    # Pour les règles de Horn, limitons à un nombre raisonnable de tables
    if len(table_occurrences) > 4:  # Limiter à 4 tables maximum
        return False
    
    # Vérifier la compatibilité des attributs pour les règles de Horn
    attrs = candidate_rule.indexed_attributes
    
    # Vérifier si les attributs sont compatibles entre eux
    if compatibility_checker:
        # Pour les règles de Horn, on se concentre surtout sur les attributs
        # qui peuvent être liés sémantiquement
        for i in range(len(attrs)):
            for j in range(i+1, len(attrs)):
                table1 = attrs[i].base_attribute.table_name
                col1 = attrs[i].base_attribute.column_name
                table2 = attrs[j].base_attribute.table_name
                col2 = attrs[j].base_attribute.column_name
                
                # Vérifier la compatibilité pour les attributs de tables différentes
                if table1 != table2:
                    if not compatibility_checker.is_compatible(
                        table1, col1, table2, col2,
                        mode=compatibility_mode,
                        sample_size=100
                    ):
                        return False
    
    # Heuristique spécifique aux règles de Horn : 
    # Préférer les attributs booléens ou à faible cardinalité
    boolean_attrs = 0
    low_cardinality_attrs = 0
    
    for attr in attrs:
        table_name = attr.base_attribute.table_name
        col_name = attr.base_attribute.column_name
        col_info = db_inspector.get_column_info(table_name, col_name)
        col_type = str(col_info.get('type', '')).lower()
        
        if 'bool' in col_type:
            boolean_attrs += 1
        
        # Vérifier la cardinalité si possible
        try:
            table_obj = db_inspector.get_table_object(table_name)
            column_obj = getattr(table_obj.c, col_name)
            query = select([func.count(func.distinct(column_obj))]).limit(1)
            result = db_inspector.get_engine().execute(query).fetchone()
            if result and result[0] < 10:  # Seuil arbitraire pour la "faible cardinalité"
                low_cardinality_attrs += 1
        except Exception:
            # Si impossible de déterminer la cardinalité, on continue sans modifier le score
            pass
    
    # Si aucun attribut booléen ou à faible cardinalité, on peut pénaliser ce chemin
    if boolean_attrs == 0 and low_cardinality_attrs == 0 and len(attrs) > 3:
        return False
    
    # Si tous les tests sont passés, continuer l'exploration
    return True

def split_candidate_rule(candidate_rule: CandidateRule) -> List[Tuple[List[int], List[int]]]:
    """
    Divise une règle candidate en parties gauche et droite pour former des règles de Horn.
    Pour les règles de Horn, nous cherchons à avoir une partie droite (tête) avec un seul littéral positif.
    
    :param candidate_rule: La règle candidate à diviser
    :return: Liste de tuples (corps, tête) où corps et tête sont des listes d'indices d'attributs
    """
    results = []
    n = len(candidate_rule.indexed_attributes)
    
    if n < 2:
        return results
    
    # Pour chaque attribut comme tête potentielle (un seul littéral positif)
    for head_idx in range(n):
        # Tous les autres attributs forment le corps
        body_indices = [i for i in range(n) if i != head_idx]
        results.append((body_indices, [head_idx]))
    
    return results

def split_pruning(candidate_rule: CandidateRule, 
                 body_indices: List[int], 
                 head_indices: List[int], 
                 db_inspector: AlchemyUtility, 
                 mapper: AttributeMapper) -> Tuple[bool, float, float]:
    """
    Évalue si une division en corps/tête forme une règle de Horn valide.
    
    :param candidate_rule: Règle candidate
    :param body_indices: Indices des attributs du corps
    :param head_indices: Indices des attributs de la tête
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :return: Tuple (est_valide, support, confiance)
    """
    # Récupérer les attributs du corps et de la tête
    body_attrs = [candidate_rule.indexed_attributes[i] for i in body_indices]
    head_attrs = [candidate_rule.indexed_attributes[i] for i in head_indices]
    
    if not body_attrs or not head_attrs or len(head_attrs) != 1:
        return False, 0.0, 0.0
    
    try:
        # Construire les tables et colonnes pour l'extraction de données
        tables = {}
        for attr in body_attrs + head_attrs:
            table_name = attr.base_attribute.table_name
            if table_name not in tables:
                tables[table_name] = []
            
            tables[table_name].append(attr.base_attribute.column_name)
        
        # Collecter les données
        data = {}
        for table_name, columns in tables.items():
            table_obj = db_inspector.get_table_object(table_name)
            query = select([getattr(table_obj.c, col) for col in columns]).limit(1000)
            result = db_inspector.get_engine().execute(query)
            
            data[table_name] = pd.DataFrame(result.fetchall(), columns=columns)
        
        # Si plusieurs tables, nous devons les joindre
        if len(tables) > 1:
            # Dans une implémentation réelle, on devrait implémenter la logique de jointure
            # Cette partie est simplifiée pour l'exemple
            df = list(data.values())[0]
        else:
            df = list(data.values())[0]
        
        # Préparer les noms de colonnes pour le corps et la tête
        body_columns = [attr.base_attribute.column_name for attr in body_attrs]
        head_column = head_attrs[0].base_attribute.column_name
        
        # Pour les règles de Horn, nous voulons vérifier:
        # 1. Si body_columns sont tous True/1, est-ce que head_column est aussi True/1?
        # 2. Convertir toutes les colonnes en booléennes pour cette évaluation
        
        # Convertir en booléens (simplification)
        df_bool = df.copy()
        for col in body_columns + [head_column]:
            # Conversion simple: tout ce qui est non-nul ou non-zéro est True
            df_bool[col] = df_bool[col].fillna(False).astype(bool)
        
        # Vérifier la règle de Horn: si tous les prédicats du corps sont vrais,
        # alors le prédicat de la tête doit être vrai
        
        # Compter les cas où tous les prédicats du corps sont vrais
        body_all_true = df_bool[body_columns].all(axis=1)
        body_count = body_all_true.sum()
        
        # Parmi ces cas, compter ceux où la tête est vraie
        rule_satisfied = (body_all_true & df_bool[head_column])
        rule_count = rule_satisfied.sum()
        
        # Total des lignes de données
        total_rows = len(df_bool)
        
        # Calculer le support et la confiance
        support = body_count / total_rows if total_rows > 0 else 0
        confidence = rule_count / body_count if body_count > 0 else 0
        
        # La règle est valide si elle a un support et une confiance minimaux
        is_valid = support > 0.1 and confidence > 0.5  # Seuils arbitraires
        
        return is_valid, support, confidence
        
    except Exception as e:
        logger.exception(f"Erreur lors de l'évaluation de la règle de Horn: {e}")
        return False, 0.0, 0.0

def instantiate_horn(candidate_rule: CandidateRule, 
                    split: Tuple[List[int], List[int]], 
                    mapper: AttributeMapper) -> str:
    """
    Crée une chaîne de caractères représentant la règle de Horn.
    
    :param candidate_rule: Règle candidate
    :param split: Tuple (corps_indices, tête_indices)
    :param mapper: Mappeur d'attributs
    :return: Chaîne représentant la règle de Horn
    """
    body_indices, head_indices = split
    
    # Récupérer les attributs du corps et de la tête
    body_attrs = [candidate_rule.indexed_attributes[i] for i in body_indices]
    head_attrs = [candidate_rule.indexed_attributes[i] for i in head_indices]
    
    if not body_attrs or not head_attrs:
        return ""
    
    # Formater les attributs pour affichage
    format_attr = lambda attr: f"{attr.base_attribute.table_name}.{attr.base_attribute.column_name}"
    
    # Si le corps est vide, utiliser le symbole ⊤ (top/true)
    if not body_attrs:
        body_str = "⊤"
    else:
        body_str = " ∧ ".join(format_attr(attr) for attr in body_attrs)
    
    head_str = " ∨ ".join(format_attr(attr) for attr in head_attrs)
    
    # Formater la règle complète: p1 ∧ p2 ∧ ... → q
    horn_str = f"{body_str} → {head_str}"
    
    return horn_str

def instantiate_horn_object(candidate_rule, split, mapper, support=1.0, confidence=1.0):
    """
    Crée directement un objet HornRule à partir d'un candidat et d'un split.
    
    :param candidate_rule: Le candidat de règle (liste de JoinableIndexedAttributes)
    :param split: La division du candidat en corps/tête (body_indices, head_indices)
    :param mapper: Le mappeur d'attributs
    :param support: Le support de la règle
    :param confidence: La confiance de la règle
    :return: Un objet HornRule ou None si l'instanciation échoue
    """
    try:
        from utils.rules import HornRule
        
        if HornRule is None:
            import logging
            logging.getLogger(__name__).error("HornRule class not available")
            return None
        
        body_indices, head_indices = split
        
        # Structure pour stocker les attributs avec leurs variables
        all_attrs = []
        
        # Collecter tous les attributs du candidat en accédant correctement aux propriétés
        for i, jia in enumerate(candidate_rule):
            # Accéder aux attributs via l'indexation
            attr1 = jia[0]
            attr2 = jia[1]
            
            for j, attr in enumerate([attr1, attr2]):
                attribute = mapper.indexed_attribute_to_attribute(attr)
                if attribute:
                    all_attrs.append((i, j, attribute.table, attribute.name, attr.variable))
        
        # Extraire les attributs du corps et de la tête
        body_attributes = []
        for idx in body_indices:
            if idx < len(all_attrs):
                i, j, table, name, variable = all_attrs[idx]
                body_attributes.append((table, name, variable))
        
        head_attributes = []
        for idx in head_indices:
            if idx < len(all_attrs):
                i, j, table, name, variable = all_attrs[idx]
                head_attributes.append((table, name, variable))
        
        return HornRule(body=body_attributes, head=head_attributes, support=support, confidence=confidence)
                
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(f"Error instantiating Horn rule object: {e}")
        return None
