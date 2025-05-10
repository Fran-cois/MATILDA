import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Set, Tuple, Optional

from algorithms.rule_discovery_algorithm import RuleDiscoveryAlgorithm
from utils.rules_classes.functional_dependency import FunctionalDependency

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIDFD(RuleDiscoveryAlgorithm):
    """
    Implémentation de l'algorithme AIDFD (Approximate Incremental Dependency Discovery)
    pour la découverte de dépendances fonctionnelles approximatives.
    """
    
    def __init__(self, database):
        """
        Initialise l'algorithme AIDFD.
        
        Args:
            database: La base de données à analyser
        """
        super().__init__(database)
        self.min_support = 0.5
        self.min_confidence = 0.9
        self.max_lhs_size = 3  # Taille maximale des déterminants (partie gauche)
        
    def discover_rules(self, **kwargs) -> List[FunctionalDependency]:
        """
        Découvre les dépendances fonctionnelles dans la base de données.
        
        Args:
            **kwargs: Paramètres optionnels:
                - min_support: Support minimum (défaut: 0.5)
                - min_confidence: Confiance minimum (défaut: 0.9)
                - max_lhs_size: Taille maximale des déterminants (défaut: 3)
                
        Returns:
            List[FunctionalDependency]: Liste des dépendances fonctionnelles découvertes
        """
        self.min_support = kwargs.get("min_support", self.min_support)
        self.min_confidence = kwargs.get("min_confidence", self.min_confidence)
        self.max_lhs_size = kwargs.get("max_lhs_size", self.max_lhs_size)
        
        all_fds = []
        
        # Analyser chaque table de la base de données
        for table_name in self.database.get_table_names():
            logger.info(f"Analysing table {table_name} for functional dependencies")
            
            # Charger les données de la table
            df = self.database.get_table_data(table_name)
            if df is None or df.empty:
                logger.warning(f"Table {table_name} is empty or cannot be loaded")
                continue
                
            # Découvrir les dépendances fonctionnelles pour cette table
            table_fds = self._discover_fds_in_table(table_name, df)
            all_fds.extend(table_fds)
            
        return all_fds
    
    def _discover_fds_in_table(self, table_name: str, df: pd.DataFrame) -> List[FunctionalDependency]:
        """
        Découvre les dépendances fonctionnelles dans une table.
        
        Args:
            table_name: Nom de la table
            df: DataFrame contenant les données de la table
            
        Returns:
            List[FunctionalDependency]: Liste des dépendances fonctionnelles découvertes
        """
        columns = df.columns.tolist()
        fds = []
        
        # Pour chaque attribut potentiel côté droit (déterminé)
        for rhs in columns:
            # Évaluer les dépendances avec des déterminants de taille croissante
            for lhs_size in range(1, self.max_lhs_size + 1):
                # Générer toutes les combinaisons possibles de colonnes pour le côté gauche
                lhs_candidates = self._generate_lhs_candidates(columns, rhs, lhs_size)
                
                for lhs in lhs_candidates:
                    support, confidence = self._calculate_fd_metrics(df, lhs, rhs)
                    
                    if support >= self.min_support and confidence >= self.min_confidence:
                        fd = FunctionalDependency(
                            table=table_name,
                            lhs=list(lhs),
                            rhs=rhs,
                            support=support,
                            confidence=confidence
                        )
                        fds.append(fd)
                        logger.debug(f"Found FD: {fd}")
        
        # Éliminer les dépendances redondantes
        return self._remove_redundant_fds(fds)
    
    def _generate_lhs_candidates(self, columns: List[str], rhs: str, size: int) -> List[Tuple[str, ...]]:
        """
        Génère des combinaisons d'attributs pour le côté gauche (déterminants).
        
        Args:
            columns: Liste des colonnes de la table
            rhs: Attribut côté droit (déterminé)
            size: Taille du déterminant à générer
            
        Returns:
            List[Tuple[str, ...]]: Liste des combinaisons d'attributs
        """
        from itertools import combinations
        
        # Exclure l'attribut rhs des candidats lhs
        lhs_cols = [col for col in columns if col != rhs]
        return list(combinations(lhs_cols, size))
    
    def _calculate_fd_metrics(self, df: pd.DataFrame, lhs: Tuple[str, ...], rhs: str) -> Tuple[float, float]:
        """
        Calcule le support et la confiance d'une dépendance fonctionnelle.
        
        Args:
            df: DataFrame contenant les données
            lhs: Attributs du côté gauche (déterminants)
            rhs: Attribut du côté droit (déterminé)
            
        Returns:
            Tuple[float, float]: Support et confiance de la dépendance
        """
        # Nombre total de tuples
        total_rows = len(df)
        
        # Grouper par les attributs lhs et compter les valeurs distinctes de rhs
        grouped = df.groupby(list(lhs))[rhs].nunique()
        
        # Nombre de groupes où la dépendance est respectée (valeur unique de rhs)
        valid_groups = (grouped == 1).sum()
        
        # Nombre total de groupes
        total_groups = len(grouped)
        
        # Calculer le support et la confiance
        if total_groups == 0:
            return 0.0, 0.0
            
        # Support = proportion de tuples dans des groupes valides
        valid_tuples = df.groupby(list(lhs)).size()[grouped == 1].sum() if valid_groups > 0 else 0
        support = valid_tuples / total_rows
        
        # Confiance = proportion de groupes valides
        confidence = valid_groups / total_groups
        
        return support, confidence
    
    def _remove_redundant_fds(self, fds: List[FunctionalDependency]) -> List[FunctionalDependency]:
        """
        Élimine les dépendances fonctionnelles redondantes.
        
        Args:
            fds: Liste des dépendances fonctionnelles
            
        Returns:
            List[FunctionalDependency]: Liste des dépendances non redondantes
        """
        # Trier les FDs par taille croissante des déterminants, puis par confiance décroissante
        sorted_fds = sorted(fds, key=lambda fd: (len(fd.lhs), -fd.confidence))
        
        # Regrouper les FDs par attribut déterminé (rhs)
        rhs_groups = {}
        for fd in sorted_fds:
            if fd.rhs not in rhs_groups:
                rhs_groups[fd.rhs] = []
            rhs_groups[fd.rhs].append(fd)
        
        non_redundant_fds = []
        
        # Pour chaque groupe d'attributs déterminés
        for rhs, group in rhs_groups.items():
            minimal_fds = []
            
            for fd in group:
                # Vérifier si fd est minimal (non redondant)
                is_minimal = True
                lhs_set = set(fd.lhs)
                
                for min_fd in minimal_fds:
                    min_lhs_set = set(min_fd.lhs)
                    # Si un sous-ensemble des déterminants existe déjà, cette FD est redondante
                    if min_lhs_set.issubset(lhs_set):
                        is_minimal = False
                        break
                
                if is_minimal:
                    # Supprimer toutes les FDs non-minimales existantes qui sont des sur-ensembles
                    minimal_fds = [mfd for mfd in minimal_fds if not set(mfd.lhs).issuperset(lhs_set)]
                    minimal_fds.append(fd)
            
            non_redundant_fds.extend(minimal_fds)
        
        return non_redundant_fds
