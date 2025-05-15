#!/usr/bin/env python3
# test_all_corrected_algos.py - Teste tous les algorithmes Java après corrections

import os
import sys
import logging
import pandas as pd
from datetime import datetime

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

class MockDatabase:
    def __init__(self):
        self.base_csv_dir = test_data_dir

def create_test_csvs():
    """Crée des fichiers CSV de test simples"""
    logger.info("Création des fichiers CSV de test")
    
    # Premier fichier - données simples
    test_file1 = os.path.join(test_data_dir, 'test_fd.csv')
    with open(test_file1, 'w') as f:
        f.write('id,name,age,city,country\n')
        f.write('1,John,25,Paris,France\n')
        f.write('2,Emma,30,Lyon,France\n')
        f.write('3,Paul,28,Marseille,France\n')
        f.write('4,Sophia,22,Paris,France\n')
        f.write('5,James,35,Nice,France\n')
    logger.info(f"Fichier CSV de test créé: {test_file1}")
    
    # Deuxième fichier - données plus complexes
    test_file2 = os.path.join(test_data_dir, 'test_fd2.csv')
    with open(test_file2, 'w') as f:
        f.write('emp_id,first_name,last_name,department,manager_id,salary\n')
        f.write('101,Jean,Dupont,IT,201,55000\n')
        f.write('102,Marie,Martin,HR,202,48000\n')
        f.write('103,Pierre,Durand,IT,201,52000\n')
        f.write('104,Sophie,Leroy,Finance,203,60000\n')
        f.write('105,Thomas,Petit,IT,201,51000\n')
    logger.info(f"Fichier CSV de test créé: {test_file2}")
    
    return [test_file1, test_file2]

def test_algorithm(algo_class, algo_name):
    """Teste un algorithme spécifique"""
    logger.info(f"\n==== Test de l'implémentation Java de {algo_name} ====")
    db = MockDatabase()
    algorithm = algo_class(db)
    
    # Forcer l'utilisation de l'implémentation Java
    try:
        rules = algorithm._discover_rules_java()
        
        if rules:
            logger.info(f"✅ L'implémentation Java de {algo_name} a réussi à découvrir {len(rules)} règles")
            logger.info("Exemples de règles:")
            for rule in rules[:5]:
                logger.info(f"  - {rule}")
        else:
            logger.error(f"❌ L'implémentation Java de {algo_name} a échoué (aucune règle découverte)")
        
        return rules
    except Exception as e:
        logger.error(f"❌ L'implémentation Java de {algo_name} a échoué avec l'erreur: {str(e)}")
        return None

def cleanup():
    """Nettoie les fichiers temporaires"""
    import shutil
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)
        logger.info(f"Répertoire de test supprimé: {test_data_dir}")
    
    # Nettoyer également les fichiers de résultats générés
    results_dir = os.path.join(os.getcwd(), "results")
    if os.path.exists(results_dir):
        for file in os.listdir(results_dir):
            file_path = os.path.join(results_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Erreur lors de la suppression du fichier {file_path}: {str(e)}")

if __name__ == "__main__":
    try:
        # Créer les données de test
        create_test_csvs()
        
        # Liste des algorithmes à tester
        from src.algorithms.aidfd import AIDFD
        from src.algorithms.pyro import Pyro
        from src.algorithms.dfd import DFD
        from src.algorithms.fdep import FDep
        from src.algorithms.fastfds import FastFDs
        from src.algorithms.tane import Tane
        
        # Exécuter les tests
        results = {}
        
        # Tester AIDFD
        results["AIDFD"] = test_algorithm(AIDFD, "AIDFD")
        
        # Tester Pyro
        results["Pyro"] = test_algorithm(Pyro, "Pyro")
        
        # Tester DFD
        results["DFD"] = test_algorithm(DFD, "DFD")
        
        # Tester FDep
        results["FDep"] = test_algorithm(FDep, "FDep")
        
        # Tester FastFDs
        results["FastFDs"] = test_algorithm(FastFDs, "FastFDs")
        
        # Tester Tane
        results["Tane"] = test_algorithm(Tane, "Tane")
        
        # Nettoyer
        cleanup()
        
        # Résumé
        logger.info("\n==== Résumé des tests ====")
        for algo, rules in results.items():
            logger.info(f"{algo} Java: {'Succès' if rules else 'Échec'}")
        
    except Exception as e:
        logger.exception(f"Erreur lors de l'exécution des tests: {str(e)}")
