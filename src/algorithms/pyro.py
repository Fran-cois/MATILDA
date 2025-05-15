import os
import logging
import ast
from pathlib import Path
from datetime import datetime
from typing import List

# Utiliser des imports relatifs pour éviter les problèmes de chemin de module
from .rule_discovery_algorithm import RuleDiscoveryAlgorithm
from ..utils.rules_classes.functional_dependency import FunctionalDependency
from ..utils.run_cmd import run_cmd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Pyro(RuleDiscoveryAlgorithm):
    """
    Implémentation d'une interface pour l'algorithme Pyro qui utilise un JAR Java externe
    pour la découverte de dépendances fonctionnelles.
    """
    
    def __init__(self, database, **kwargs):
        """
        Initialise l'interface de l'algorithme Pyro.
        
        Args:
            database: La base de données à analyser
            **kwargs: Arguments supplémentaires, notamment 'settings'
        """
        super().__init__(database)
        # Extraction des settings si présents
        settings = kwargs.get('settings', {})
        self.min_support = settings.get('min_support', 0.7)
        self.max_lhs_size = settings.get('max_lhs_size', 5)

    def discover_rules(self, **kwargs) -> List[FunctionalDependency]:
        """
        Découvre les dépendances fonctionnelles en utilisant le JAR Java Pyro,
        avec repli sur une implémentation Python simplifiée en cas d'échec.
        
        Args:
            **kwargs: Paramètres optionnels
                use_fallback: Si True, utilise directement l'implémentation Python
        """
        # Mise à jour des paramètres avec ceux passés directement à la méthode
        self.min_support = kwargs.get("min_support", self.min_support)
        self.max_lhs_size = kwargs.get("max_lhs_size", self.max_lhs_size)
        use_fallback = kwargs.get("use_fallback", False)
        
        # Variables pour stocker les chemins de fichier
        csv_file = kwargs.get('csv_file', os.path.join(self.database.base_csv_dir, "test_data.csv"))
        
        # Vérifier si le fichier CSV existe
        if not os.path.exists(csv_file):
            # Utiliser le premier fichier CSV disponible
            csv_files = [
                os.path.join(self.database.base_csv_dir, f) 
                for f in os.listdir(self.database.base_csv_dir) 
                if f.endswith('.csv')
            ]
            if csv_files:
                csv_file = csv_files[0]
                logging.info(f"Utilisation du fichier CSV par défaut : {csv_file}")
            else:
                logging.error("Aucun fichier CSV trouvé dans le répertoire")
                return None
        
        if not use_fallback:
            logger.info("Lancement de l'algorithme PYRO (version Java)")
            java_rules = self._discover_rules_java(**kwargs)
            if java_rules:
                return java_rules
            logger.warning("L'exécution de PYRO (Java) a échoué, utilisation de l'implémentation Python simplifiée")
        
        # Utiliser l'implémentation Python simplifiée
        logger.info("Lancement de l'algorithme PYRO (version Python simplifiée)")
        return self._discover_rules_python(**kwargs)
        
    def _discover_rules_java(self, **kwargs) -> List[FunctionalDependency]:
        """
        Implémentation Java de l'algorithme PYRO via le JAR externe.
        """
        rules = []
        script_dir = os.path.dirname(os.path.abspath(__file__))

        algorithm_name = "PYRO"
        classPath = "de.hpi.isg.pyro.akka.algorithms.Pyro"  # La classe correcte du JAR
        rule_type = "fds"
        
        # Obtenir le fichier CSV à traiter
        csv_file = kwargs.get('csv_file')
        if not csv_file or not os.path.exists(csv_file):
            # Utiliser le premier fichier CSV du répertoire
            csv_files = [
                os.path.join(self.database.base_csv_dir, f)
                for f in os.listdir(self.database.base_csv_dir)
                if f.endswith('.csv')
            ]
            if csv_files:
                csv_file = csv_files[0]
                logging.info(f"Utilisation du fichier CSV par défaut : {csv_file}")
            else:
                logging.error("Aucun fichier CSV trouvé dans le répertoire")
                return None
        
        # Obtenir tous les fichiers CSV comme le fait spider.py
        csv_files = " ".join(
            [
                os.path.join(self.database.base_csv_dir, f"{t}")
                for t in os.listdir(self.database.base_csv_dir)
            ]
        )
        
        current_time = datetime.now()
        jar_path = f"{script_dir}/bins/metanome/"
        file_name = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_{algorithm_name}'
        
        # Vérifier si le répertoire results existe, sinon le créer
        results_dir = os.path.join(os.getcwd(), "results")
        os.makedirs(results_dir, exist_ok=True)
        
        # Ajouter tous les JAR du répertoire dans le classpath
        all_jars = [f"{jar_path}{jar_file}" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]
        # S'assurer que les jars de MDMS sont inclus pour Pyro
        mdms_jars = [
        ]
        for mdms_jar in mdms_jars:
            if os.path.exists(mdms_jar) and mdms_jar not in all_jars:
                all_jars.append(mdms_jar)
        classpath = ":".join(all_jars)
        
        # Ajouter les dépendances Pyro spécifiques
        deps_dir = os.path.join(script_dir, "bins", "metanome", "deps")
        if os.path.exists(deps_dir):
            deps_jars = [os.path.join(deps_dir, jar) for jar in os.listdir(deps_dir) if jar.endswith(".jar")]
            if deps_jars:
                classpath = classpath + ":" + ":".join(deps_jars)
        
        # Préparer les arguments pour l'algorithme
        algo_config = f"--algorithm-config threshold:{self.min_support},max_attributes_in_lhs:{self.max_lhs_size}"
        
        # Ajouter tous les JAR du répertoire dans le classpath
        all_jars = [f"{jar_path}{jar_file}" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]
        classpath = ":".join(all_jars)
        
        cmd_string = (
            f"""java -Xmx4g -cp {jar_path}metanome-cli-1.2-SNAPSHOT.jar:{jar_path}*.jar """
            f"""de.metanome.cli.App --algorithm {classPath} --files {csv_file} """
            f"""--file-key INPUT_FILES --separator "," --header """
            f"""--output file:{file_name}"""
        )
        
        logger.info(f"Exécution de la commande: {cmd_string}")
        
        if not run_cmd(cmd_string):
            logger.error("Échec de l'exécution de la commande Pyro")
            logger.info("Utilisation de l'implémentation Python comme solution de secours pour Pyro")
            
            # Implémentation Python pour découvrir les dépendances fonctionnelles
            if os.path.exists(csv_file):
                try:
                    import pandas as pd
                    from itertools import combinations
                    from collections import defaultdict
                    
                    # Charger le fichier CSV
                    df = pd.read_csv(csv_file)
                    columns = list(df.columns)
                    num_rows = len(df)
                    
                    # Dictionnaire pour stocker les dépendances fonctionnelles découvertes
                    discovered_fds = {}
                    
                    # Pyro utilise un algorithme basé sur l'analyse des partitions
                    # Approche simplifiée basée sur le concept de partitions pour l'efficacité
                    
                    # Calculer les partitions pour chaque colonne
                    partitions = {}
                    for col in columns:
                        # Créer un dictionnaire groupant les indices de lignes par valeur
                        col_partition = defaultdict(list)
                        for idx, val in enumerate(df[col].values):
                            col_partition[val].append(idx)
                        # Convertir en partitions (uniquement les groupes de taille > 1)
                        partitions[col] = [indices for val, indices in col_partition.items() if len(indices) > 1]
                    
                    # Pour chaque combinaison possible de colonnes comme déterminant
                    for lhs_size in range(1, min(self.max_lhs_size + 1, len(columns))):
                        for lhs_cols in combinations(columns, lhs_size):
                            # Calculer la partition commune pour les colonnes LHS
                            lhs_partition = []
                            if lhs_size == 1:
                                lhs_partition = partitions.get(lhs_cols[0], [])
                            else:
                                # Pour simplifier, on vérifie directement les valeurs uniques
                                lhs_values = df[list(lhs_cols)].drop_duplicates()
                                lhs_tuples = [tuple(x) for x in lhs_values.values]
                                # Si tous les LHS sont uniques, aucune partition n'est nécessaire
                                if len(lhs_tuples) == num_rows:
                                    lhs_partition = []
                                else:
                                    # Grouper par valeurs LHS
                                    groups = df.groupby(list(lhs_cols)).groups
                                    lhs_partition = [list(indices) for indices in groups.values() if len(indices) > 1]
                            
                            # Vérifier pour chaque colonne potentiellement déterminée
                            for rhs_col in columns:
                                if rhs_col in lhs_cols:
                                    continue  # Ignorer si la colonne est déjà dans le déterminant
                                
                                # Vérifier si LHS → RHS est une dépendance fonctionnelle
                                # Une DF existe si la partition LHS est plus fine que la partition RHS
                                is_fd = True
                                
                                # Si LHS a des partitions, vérifier chaque groupe
                                if lhs_partition:
                                    for part in lhs_partition:
                                        # Vérifier que tous les indices dans cette partition ont la même valeur RHS
                                        rhs_values = set(df.iloc[part][rhs_col].values)
                                        if len(rhs_values) > 1:
                                            is_fd = False
                                            break
                                else:
                                    # Si LHS n'a pas de partitions, vérifier par groupby
                                    for _, group in df.groupby(list(lhs_cols)):
                                        if len(group[rhs_col].unique()) > 1:
                                            is_fd = False
                                            break
                                
                                if is_fd:
                                    # Calculer le support comme dans Pyro (nombre de tuples couverts / nombre total)
                                    if lhs_partition:
                                        covered_tuples = sum(len(part) for part in lhs_partition)
                                    else:
                                        covered_tuples = num_rows
                                    
                                    support = covered_tuples / num_rows
                                    
                                    if support >= self.min_support:
                                        rule_key = f"{','.join(lhs_cols)} -> {rhs_col}"
                                        table_name = os.path.basename(csv_file).replace('.csv', '')
                                        discovered_fds[rule_key] = {
                                            "rule": rule_key,
                                            "table": table_name,
                                            "confidence": 1.0,  # Les DFs ont toujours une confiance de 1.0
                                            "support": support
                                        }
                    
                    logger.info(f"Implémentation Python Pyro a découvert {len(discovered_fds)} dépendances fonctionnelles")
                    return discovered_fds
                except Exception as e:
                    logger.error(f"Erreur lors de l'implémentation Python de Pyro: {str(e)}")
            
            return rules
            
        logger.info(f"Rules discovered by {algorithm_name} algorithm saved to {file_name}")
        result_file_path = os.path.join("results", f"{file_name}_{rule_type}")
        
        try:
            with open(result_file_path, mode="r") as f:
                raw_rules = [line for line in f if line.strip()]
        except FileNotFoundError:
            logger.error(f"Fichier de résultats non trouvé: {result_file_path}")
            return rules

        if os.path.exists(result_file_path):
            os.remove(result_file_path)

        for raw_rule in raw_rules:
            try:
                raw_rule = ast.literal_eval(raw_rule)
            except (ValueError, SyntaxError) as e:
                logger.warning(f"Format de règle invalide: {raw_rule} - {e}")
                continue  # Ignorer les formats de règle invalides

            try:
                # Parse les dépendances fonctionnelles depuis le format JSON retourné par Pyro
                table_name = raw_rule.get("tableName", "").replace(".csv", "")
                
                # Extraction des colonnes déterminantes (côté gauche de la DF)
                lhs_columns = [
                    col["columnIdentifier"] for col in raw_rule.get("determinant", {}).get("columnIdentifiers", [])
                ]
                
                # Extraction de la colonne dépendante (côté droit de la DF)
                rhs_column = raw_rule.get("dependant", {}).get("columnIdentifiers", [])[0]["columnIdentifier"]
                
                if table_name and lhs_columns and rhs_column:
                    # Créer la dépendance fonctionnelle
                    fd = FunctionalDependency(
                        table=table_name,
                        lhs=lhs_columns,
                        rhs=rhs_column,
                        support=self.min_support,  # Valeur par défaut, pourrait être extraite du résultat
                        confidence=1.0  # Les FDs ont toujours une confiance de 1.0
                    )
                    rules.append(fd)
                    logger.info(f"Dépendance fonctionnelle découverte: {fd}")
            except (KeyError, IndexError, AttributeError) as e:
                logger.warning(f"Données de règle malformées: {raw_rule} - {e}")
                continue  # Ignorer les données de règle malformées
        
        logger.info(f"Découvert {len(rules)} dépendances fonctionnelles au total")
        return rules
        
    def _discover_rules_python(self, **kwargs) -> List[FunctionalDependency]:
        """
        Implémentation Python simplifiée de l'algorithme PYRO.
        Cette version est utilisée comme solution de repli quand l'implémentation Java échoue.
        
        PYRO est spécialisé dans la découverte de dépendances fonctionnelles avec des grands ensembles
        de données en utilisant un échantillonnage par niveau (levelwise sampling).
        """
        rules = []
        import pandas as pd
        import itertools
        import random
        from collections import defaultdict
        
        try:
            # Obtenir la liste des fichiers CSV
            csv_files = [
                os.path.join(self.database.base_csv_dir, f)
                for f in os.listdir(self.database.base_csv_dir)
                if f.endswith('.csv')
            ]
            
            logger.info(f"Traitement de {len(csv_files)} fichiers CSV avec l'implémentation Python de PYRO")
            
            # Traiter chaque fichier séparément
            for csv_file in csv_files:
                try:
                    # Lire le fichier CSV
                    df = pd.read_csv(csv_file)
                    
                    # Vérifier s'il y a des données
                    if df.empty:
                        logger.warning(f"Fichier CSV vide, ignoré: {csv_file}")
                        continue
                    
                    # Si le fichier est grand, prendre un échantillon
                    if len(df) > 10000:
                        sample_size = min(10000, int(0.1 * len(df)))
                        df = df.sample(sample_size, random_state=42)
                        logger.info(f"Utilisation d'un échantillon de {sample_size} lignes pour {csv_file}")
                    
                    table_name = os.path.basename(csv_file).replace('.csv', '')
                    logger.info(f"Traitement du fichier: {csv_file} (table: {table_name})")
                    
                    # Découvrir les FDs avec un algorithme inspiré de PYRO
                    file_rules = self._discover_fds_pyro_style(df, table_name, 
                                                        min_support=self.min_support,
                                                        max_lhs_size=self.max_lhs_size)
                    
                    rules.extend(file_rules)
                    
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du fichier {csv_file}: {str(e)}")
                    continue
            
            logger.info(f"Découvert {len(rules)} dépendances fonctionnelles au total avec l'implémentation Python")
            return rules
            
        except Exception as e:
            logger.error(f"Erreur lors de la découverte des dépendances fonctionnelles via Python: {str(e)}")
            return []
            
    def _discover_fds_pyro_style(self, df, table_name, min_support=0.7, max_lhs_size=5):
        """
        Implémentation Python simplifiée inspirée de l'approche PYRO.
        
        Args:
            df: DataFrame contenant les données
            table_name: Nom de la table
            min_support: Support minimum requis (fraction des données que la règle couvre)
            max_lhs_size: Taille maximale du côté gauche (LHS) des dépendances
            
        Returns:
            Liste de dépendances fonctionnelles
        """
        import pandas as pd
        import itertools
        from collections import defaultdict
        
        discovered_fds = []
        columns = list(df.columns)
        
        # Support minimum en nombre de lignes
        min_rows = int(len(df) * min_support)
        
        # Pour chaque colonne potentielle du côté droit (RHS)
        for rhs_column in columns:
            # Trouver les candidats du côté gauche (LHS) qui seuls déterminent le RHS
            valid_lhs_columns = []
            
            # 1. Vérifier les dépendances simples (1 colonne -> 1 colonne)
            for lhs_column in [c for c in columns if c != rhs_column]:
                # Tester si lhs_column -> rhs_column en vérifiant les valeurs uniques
                is_candidate = True
                
                # Créer un dictionnaire de vérification LHS -> RHS
                lhs_to_rhs = defaultdict(set)
                row_count = 0
                
                # Parcourir le DataFrame par blocs pour économiser la mémoire
                for _, chunk in df[[lhs_column, rhs_column]].groupby(lhs_column):
                    # Si un LHS mapppe vers plusieurs RHS, ce n'est pas une FD
                    if len(chunk[rhs_column].unique()) > 1:
                        is_candidate = False
                        break
                    
                    row_count += len(chunk)
                
                # Si c'est une FD valide avec support suffisant
                if is_candidate and row_count >= min_rows:
                    valid_lhs_columns.append(lhs_column)
                    fd = FunctionalDependency(
                        table=table_name,
                        lhs=[lhs_column],
                        rhs=rhs_column,
                        support=row_count / len(df),
                        confidence=1.0  # Confiance = 1 pour les FDs exactes
                    )
                    discovered_fds.append(fd)
                    logger.info(f"FD découverte: {table_name}.{lhs_column} -> {table_name}.{rhs_column}")
            
            # 2. Explorer les combinaisons plus grandes de colonnes LHS si nécessaire
            # Similaire à l'algorithme TANE, mais seulement pour les candidats intéressants
            if len(valid_lhs_columns) > 1 and max_lhs_size > 1:
                # Génération des combinaisons de candidats
                for lhs_size in range(2, min(max_lhs_size + 1, len(valid_lhs_columns) + 1)):
                    for lhs_columns in itertools.combinations(valid_lhs_columns, lhs_size):
                        # Vérifier si toutes les sous-combinaisons sont déjà des FDs
                        # Si oui, cette combinaison est redondante et on peut la sauter
                        skip = False
                        for i in range(len(lhs_columns)):
                            subset = list(lhs_columns[:i]) + list(lhs_columns[i+1:])
                            if all(c in valid_lhs_columns for c in subset):
                                skip = True
                                break
                        
                        if skip:
                            continue
                        
                        # Tester la combinaison pour voir si c'est une FD
                        is_fd = True
                        lhs_to_rhs = defaultdict(set)
                        row_count = 0
                        
                        # Regrouper par les colonnes LHS
                        for _, chunk in df[list(lhs_columns) + [rhs_column]].groupby(list(lhs_columns)):
                            # Si un groupe a plusieurs valeurs RHS, ce n'est pas une FD
                            if len(chunk[rhs_column].unique()) > 1:
                                is_fd = False
                                break
                            
                            row_count += len(chunk)
                        
                        # Si c'est une FD valide avec support suffisant
                        if is_fd and row_count >= min_rows:
                            fd = FunctionalDependency(
                                table=table_name,
                                lhs=list(lhs_columns),
                                rhs=rhs_column,
                                support=row_count / len(df),
                                confidence=1.0  # Confiance = 1 pour les FDs exactes
                            )
                            discovered_fds.append(fd)
                            logger.info(f"FD complexe découverte: {table_name}.{', '.join(lhs_columns)} -> {table_name}.{rhs_column}")
        
        return discovered_fds
