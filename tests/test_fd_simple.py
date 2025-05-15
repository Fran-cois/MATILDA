#!/usr/bin/env python3
# test_fd_simple.py

import os
import sys
import logging
import pandas as pd
import shutil
from datetime import datetime

# Configurez le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Créer un répertoire temporaire pour les tests
TEST_DIR = 'test_fd_temp'
os.makedirs(TEST_DIR, exist_ok=True)

def create_test_csv():
    """Crée un fichier CSV simple pour les tests."""
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
    csv_path = os.path.join(TEST_DIR, 'test_data.csv')
    df.to_csv(csv_path, index=False)
    
    logging.info(f"Fichier CSV de test créé: {csv_path}")
    return csv_path

def discover_fds_simple(df):
    """
    Méthode simplifiée pour découvrir les dépendances fonctionnelles.
    Cette implémentation vérifie uniquement les dépendances de base (une colonne -> une colonne).
    """
    import itertools
    from collections import defaultdict
    
    discovered_fds = []
    columns = list(df.columns)
    
    # Pour chaque paire de colonnes, vérifier s'il y a une dépendance fonctionnelle
    logging.info(f"Recherche de dépendances fonctionnelles entre {len(columns)} colonnes...")
    for col1, col2 in itertools.permutations(columns, 2):
        # Créer un dictionnaire pour regrouper les valeurs de col2 par valeurs de col1
        dependency_dict = defaultdict(set)
        
        # Remplir le dictionnaire avec les valeurs
        for _, row in df.iterrows():
            val1 = row[col1]
            val2 = row[col2]
            dependency_dict[val1].add(val2)
        
        # Si pour chaque valeur distincte de col1, il y a exactement une valeur de col2,
        # alors col1 -> col2 est une dépendance fonctionnelle
        is_fd = all(len(values) == 1 for values in dependency_dict.values())
        
        if is_fd:
            fd = f"{col1} -> {col2}"
            discovered_fds.append(fd)
            logging.info(f"Dépendance fonctionnelle découverte: {fd}")
    
    return discovered_fds

def main():
    try:
        # Créer le fichier CSV de test
        csv_path = create_test_csv()
        
        # Lire le fichier avec pandas
        df = pd.read_csv(csv_path)
        logging.info(f"Données chargées: {len(df)} lignes, {len(df.columns)} colonnes")
        
        # Découvrir les dépendances fonctionnelles
        start_time = datetime.now()
        fds = discover_fds_simple(df)
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        # Afficher les résultats
        logging.info(f"Temps d'exécution: {elapsed:.2f} secondes")
        logging.info(f"Dépendances fonctionnelles découvertes ({len(fds)}):")
        for fd in fds:
            logging.info(f"  - {fd}")
        
    except Exception as e:
        logging.error(f"Erreur: {str(e)}")
    finally:
        # Nettoyer les fichiers de test
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)
            logging.info(f"Répertoire de test {TEST_DIR} supprimé")

if __name__ == "__main__":
    main()
