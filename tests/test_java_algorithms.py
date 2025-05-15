#!/usr/bin/env python3
# test_java_algorithms.py - Test les implémentations Java des algorithmes FD

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
    logger.info(f"Fichier CSV de test créé: {test_file1}")
    
    return test_file1

def test_aidfd_java():
    """Teste l'implémentation Java de AIDFD"""
    from src.algorithms.aidfd import AIDFD
    
    logger.info("\n==== Test de l'implémentation Java de AIDFD ====")
    db = MockDatabase()
    algorithm = AIDFD(db)
    
    # Forcer l'utilisation de l'implémentation Java
    rules = algorithm._discover_rules_java()
    
    if rules:
        logger.info(f"✅ L'implémentation Java de AIDFD a réussi à découvrir {len(rules)} règles")
        logger.info("Exemples de règles:")
        for rule in rules[:5]:
            logger.info(f"  - {rule}")
    else:
        logger.error("❌ L'implémentation Java de AIDFD a échoué")
    
    return rules

def test_pyro_java():
    """Teste l'implémentation Java de Pyro"""
    from src.algorithms.pyro import Pyro
    
    logger.info("\n==== Test de l'implémentation Java de Pyro ====")
    db = MockDatabase()
    algorithm = Pyro(db)
    
    # Forcer l'utilisation de l'implémentation Java
    rules = algorithm._discover_rules_java()
    
    if rules:
        logger.info(f"✅ L'implémentation Java de Pyro a réussi à découvrir {len(rules)} règles")
        logger.info("Exemples de règles:")
        for rule in rules[:5]:
            logger.info(f"  - {rule}")
    else:
        logger.error("❌ L'implémentation Java de Pyro a échoué")
    
    return rules

def cleanup():
    """Nettoie les fichiers temporaires"""
    import shutil
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)
        logger.info(f"Répertoire de test supprimé: {test_data_dir}")

if __name__ == "__main__":
    try:
        # Créer les données de test
        create_test_csvs()
        
        # Tester AIDFD
        aidfd_rules = test_aidfd_java()
        
        # Tester Pyro
        pyro_rules = test_pyro_java()
        
        # Nettoyer
        cleanup()
        
        # Résumé
        logger.info("\n==== Résumé des tests ====")
        logger.info(f"AIDFD Java: {'Succès' if aidfd_rules else 'Échec'}")
        logger.info(f"Pyro Java: {'Succès' if pyro_rules else 'Échec'}")
        
    except Exception as e:
        logger.exception(f"Erreur lors de l'exécution des tests: {str(e)}")
