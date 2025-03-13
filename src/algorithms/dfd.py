# algorithms/dfd.py

import os
import logging
import pandas as pd
import time
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Generator, FrozenSet
import random

from algorithms.base_algorithm import BaseAlgorithm
from utils.rules import FunctionalDependency, Rule


class DFD(BaseAlgorithm):
    """
    Implémentation de l'algorithme DFD (Depth-First Discovery) pour la découverte de dépendances fonctionnelles.
    
    DFD utilise une stratégie de parcours en profondeur d'abord pour découvrir des dépendances
    fonctionnelles minimales de manière efficace. Cette approche permet souvent de trouver rapidement
    des dépendances sans avoir à explorer exhaustivement l'espace de recherche.
    """

    def discover_rules(self, **kwargs) -> Generator[Rule, None, None]:
        """
        Découvre les dépendances fonctionnelles à l'aide de l'algorithme DFD.
        """
        logging.info("Lancement de l'algorithme DFD (Depth-First Discovery)")
        
        # Paramètres de l'algorithme
        max_lhs_size = kwargs.get('max_lhs_size', 3)  # Taille maximale du déterminant
        time_limit = kwargs.get('time_limit', 600)    # Limite de temps en secondes (10 minutes par défaut)
        sample_size = kwargs.get('sample_size', None) # Taille de l'échantillon (None = utiliser toutes les données)
        min_conf = kwargs.get('min_confidence', 0.9)  # Confiance minimale pour les dépendances approximatives
        
        start_time = time.time()
        
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
                    # Chargement des données avec échantillonnage optionnel
                    if sample_size and sample_size > 0:
                        df_full = pd.read_csv(csv_file)
                        if len(df_full) > sample_size:
                            df = df_full.sample(n=sample_size, random_state=42)
                            logging.info(f"Échantillonnage de {sample_size} lignes sur {len(df_full)}")
                        else:
                            df = df_full
                    else:
                        df = pd.read_csv(csv_file)
                    
                    if len(df.columns) <= 1:
                        logging.warning(f"Table {table_name} a moins de 2 colonnes. Ignorée.")
                        continue
                        
                    logging.info(f"Table {table_name}: {len(df)} lignes, {len(df.columns)} colonnes")
                    
                    # Calculer les partitions d'attributs pour une recherche efficace
                    partitions = self._compute_partitions(df)
                    
                    # Découvrir les dépendances fonctionnelles avec DFD
                    for target_col in df.columns:
                        discovered_fds = self._depth_first_discovery(
                            df, 
                            partitions,
                            target_col,
                            max_lhs_size, 
                            start_time,
                            time_limit,
                            min_conf
                        )
                        
                        # Yield chaque dépendance fonctionnelle découverte
                        for determinant, confidence in discovered_fds:
                            det_tuple = tuple(sorted(determinant))
                            
                            # Créer une dépendance fonctionnelle
                            try:
                                fd = None
                                try:
                                    # Version avec table_dependant, etc.
                                    fd = FunctionalDependency(
                                        table_dependant=table_name,
                                        columns_dependant=det_tuple,
                                        table_referenced=table_name,
                                        columns_referenced=(target_col,)
                                    )
                                except TypeError:
                                    # Version simplifiée
                                    fd = FunctionalDependency(table_name, det_tuple, (target_col,))
                                
                                if fd:
                                    # Au lieu d'essayer de modifier l'objet directement,
                                    # stockons la confiance dans le dictionnaire que nous retournons
                                    # avec la règle comme clé
                                    yield fd
                                    # Logging de la confiance à des fins d'information
                                    logging.info(f"Dépendance avec confiance {confidence:.3f}: {table_name}.{det_tuple} -> {table_name}.{target_col}")
                            except Exception as e:
                                logging.error(f"Erreur lors de la création de la dépendance: {str(e)}")
                
                except Exception as e:
                    logging.error(f"Erreur lors de l'analyse de {csv_file}: {str(e)}")
                    continue
                
        except Exception as e:
            logging.error(f"Erreur lors de la découverte des dépendances: {str(e)}")
    
    def _compute_partitions(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Calcule les partitions d'attributs pour tous les attributs.
        Une partition groupe les indices des lignes par valeur d'attribut.
        
        :param df: DataFrame pandas contenant les données
        :return: Dictionnaire des partitions par attribut
        """
        partitions = {}
        
        for col in df.columns:
            partition = defaultdict(list)
            for idx, value in enumerate(df[col]):
                key = value if not pd.isna(value) else "__NULL__"
                partition[key].append(idx)
            partitions[col] = dict(partition)
            
        return partitions
    
    def _depth_first_discovery(
        self, 
        df: pd.DataFrame,
        partitions: Dict[str, Dict], 
        target: str,
        max_lhs_size: int,
        start_time: float,
        time_limit: float,
        min_conf: float
    ) -> List[Tuple[FrozenSet[str], float]]:
        """
        Algorithme de découverte en profondeur d'abord des dépendances fonctionnelles.
        
        :param df: DataFrame pandas contenant les données
        :param partitions: Partitions pré-calculées des attributs
        :param target: Colonne cible (partie droite de la dépendance)
        :param max_lhs_size: Taille maximale des déterminants
        :param start_time: Heure de début de l'algorithme
        :param time_limit: Limite de temps en secondes
        :param min_conf: Confiance minimale pour les dépendances approximatives
        :return: Liste des déterminants minimaux avec leur confiance
        """
        logging.info(f"Recherche de dépendances pour la cible: {target}")
        
        results = []
        visited = set()  # Ensembles d'attributs déjà visités
        minimal_deps = set()  # Déterminants minimaux trouvés
        candidates = []  # Pile pour DFS
        
        # Exclure la colonne cible des attributs candidats
        attributes = [col for col in df.columns if col != target]
        
        # Calculer la partition cible une seule fois
        target_partition = partitions[target]
        
        # Initialisation de la pile avec des ensembles d'attributs vides
        candidates.append(frozenset())
        
        while candidates and (time.time() - start_time) < time_limit:
            # Prendre le prochain candidat
            current = candidates.pop()
            
            # Si déjà visité, ignorer
            if current in visited:
                continue
                
            visited.add(current)
            
            # Vérifier si c'est déjà un sur-ensemble d'une dépendance minimale connue
            if any(min_dep.issubset(current) for min_dep in minimal_deps):
                continue
            
            # Vérifier si current est un déterminant pour target
            if len(current) > 0:  # Ignorer l'ensemble vide
                conf = self._calculate_dependency_confidence(df, current, target, partitions)
                
                if conf >= min_conf:
                    # Vérifier si c'est un déterminant minimal
                    is_minimal = True
                    for attr in current:
                        subset = frozenset(x for x in current if x != attr)
                        if subset in visited and any(min_dep.issubset(subset) for min_dep in minimal_deps):
                            is_minimal = False
                            break
                    
                    if is_minimal:
                        minimal_deps.add(current)
                        results.append((current, conf))
                        logging.info(f"Dépendance trouvée: {sorted(current)} -> {target} (conf: {conf:.3f})")
                        continue  # Pas besoin d'explorer les sur-ensembles
            
            # Si on n'a pas atteint la taille maximale, ajouter des candidats fils
            if len(current) < max_lhs_size:
                # Choisir les attributs à ajouter (ceux qui ne sont pas déjà dans l'ensemble)
                available_attrs = [attr for attr in attributes if attr not in current]
                
                # Utiliser une heuristique pour ordonner les attributs
                # Par exemple, on peut choisir de prioriser les attributs qui ont le plus de valeurs uniques
                available_attrs = self._order_attributes_heuristic(df, available_attrs, current, target)
                
                # Ajouter les nouveaux candidats à la pile
                for attr in available_attrs:
                    new_candidate = frozenset(current.union([attr]))
                    if new_candidate not in visited:
                        candidates.append(new_candidate)
        
        # Si on a atteint la limite de temps
        if (time.time() - start_time) >= time_limit:
            logging.warning(f"Limite de temps atteinte pour la cible {target}. Exploration incomplète.")
            
        return results
    
    def _calculate_dependency_confidence(
        self, 
        df: pd.DataFrame, 
        determinant: FrozenSet[str], 
        target: str,
        partitions: Dict[str, Dict]
    ) -> float:
        """
        Calcule la confiance d'une dépendance fonctionnelle X → Y.
        La confiance est le rapport entre le nombre de valeurs distinctes de X
        et le nombre de combinaisons distinctes de valeurs (X, Y).
        
        :param df: DataFrame pandas contenant les données
        :param determinant: Ensemble des attributs déterminants (X)
        :param target: Attribut cible (Y)
        :param partitions: Partitions d'attributs pré-calculées
        :return: Confiance de la dépendance (entre 0 et 1)
        """
        # Si le déterminant est vide, c'est une constante
        if not determinant:
            # Vérifier si la cible est une constante
            return 1.0 if len(partitions[target]) == 1 else 0.0
        
        # Utiliser les partitions pour vérifier la dépendance rapidement
        det_list = list(determinant)
        
        # Méthode optimisée pour les grands ensembles de données
        # Calculer la partition jointure des déterminants
        if len(det_list) == 1:
            # Cas spécial: un seul attribut déterminant
            X_partition = partitions[det_list[0]]
        else:
            # Combiner les partitions
            # Créer un dictionnaire qui mappe chaque tuple de valeurs de déterminants
            # à l'ensemble des indices de lignes qui ont ces valeurs
            X_partition = defaultdict(list)
            
            # Prendre une stratégie d'intersection pour calculer la partition
            # On commence avec la partition de l'attribut qui a le moins de classes d'équivalence
            smallest_partition_attr = min(det_list, key=lambda x: len(partitions[x]))
            base_partition = partitions[smallest_partition_attr]
            
            # Pour chaque classe d'équivalence dans la partition de base
            for val, indices in base_partition.items():
                # Grouper davantage par les autres attributs
                value_map = defaultdict(list)
                
                for idx in indices:
                    # Créer un tuple des valeurs de tous les attributs déterminants pour cette ligne
                    key = tuple(df.iloc[idx][attr] for attr in det_list)
                    value_map[key].append(idx)
                
                # Ajouter chaque groupe à la partition X
                for k, v in value_map.items():
                    X_partition[k] = v
        
        # Calculer la confiance
        total_X_classes = len(X_partition)
        if total_X_classes == 0:
            return 0.0
            
        violations = 0
        
        # Pour chaque classe d'équivalence dans X_partition
        for indices in X_partition.values():
            if len(indices) > 1:
                # Vérifier si tous les tuples dans cette classe ont la même valeur pour target
                target_values = set(df.iloc[idx][target] for idx in indices)
                if len(target_values) > 1:
                    violations += 1
        
        # La confiance est le pourcentage de classes d'équivalence qui n'ont pas de violations
        conf = 1.0 - (violations / total_X_classes)
        return conf
    
    def _order_attributes_heuristic(
        self, 
        df: pd.DataFrame, 
        available_attrs: List[str], 
        current_set: FrozenSet[str],
        target: str
    ) -> List[str]:
        """
        Ordonne les attributs selon une heuristique pour optimiser la recherche en profondeur.
        Cette implémentation utilise le nombre de valeurs distinctes comme heuristique.
        
        :param df: DataFrame pandas contenant les données
        :param available_attrs: Liste des attributs disponibles à ajouter
        :param current_set: Ensemble courant d'attributs
        :param target: Attribut cible
        :return: Liste ordonnée d'attributs
        """
        # Par défaut, on peut ordonner selon le nombre de valeurs distinctes (décroissant)
        # L'intuition est que les attributs avec plus de valeurs distinctes ont plus de chances
        # de déterminer la valeur cible
        attribute_scores = []
        
        for attr in available_attrs:
            # Nombre de valeurs distinctes de l'attribut
            distinct_count = df[attr].nunique()
            # Corrélation avec la cible (si possible)
            try:
                correlation = abs(df[attr].corr(df[target]))
                if pd.isna(correlation):
                    correlation = 0
            except:
                correlation = 0
                
            # Score combiné: plus de valeurs distinctes et plus de corrélation = meilleur score
            score = distinct_count * (1 + correlation)
            attribute_scores.append((attr, score))
        
        # Trier par score décroissant
        ordered_attrs = [attr for attr, _ in sorted(attribute_scores, key=lambda x: -x[1])]
        
        # Ajouter un peu de hasard pour éviter les minima locaux
        if len(ordered_attrs) > 1 and random.random() < 0.2:
            i, j = random.sample(range(len(ordered_attrs)), 2)
            ordered_attrs[i], ordered_attrs[j] = ordered_attrs[j], ordered_attrs[i]
            
        return ordered_attrs
