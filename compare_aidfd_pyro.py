#!/usr/bin/env python3
# compare_aidfd_pyro.py - Comparaison détaillée des règles générées par AIDFD et PYRO

import os
import sys
import logging
import pandas as pd
import importlib.util

# Configuration du chemin d'accès et du logging
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'src'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Création des données de test
test_data_dir = 'test_data'
os.makedirs(test_data_dir, exist_ok=True)

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

# Classe base de données fictive pour les tests
class MockDatabase:
    def __init__(self):
        self.base_csv_dir = test_data_dir

def load_algorithm(module_path, class_name):
    """Charge dynamiquement un algorithme depuis son module"""
    try:
        spec = importlib.util.find_spec(module_path)
        if spec is None:
            logger.error(f"Module {module_path} non trouvé")
            return None
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if not hasattr(module, class_name):
            logger.error(f"Classe {class_name} non trouvée dans {module_path}")
            return None
            
        return getattr(module, class_name)
    except Exception as e:
        logger.error(f"Erreur lors du chargement de {module_path}.{class_name}: {str(e)}")
        return None

def categorize_rules(rules, table_name):
    """Catégorise les règles par type"""
    categorized = {
        'single_lhs_single_rhs': [],  # A -> B
        'multi_lhs_single_rhs': [],   # A,B -> C
        'by_rhs': {}                  # Regroupé par attribut cible
    }
    
    for rule in rules:
        if hasattr(rule, 'table') and rule.table == table_name:
            # Catégoriser par nombre d'attributs dans LHS
            if len(rule.lhs) == 1:
                categorized['single_lhs_single_rhs'].append(rule)
            else:
                categorized['multi_lhs_single_rhs'].append(rule)
            
            # Catégoriser par attribut RHS
            rhs = rule.rhs
            if rhs not in categorized['by_rhs']:
                categorized['by_rhs'][rhs] = []
            categorized['by_rhs'][rhs].append(rule)
    
    return categorized

def analyze_differences(aidfd_rules, pyro_rules, table_name):
    """Analyse détaillée des différences entre les règles de AIDFD et PYRO"""
    logger.info(f"\n===== ANALYSE DES DIFFÉRENCES POUR LA TABLE {table_name} =====")
    
    # Catégoriser les règles
    aidfd_categorized = categorize_rules(aidfd_rules, table_name)
    pyro_categorized = categorize_rules(pyro_rules, table_name)
    
    # Compter le nombre de règles par catégorie
    logger.info(f"Règles AIDFD avec un seul attribut à gauche: {len(aidfd_categorized['single_lhs_single_rhs'])}")
    logger.info(f"Règles AIDFD avec plusieurs attributs à gauche: {len(aidfd_categorized['multi_lhs_single_rhs'])}")
    logger.info(f"Règles PYRO avec un seul attribut à gauche: {len(pyro_categorized['single_lhs_single_rhs'])}")
    logger.info(f"Règles PYRO avec plusieurs attributs à gauche: {len(pyro_categorized['multi_lhs_single_rhs'])}")
    
    # Compter par attribut RHS
    logger.info("\nNombre de règles par attribut cible:")
    all_rhs = set(list(aidfd_categorized['by_rhs'].keys()) + list(pyro_categorized['by_rhs'].keys()))
    for rhs in sorted(all_rhs):
        aidfd_count = len(aidfd_categorized['by_rhs'].get(rhs, []))
        pyro_count = len(pyro_categorized['by_rhs'].get(rhs, []))
        diff = aidfd_count - pyro_count
        logger.info(f"  - Attribut {rhs}: AIDFD={aidfd_count}, PYRO={pyro_count}, Diff={diff}")
    
    # Trouver les règles communes et uniques
    aidfd_rule_strings = set([f"{','.join(r.lhs)}->{r.rhs}" for r in aidfd_rules if hasattr(r, 'table') and r.table == table_name])
    pyro_rule_strings = set([f"{','.join(r.lhs)}->{r.rhs}" for r in pyro_rules if hasattr(r, 'table') and r.table == table_name])
    
    common_rules = aidfd_rule_strings.intersection(pyro_rule_strings)
    only_aidfd = aidfd_rule_strings - pyro_rule_strings
    only_pyro = pyro_rule_strings - aidfd_rule_strings
    
    logger.info(f"\nRègles communes: {len(common_rules)}")
    logger.info(f"Règles uniquement dans AIDFD: {len(only_aidfd)}")
    logger.info(f"Règles uniquement dans PYRO: {len(only_pyro)}")
    
    # Exemples de règles uniques à AIDFD
    if only_aidfd:
        logger.info("\nExemples de règles uniquement dans AIDFD:")
        for rule in list(only_aidfd)[:10]:  # Affiche les 10 premières
            logger.info(f"  - {rule}")
        if len(only_aidfd) > 10:
            logger.info(f"  - ... et {len(only_aidfd) - 10} autres règles")
    
    return {
        'common': len(common_rules),
        'only_aidfd': len(only_aidfd),
        'only_pyro': len(only_pyro),
        'aidfd_single_lhs': len(aidfd_categorized['single_lhs_single_rhs']),
        'aidfd_multi_lhs': len(aidfd_categorized['multi_lhs_single_rhs']),
        'pyro_single_lhs': len(pyro_categorized['single_lhs_single_rhs']),
        'pyro_multi_lhs': len(pyro_categorized['multi_lhs_single_rhs']),
    }

