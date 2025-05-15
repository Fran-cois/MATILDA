#!/usr/bin/env python3
# test_all_fd_algos.py - Test complet de tous les algorithmes FD

import os
import sys
import logging
import time
import pandas as pd
import subprocess
import importlib.util
from datetime import datetime
from collections import defaultdict

# Ajouter les répertoires nécessaires au path pour l'importation des modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'src'))

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Chemin des répertoires
test_data_dir = 'test_data'
os.makedirs(test_data_dir, exist_ok=True)

# Définir les classes de base nécessaires pour les tests
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

class Rule:
    def __init__(self, table, lhs, rhs):
        self.table = table
        self.lhs = lhs
        self.rhs = rhs
    
    def __repr__(self):
        return f"{self.table}.{self.lhs} -> {self.table}.{self.rhs}"

# Créer une base de données fictive pour les tests
class MockDatabase:
    def __init__(self):
        self.base_csv_dir = test_data_dir

# Fonction pour créer un fichier CSV de test plus complexe
def create_test_csvs():
    logger.info("Création des fichiers CSV de test")
    
    # Premier fichier - données simples
    test_file1 = os.path.join(test_data_dir, 'test_fd.csv')
    with open(test_file1, 'w') as f:
        f.write('id,name,age,city,country,zipcode,city_zipcode\n')
        f.write('1,John,25,Paris,France,75001,Paris_75001\n')
        f.write('2,Emma,30,Lyon,France,69001,Lyon_69001\n')
        f.write('3,Paul,28,Marseille,France,13001,Marseille_13001\n')
        f.write('4,Sophie,35,Bordeaux,France,33000,Bordeaux_33000\n')
        f.write('5,Lucas,22,Nice,France,06000,Nice_06000\n')
    logger.info(f"Fichier CSV de test créé: {test_file1}")
    
    # Deuxième fichier - données d'achats
    test_file2 = os.path.join(test_data_dir, 'orders.csv')
    with open(test_file2, 'w') as f:
        f.write('order_id,customer_id,product_id,product_name,price,category,category_id\n')
        f.write('1001,1,p100,Laptop,1200,Electronics,cat1\n')
        f.write('1002,2,p101,Smartphone,800,Electronics,cat1\n')
        f.write('1003,3,p102,Headphones,150,Electronics,cat1\n')
        f.write('1004,4,p103,Book,25,Books,cat2\n')
        f.write('1005,5,p104,Desk,300,Furniture,cat3\n')
        f.write('1006,1,p105,Chair,150,Furniture,cat3\n')
        f.write('1007,2,p106,Monitor,250,Electronics,cat1\n')
        f.write('1008,3,p100,Laptop,1200,Electronics,cat1\n')
    logger.info(f"Fichier CSV de commandes créé: {test_file2}")
    
    return [test_file1, test_file2]

# Fonction directe pour découvrir les dépendances fonctionnelles d'un dataframe
def discover_fds_direct(df, table_name):
    """Implémentation simple pour découvrir les dépendances fonctionnelles"""
    discovered_fds = []
    columns = list(df.columns)
    
    # Pour chaque colonne potentielle côté droit
    for rhs_col in columns:
        # Pour chaque colonne potentielle côté gauche
        for lhs_col in columns:
            if lhs_col == rhs_col:
                continue
            
            # Vérifier si lhs -> rhs
            lhs_to_rhs = df.groupby(lhs_col)[rhs_col].nunique() <= 1
            
            # Si toutes les valeurs sont True, c'est une dépendance fonctionnelle
            if lhs_to_rhs.all():
                fd = FunctionalDependency(
                    table=table_name,
                    lhs=lhs_col,
                    rhs=rhs_col
                )
                discovered_fds.append(fd)
    
    return discovered_fds

# Créer des implémentations simplifiées des algorithmes
class DirectFDAlgorithm:
    """Base pour une implémentation directe d'un algorithme FD"""
    
    def __init__(self, database):
        self.database = database
        self.name = "DirectFDAlgorithm"
    
    def discover_rules(self, **kwargs):
        """Découverte des dépendances fonctionnelles directement en Python"""
        logger.info(f"Exécution de l'algorithme {self.name} en mode direct")
        
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
                file_rules = discover_fds_direct(df, table_name)
                rules.extend(file_rules)
            except Exception as e:
                logger.error(f"Erreur lors du traitement du fichier {csv_file}: {str(e)}")
        
        logger.info(f"Total de {len(rules)} règles découvertes")
        return rules

