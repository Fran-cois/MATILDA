#!/usr/bin/env python3
# test_tane_integration.py - Test de l'intégration de TANE via la classe Python

import os
import sys
import shutil
import logging
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

def test_tane():
    """Teste l'algorithme TANE via son interface Python"""
    from src.algorithms.tane import Tane
    
    logger.info("\n==== Test de l'algorithme TANE via la classe Python ====")
    
    # Créer une instance de la base de données simulée
    db = MockDatabase()
    
    # Créer une instance de l'algorithme TANE
    algorithm = Tane(db)
    
    # Exécuter la découverte de règles
    try:
        # Configuration spécifique de l'algorithme
        settings = {
            'max_lhs_size': 3,
            'use_java': True  # Force l'utilisation de Java
        }
        
        # Découvrir les règles
        rules = algorithm.discover_rules(**settings)
        
        if rules:
            logger.info(f"✅ Réussite de la découverte avec {len(rules)} règles")
            logger.info("Exemples de règles:")
            for rule in rules[:5]:
                logger.info(f"  - {rule}")
            return rules
        else:
            logger.warning("⚠️ Aucune règle n'a été découverte")
            return []
    except Exception as e:
        logger.error(f"❌ Échec de la découverte de règles: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def cleanup():
    """Nettoie les fichiers temporaires"""
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)
        logger.info(f"Répertoire de test supprimé: {test_data_dir}")

if __name__ == "__main__":
    try:
        # Créer les données de test
        create_test_csvs()
        
        # Tester TANE
        tane_rules = test_tane()
        
        # Nettoyer
        cleanup()
        
        # Résumé
        logger.info("\n==== Résumé des tests ====")
        logger.info(f"TANE: {'Succès' if tane_rules else 'Échec'}")
        
    except Exception as e:
        logger.exception(f"Erreur lors de l'exécution des tests: {str(e)}")
