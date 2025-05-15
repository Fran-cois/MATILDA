#!/usr/bin/env python3
# test_aidfd_pyro.py - Test des algorithmes AIDFD et PYRO

import os
import sys
import logging
import time
import pandas as pd
from datetime import datetime
from collections import defaultdict

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("root")

# Créer un répertoire pour les fichiers de test
test_dir = "test_fd_data_direct"
os.makedirs(test_dir, exist_ok=True)

# Créer un fichier CSV de test
test_file = os.path.join(test_dir, "test_fd.csv")
with open(test_file, "w") as f:
    f.write("id,name,age,city,country,zipcode,city_zipcode\n")
    f.write("1,John,25,Paris,France,75001,Paris_75001\n")
    f.write("2,Emma,30,Lyon,France,69001,Lyon_69001\n")
    f.write("3,Paul,28,Marseille,France,13001,Marseille_13001\n")
    f.write("4,Sophie,35,Bordeaux,France,33000,Bordeaux_33000\n")
    f.write("5,Lucas,22,Nice,France,06000,Nice_06000\n")

logger.info(f"Fichier CSV de test créé: {test_file}")

# Créer une base de données fictive
class MockDatabase:
    def __init__(self):
        self.base_csv_dir = test_dir

# Définir une classe de dépendance fonctionnelle simplifiée
class FunctionalDependency:
    def __init__(self, table, lhs, rhs, support=1.0, confidence=1.0):
        self.table = table
        self.lhs = lhs if isinstance(lhs, list) else [lhs]
        self.rhs = rhs
        self.support = support
        self.confidence = confidence
    
    def __repr__(self):
        lhs_str = ", ".join(self.lhs)
        return f"{self.table}.({lhs_str}) -> {self.table}.{self.rhs} [s={self.support:.2f}, c={self.confidence:.2f}]"

# Implémentation simplifiée d'AIDFD
class AIDFD_Direct:
    """Implémentation directe et simplifiée d'AIDFD pour test"""
    
    def __init__(self, database):
        self.database = database
        self.min_support = 0.5
        self.min_confidence = 0.9
    
    def discover_rules(self, **kwargs):
        """Découverte des dépendances fonctionnelles approximatives"""
        logger.info("Découverte des dépendances avec AIDFD (impl. Python directe)")
        use_fallback = kwargs.get("use_fallback", True)
        self.min_support = kwargs.get("min_support", self.min_support)
        self.min_confidence = kwargs.get("min_confidence", self.min_confidence)
        
        rules = []
        csv_files = [
            os.path.join(self.database.base_csv_dir, f)
            for f in os.listdir(self.database.base_csv_dir)
            if f.endswith('.csv')
        ]
        
        for csv_file in csv_files:
            table_name = os.path.basename(csv_file).replace('.csv', '')
            logger.info(f"Traitement du fichier: {csv_file}")
            
            try:
                df = pd.read_csv(csv_file)
                file_rules = self._discover_approx_fds(df, table_name)
                rules.extend(file_rules)
            except Exception as e:
                logger.error(f"Erreur lors du traitement du fichier {csv_file}: {e}")
        
        logger.info(f"Total de {len(rules)} règles découvertes")
        return rules
    
    def _discover_approx_fds(self, df, table_name):
        """Découverte des dépendances fonctionnelles approximatives"""
        discovered_fds = []
        columns = list(df.columns)
        
        # Pour chaque colonne potentielle côté droit
        for rhs_col in columns:
            # Pour chaque colonne potentielle côté gauche
            for lhs_col in columns:
                if lhs_col == rhs_col:
                    continue
                
                # Calculer support et confiance
                support, confidence = self._calculate_metrics(df, lhs_col, rhs_col)
                
                # Si la règle satisfait les seuils
                if support >= self.min_support and confidence >= self.min_confidence:
                    fd = FunctionalDependency(
                        table=table_name,
                        lhs=lhs_col,
                        rhs=rhs_col,
                        support=support,
                        confidence=confidence
                    )
                    discovered_fds.append(fd)
                    logger.info(f"FD approx découverte: {fd}")
        
        return discovered_fds
    
    def _calculate_metrics(self, df, lhs_col, rhs_col):
        """Calcule le support et la confiance pour une dépendance"""
        # Grouper par la colonne LHS
        grouped = df.groupby(lhs_col)
        
        total_groups = len(grouped)
        valid_groups = 0
        total_rows = len(df)
        covered_rows = 0
        
        for _, group in grouped:
            group_size = len(group)
            covered_rows += group_size
            
            # Si RHS a une seule valeur dans ce groupe, la règle est valide
            if len(group[rhs_col].unique()) == 1:
                valid_groups += 1
        
        # Éviter division par zéro
        if total_groups == 0:
            return 0, 0
            
        support = covered_rows / total_rows
        confidence = valid_groups / total_groups
        
        return support, confidence

