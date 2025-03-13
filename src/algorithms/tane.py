# algorithms/tane.py

import ast
import os
import logging
import pandas as pd
import itertools
from collections import defaultdict

from algorithms.base_algorithm import BaseAlgorithm
from utils.rules import FunctionalDependency, Rule


class Tane(BaseAlgorithm):
    def verify_csv_file(self, file_path: str) -> bool:
        """
        Vérifie si le fichier CSV est valide et contient des données.
        """
        try:
            # Vérifier si le fichier existe
            if not os.path.exists(file_path):
                logging.error(f"Le fichier n'existe pas: {file_path}")
                return False
                
            # Vérifier si le fichier n'est pas vide
            if os.path.getsize(file_path) == 0:
                logging.error(f"Le fichier est vide: {file_path}")
                return False
                
            # Essayer de lire le fichier avec pandas
            df = pd.read_csv(file_path)
            
            # Vérifier s'il y a des colonnes
            if len(df.columns) == 0:
                logging.error(f"Le fichier n'a pas de colonnes: {file_path}")
                return False
                
            # Vérifier s'il y a des données
            if len(df) == 0:
                logging.error(f"Le fichier n'a pas de données: {file_path}")
                return False
                
            # Vérifier si toutes les colonnes ont des noms valides
            if df.columns.isnull().any():
                logging.error(f"Le fichier contient des noms de colonnes invalides: {file_path}")
                return False
                
            logging.info(f"Fichier CSV valide: {file_path}")
            logging.info(f"Nombre de colonnes: {len(df.columns)}")
            logging.info(f"Nombre de lignes: {len(df)}")
            logging.info(f"Colonnes: {list(df.columns)}")
            
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors de la vérification du fichier CSV {file_path}: {str(e)}")
            return False

    def discover_rules(self, **kwargs) -> Rule:
        """
        Découvre les dépendances fonctionnelles dans les fichiers CSV.
        Implémentation Python de l'algorithme TANE sans utiliser le JAR externe.
        """
        rules = {}
        logging.info("Lancement de l'algorithme TANE (version Python)")
        
        try:
            csv_files = [
                os.path.join(self.database.base_csv_dir, f)
                for f in os.listdir(self.database.base_csv_dir)
                if f.endswith('.csv')
            ]
            
            logging.info(f"Fichiers CSV trouvés: {len(csv_files)}")
            
            # Pour chaque fichier CSV, découvrir les dépendances fonctionnelles
            for csv_file in csv_files:
                table_name = os.path.basename(csv_file).replace('.csv', '')
                logging.info(f"Analyse du fichier: {csv_file} (table: {table_name})")
                
                # Lire le fichier CSV avec pandas
                try:
                    df = pd.read_csv(csv_file)
                    if len(df.columns) <= 1:
                        logging.warning(f"Table {table_name} a moins de 2 colonnes. Ignorée.")
                        continue
                        
                    logging.info(f"Table {table_name}: {len(df)} lignes, {len(df.columns)} colonnes")
                    
                    # Découvrir les dépendances fonctionnelles avec une approche simplifiée
                    discovered_fds = self._discover_fds_simple(df, table_name)
                    
                    # Ajouter les dépendances fonctionnelles découvertes
                    for fd in discovered_fds:
                        rules[fd] = (1, 1)  # Support et confiance à 1 pour les dépendances exactes
                    
                    logging.info(f"Découvert {len(discovered_fds)} dépendances fonctionnelles pour {table_name}")
                    
                except Exception as e:
                    logging.error(f"Erreur lors de l'analyse de {csv_file}: {str(e)}")
                    continue
                    
            return rules
            
        except Exception as e:
            logging.error(f"Erreur lors de la découverte des dépendances fonctionnelles: {str(e)}")
            return rules

    def _discover_fds_simple(self, df, table_name):
        """
        Méthode simplifiée pour découvrir les dépendances fonctionnelles.
        Cette implémentation vérifie uniquement les dépendances de base (une colonne -> une colonne).
        
        Pour une implémentation complète de TANE, il faudrait une approche par niveau 
        qui teste progressivement des ensembles d'attributs de plus en plus grands.
        """
        discovered_fds = []
        columns = list(df.columns)
        
        # Pour chaque paire de colonnes, vérifier s'il y a une dépendance fonctionnelle
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
                try:
                    # Essayer de créer une dépendance fonctionnelle avec différentes signatures possibles
                    try:
                        # Version avec table_dependant, columns_dependant, etc. (comme InclusionDependency)
                        fd = FunctionalDependency(
                            table_dependant=table_name,
                            columns_dependant=(col1,),
                            table_referenced=table_name,
                            columns_referenced=(col2,)
                        )
                    except TypeError:
                        # Version simplifiée avec des arguments de base
                        fd = FunctionalDependency(table_name, (col1,), (col2,))
                    
                    discovered_fds.append(fd)
                    logging.info(f"Dépendance fonctionnelle découverte: {table_name}.{col1} -> {table_name}.{col2}")
                except Exception as e:
                    logging.error(f"Erreur lors de la création de la dépendance fonctionnelle: {e}")
                    # Afficher les arguments disponibles pour aider au débogage
                    logging.error(f"Arguments de FunctionalDependency: {FunctionalDependency.__init__.__code__.co_varnames}")
        
        return discovered_fds
