#!/usr/bin/env python3
# test_algorithms_fixed.py - Test des algorithmes Java après correction

import os
import sys
import logging
import shutil
from datetime import datetime

# Ajouter le répertoire courant au chemin
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "src"))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Répertoire de données de test
test_dir = os.path.join(current_dir, "test_data")
os.makedirs(test_dir, exist_ok=True)

def create_test_data():
    """Crée des données de test simples"""
    logger.info("Création des données de test...")
    
    # Fichier test simple
    test_file = os.path.join(test_dir, "test_simple.csv")
    with open(test_file, 'w') as f:
        f.write("id,name,age,city,country\n")
        f.write("1,John,25,Paris,France\n")
        f.write("2,Emma,30,Lyon,France\n")
        f.write("3,Paul,28,Marseille,France\n")
        f.write("4,Sophia,22,Paris,France\n")
        f.write("5,James,35,Nice,France\n")
    
    logger.info(f"Fichier de test créé: {test_file}")

class MockDatabase:
    """Classe simulant une base de données pour les tests"""
    def __init__(self):
        self.base_csv_dir = test_dir

def run_algorithm(algorithm_name):
    """Exécute un algorithme spécifique"""
    logger.info(f"\n==== Test de l'algorithme {algorithm_name} ====")
    
    # Importer l'algorithme dynamiquement
    try:
        if algorithm_name.lower() == "aidfd":
            from src.algorithms.aidfd import AIDFD
            algorithm_class = AIDFD
        elif algorithm_name.lower() == "pyro":
            from src.algorithms.pyro import Pyro
            algorithm_class = Pyro
        elif algorithm_name.lower() == "dfd":
            from src.algorithms.dfd import DFD
            algorithm_class = DFD
        elif algorithm_name.lower() == "fdep":
            from src.algorithms.fdep import FDep
            algorithm_class = FDep
        elif algorithm_name.lower() == "fastfds":
            from src.algorithms.fastfds import FastFDs
            algorithm_class = FastFDs
        elif algorithm_name.lower() == "tane":
            from src.algorithms.tane import Tane
            algorithm_class = Tane
        else:
            logger.error(f"Algorithme inconnu: {algorithm_name}")
            return False
    except ImportError as e:
        logger.error(f"Impossible d'importer l'algorithme {algorithm_name}: {e}")
        return False
    
    # Créer l'instance
    db = MockDatabase()
    algorithm = algorithm_class(db)
    
    # Exécuter l'algorithme
    try:
        logger.info(f"Exécution de {algorithm_name}...")
        rules = algorithm._discover_rules_java()
        
        if rules:
            logger.info(f"✅ {algorithm_name} a découvert {len(rules)} règles")
            return True
        else:
            logger.error(f"❌ {algorithm_name} n'a pas découvert de règles")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution de {algorithm_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def cleanup():
    """Nettoie les fichiers temporaires"""
    logger.info("Nettoyage des fichiers temporaires...")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        logger.info(f"Répertoire supprimé: {test_dir}")

def main():
    """Fonction principale"""
    try:
        # Créer les données de test
        create_test_data()
        
        # Algorithmes à tester
        algorithms = ["aidfd", "pyro", "dfd", "fdep", "fastfds", "tane"]
        
        # Résultats
        results = {}
        
        # Tester chaque algorithme
        for algo in algorithms:
            results[algo] = run_algorithm(algo)
        
        # Nettoyage
        cleanup()
        
        # Afficher les résultats
        logger.info("\n==== Résumé des tests ====")
        for algo, success in results.items():
            status = "✅ Succès" if success else "❌ Échec"
            logger.info(f"{algo.upper()}: {status}")
        
        # Vérifier si tous les algorithmes ont réussi
        if all(results.values()):
            logger.info("\n✅ Tous les algorithmes fonctionnent correctement!")
        else:
            failed = [algo for algo, success in results.items() if not success]
            logger.warning(f"\n❌ Les algorithmes suivants ont échoué: {', '.join(failed)}")
    
    except Exception as e:
        logger.exception(f"Erreur lors de l'exécution: {e}")

if __name__ == "__main__":
    main()
