#!/usr/bin/env python3
# test_algorithms_simple.py - Test simple des algorithmes FD

import os
import sys
import logging
import pandas as pd
import time

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Créer un répertoire pour les fichiers de test
test_dir = "test_simple_fd"
os.makedirs(test_dir, exist_ok=True)

# Créer un fichier CSV de test simple
test_file = os.path.join(test_dir, "simple.csv")
df = pd.DataFrame({
    'id': [1, 2, 3, 4, 5],
    'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eva'],
    'age': [25, 30, 35, 40, 45],
    'city': ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Lille']
})
df.to_csv(test_file, index=False)
logger.info(f"Fichier CSV de test créé: {test_file}")

# Base de données fictive pour les tests
class MockDatabase:
    def __init__(self):
        self.base_csv_dir = test_dir

# Tester l'algorithme FDep avec un implémentation simple directe
def test_fdep():
    logger.info("\n===== TEST DE FDEP (IMPLÉMENTATION DIRECTE) =====")
    
    # Lire le fichier CSV
    df = pd.read_csv(test_file)
    
    # Chercher des dépendances fonctionnelles simples (X -> Y)
    logger.info("Recherche de dépendances fonctionnelles...")
    
    fds = []
    columns = list(df.columns)
    
    for col1 in columns:
        for col2 in columns:
            if col1 != col2:
                # Vérifier si col1 -> col2
                grouped = df.groupby(col1)[col2]
                is_fd = True
                
                for _, group in grouped:
                    if len(set(group)) > 1:
                        is_fd = False
                        break
                
                if is_fd:
                    fds.append(f"{col1} -> {col2}")
    
    # Afficher les résultats
    logger.info(f"Nombre de dépendances fonctionnelles découvertes: {len(fds)}")
    for fd in fds:
        logger.info(f"  - {fd}")
    
    return fds

# Exécuter le test
fds = test_fdep()

# Nettoyer
import shutil
if os.path.exists(test_dir):
    shutil.rmtree(test_dir)
    logger.info(f"Répertoire de test supprimé: {test_dir}")