def analyze_algorithm_behavior(algorithm_class, database, name):
    """Analyse le comportement interne de l'algorithme"""
    logger.info(f"\n===== ANALYSE DU COMPORTEMENT DE {name} =====")
    
    # Créer l'instance de l'algorithme
    algorithm = algorithm_class(database)
    
    # Examiner les méthodes et propriétés disponibles
    logger.info(f"Méthodes et propriétés disponibles:")
    for attr_name in dir(algorithm):
        if not attr_name.startswith('_'):  # Exclure les attributs privés
            attr = getattr(algorithm, attr_name)
            if callable(attr):
                logger.info(f"  - Méthode: {attr_name}")
            else:
                logger.info(f"  - Propriété: {attr_name}")
    
    return algorithm

def main():
    try:
        # Créer les données de test
        csv_files = create_test_csvs()
        database = MockDatabase()
        
        # Charger les algorithmes
        AIDFD = load_algorithm('src.algorithms.aidfd', 'AIDFD')
        Pyro = load_algorithm('src.algorithms.pyro', 'Pyro')
        
        if not AIDFD or not Pyro:
            logger.error("Impossible de charger les algorithmes requis.")
            return
        
        # Créer les instances d'algorithmes
        logger.info("Exécution de l'algorithme AIDFD...")
        aidfd_algo = AIDFD(database)
        aidfd_rules = aidfd_algo.discover_rules()
        
        logger.info("Exécution de l'algorithme PYRO...")
        pyro_algo = Pyro(database)
        pyro_rules = pyro_algo.discover_rules()
        
        # Compter les règles par table
        aidfd_tables = {}
        pyro_tables = {}
        
        for rule in aidfd_rules:
            if hasattr(rule, 'table'):
                aidfd_tables[rule.table] = aidfd_tables.get(rule.table, 0) + 1
        
        for rule in pyro_rules:
            if hasattr(rule, 'table'):
                pyro_tables[rule.table] = pyro_tables.get(rule.table, 0) + 1
        
        logger.info("\n===== RÉSULTATS GLOBAUX =====")
        logger.info(f"Total des règles AIDFD: {len(aidfd_rules)}")
        logger.info(f"Total des règles PYRO: {len(pyro_rules)}")
        
        logger.info("\nRègles par table (AIDFD):")
        for table, count in aidfd_tables.items():
            logger.info(f"  - {table}: {count}")
        
        logger.info("\nRègles par table (PYRO):")
        for table, count in pyro_tables.items():
            logger.info(f"  - {table}: {count}")
        
        # Analyser les différences pour chaque table
        comparison_results = {}
        for table in set(list(aidfd_tables.keys()) + list(pyro_tables.keys())):
            comparison_results[table] = analyze_differences(aidfd_rules, pyro_rules, table)
        
        # Analyser le comportement des algorithmes
        aidfd_instance = analyze_algorithm_behavior(AIDFD, database, "AIDFD")
        pyro_instance = analyze_algorithm_behavior(Pyro, database, "PYRO")
        
        # Afficher les exemples de règles pour chaque algorithme
        logger.info("\n===== EXEMPLES DE RÈGLES AIDFD =====")
        for i, rule in enumerate(aidfd_rules[:10]):
            logger.info(f"{i+1}. {rule}")
        
        logger.info("\n===== EXEMPLES DE RÈGLES PYRO =====")
        for i, rule in enumerate(pyro_rules[:10]):
            logger.info(f"{i+1}. {rule}")
        
        # Nettoyer
        if os.path.exists(test_data_dir):
            import shutil
            shutil.rmtree(test_data_dir)
            logger.info(f"Répertoire de test supprimé: {test_data_dir}")
        
    except Exception as e:
        logger.exception(f"Erreur lors de l'exécution: {str(e)}")

if __name__ == "__main__":
    main()
