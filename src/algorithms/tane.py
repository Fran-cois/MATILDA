# algorithms/tane.py

import ast
import os
import logging
import pandas as pd
import itertools
from collections import defaultdict
from datetime import datetime

from algorithms.base_algorithm import BaseAlgorithm
from utils.rules import FunctionalDependency, Rule
from utils.run_cmd import run_cmd


class Tane(BaseAlgorithm):
    def verify_csv_file(self, file_path):
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
        Découvre les dépendances fonctionnelles dans les fichiers CSV.
        Essaie d'abord d'utiliser l'implémentation Java de l'algorithme TANE via le JAR externe.
        En cas d'échec, utilise une implémentation Python simplifiée.
        """
        rules = {}
        use_fallback = kwargs.get('use_fallback', False)
        
        if not use_fallback:
            logging.info("Lancement de l'algorithme TANE (version Java)")
            try_java = self._discover_rules_java(**kwargs)
            if try_java:
                return try_java
            logging.warning("L'exécution de TANE (Java) a échoué, utilisation de l'implémentation Python simplifiée")
        
        # Utiliser l'implémentation Python simplifiée
        logging.info("Lancement de l'algorithme TANE (version Python simplifiée)")
        return self._discover_rules_python(**kwargs)
    
    def _discover_rules_java(self, **kwargs):
        """
        Implémentation de la découverte de dépendances fonctionnelles via TANE (JAR Java).
        """
        rules = {}
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tane_jar = kwargs.get('tane_jar', f"{script_dir}/bins/metanome/tane-0.0.2-SNAPSHOT.jar")
        tmp_csv_file = kwargs.get('tmp_csv_file', 'temp_csv_file.csv')
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            algorithm_name = "tane"  # Utiliser le nom en minuscules
            classPath = "de.metanome.algorithms.tane.algorithm_helper.test_helper.fixtures.AbstractAlgorithmTestFixture"  # Classe principale d'après l'analyse
            rule_type = "fds"
            
            # Obtenir la liste des fichiers CSV
            csv_files = [
                os.path.join(self.database.base_csv_dir, f)
                for f in os.listdir(self.database.base_csv_dir)
                if f.endswith('.csv')
            ]
            
            logging.info(f"Traitement de {len(csv_files)} fichiers CSV individuellement")
            
            # Traiter chaque fichier séparément
            for csv_file in csv_files:
                table_name = os.path.basename(csv_file).replace('.csv', '')
                logging.info(f"Traitement du fichier: {csv_file} (table: {table_name})")
                
                current_time = datetime.now()
                jar_path = f"{script_dir}/bins/metanome/"
                file_name = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_{algorithm_name}_{table_name}'
                
                # Exécuter la commande uniquement pour ce fichier
                # Utiliser tous les JAR du répertoire
                if not os.path.exists(tane_jar):
                    logging.error(f"Fichier JAR manquant: {tane_jar}")
                    continue
                
                # Ajouter les paramètres explicites pour l'initialisation des noms de colonnes
                # Utiliser --file-key au lieu de --file-key pour corriger l'erreur columnNames is null                    # Précharger et analyser le fichier CSV pour s'assurer que les noms de colonnes sont corrects
                    try:
                        # Vérifier le contenu du fichier CSV
                        import pandas as pd
                        df = pd.read_csv(csv_file)
                        logging.info(f"Fichier CSV préchargé avec succès. Colonnes: {list(df.columns)}")
                        
                        if len(df) == 0:
                            logging.error(f"Le fichier CSV {csv_file} est vide")
                            continue
                            
                        # Créer un fichier temporaire avec entêtes explicites si nécessaire
                        tmp_csv_file = f"{csv_file}.tmp"
                        df.to_csv(tmp_csv_file, index=False)
                        csv_file = tmp_csv_file
                    except Exception as e:
                        logging.error(f"Erreur lors du préchargement du fichier CSV {csv_file}: {str(e)}")
                        csv_file = csv_file
                        
                                    # Extraire les noms de colonnes pour éviter l'erreur "columnNames is null"
                try:
                    import pandas as pd
                    df = pd.read_csv(csv_file, nrows=1)
                    column_names = list(df.columns)
                    column_names_arg = f"--column-names {','.join(column_names)}"
                except Exception as e:
                    logging.warning(f"Erreur lors de la lecture des noms de colonnes: {str(e)}")
                    column_names_arg = ""
                
                cmd_string = (
                    f"""java -Xmx4g -cp {jar_path}metanome-cli-1.2-SNAPSHOT.jar:{jar_path}*.jar """
                    f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file} """
                    f"""--file-key INPUT_FILES --separator "," --header """
                    f"""--output file:{file_name}"""
                )
                
                logging.info(f"Exécution de la commande: {cmd_string}")
                
                if not run_cmd(cmd_string):
                    logging.error(f"Échec de l'exécution de TANE pour {table_name}")
                    logging.info(f"Utilisation de l'implémentation Python comme solution de secours pour TANE sur {table_name}")
                    
                    # TANE est un algorithme efficace pour découvrir les DFs avec un parcours par niveau
                    # Implémentons une version simplifiée
                    try:
                        import pandas as pd
                        import numpy as np
                        from itertools import combinations
                        from collections import defaultdict
                        
                        # Charger le fichier CSV si ce n'est pas déjà fait
                        if 'df' not in locals() or df is None or len(df) <= 1:
                            df = pd.read_csv(csv_file)
                        
                        columns = list(df.columns)
                        num_rows = len(df)
                        
                        # Limiter le jeu de données pour les grands ensembles
                        max_rows = min(num_rows, 1000)
                        if num_rows > max_rows:
                            df_sample = df.sample(max_rows, random_state=42)
                        else:
                            df_sample = df
                        
                        # Dictionnaire pour stocker les DFs découvertes pour cette table
                        table_fds = {}
                        
                        # Calculer les dépendances de niveau 1 (une colonne vers une colonne)
                        level_1_deps = {}
                        for col1 in columns:
                            # Pour chaque colonne, calculer sa partition
                            # (grouper les indices de lignes par valeur de colonne)
                            partition = defaultdict(list)
                            for idx, val in enumerate(df_sample[col1]):
                                partition[val].append(idx)
                            
                            # Conserver uniquement les ensembles avec plus d'un élément
                            partition = [indices for val, indices in partition.items() if len(indices) > 1]
                            
                            # Stocker la partition pour cette colonne
                            level_1_deps[col1] = partition
                        
                        # Découvrir les dépendances fonctionnelles
                        # Pour chaque paire (X, A), vérifier si X → A est une DF
                        for rhs_col in columns:
                            rhs_partition = level_1_deps.get(rhs_col, [])
                            
                            # Commencer par les dépendances simples (LHS avec une seule colonne)
                            for lhs_col in columns:
                                if lhs_col == rhs_col:
                                    continue
                                
                                lhs_partition = level_1_deps.get(lhs_col, [])
                                
                                # Une colonne détermine une autre si sa partition est plus fine
                                # que la partition de l'autre colonne
                                is_fd = True
                                
                                # Approche TANE: Vérifier les partitions
                                for lhs_part in lhs_partition:
                                    # Pour chaque ensemble dans la partition LHS,
                                    # vérifier que toutes les lignes ont la même valeur RHS
                                    rhs_values = set(df_sample.iloc[lhs_part][rhs_col])
                                    if len(rhs_values) > 1:
                                        is_fd = False
                                        break
                                
                                if is_fd:
                                    rule_key = f"{lhs_col} -> {rhs_col}"
                                    table_fds[rule_key] = {
                                        "rule": rule_key,
                                        "table": table_name,
                                        "confidence": 1.0,
                                        "support": len(lhs_partition) / num_rows if lhs_partition else 1.0
                                    }
                            
                            # Si aucune dépendance simple n'est trouvée, essayer des combinaisons de niveau 2
                            if not any(f" -> {rhs_col}" in key for key in table_fds.keys()):
                                for lhs_cols in combinations([c for c in columns if c != rhs_col], 2):
                                    # TANE calcule les partitions pour les ensembles d'attributs
                                    # C'est complexe à implémenter, donc utilisons une approche plus simple
                                    groups = df_sample.groupby(list(lhs_cols))
                                    is_fd = True
                                    
                                    for _, group in groups:
                                        if len(group[rhs_col].unique()) > 1:
                                            is_fd = False
                                            break
                                    
                                    if is_fd:
                                        rule_key = f"{','.join(lhs_cols)} -> {rhs_col}"
                                        table_fds[rule_key] = {
                                            "rule": rule_key,
                                            "table": table_name,
                                            "confidence": 1.0,
                                            "support": groups.ngroups / num_rows
                                        }
                        
                        # Ajouter les FDs de cette table au résultat global
                        rules.update(table_fds)
                        logging.info(f"Implémentation Python TANE a découvert {len(table_fds)} dépendances fonctionnelles pour {table_name}")
                    
                    except Exception as e:
                        logging.error(f"Erreur lors de l'implémentation Python de TANE pour {table_name}: {str(e)}")
                        import traceback
                        logging.error(traceback.format_exc())
                    
                    continue  # Passer au fichier suivant
                    
                # Traiter les résultats pour ce fichier
                result_file_path = os.path.join("results", f"{file_name}_{rule_type}")
                
                try:
                    with open(result_file_path, mode="r") as f:
                        raw_rules = [line for line in f if line.strip()]
                except FileNotFoundError:
                    logging.error(f"Fichier de résultats non trouvé: {result_file_path}")
                    continue

                if os.path.exists(result_file_path):
                    os.remove(result_file_path)
                    
                # Nettoyer le fichier temporaire si créé
                if 'tmp_csv_file' in locals() and os.path.exists(tmp_csv_file):
                    os.remove(tmp_csv_file)
                    logging.info(f"Fichier temporaire supprimé: {tmp_csv_file}")

                # Traiter les règles de ce fichier
                for raw_rule in raw_rules:
                    try:
                        raw_rule = ast.literal_eval(raw_rule)
                    except (ValueError, SyntaxError) as e:
                        logging.warning(f"Format de règle invalide: {raw_rule} - {e}")
                        continue  # Ignorer les formats de règle invalides

                    try:
                        # Parse les dépendances fonctionnelles depuis le format JSON
                        determinant_columns = tuple(
                            col["columnIdentifier"] for col in raw_rule.get("determinant", {}).get("columnIdentifiers", [])
                        )
                        
                        dependant_columns = tuple(
                            col["columnIdentifier"] for col in raw_rule.get("dependant", {}).get("columnIdentifiers", [])
                        )
                        
                        if determinant_columns and dependant_columns:
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
            logging.error(f"Erreur lors de la découverte des dépendances fonctionnelles via Java: {str(e)}")
            return None
    
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

    # Garder la méthode _discover_fds_simple comme solution de secours ou pour des tests
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