# Implémentation simplifiée de PYRO
class PYRO_Direct:
    """Implémentation directe et simplifiée de PYRO pour test"""
    
    def __init__(self, database):
        self.database = database
        self.min_support = 0.5
        self.min_confidence = 0.9
    
    def discover_rules(self, **kwargs):
        """Découverte des dépendances fonctionnelles avec PYRO"""
        logger.info("Découverte des dépendances avec PYRO (impl. Python directe)")
        use_fallback = kwargs.get("use_fallback", True)
        self.min_support = kwargs.get("min_support", self.min_support)
        self.min_confidence = kwargs.get("min_confidence", self.min_confidence)
        
        rules = []
        csv_files = [
            os.path.join(self.database.base_csv_dir, f)
            for f in os.listdir(self.database.base_csv_dir)
            if f.endswith('.csv')
        ]
        
        for csv_file in csv_files:
            table_name = os.path.basename(csv_file).replace('.csv', '')
            logger.info(f"Traitement du fichier: {csv_file}")
            
            try:
                df = pd.read_csv(csv_file)
                file_rules = self._discover_fds_pyro(df, table_name)
                rules.extend(file_rules)
            except Exception as e:
                logger.error(f"Erreur lors du traitement du fichier {csv_file}: {e}")
        
        logger.info(f"Total de {len(rules)} règles découvertes")
        return rules
    
    def _discover_fds_pyro(self, df, table_name):
        """Implémentation simplifiée de l'algorithme PYRO"""
        discovered_fds = []
        columns = list(df.columns)
        
        # Vérification des dépendances en commençant par les simples (taille 1)
        for rhs_idx, rhs_col in enumerate(columns):
            # Commencer par vérifier les dépendances à gauche simple (une colonne)
            for lhs_idx, lhs_col in enumerate(columns):
                if lhs_idx == rhs_idx:  # Éviter la même colonne
                    continue
                
                # Vérifier si lhs détermine rhs
                is_fd, support, confidence = self._check_fd(df, [lhs_col], rhs_col)
                if is_fd:
                    fd = FunctionalDependency(
                        table=table_name,
                        lhs=[lhs_col],
                        rhs=rhs_col,
                        support=support,
                        confidence=confidence
                    )
                    discovered_fds.append(fd)
                    logger.info(f"FD découverte: {fd}")
            
            # Essayer les combinaisons de deux colonnes à gauche
            for i in range(len(columns)):
                if i == rhs_idx:
                    continue
                for j in range(i+1, len(columns)):
                    if j == rhs_idx:
                        continue
                    
                    lhs_cols = [columns[i], columns[j]]
                    is_fd, support, confidence = self._check_fd(df, lhs_cols, rhs_col)
                    if is_fd:
                        fd = FunctionalDependency(
                            table=table_name,
                            lhs=lhs_cols,
                            rhs=rhs_col,
                            support=support,
                            confidence=confidence
                        )
                        discovered_fds.append(fd)
                        logger.info(f"FD découverte: {fd}")
        
        return discovered_fds
    
    def _check_fd(self, df, lhs_cols, rhs_col):
        """Vérifie si lhs_cols -> rhs_col est une dépendance fonctionnelle"""
        # Grouper par les colonnes LHS
        grouped = df.groupby(lhs_cols)
        
        total_groups = len(grouped)
        valid_groups = 0
        total_rows = len(df)
        covered_rows = 0
        
        for _, group in grouped:
            group_size = len(group)
            covered_rows += group_size
            
            # Si RHS a une seule valeur dans ce groupe, la règle est valide
            if len(group[rhs_col].unique()) == 1:
                valid_groups += 1
        
        # Éviter division par zéro
        if total_groups == 0:
            return False, 0, 0
            
        support = covered_rows / total_rows
        confidence = valid_groups / total_groups
        
        # La règle est valide si elle satisfait les seuils
        is_fd = confidence >= self.min_confidence and support >= self.min_support
        
        return is_fd, support, confidence

