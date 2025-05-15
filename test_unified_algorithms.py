#!/usr/bin/env python3
# test_unified_algorithms.py - Test unifié pour tous les algorithmes FD

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
    """Crée les données de test"""
    logger.info("Création des données de test...")
    
    # Fichier test 1 - données simples
    test_file1 = os.path.join(test_dir, "customers.csv")
    with open(test_file1, "w") as f:
        f.write("customer_id,first_name,last_name,email,city,country\n")
        f.write("1,John,Smith,john.smith@example.com,Paris,France\n")
        f.write("2,Emma,Johnson,emma.j@example.com,Lyon,France\n")
        f.write("3,Paul,Williams,p.williams@example.com,Marseille,France\n")
        f.write("4,Sophia,Brown,sophia.brown@example.com,Paris,France\n")
        f.write("5,James,Davis,james.d@example.com,Nice,France\n")
        f.write("6,Olivia,Miller,o.miller@example.com,Bordeaux,France\n")
        f.write("7,Alexander,Wilson,alex.w@example.com,Lille,France\n")
        f.write("8,Emily,Garcia,emily.g@example.com,Toulouse,France\n")
        f.write("9,Daniel,Taylor,d.taylor@example.com,Paris,France\n")
        f.write("10,Sophie,Thomas,s.thomas@example.com,Lyon,France\n")
    logger.info(f"Fichier créé: {test_file1}")
    
    # Fichier test 2 - données d'employés
    test_file2 = os.path.join(test_dir, "employees.csv")
    with open(test_file2, "w") as f:
        f.write("emp_id,first_name,last_name,department,manager_id,salary\n")
        f.write("101,Jean,Dupont,IT,201,55000\n")
        f.write("102,Marie,Martin,HR,202,48000\n")
        f.write("103,Pierre,Durand,IT,201,52000\n")
        f.write("104,Sophie,Leroy,Finance,203,60000\n")
        f.write("105,Thomas,Petit,IT,201,51000\n")
        f.write("106,Claire,Moreau,HR,202,49000\n")
        f.write("107,Antoine,Robert,Finance,203,58000\n")
        f.write("108,Emilie,Simon,IT,201,53000\n")
        f.write("109,Nicolas,Michel,Marketing,204,51000\n")
        f.write("110,Julie,Dubois,Marketing,204,50000\n")
    logger.info(f"Fichier créé: {test_file2}")
    
    return [test_file1, test_file2]

class MockDatabase:
    """Classe simulant une base de données pour les tests"""
    def __init__(self):
        self.base_csv_dir = test_dir

def test_algorithm(algo_class, algo_name):
    """Teste un algorithme spécifique"""
    logger.info(f"\n==== Test de {algo_name} ====")
    db = MockDatabase()
    algorithm = algo_class(db)
    
    # Assurer que l'algorithme utilise le répertoire de test
    algorithm.database = db
    
    try:
        # Si c'est AIDFD, utiliser test_data/customers.csv
        if algo_name == "AIDFD":
            csv_file = os.path.join(test_dir, "customers.csv")
            rules = algorithm._discover_rules_java(csv_file=csv_file)
        else:
            # Pour les autres algorithmes, découvrir les règles normalement
            rules = algorithm._discover_rules_java()
        
        # Si nous avons des règles
        if rules:
            if isinstance(rules, list):
                # Format de liste pour AIDFD
                logger.info(f"✅ {algo_name} a découvert {len(rules)} dépendances fonctionnelles")
                logger.info("Exemples de dépendances:")
                
                # Afficher les 5 premières règles
                for rule in rules[:5]:  
                    if hasattr(rule, 'lhs') and hasattr(rule, 'rhs'):
                        logger.info(f"  - {','.join(rule.lhs)} -> {rule.rhs}")
                    else:
                        logger.info(f"  - {rule}")
                return True
            elif isinstance(rules, dict):
                # Format de dictionnaire pour les autres algorithmes
                logger.info(f"✅ {algo_name} a découvert {len(rules)} dépendances fonctionnelles")
                logger.info("Exemples de dépendances:")
                
                # Afficher les 5 premières règles
                for rule in list(rules.keys())[:5]:
                    logger.info(f"  - {rule}")
                return True
            else:
                logger.error(f"❌ {algo_name} a retourné un format de règles non pris en charge: {type(rules)}")
                return False
        else:
            logger.error(f"❌ {algo_name} n'a pas découvert de dépendances")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution de {algo_name}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def cleanup():
    """Nettoie les fichiers temporaires"""
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        logger.info(f"Répertoire supprimé: {test_dir}")

def main():
    """Fonction principale"""
    try:
        # Créer les données de test
        create_test_data()
        
        # Importer les algorithmes
        from src.algorithms.aidfd import AIDFD
        from src.algorithms.pyro import Pyro
        from src.algorithms.dfd import DFD
        from src.algorithms.fdep import FDep
        from src.algorithms.fastfds import FastFDs
        from src.algorithms.tane import Tane
        
        # Algorithmes à tester
        algorithms = [
            (AIDFD, "AIDFD"),
            (Pyro, "Pyro"),
            (DFD, "DFD"),
            (FDep, "FDep"),
            (FastFDs, "FastFDs"),
            (Tane, "TANE")
        ]
        
        # Résultats
        results = {}
        
        # Tester chaque algorithme
        for algo_class, algo_name in algorithms:
            results[algo_name] = test_algorithm(algo_class, algo_name)
        
        # Nettoyage
        cleanup()
        
        # Afficher les résultats
        logger.info("\n==== Résumé des tests ====")
        for algo_name, success in results.items():
            status = "✅ Succès" if success else "❌ Échec"
            logger.info(f"{algo_name}: {status}")
        
    except Exception as e:
        logger.exception(f"Erreur lors de l'exécution: {str(e)}")

if __name__ == "__main__":
    main()
