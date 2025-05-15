#!/usr/bin/env python3
# test_fd_algorithms_simple.py

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

# Créer les répertoires nécessaires
os.makedirs('src/algorithms/bins/metanome', exist_ok=True)
os.makedirs('test_fd_data', exist_ok=True)

# Créer un fichier CSV simple pour les tests
def create_test_csv():
    """Crée un fichier CSV simple pour les tests."""
    df = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'city': ['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Lille'],
        'country': ['France', 'France', 'France', 'France', 'France'],
        'zipcode': ['75001', '69001', '13001', '31000', '59000'],
        'city_zipcode': ['Paris_75001', 'Lyon_69001', 'Marseille_13001', 'Toulouse_31000', 'Lille_59000']
    })
    
    csv_path = os.path.join('test_fd_data', 'test_fd.csv')
    df.to_csv(csv_path, index=False)
    
    logging.info(f"Fichier CSV de test créé: {csv_path}")
    return csv_path

# Classe de base simplifiée pour les tests
class MockDatabase:
    def __init__(self):
        self.base_csv_dir = 'test_fd_data'

# Découverte simplifiée de dépendances fonctionnelles
def discover_fds_simple(df, table_name='test_table', max_lhs_size=1):
    """
    Découvre les dépendances fonctionnelles avec une approche simple.
    """
    import itertools
    from collections import defaultdict
    
    discovered_fds = []
    columns = list(df.columns)
    
    # Pour chaque taille possible du déterminant jusqu'à max_lhs_size
    for lhs_size in range(1, min(max_lhs_size + 1, len(columns))):
        # Pour chaque combinaison possible de colonnes comme déterminant
        for lhs_cols in itertools.combinations(columns, lhs_size):
            # Pour chaque colonne possible comme dépendante
            for rhs_col in columns:
                # Ignorer si la colonne dépendante est dans le déterminant
                if rhs_col in lhs_cols:
                    continue
                
                # Créer un dictionnaire pour regrouper les valeurs de rhs_col par valeurs de lhs_cols
                dependency_dict = defaultdict(set)
                
                # Remplir le dictionnaire avec les valeurs
                for _, row in df.iterrows():
                    # Créer une clé composite pour les valeurs du déterminant
                    lhs_key = tuple(str(row[col]) for col in lhs_cols)
                    rhs_val = str(row[rhs_col])
                    dependency_dict[lhs_key].add(rhs_val)
                
                # Si pour chaque valeur distincte de lhs_cols, il y a exactement une valeur de rhs_col,
                # alors lhs_cols -> rhs_col est une dépendance fonctionnelle
                is_fd = all(len(values) == 1 for values in dependency_dict.values())
                
                if is_fd:
                    fd = f"{','.join(lhs_cols)} -> {rhs_col}"
                    discovered_fds.append((lhs_cols, rhs_col))
                    logging.info(f"Dépendance fonctionnelle découverte: {fd}")
    
    return discovered_fds

def main():
    try:
        # Créer le fichier CSV de test
        csv_path = create_test_csv()
        
        # Lire le fichier avec pandas
        df = pd.read_csv(csv_path)
        logging.info(f"Données chargées: {len(df)} lignes, {len(df.columns)} colonnes")
        
        # Tester l'algorithme de découverte de dépendances fonctionnelles
        start_time = datetime.now()
        fds = discover_fds_simple(df)
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        # Afficher les résultats
        logging.info(f"Temps d'exécution: {elapsed:.2f} secondes")
        logging.info(f"Dépendances fonctionnelles découvertes ({len(fds)}):")
        for lhs, rhs in fds:
            logging.info(f"  - {','.join(lhs)} -> {rhs}")
            
        # Démontrer comment créer une instance des algorithmes avec notre solution de repli
        logging.info("\n===== TANE =====")
        logging.info("Pour utiliser TANE avec la solution de repli:")
        logging.info("from src.algorithms.tane import Tane")
        logging.info("tane = Tane(database)")
        logging.info("results = tane.discover_rules(use_fallback=True)")
        
        logging.info("\n===== DFD =====")
        logging.info("Pour utiliser DFD avec la solution de repli:")
        logging.info("from src.algorithms.dfd import DFD")
        logging.info("dfd = DFD(database)")
        logging.info("results = dfd.discover_rules(use_fallback=True)")
        
        logging.info("\n===== FastFDs =====")
        logging.info("Pour utiliser FastFDs avec la solution de repli:")
        logging.info("from src.algorithms.fastfds import FastFDs")
        logging.info("fastfds = FastFDs(database)")
        logging.info("results = fastfds.discover_rules(use_fallback=True)")
        
        logging.info("\n===== FDep =====")
        logging.info("Pour utiliser FDep avec la solution de repli:")
        logging.info("from src.algorithms.fdep import FDep")
        logging.info("fdep = FDep(database)")
        logging.info("results = fdep.discover_rules(use_fallback=True)")
        
    except Exception as e:
        logging.error(f"Erreur: {str(e)}")
    finally:
        # Nettoyer les fichiers de test
        if os.path.exists('test_fd_data'):
            shutil.rmtree('test_fd_data')
            logging.info(f"Répertoire de test supprimé")

if __name__ == "__main__":
    main()