# Tester l'implémentation directe d'AIDFD
logger.info("\n===== TEST DE L'IMPLÉMENTATION DIRECTE D'AIDFD =====")
try:
    # Créer l'instance d'AIDFD direct
    database = MockDatabase()
    aidfd_direct = AIDFD_Direct(database)
    
    # Exécuter la découverte
    logger.info("Exécution de l'implémentation directe d'AIDFD")
    start_time = time.time()
    rules = aidfd_direct.discover_rules()
    elapsed = time.time() - start_time
    
    # Afficher les résultats
    logger.info(f"Exécution terminée en {elapsed:.2f} secondes")
    logger.info(f"Nombre de règles découvertes: {len(rules)}")
    
    # Afficher quelques règles
    for i, rule in enumerate(rules[:5]):
        logger.info(f"Règle {i+1}: {rule}")
    
    if len(rules) > 5:
        logger.info(f"... et {len(rules) - 5} autres règles")
    
except Exception as e:
    logger.error(f"Erreur lors du test de l'implémentation directe d'AIDFD: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

# Tester l'implémentation directe de PYRO
logger.info("\n===== TEST DE L'IMPLÉMENTATION DIRECTE DE PYRO =====")
try:
    # Créer l'instance de PYRO direct
    database = MockDatabase()
    pyro_direct = PYRO_Direct(database)
    
    # Exécuter la découverte
    logger.info("Exécution de l'implémentation directe de PYRO")
    start_time = time.time()
    rules = pyro_direct.discover_rules()
    elapsed = time.time() - start_time
    
    # Afficher les résultats
    logger.info(f"Exécution terminée en {elapsed:.2f} secondes")
    logger.info(f"Nombre de règles découvertes: {len(rules)}")
    
    # Afficher quelques règles
    for i, rule in enumerate(rules[:5]):
        logger.info(f"Règle {i+1}: {rule}")
    
    if len(rules) > 5:
        logger.info(f"... et {len(rules) - 5} autres règles")
    
except Exception as e:
    logger.error(f"Erreur lors du test de l'implémentation directe de PYRO: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

# Tester l'implémentation AIDFD de MATILDA
logger.info("\n===== TEST DE AIDFD DE MATILDA =====")
try:
    # Ajouter le chemin src au path pour l'importation
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.algorithms.aidfd import AIDFD
    
    # Créer l'instance de AIDFD
    database = MockDatabase()
    aidfd = AIDFD(database)
    
    # Exécuter avec la solution de repli
    logger.info("Exécution de AIDFD avec la solution de repli (Python)")
    start_time = time.time()
    rules = aidfd.discover_rules(use_fallback=True)
    elapsed = time.time() - start_time
    
    # Afficher les résultats
    logger.info(f"Exécution terminée en {elapsed:.2f} secondes")
    logger.info(f"Nombre de règles découvertes: {len(rules)}")
    
    # Afficher quelques règles
    for i, rule in enumerate(rules[:5]):
        logger.info(f"Règle {i+1}: {rule}")
    
    if len(rules) > 5:
        logger.info(f"... et {len(rules) - 5} autres règles")
    
except Exception as e:
    logger.error(f"Erreur lors du test de AIDFD: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

# Tester l'implémentation PYRO de MATILDA
logger.info("\n===== TEST DE PYRO DE MATILDA =====")
try:
    # Déjà ajouté le chemin src au path pour l'importation
    from src.algorithms.pyro import Pyro
    
    # Créer l'instance de Pyro
    database = MockDatabase()
    pyro = Pyro(database)
    
    # Exécuter avec la solution de repli
    logger.info("Exécution de PYRO avec la solution de repli (Python)")
    start_time = time.time()
    rules = pyro.discover_rules(use_fallback=True)
    elapsed = time.time() - start_time
    
    # Afficher les résultats
    logger.info(f"Exécution terminée en {elapsed:.2f} secondes")
    logger.info(f"Nombre de règles découvertes: {len(rules)}")
    
    # Afficher quelques règles
    for i, rule in enumerate(rules[:5]):
        logger.info(f"Règle {i+1}: {rule}")
    
    if len(rules) > 5:
        logger.info(f"... et {len(rules) - 5} autres règles")
    
except Exception as e:
    logger.error(f"Erreur lors du test de PYRO: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

# Nettoyer
import shutil
if os.path.exists(test_dir):
    shutil.rmtree(test_dir)
    logger.info(f"Répertoire de test supprimé: {test_dir}")
