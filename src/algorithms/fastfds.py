# algorithms/fastfds.py

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


class FastFDs(BaseAlgorithm):
    """
    Implémentation de l'interface pour l'algorithme FastFDs pour la découverte de dépendances fonctionnelles.
    Cette implémentation utilise un JAR Java externe avec une solution de repli Python en cas d'échec.
    """

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
        Découvre les dépendances fonctionnelles.
        Essaie d'abord d'utiliser l'implémentation Java de l'algorithme FastFDs via le JAR externe.
        En cas d'échec, utilise une implémentation Python simplifiée.
        """
        rules = {}
        use_fallback = kwargs.get('use_fallback', False)
        
        if not use_fallback:
            logging.info("Lancement de l'algorithme FastFDs (version Java)")
            try_java = self._discover_rules_java(**kwargs)
            if try_java:
                return try_java
            logging.warning("L'exécution de FastFDs (Java) a échoué, utilisation de l'implémentation Python simplifiée")
        
        # Utiliser l'implémentation Python simplifiée
        logging.info("Lancement de l'algorithme FastFDs (version Python simplifiée)")
        return self._discover_rules_python(**kwargs)
    
    def _discover_rules_java(self, **kwargs):
        """
        Implémentation de la découverte de dépendances fonctionnelles via FastFDs (JAR Java).
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fastfds_jar = kwargs.get('fastfds_jar', f"{script_dir}/bins/metanome/fastfds_algorithm-0.0.2-SNAPSHOT.jar")
        rules = {}
        try:
            algorithm_name = "FASTFDS"
            classPath = "de.metanome.algorithms.fastfds.fastfds_helper.modules.StrippedPartitionGenerator"  # Classe principale du module FastFDs
            rule_type = "fds"
            params = " --file-key INPUT_FILES"

            # Obtenir la liste des fichiers CSV
            csv_files = [
                os.path.join(self.database.base_csv_dir, f)
                for f in os.listdir(self.database.base_csv_dir)
                if f.endswith('.csv')
            ]
            
            logging.info(f"Traitement de {len(csv_files)} fichiers CSV individuellement")
            
            # Traiter chaque fichier séparément pour éviter les problèmes
            for csv_file in csv_files:
                table_name = os.path.basename(csv_file).replace('.csv', '')
                logging.info(f"Traitement du fichier: {csv_file} (table: {table_name})")
                
                current_time = datetime.now()
                jar_path = f"{script_dir}/bins/metanome/"
                file_name = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_{algorithm_name}_{table_name}'
                
                # Utiliser tous les JAR du répertoire
                if not os.path.exists(fastfds_jar):
                    logging.error(f"Fichier JAR manquant: {fastfds_jar}")
                    continue
                
                # Ajouter l'option -Xmx4g pour augmenter la mémoire disponible pour Java
                # Ajouter l'option -XX:+HeapDumpOnOutOfMemoryError pour créer un dump en cas d'erreur de mémoire
                cmd_string = (
                    f"""java -Xmx4g -cp {jar_path}metanome-cli-1.2-SNAPSHOT.jar:{jar_path}*.jar """
                    f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file} """
                    f"""--file-key INPUT_FILES --separator "," --header """
                    f"""--output file:{file_name}"""
                )
                
                logging.info(f"Exécution de la commande: {cmd_string}")
                
                if not run_cmd(cmd_string):
                    logging.error(f"Échec de l'exécution de FastFDs pour {table_name}")
                    logging.info(f"Utilisation de l'implémentation Python comme solution de secours pour FastFDs sur {table_name}")
                    
                    # FastFDs utilise un algorithme de recherche rapide basé sur la couverture minimale
                    # Implémentons une version simplifiée
                    try:
                        import pandas as pd
                        from itertools import combinations
                        import random
                        
                        # Nous avons déjà chargé le df plus haut pour la prévalidation
                        # Réutiliser ou recharger si nécessaire
                        if 'df' not in locals() or df is None:
                            df = pd.read_csv(csv_file)
                        
                        columns = list(df.columns)
                        num_rows = len(df)
                        
                        # Réduire la taille pour les grands ensembles de données
                        max_rows = min(num_rows, 1000)
                        if num_rows > max_rows:
                            df_sample = df.sample(max_rows, random_state=42)
                        else:
                            df_sample = df
                        
                        # Dictionnaire pour stocker les FDs découvertes pour cette table
                        table_fds = {}
                        
                        # FastFDs recherche les FDs minimales
                        # Pour chaque colonne de droite potentielle
                        for rhs_col in columns:
                            # Commencer par les dépendances simples (LHS avec une seule colonne)
                            for lhs_col in columns:
                                if lhs_col == rhs_col:
                                    continue
                                
                                # Vérifier si c'est une dépendance fonctionnelle
                                groups = df_sample.groupby(lhs_col)
                                is_fd = True
                                
                                for _, group in groups:
                                    # Si un groupe a plus d'une valeur distincte pour RHS, ce n'est pas une FD
                                    if len(group[rhs_col].unique()) > 1:
                                        is_fd = False
                                        break
                                
                                if is_fd:
                                    rule_key = f"{lhs_col} -> {rhs_col}"
                                    table_fds[rule_key] = {
                                        "rule": rule_key,
                                        "table": table_name,
                                        "confidence": 1.0,
                                        "support": len(groups) / num_rows
                                    }
                            
                            # Si aucune FD simple n'est trouvée, essayer des combinaisons de colonnes
                            if not any(f" -> {rhs_col}" in key for key in table_fds.keys()):
                                # Essayer des combinaisons de 2 colonnes comme LHS
                                for lhs_cols in combinations([c for c in columns if c != rhs_col], 2):
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
                                            "support": len(groups) / num_rows
                                        }
                                        
                                        # FastFDs s'arrête généralement après avoir trouvé une bonne FD
                                        break
                        
                        # Ajouter les FDs de cette table au résultat global
                        rules.update(table_fds)
                        logging.info(f"Implémentation Python FastFDs a découvert {len(table_fds)} dépendances fonctionnelles pour {table_name}")
                    
                    except Exception as e:
                        logging.error(f"Erreur lors de l'implémentation Python de FastFDs pour {table_name}: {str(e)}")
                    
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
            return rules if rules else None
                
        except Exception as e:
            logging.error(f"Erreur lors de la découverte des dépendances fonctionnelles via Java: {str(e)}")
            return None
    
    def _discover_rules_python(self, **kwargs):
        """
        Implémentation Python simplifiée pour découvrir les dépendances fonctionnelles.
        Utilise une approche simple par paires de colonnes.
        """
        rules = {}
        
        try:
            # Récupération des paramètres
            max_lhs_size = kwargs.get('max_lhs_size', 1)  # Par défaut, limiter à des dépendances simples
            
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
                    file_fds = self._discover_fds_simple(df, table_name, max_lhs_size)
                    
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
            
    def _discover_fds_simple(self, df, table_name, max_lhs_size=1):
        """
        Méthode simplifiée pour découvrir les dépendances fonctionnelles.
        Cette implémentation vérifie les dépendances avec au plus max_lhs_size colonnes dans le déterminant.
        """
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
                        try:
                            fd = FunctionalDependency(
                                table_dependant=table_name,
                                columns_dependant=lhs_cols,
                                table_referenced=table_name,
                                columns_referenced=(rhs_col,),
                                table=table_name
                            )
                            discovered_fds.append(fd)
                            logging.info(f"Dépendance fonctionnelle découverte: {table_name}.{','.join(lhs_cols)} -> {table_name}.{rhs_col}")
                        except Exception as e:
                            logging.error(f"Erreur lors de la création de la dépendance fonctionnelle: {e}")
        
        return discovered_fds
