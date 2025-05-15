#!/usr/bin/env python3
# test_fd_algorithms.py

import os
import sys
import logging
import pandas as pd
from datetime import datetime

# Configurez le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Ajoutez le chemin du projet au PYTHONPATH
sys.path.append('/Users/famat/PycharmProjects/MATILDA_ALL/MATILDA')

# Importez les classes d'algorithme
from src.algorithms.tane import Tane
from src.algorithms.fdep import FDep
from src.algorithms.dfd import DFD
from src.algorithms.fastfds import FastFDs

# Créez une classe de test pour la base de données
class MockDatabase:
    def __init__(self, csv_dir):
        self.base_csv_dir = csv_dir

def create_test_csv():
    """Crée un fichier CSV simple pour les tests."""
    # Créez un répertoire temporaire pour les fichiers CSV
    test_dir = 'test_csv'
    os.makedirs(test_dir, exist_ok=True)
    
    # Créez un DataFrame simple avec des dépendances fonctionnelles évidentes
    df = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'city': ['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Lille'],
        'country': ['France', 'France', 'France', 'France', 'France'],
        'zipcode': ['75001', '69001', '13001', '31000', '59000'],
        'city_zipcode': ['Paris_75001', 'Lyon_69001', 'Marseille_13001', 'Toulouse_31000', 'Lille_59000']
    })
    
    # Enregistrez le DataFrame au format CSV
    csv_path = os.path.join(test_dir, 'test_data.csv')
    df.to_csv(csv_path, index=False)
    
    logging.info(f"Fichier CSV de test créé: {csv_path}")
    return test_dir

def run_all_tests():
    """Exécute tous les tests pour chaque algorithme."""
    # Créez le fichier CSV de test
    test_dir = create_test_csv()
    
    # Créez une instance de base de données fictive
    mock_db = MockDatabase(test_dir)
    
    # Liste des algorithmes à tester
    algorithms = [
        ('TANE', Tane(mock_db)),
        ('FDEP', FDep(mock_db)),
        ('DFD', DFD(mock_db)),
        ('FastFDs', FastFDs(mock_db)),
    ]
    
    # Pour chaque algorithme, exécutez le test
    for name, algorithm in algorithms:
        logging.info(f"\n===== Test de l'algorithme {name} =====")
        
        # Configuration des paramètres
        params = {
            'max_lhs_size': 3,  # Taille maximale du côté gauche
            'min_confidence': 0.9,  # Confiance minimale
        }
        
        try:
            # Version Java
            logging.info(f"Exécution de {name} (version Java)...")
            start_time = datetime.now()
            rules = algorithm.discover_rules(**params)
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            
            if rules:
                logging.info(f"Succès! {len(rules)} dépendances fonctionnelles découvertes en {elapsed:.2f} secondes")
                for fd, (support, confidence) in list(rules.items())[:5]:  # Afficher les 5 premières règles
                    logging.info(f"  - {fd} (support: {support}, confiance: {confidence})")
                if len(rules) > 5:
                    logging.info(f"  ... et {len(rules) - 5} autres règles")
            else:
                logging.warning(f"Échec ou aucune dépendance fonctionnelle découverte")
                
                # Version Python (solution de repli)
                logging.info(f"Exécution de {name} (version Python, solution de repli)...")
                start_time = datetime.now()
                params['use_fallback'] = True
                rules = algorithm.discover_rules(**params)
                end_time = datetime.now()
                elapsed = (end_time - start_time).total_seconds()
                
                if rules:
                    logging.info(f"Succès avec la solution de repli! {len(rules)} dépendances fonctionnelles découvertes en {elapsed:.2f} secondes")
                    for fd, (support, confidence) in list(rules.items())[:5]:  # Afficher les 5 premières règles
                        logging.info(f"  - {fd} (support: {support}, confiance: {confidence})")
                    if len(rules) > 5:
                        logging.info(f"  ... et {len(rules) - 5} autres règles")
                else:
                    logging.error(f"Échec total: aucune dépendance fonctionnelle découverte!")
        
        except Exception as e:
            logging.error(f"Erreur lors de l'exécution de {name}: {str(e)}")
    
    # Nettoyage du répertoire de test
    logging.info("Nettoyage...")
    for file in os.listdir(test_dir):
        os.remove(os.path.join(test_dir, file))
    os.rmdir(test_dir)
    logging.info("Tests terminés.")

if __name__ == "__main__":
    run_all_tests()