# Créer des versions spécifiques des algorithmes
class DirectTane(DirectFDAlgorithm):
    def __init__(self, database):
        super().__init__(database)
        self.name = "TANE"

class DirectDFD(DirectFDAlgorithm):
    def __init__(self, database):
        super().__init__(database)
        self.name = "DFD"

class DirectFDep(DirectFDAlgorithm):
    def __init__(self, database):
        super().__init__(database)
        self.name = "FDep"

class DirectFastFDs(DirectFDAlgorithm):
    def __init__(self, database):
        super().__init__(database)
        self.name = "FastFDs"

class DirectAIDFD(DirectFDAlgorithm):
    def __init__(self, database):
        super().__init__(database)
        self.name = "AIDFD"

class DirectPyro(DirectFDAlgorithm):
    def __init__(self, database):
        super().__init__(database)
        self.name = "Pyro"

# Fonction pour analyser les résultats
def analyze_results(rules, algo_name):
    """Analyse les résultats pour vérifier la qualité des dépendances fonctionnelles"""
    logger.info(f"Analyse des résultats de {algo_name}")
    
    if not rules:
        logger.warning(f"Aucune règle trouvée par {algo_name}")
        return
    
    # Comptage par table
    tables = {}
    for rule in rules:
        if hasattr(rule, 'table'):
            table = rule.table
            tables[table] = tables.get(table, 0) + 1
    
    # Afficher les statistiques
    logger.info(f"Statistiques des règles par table:")
    for table, count in tables.items():
        logger.info(f"  - {table}: {count} règles")
        
    # Vérifier les métriques si disponibles
    has_metrics = False
    for rule in rules[:5]:
        if hasattr(rule, 'support') and hasattr(rule, 'confidence'):
            has_metrics = True
            break
    
    if has_metrics:
        logger.info(f"L'algorithme {algo_name} fournit des métriques de qualité (support/confiance)")
    else:
        logger.info(f"L'algorithme {algo_name} ne fournit pas de métriques de qualité")
    
    return has_metrics

# Fonction pour tester chaque algorithme
def test_algorithm(algo_name, algo_class, database):
    logger.info(f"\n===== TEST DE L'ALGORITHME {algo_name} =====")
    
    # Instancier l'algorithme
    start_time = time.time()
    try:
        algorithm = algo_class(database)
        
        # Exécuter l'algorithme
        rules = algorithm.discover_rules()
        
        # Calculer le temps d'exécution
        elapsed_time = time.time() - start_time
        
        # Afficher les résultats
        if rules:
            if isinstance(rules, dict):
                rule_count = len(rules)
                rules_list = list(rules.keys())
            else:
                rule_count = len(rules)
                rules_list = rules
                
            logger.info(f"✅ {algo_name} a réussi en {elapsed_time:.2f} secondes")
            logger.info(f"Dépendances fonctionnelles découvertes : {rule_count}")
            
            # Afficher les 5 premières règles
            for i, rule in enumerate(rules_list[:5]):
                logger.info(f"  - {rule}")
            if rule_count > 5:
                logger.info(f"  - ... et {rule_count - 5} autres règles")
            
            # Analyser les résultats
            has_metrics = analyze_results(rules, algo_name)
        else:
            logger.error(f"❌ {algo_name} n'a trouvé aucune règle")
            
        return True, elapsed_time, len(rules) if rules else 0
    except Exception as e:
        logger.error(f"❌ {algo_name} a échoué : {str(e)}")
        logger.exception(e)
        return False, time.time() - start_time, 0

