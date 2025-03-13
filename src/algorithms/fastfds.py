# algorithms/fastfds.py

import os
import logging
import pandas as pd
import itertools
from collections import defaultdict, namedtuple
from typing import Dict, List, Set, Tuple, Generator

from algorithms.base_algorithm import BaseAlgorithm
from utils.rules import FunctionalDependency, Rule


class FastFDs(BaseAlgorithm):
    """
    Implémentation de l'algorithme FastFDs pour la découverte de dépendances fonctionnelles.
    Cette implémentation est basée sur l'article "Discovering Functional Dependencies in Relational Databases"
    par Huhtala et al.
    """

    def discover_rules(self, **kwargs) -> Generator[Rule, None, None]:
        """
        Découvre les dépendances fonctionnelles à l'aide de l'algorithme FastFDs.
        """
        rules = {}
        logging.info("Lancement de l'algorithme FastFDs")
        
        try:
            csv_files = [
                os.path.join(self.database.base_csv_dir, f)
                for f in os.listdir(self.database.base_csv_dir)
                if f.endswith('.csv')
            ]
            
            logging.info(f"Fichiers CSV trouvés: {len(csv_files)}")
            
            # Pour chaque fichier CSV, découvrir les dépendances fonctionnelles
            for csv_file in csv_files:
                table_name = os.path.basename(csv_file).replace('.csv', '')
                logging.info(f"Analyse du fichier: {csv_file} (table: {table_name})")
                
                # Lire le fichier CSV avec pandas
                try:
                    df = pd.read_csv(csv_file)
                    if len(df.columns) <= 1:
                        logging.warning(f"Table {table_name} a moins de 2 colonnes. Ignorée.")
                        continue
                        
                    logging.info(f"Table {table_name}: {len(df)} lignes, {len(df.columns)} colonnes")
                    
                    # Découvrir les dépendances fonctionnelles avec FastFDs
                    discovered_fds = self._discover_fds_fastfds(df, table_name)
                    
                    # Ajouter les dépendances fonctionnelles découvertes
                    for determinant, dependant in discovered_fds:
                        try:
                            # Créer une dépendance fonctionnelle
                            fd = None
                            try:
                                # Version avec table_dependant, columns_dependant, etc.
                                fd = FunctionalDependency(
                                    table_dependant=table_name,
                                    columns_dependant=determinant,
                                    table_referenced=table_name,
                                    columns_referenced=dependant
                                )
                            except TypeError:
                                # Version simplifiée avec des arguments de base
                                fd = FunctionalDependency(table_name, determinant, dependant)
                            
                            if fd:
                                rules[fd] = (1, 1)  # Confiance et support à 1 pour les dépendances exactes
                                yield fd
                                logging.info(f"Dépendance: {table_name}.{determinant} -> {table_name}.{dependant}")
                        except Exception as e:
                            logging.error(f"Erreur lors de la création de la dépendance: {str(e)}")
                    
                    logging.info(f"Découvert {len(discovered_fds)} dépendances pour {table_name}")
                    
                except Exception as e:
                    logging.error(f"Erreur lors de l'analyse de {csv_file}: {str(e)}")
                    continue
                    
        except Exception as e:
            logging.error(f"Erreur lors de la découverte des dépendances: {str(e)}")
            
        return rules

    def _discover_fds_fastfds(self, df: pd.DataFrame, table_name: str) -> List[Tuple[tuple, tuple]]:
        """
        Implémentation de l'algorithme FastFDs pour découvrir des dépendances fonctionnelles.
        
        :param df: DataFrame pandas contenant les données
        :param table_name: Nom de la table
        :return: Liste de tuples (determinant, dependant) où determinant et dependant sont des tuples de noms d'attributs
        """
        results = []
        columns = list(df.columns)
        n = len(columns)
        
        logging.info(f"Exécution de FastFDs sur {table_name} avec {n} colonnes")
        
        # Phase 1: Calculer les partitions des attributs
        partitions = {}
        for col in columns:
            partitions[col] = self._compute_partition(df, col)
        
        # Phase 2: Pour chaque attribut cible, trouver les déterminants minimaux
        for target_col in columns:
            logging.info(f"Recherche des déterminants pour {target_col}")
            determinants = self._find_minimal_determinants(df, columns, target_col, partitions)
            
            for determinant in determinants:
                if determinant:  # Éviter les déterminants vides
                    determinant_tuple = tuple(determinant)
                    results.append((determinant_tuple, (target_col,)))
                    logging.info(f"Dépendance trouvée: {determinant_tuple} -> {target_col}")
        
        return results
        
    def _compute_partition(self, df: pd.DataFrame, column: str) -> Dict:
        """
        Calcule la partition d'un attribut (équivalence classes).
        
        :param df: DataFrame pandas contenant les données
        :param column: Nom de la colonne
        :return: Dictionnaire où les clés sont les valeurs distinctes et les valeurs sont les indices des lignes
        """
        partition = defaultdict(list)
        for idx, value in enumerate(df[column]):
            # Gérer les valeurs None/NaN en les convertissant en chaîne spéciale
            if pd.isna(value):
                partition["__NULL__"].append(idx)
            else:
                partition[value].append(idx)
        return partition
    
    def _find_minimal_determinants(self, df: pd.DataFrame, columns: List[str], target: str, partitions: Dict) -> List[Set[str]]:
        """
        Trouve les déterminants minimaux pour un attribut cible.
        
        :param df: DataFrame pandas contenant les données
        :param columns: Liste des noms de colonnes
        :param target: Colonne cible
        :param partitions: Partitions pré-calculées des attributs
        :return: Liste des déterminants minimaux (chaque déterminant est un ensemble d'attributs)
        """
        # Exclure la colonne cible des attributs candidats
        candidates = [c for c in columns if c != target]
        target_partition = partitions[target]
        
        if not self._has_non_trivial_partitions(target_partition):
            # Si la partition cible est triviale (tous les éléments sont distincts), pas de dépendance
            return []
        
        # Initialiser la liste des déterminants minimaux
        minimal_determinants = []
        
        # Structure pour suivre les ensembles d'échec pour chaque paire d'enregistrements incompatibles
        FailSet = namedtuple('FailSet', ['i', 'j', 'attrs'])
        fail_sets = []
        
        # Trouver les paires d'enregistrements qui ont la même valeur pour target
        # mais des valeurs différentes pour certains autres attributs
        for value, indices in target_partition.items():
            if len(indices) > 1:  # Si plusieurs enregistrements ont la même valeur target
                # Pour chaque paire d'indices dans ce groupe
                for i, j in itertools.combinations(indices, 2):
                    # Trouver les attributs qui distinguent ces deux enregistrements
                    diff_attrs = set()
                    for attr in candidates:
                        if df.iloc[i][attr] != df.iloc[j][attr]:
                            diff_attrs.add(attr)
                    
                    if diff_attrs:  # S'il y a des attributs qui distinguent ces enregistrements
                        fail_sets.append(FailSet(i, j, diff_attrs))
        
        # Si aucun ensemble d'échec, la colonne cible dépend fonctionnellement de l'ensemble vide
        if not fail_sets:
            return []
        
        # Utiliser l'algorithme de couverture d'ensemble pour trouver les déterminants minimaux
        while fail_sets:
            # Choisir l'attribut qui apparaît dans le plus grand nombre d'ensembles d'échec
            attr_counts = defaultdict(int)
            for fail_set in fail_sets:
                for attr in fail_set.attrs:
                    attr_counts[attr] += 1
            
            if not attr_counts:  # Si aucun attribut ne reste, sortir
                break
                
            # Choisir l'attribut avec le plus grand nombre d'occurrences
            chosen_attr = max(attr_counts.items(), key=lambda x: x[1])[0]
            
            # Créer un nouveau déterminant avec cet attribut
            new_determinant = {chosen_attr}
            minimal_determinants.append(new_determinant)
            
            # Supprimer les ensembles d'échec qui sont couverts par cet attribut
            fail_sets = [fs for fs in fail_sets if chosen_attr not in fs.attrs]
        
        return minimal_determinants

    def _has_non_trivial_partitions(self, partition: Dict) -> bool:
        """
        Vérifie si une partition contient des classes d'équivalence non triviales.
        
        :param partition: Dictionnaire de partition
        :return: True si au moins une classe contient plus d'un élément
        """
        return any(len(indices) > 1 for indices in partition.values())
