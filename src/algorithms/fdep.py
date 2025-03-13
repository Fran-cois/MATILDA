# algorithms/fdep.py

import os
import logging
import pandas as pd
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Generator
from itertools import combinations

from algorithms.base_algorithm import BaseAlgorithm
from utils.rules import FunctionalDependency, Rule


class FDep(BaseAlgorithm):
    """
    Implémentation de l'algorithme FDep pour la découverte de dépendances fonctionnelles.
    
    FDep est un algorithme qui utilise une approche par niveau (levelwise) pour découvrir des 
    dépendances fonctionnelles minimales dans une base de données relationnelle. Il est basé 
    sur l'article "FD_Mine: Discovering Functional Dependencies in a Database by Detecting the Differences"
    par Flach et Savnik.
    """

    def discover_rules(self, **kwargs) -> Generator[Rule, None, None]:
        """
        Découvre les dépendances fonctionnelles à l'aide de l'algorithme FDep.
        """
        logging.info("Lancement de l'algorithme FDep")
        max_lhs_size = kwargs.get('max_lhs_size', 3)  # Limite la taille des déterminants
        
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
                    
                    # Découvrir les dépendances fonctionnelles avec FDep
                    discovered_fds = self._discover_fds_fdep(df, table_name, max_lhs_size)
                    
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
                                yield fd
                        except Exception as e:
                            logging.error(f"Erreur lors de la création de la dépendance: {str(e)}")
                    
                    logging.info(f"Découvert {len(discovered_fds)} dépendances pour {table_name}")
                    
                except Exception as e:
                    logging.error(f"Erreur lors de l'analyse de {csv_file}: {str(e)}")
                    continue
                    
        except Exception as e:
            logging.error(f"Erreur lors de la découverte des dépendances: {str(e)}")

    def _discover_fds_fdep(self, df: pd.DataFrame, table_name: str, max_lhs_size: int = 3) -> List[Tuple[tuple, tuple]]:
        """
        Implémentation de l'algorithme FDep pour découvrir des dépendances fonctionnelles.
        
        :param df: DataFrame pandas contenant les données
        :param table_name: Nom de la table
        :param max_lhs_size: Taille maximale des déterminants (partie gauche)
        :return: Liste de tuples (determinant, dependant) où determinant et dependant sont des tuples de noms d'attributs
        """
        results = []
        columns = list(df.columns)
        n = len(columns)
        
        logging.info(f"Exécution de FDep sur {table_name} avec {n} colonnes et max_lhs_size={max_lhs_size}")
        
        # Phase 1: Calculer les agree sets pour chaque paire de tuples
        agree_sets = self._compute_agree_sets(df)
        
        # Phase 2: Calculer les difference sets (complémentaire des agree sets)
        diff_sets = self._compute_difference_sets(agree_sets, columns)
        
        # Phase 3: Pour chaque attribut, trouver les dépendances fonctionnelles minimales
        for target_col in columns:
            deps = self._find_dependencies_for_target(diff_sets, columns, target_col, max_lhs_size)
            
            # Ajouter les dépendances trouvées aux résultats
            for dep in deps:
                determinant = tuple(dep)
                results.append((determinant, (target_col,)))
                logging.info(f"Dépendance trouvée: {determinant} -> {target_col}")
        
        return results
    
    def _compute_agree_sets(self, df: pd.DataFrame) -> Dict[Tuple[int, int], Set[str]]:
        """
        Calcule les agree sets pour chaque paire de tuples.
        Un agree set contient les attributs pour lesquels deux tuples ont la même valeur.
        
        :param df: DataFrame pandas contenant les données
        :return: Dictionnaire indexant les agree sets par paires de tuples
        """
        agree_sets = {}
        columns = list(df.columns)
        n_rows = len(df)
        
        logging.info(f"Calcul des agree sets pour {n_rows} tuples")
        
        # Pour chaque paire de tuples distincte
        for i in range(n_rows):
            for j in range(i + 1, n_rows):
                agree_set = set()
                
                # Trouver les colonnes où les deux tuples ont la même valeur
                for col in columns:
                    val_i = df.iloc[i][col]
                    val_j = df.iloc[j][col]
                    
                    # Vérifier l'égalité (en tenant compte des valeurs NaN)
                    if pd.isna(val_i) and pd.isna(val_j):
                        agree_set.add(col)
                    elif not pd.isna(val_i) and not pd.isna(val_j) and val_i == val_j:
                        agree_set.add(col)
                
                # Stocker l'agree set pour cette paire de tuples
                agree_sets[(i, j)] = agree_set
        
        return agree_sets
    
    def _compute_difference_sets(self, agree_sets: Dict[Tuple[int, int], Set[str]], 
                               columns: List[str]) -> Dict[Tuple[int, int], Set[str]]:
        """
        Calcule les difference sets (complémentaire des agree sets).
        
        :param agree_sets: Dictionnaire des agree sets par paire de tuples
        :param columns: Liste des noms de colonnes
        :return: Dictionnaire des difference sets par paire de tuples
        """
        all_columns = set(columns)
        diff_sets = {}
        
        for pair, agree_set in agree_sets.items():
            # Le difference set est le complément de l'agree set
            diff_sets[pair] = all_columns - agree_set
        
        return diff_sets
    
    def _find_dependencies_for_target(self, diff_sets: Dict[Tuple[int, int], Set[str]],
                                    columns: List[str], target: str, 
                                    max_lhs_size: int) -> List[Set[str]]:
        """
        Trouve les dépendances fonctionnelles minimales pour un attribut cible.
        
        :param diff_sets: Dictionnaire des difference sets par paire de tuples
        :param columns: Liste des noms de colonnes
        :param target: Nom de la colonne cible (partie droite de la dépendance)
        :param max_lhs_size: Taille maximale des déterminants (partie gauche)
        :return: Liste des déterminants minimaux pour la colonne cible
        """
        # Tous les attributs sauf la cible
        attributes = [col for col in columns if col != target]
        
        # Collecter les paires de tuples où la valeur de l'attribut cible diffère
        relevant_pairs = []
        for pair, diff_set in diff_sets.items():
            if target in diff_set:
                relevant_pairs.append(pair)
        
        if not relevant_pairs:
            # Si aucune paire n'a de différence sur l'attribut cible,
            # alors l'attribut cible est constant (ou toutes les paires avec des
            # valeurs différentes ont aussi des différences sur tous les autres attributs)
            return []
        
        # Initialiser les dépendances candidates avec des ensembles de taille 1
        current_level = [{attr} for attr in attributes]
        minimal_dependencies = []
        
        # Approche par niveau (levelwise)
        for level in range(1, max_lhs_size + 1):
            next_level = []
            
            # Pour chaque ensemble candidat de ce niveau
            for candidate in current_level:
                # Vérifier s'il s'agit d'un déterminant pour la cible
                if self._is_determinant(candidate, target, relevant_pairs, diff_sets):
                    # Vérifier si c'est un déterminant minimal
                    if self._is_minimal_determinant(candidate, minimal_dependencies):
                        minimal_dependencies.append(candidate)
                else:
                    # Si ce n'est pas un déterminant, générer les candidats du niveau suivant
                    if level < max_lhs_size:
                        for attr in attributes:
                            if attr not in candidate:
                                new_candidate = candidate.union({attr})
                                # Vérifier si tous les sous-ensembles de taille level sont dans current_level
                                if level == 1 or all(frozenset(c) in [frozenset(cand) for cand in current_level] 
                                                    for c in combinations(new_candidate, level)):
                                    next_level.append(new_candidate)
            
            if not next_level or level == max_lhs_size:
                break
                
            current_level = next_level
        
        return minimal_dependencies
    
    def _is_determinant(self, attributes: Set[str], target: str, 
                      relevant_pairs: List[Tuple[int, int]], 
                      diff_sets: Dict[Tuple[int, int], Set[str]]) -> bool:
        """
        Vérifie si un ensemble d'attributs est un déterminant pour une colonne cible.
        
        :param attributes: Ensemble d'attributs candidat
        :param target: Colonne cible
        :param relevant_pairs: Paires de tuples où la valeur de la cible diffère
        :param diff_sets: Dictionnaire des difference sets
        :return: True si c'est un déterminant, False sinon
        """
        # Pour être un déterminant, l'ensemble d'attributs doit avoir au moins
        # un attribut qui diffère dans chaque paire où la cible diffère
        for pair in relevant_pairs:
            if not any(attr in diff_sets[pair] for attr in attributes):
                return False
        
        return True
    
    def _is_minimal_determinant(self, candidate: Set[str], 
                              minimal_dependencies: List[Set[str]]) -> bool:
        """
        Vérifie si un déterminant candidat est minimal.
        
        :param candidate: Ensemble d'attributs candidat
        :param minimal_dependencies: Liste des déterminants minimaux déjà trouvés
        :return: True si le candidat est minimal, False sinon
        """
        # Un déterminant est minimal si aucun de ses sous-ensembles n'est déjà un déterminant
        # et s'il n'est pas un sur-ensemble d'un déterminant minimal déjà trouvé
        for dep in minimal_dependencies:
            if dep.issubset(candidate):
                return False
        
        return True