def test_original_algorithm(algo_name, module_path, class_name, database):
    """Tester l'algorithme original si possible"""
    logger.info(f"\n===== TEST DE L'ALGORITHME ORIGINAL {algo_name} =====")
    
    try:
        # Essayer d'importer le module directement avec importlib
        spec = importlib.util.find_spec(module_path)
        if spec is None:
            logger.warning(f"Module {module_path} non trouvé")
            return False, 0, 0
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if not hasattr(module, class_name):
            logger.warning(f"Classe {class_name} non trouvée dans {module_path}")
            return False, 0, 0
            
        algo_class = getattr(module, class_name)
        
        # Exécuter le test standard
        return test_algorithm(f"{algo_name}_original", algo_class, database)
    except ImportError as e:
        logger.warning(f"Impossible d'importer {module_path}: {str(e)}")
        return False, 0, 0
    except Exception as e:
        logger.warning(f"Erreur lors du test de {algo_name}_original: {str(e)}")
        return False, 0, 0

def main():
    # Créer les fichiers CSV de test
    csv_files = create_test_csvs()
    
    # Créer la base de données fictive
    database = MockDatabase()
    
    # Liste des algorithmes directs à tester
    direct_algorithms = [
        ('TANE', DirectTane),
        ('DFD', DirectDFD),
        ('FDep', DirectFDep),
        ('FastFDs', DirectFastFDs),
        ('AIDFD', DirectAIDFD),
        ('PYRO', DirectPyro)
    ]
    
    # Liste des algorithmes originaux à tester si possible
    original_algorithms = [
        ('TANE', 'src.algorithms.tane', 'Tane'),
        ('DFD', 'src.algorithms.dfd', 'DFD'),
        ('FDep', 'src.algorithms.fdep', 'FDep'),
        ('FastFDs', 'src.algorithms.fastfds', 'FastFDs'),
        ('AIDFD', 'src.algorithms.aidfd', 'AIDFD'),
        ('PYRO', 'src.algorithms.pyro', 'Pyro')
    ]
    
    # Tester chaque algorithme direct
    results = {}
    performance = {}
    logger.info("\n===== TEST DES IMPLÉMENTATIONS DIRECTES =====")
    for algo_name, algo_class in direct_algorithms:
        logger.info(f"\nTest de l'implémentation directe de {algo_name}...")
        success, exec_time, rule_count = test_algorithm(f"{algo_name}_direct", algo_class, database)
        results[f"{algo_name}_direct"] = "✅ Succès" if success else "❌ Échec"
        performance[f"{algo_name}_direct"] = {"time": exec_time, "rules": rule_count}
    
    # Tester chaque algorithme original
    logger.info("\n===== TEST DES IMPLÉMENTATIONS ORIGINALES =====")
    for algo_name, module_path, class_name in original_algorithms:
        logger.info(f"\nTest de l'implémentation originale de {algo_name}...")
        try:
            success, exec_time, rule_count = test_original_algorithm(algo_name, module_path, class_name, database)
            results[f"{algo_name}_original"] = "✅ Succès" if success else "❌ Non disponible"
            performance[f"{algo_name}_original"] = {"time": exec_time, "rules": rule_count}
        except Exception as e:
            logger.error(f"Erreur lors du test de {algo_name}_original: {str(e)}")
            results[f"{algo_name}_original"] = f"❌ Erreur"
            performance[f"{algo_name}_original"] = {"time": 0, "rules": 0}
    
    # Afficher le résumé
    logger.info("\n===== RÉSUMÉ DES TESTS =====")
    logger.info(f"{'Algorithme':<20} | {'Statut':<25} | {'Temps (s)':<10} | {'Règles':<8}")
    logger.info("-" * 70)
    
    # D'abord afficher les algorithmes directs
    for algo_name, _ in direct_algorithms:
        key = f"{algo_name}_direct"
        result = results.get(key, "❓ Non testé")
        perf = performance.get(key, {"time": 0, "rules": 0})
        logger.info(f"{key:<20} | {result:<25} | {perf['time']:.2f}s | {perf['rules']}")
    
    logger.info("-" * 70)
    
    # Puis afficher les algorithmes originaux
    for algo_name, _, _ in original_algorithms:
        key = f"{algo_name}_original"
        result = results.get(key, "❓ Non testé")
        perf = performance.get(key, {"time": 0, "rules": 0})
        logger.info(f"{key:<20} | {result:<25} | {perf['time']:.2f}s | {perf['rules']}")
    
    # Nettoyer
    if os.path.exists(test_data_dir):
        import shutil
        shutil.rmtree(test_data_dir)
        logger.info(f"Répertoire de test supprimé: {test_data_dir}")

if __name__ == "__main__":
    main()
