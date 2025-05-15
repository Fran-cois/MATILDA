# algorithms/fdep.py

import ast
import os
import glob
import random
import logging
import pandas as pd
import itertools
from collections import defaultdict
from datetime import datetime

# Utiliser des imports relatifs pour éviter les problèmes de chemin de module
from .base_algorithm import BaseAlgorithm
from ..utils.rules import FunctionalDependency, Rule
from ..utils.run_cmd import run_cmd


class FDep(BaseAlgorithm):
    """
    Implémentation de l'algorithme FDep pour la découverte de dépendances fonctionnelles.
    Cette implémentation utilise un JAR Java externe avec une solution de repli Python en cas d'échec.
    """

    def __init__(self, database):
        """
        Initialise l'algorithme FDep avec une base de données.
        """
        super().__init__(database)
        self.min_confidence = 0.8  # Confiance minimale pour les règles
        self.min_support = 0.1     # Support minimal pour les règles
    
    def verify_csv_file(self, file_path: str):
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

    def discover_rules(self, **kwargs):
        """
        Découvre les dépendances fonctionnelles.
        Essaie d'abord d'utiliser l'implémentation Java de l'algorithme FDep via le JAR externe.
        En cas d'échec, utilise une implémentation Python simplifiée.
        """
        rules = {}
        use_fallback = kwargs.get('use_fallback', False)
        
        if not use_fallback:
            logging.info("Lancement de l'algorithme FDep (version Java)")
            try_java = self._discover_rules_java(**kwargs)
            if try_java:
                return try_java
            logging.warning("L'exécution de FDep (Java) a échoué, utilisation de l'implémentation Python simplifiée")
        
        # Utiliser l'implémentation Python simplifiée
        logging.info("Lancement de l'algorithme FDep (version Python simplifiée)")
        return self._discover_rules_python(**kwargs)
    
    def _discover_rules_java(self, **kwargs):
        """
        Implémentation de la découverte de dépendances fonctionnelles via FDep (JAR Java).
        """
        rules = {}
        try:
            csv_file = kwargs.get('csv_file', 'default.csv')
            script_dir = os.path.dirname(os.path.abspath(__file__))
            algorithm_name = "FDEP"
            classPath = "de.metanome.algorithms.fdep.FdepAlgorithm"  # Correction du nom de classe
            rule_type = "fds"
            params = " --file-key INPUT_FILES"

            #  get csv files from database
            csv_files = " ".join(
                [
                    os.path.join(self.database.base_csv_dir, f)
                    for f in os.listdir(self.database.base_csv_dir)
                    if f.endswith('.csv')
                ]
            )
            
            current_time = datetime.now()
            jar_path = f"{script_dir}/bins/metanome/"
            file_name = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_{algorithm_name}'
            # Ajouter tous les JAR du répertoire dans le classpath
            all_jars = [f"{jar_path}{jar_file}" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]
            classpath = ":".join(all_jars)
            
            cmd_string = (
                f"""java -Xmx4g -cp {jar_path}metanome-cli-1.2-SNAPSHOT.jar:{jar_path}*.jar """
                f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file} """
                f"""--file-key INPUT_FILES --separator "," --header """
                f"""--output file:{file_name}"""
            )
            
            logging.info(f"Exécution de la commande: {cmd_string}")
            
            if not run_cmd(cmd_string):
                logging.error("Échec de l'exécution de la commande FDep")
                logging.info("Utilisation de l'implémentation Python comme solution de secours pour FDep")
                
                # L'algorithme FDep fonctionne à base d'ensembles d'évidence
                # Implémentons une version simplifiée de cet algorithme
                try:
                    import pandas as pd
                    from itertools import combinations
                    
                    # Utiliser le premier fichier CSV s'il y en a plusieurs
                    if isinstance(csv_file, str) and '*' in csv_file:
                        csv_files = glob.glob(csv_file)
                        if csv_files:
                            csv_file = csv_files[0]
                        else:
                            raise ValueError(f"Aucun fichier correspondant à {csv_file}")
                    
                    # Si le csv_file est une chaîne contenant plusieurs fichiers, prendre le premier
                    if isinstance(csv_file, str) and ' ' in csv_file:
                        csv_file = csv_file.split()[0]
                    
                    if not os.path.exists(csv_file):
                        csv_file = os.path.join(self.database.base_csv_dir, os.listdir(self.database.base_csv_dir)[0])
                        if not csv_file.endswith('.csv'):
                            for f in os.listdir(self.database.base_csv_dir):
                                if f.endswith('.csv'):
                                    csv_file = os.path.join(self.database.base_csv_dir, f)
                                    break
                    
                    logging.info(f"Utilisation du fichier CSV pour FDep Python: {csv_file}")
                    
                    # Charger le fichier CSV
                    df = pd.read_csv(csv_file)
                    columns = list(df.columns)
                    num_rows = len(df)
                    
                    # Dictionnaire pour stocker les DFs découvertes
                    discovered_fds = {}
                    
                    # Calculer les "agree sets" (ensembles d'accords) - simplifié
                    # Pour chaque paire de lignes, trouver les colonnes où elles ont les mêmes valeurs
                    agree_sets = []
                    
                    # Limiter le nombre de lignes pour les grands ensembles de données
                    max_rows = min(num_rows, 1000)
                    if num_rows > max_rows:
                        sample_indices = random.sample(range(num_rows), max_rows)
                        sample_rows = df.iloc[sample_indices]
                    else:
                        sample_rows = df
                    
                    # Calcul des ensembles d'accord (simplifié)
                    for i in range(len(sample_rows)):
                        for j in range(i+1, len(sample_rows)):
                            row1 = sample_rows.iloc[i]
                            row2 = sample_rows.iloc[j]
                            
                            # Trouver les colonnes où les deux lignes ont les mêmes valeurs
                            agree_columns = set()
                            for col in columns:
                                if row1[col] == row2[col]:
                                    agree_columns.add(col)
                            
                            if agree_columns:
                                agree_sets.append(agree_columns)
                    
                    # Découvrir les DFs en utilisant les agree sets
                    # Une FD X → Y est valide si Y est contenu dans chaque agree set qui contient X
                    for rhs_col in columns:
                        for lhs_size in range(1, min(4, len(columns))):  # Limiter à des LHS de taille 3 au maximum
                            for lhs_cols in combinations([c for c in columns if c != rhs_col], lhs_size):
                                lhs_set = set(lhs_cols)
                                
                                # Vérifier si LHS → RHS est une DF valide
                                is_fd = True
                                for agree_set in agree_sets:
                                    if lhs_set.issubset(agree_set) and rhs_col not in agree_set:
                                        # Si LHS est contenu dans agree_set mais pas RHS,
                                        # alors il existe deux lignes ayant les mêmes valeurs pour LHS
                                        # mais des valeurs différentes pour RHS
                                        is_fd = False
                                        break
                                
                                if is_fd:
                                    # Vérifier directement dans les données pour confirmer (pour les petits ensembles)
                                    groups = df.groupby(list(lhs_cols))
                                    direct_violations = 0
                                    for _, group in groups:
                                        if len(group[rhs_col].unique()) > 1:
                                            direct_violations += 1
                                    
                                    confidence = 1.0
                                    if groups.ngroups > 0:
                                        confidence = 1.0 - (direct_violations / groups.ngroups)
                                    
                                    # Ajouter si la confiance est suffisante
                                    if confidence >= self.min_confidence:
                                        rule_key = f"{','.join(lhs_cols)} -> {rhs_col}"
                                        table_name = os.path.basename(csv_file).replace('.csv', '')
                                        discovered_fds[rule_key] = {
                                            "rule": rule_key,
                                            "table": table_name,
                                            "confidence": confidence,
                                            "support": groups.ngroups / num_rows
                                        }
                    
                    logging.info(f"Implémentation Python FDep a découvert {len(discovered_fds)} dépendances fonctionnelles")
                    return discovered_fds
                
                except Exception as e:
                    logging.error(f"Erreur lors de l'implémentation Python de FDep: {str(e)}")
                    import traceback
                    logging.error(traceback.format_exc())
                
                return rules
                
            logging.info(f"Rules discovered by {algorithm_name} algorithm saved to {file_name}")
            result_file_path = os.path.join("results", f"{file_name}_{rule_type}")
            
            try:
                with open(result_file_path, mode="r") as f:
                    raw_rules = [line for line in f if line.strip()]
            except FileNotFoundError:
                logging.error(f"Fichier de résultats non trouvé: {result_file_path}")
                return rules

            if os.path.exists(result_file_path):
                os.remove(result_file_path)

            for raw_rule in raw_rules:
                try:
                    raw_rule = ast.literal_eval(raw_rule)
                except (ValueError, SyntaxError) as e:
                    logging.warning(f"Format de règle invalide: {raw_rule} - {e}")
                    continue  # Ignorer les formats de règle invalides

                try:
                    # Parse les dépendances fonctionnelles depuis le format JSON retourné par FDep
                    table_name = raw_rule.get("tableName", "").replace(".csv", "")
                    
                    # Extraction des colonnes déterminantes (côté gauche de la DF)
                    determinant_columns = tuple(
                        col["columnIdentifier"] for col in raw_rule.get("determinant", {}).get("columnIdentifiers", [])
                    )
                    
                    # Extraction des colonnes dépendantes (côté droit de la DF)
                    dependant_columns = tuple(
                        col["columnIdentifier"] for col in raw_rule.get("dependant", {}).get("columnIdentifiers", [])
                    )
                    
                    if table_name and determinant_columns and dependant_columns:
                        fd = FunctionalDependency(
                            table_dependant=table_name,
                            columns_dependant=determinant_columns,
                            table_referenced=table_name,
                            columns_referenced=dependant_columns,
                            table=table_name
                        )
                        rules[fd] = (1, 1)  # Support et confiance à 1 pour les dépendances exactes
                        logging.info(f"Dépendance fonctionnelle découverte: {fd}")
                except (KeyError, IndexError, AttributeError) as e:
                    logging.warning(f"Données de règle malformées: {raw_rule} - {e}")
                    continue  # Ignorer les données de règle malformées
            
            logging.info(f"Découvert {len(rules)} dépendances fonctionnelles au total")
            return rules
            
        except Exception as e:
            logging.error(f"Erreur lors de la découverte des dépendances fonctionnelles: {str(e)}")
            return rules
            
    def _discover_rules_python(self, **kwargs):
        """
        Implémentation Python simplifiée pour découvrir les dépendances fonctionnelles.
        Utilise la méthode _discover_fds_simple pour chaque fichier CSV.
        """
        rules = {}
        
        try:
            # Obtenir la liste des fichiers CSV
            csv_files = [
                os.path.join(self.database.base_csv_dir, f)
                for f in os.listdir(self.database.base_csv_dir)
                if f.endswith('.csv')
            ]
            
            logging.info(f"Traitement de {len(csv_files)} fichiers CSV avec l'implémentation Python")
            
            # Traiter chaque fichier séparément
            for csv_file in csv_files:
                if not self.verify_csv_file(csv_file):
                    logging.warning(f"Fichier CSV invalide, ignoré: {csv_file}")
                    continue
                
                table_name = os.path.basename(csv_file).replace('.csv', '')
                logging.info(f"Traitement du fichier: {csv_file} (table: {table_name})")
                
                try:
                    # Lire le fichier CSV avec pandas
                    df = pd.read_csv(csv_file)
                    
                    # Découvrir les dépendances fonctionnelles pour ce fichier
                    file_fds = self._discover_fds_simple(df, table_name)
                    
                    # Ajouter les dépendances découvertes au résultat global
                    for fd in file_fds:
                        rules[fd] = (1, 1)  # Support et confiance à 1 pour les dépendances exactes
                
                except Exception as e:
                    logging.error(f"Erreur lors du traitement du fichier {csv_file}: {str(e)}")
                    continue
            
            logging.info(f"Découvert {len(rules)} dépendances fonctionnelles au total avec l'implémentation Python")
            return rules
                
        except Exception as e:
            logging.error(f"Erreur lors de la découverte des dépendances fonctionnelles via Python: {str(e)}")
            return {}

    def _discover_fds_simple(self, df, table_name):
        """
        Méthode simplifiée pour découvrir les dépendances fonctionnelles.
        Cette implémentation vérifie uniquement les dépendances de base (une colonne -> une colonne).
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
                        # Version avec table_dependant, columns_dependant, etc.
                        fd = FunctionalDependency(
                            table_dependant=table_name,
                            columns_dependant=(col1,),
                            table_referenced=table_name,
                            columns_referenced=(col2,),
                            table=table_name
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
