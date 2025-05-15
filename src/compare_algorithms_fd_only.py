import argparse
import json
import logging
import os
import sqlite3
import time
import random
import string
import signal
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional, Callable

# Tentative d'importation de psutil avec gestion d'erreur
try:
    import psutil
    has_psutil = True
except ImportError:
    has_psutil = False
    print("AVERTISSEMENT: Le module 'psutil' n'est pas installé. La surveillance de la mémoire sera désactivée.")
    print("Pour installer psutil, exécutez: pip install psutil\n")

from algorithms.matilda import MATILDA
from algorithms.tane import Tane
from algorithms.fastfds import FastFDs
from algorithms.fdep import FDep
from algorithms.dfd import DFD
# Import des nouveaux algorithmes
from algorithms.aidfd import AIDFD
from algorithms.pyro import Pyro
from database.alchemy_utility import AlchemyUtility
from utils.rule_comparator import RuleComparator
from utils.rules import Rule, FunctionalDependency
from utils.logging_utils import configure_global_logger


# Fonction pour obtenir l'utilisation mémoire
def get_memory_usage():
    """
    Renvoie l'utilisation mémoire actuelle en Mo.
    Utilise psutil si disponible, sinon renvoie -1.
    
    :return: Utilisation mémoire en Mo ou -1 si psutil n'est pas disponible
    """
    if has_psutil:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        return mem_info.rss / (1024 * 1024)  # Conversion en Mo
    else:
        return -1


def create_test_database(db_path: Path, db_name: str, num_rows: int = 100, columns_per_table: int = 5, num_tables: int = 1, fd_density: float = 0.3) -> Path:
    """
    Crée une petite base de données de test pour les comparaisons.
    
    :param db_path: Chemin du répertoire où créer la base de données
    :param db_name: Nom de la base de données à créer
    :param num_rows: Nombre de lignes par table
    :param columns_per_table: Nombre de colonnes par table
    :param num_tables: Nombre de tables à créer
    :param fd_density: Densité des dépendances fonctionnelles (entre 0 et 1)
    :return: Chemin vers la base de données créée
    """
    print(f"Création d'une base de données de test: {db_name}")
    print(f"- Nombre de tables: {num_tables}")
    print(f"- Colonnes par table: {columns_per_table}")
    print(f"- Lignes par table: {num_rows}")
    print(f"- Densité de FDs: {fd_density}")
    
    # Créer le répertoire si nécessaire
    db_path.mkdir(parents=True, exist_ok=True)
    db_file = db_path / db_name
    
    # Supprimer la base de données si elle existe déjà
    if db_file.exists():
        db_file.unlink()
    
    # Créer la connexion à la base de données
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    
    for table_idx in range(1, num_tables + 1):
        table_name = f"table_{table_idx}"
        
        # Créer la définition des colonnes
        columns = []
        for col_idx in range(1, columns_per_table + 1):
            col_name = f"col_{col_idx}"
            col_type = "INTEGER" if col_idx <= 2 else "TEXT"  # Premières colonnes numériques, autres textuelles
            columns.append(f"{col_name} {col_type}")
        
        # Créer la table
        create_table_sql = f"""
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY,
            {', '.join(columns)}
        )
        """
        cursor.execute(create_table_sql)
        
        # Générer des dépendances fonctionnelles simulées
        # Pour simplifier: col_1 -> col_3, col_2 -> col_4, etc.
        fd_columns = {}
        for i in range(1, columns_per_table):
            if random.random() < fd_density and i + 2 <= columns_per_table:
                fd_columns[i] = i + 2  # col_i détermine col_(i+2)
        
        # Générer des données avec ces dépendances
        for row_idx in range(1, num_rows + 1):
            values = [row_idx]  # ID
            
            # Générer des valeurs pour chaque colonne
            generated_values = {}
            for col_idx in range(1, columns_per_table + 1):
                if col_idx <= 2:
                    # Colonnes numériques: valeurs aléatoires ou basées sur des dépendances
                    value = random.randint(1, num_rows // 5)
                else:
                    # Colonnes textuelles
                    # Vérifier si cette colonne dépend d'une autre
                    is_dependent = False
                    for det_col, dep_col in fd_columns.items():
                        if dep_col == col_idx:
                            # Cette colonne dépend d'une autre
                            det_value = generated_values.get(det_col)
                            if det_value is not None:
                                # Générer une valeur déterminée par la colonne déterminante
                                value = f"value_{det_value}_for_col_{col_idx}"
                                is_dependent = True
                                break
                    
                    if not is_dependent:
                        # Valeur aléatoire pour colonne non dépendante
                        value = ''.join(random.choices(string.ascii_lowercase, k=5))
                
                generated_values[col_idx] = value
                values.append(value)
            
            # Insérer la ligne
            placeholders = ','.join(['?'] * (len(values)))
            cursor.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", values)
    
    # Valider les changements et fermer la connexion
    conn.commit()
    conn.close()
    
    print(f"Base de données de test créée: {db_file}")
    return db_file


# Fonction pour gérer les timeouts
class TimeoutHandler:
    """
    Classe utilitaire pour gérer les timeouts d'exécution.
    """
    def __init__(self, seconds: int = 300):
        self.seconds = seconds
        self.timed_out = False
        
    def __enter__(self):
        signal.signal(signal.SIGALRM, self._handle_timeout)
        signal.alarm(self.seconds)
        return self
        
    def __exit__(self, type, value, traceback):
        signal.alarm(0)
        
    def _handle_timeout(self, signum, frame):
        self.timed_out = True
        raise TimeoutError(f"L'opération a dépassé le délai de {self.seconds} secondes")


class FDAlgorithmComparer:
    """
    Classe pour exécuter et comparer différents algorithmes de découverte de dépendances fonctionnelles.
    Version simplifiée qui se concentre uniquement sur les FDs.
    """
    
    def __init__(self, database_path: str, database_name: str, output_dir: str, timeout: int = 300, use_parallel: bool = False):
        """
        Initialise le comparateur d'algorithmes.
        
        :param database_path: Chemin vers le répertoire contenant la base de données
        :param database_name: Nom de la base de données
        :param output_dir: Répertoire où sauvegarder les résultats
        :param timeout: Timeout en secondes pour chaque algorithme (défaut: 300s)
        :param use_parallel: Utiliser le traitement parallèle si possible
        """
        self.database_path = Path(database_path)
        self.database_name = Path(database_name)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.use_parallel = use_parallel
        self.cpu_count = multiprocessing.cpu_count()
        
        # Configurer le logger
        log_dir = self.output_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        self.logger = configure_global_logger(log_dir)
        
        # Connexion à la base de données
        db_file = self.database_path / self.database_name
        self.db_uri = f"sqlite:///{db_file}"
        self.logger.info(f"Connexion à la base de données: {self.db_uri}")
        
        # Initialiser le comparateur de règles
        self.rule_comparator = RuleComparator(logger=self.logger)
        
        # Dictionnaires pour stocker les résultats
        self.discovered_rules = {}
        self.execution_times = {}
        self.statistics = {}
        
        # Variables pour suivre les erreurs
        self.algorithm_errors = {}

    def _run_algorithm_with_timeout(self, algorithm_class, algorithm_name: str, **kwargs) -> List[Rule]:
        """
        Wrapper pour exécuter un algorithme avec timeout.
        
        :param algorithm_class: Classe de l'algorithme
        :param algorithm_name: Nom de l'algorithme
        :param kwargs: Paramètres pour l'algorithme
        :return: Liste des règles découvertes
        """
        rules = []
        settings = kwargs.pop('settings', {}) if 'settings' in kwargs else kwargs.copy()
        
        try:
            with AlchemyUtility(self.db_uri, database_path=str(self.database_path), create_index=False) as db_util:
                algo = algorithm_class(db_util, settings=settings)
                
                # Afficher les détails de l'initialisation
                self.logger.info(f"{algorithm_name}: Algorithme initialisé avec: {settings}")
                
                # Utiliser un timeout pour éviter les blocages
                with TimeoutHandler(self.timeout):
                    # Exécuter la découverte de règles avec un callback de progression
                    rules_iterator = algo.discover_rules(**kwargs)
                    total_rules = 0
                    last_progress_time = time.time()
                    
                    for i, rule in enumerate(rules_iterator):
                        rules.append(rule)
                        total_rules += 1
                        
                        # Afficher la progression toutes les 3 secondes
                        current_time = time.time()
                        if current_time - last_progress_time > 3:
                            self.logger.info(f"{algorithm_name}: {total_rules} règles découvertes jusqu'à présent...")
                            last_progress_time = current_time
                
                self.logger.info(f"{algorithm_name}: Découverte terminée avec {len(rules)} règles.")
                
        except TimeoutError:
            self.logger.warning(f"{algorithm_name}: L'algorithme a dépassé le délai imparti de {self.timeout} secondes.")
            self.algorithm_errors[algorithm_name] = f"Timeout après {self.timeout} secondes"
            
        except Exception as e:
            self.logger.error(f"{algorithm_name}: Erreur lors de l'exécution: {e}")
            self.algorithm_errors[algorithm_name] = str(e)
            
        return rules
    
    def run_algorithm(self, algorithm_class, algorithm_name: str, **kwargs) -> List[Rule]:
        """
        Exécute un algorithme et mesure le temps d'exécution.
        
        :param algorithm_class: Classe de l'algorithme à exécuter
        :param algorithm_name: Nom de l'algorithme
        :param kwargs: Arguments supplémentaires à passer à l'algorithme
        :return: Liste des règles découvertes
        """
        self.logger.info(f"Démarrage de l'algorithme {algorithm_name}")
        start_time = time.time()
        
        # Mesure de la mémoire avant l'exécution
        mem_before = get_memory_usage()
        if mem_before >= 0:
            self.logger.debug(f"Utilisation mémoire avant {algorithm_name}: {mem_before:.2f} Mo")
        
        # Exécuter avec un timeout
        try:
            rules = self._run_algorithm_with_timeout(algorithm_class, algorithm_name, **kwargs)
            
            execution_time = time.time() - start_time
            self.execution_times[algorithm_name] = execution_time
            
            # Mesure de la mémoire après l'exécution
            mem_after = get_memory_usage()
            if mem_after >= 0:
                self.logger.debug(f"Utilisation mémoire après {algorithm_name}: {mem_after:.2f} Mo")
                self.logger.debug(f"Différence de mémoire pour {algorithm_name}: {mem_after - mem_before:.2f} Mo")
            
            self.logger.info(f"{algorithm_name} terminé en {execution_time:.2f} secondes, {len(rules)} règles découvertes")
            
            # Sauvegarder les règles dans un fichier
            self._save_rules_to_file(rules, f"{algorithm_name}_rules.txt")
            
            return rules
            
        except Exception as e:
            self.logger.error(f"Erreur critique lors de l'exécution de {algorithm_name}: {e}", exc_info=True)
            self.execution_times[algorithm_name] = time.time() - start_time
            self.algorithm_errors[algorithm_name] = str(e)
            return []

    def _save_rules_to_file(self, rules: List[Rule], filename: str) -> None:
        """
        Sauvegarde une liste de règles dans un fichier texte.
        
        :param rules: Liste des règles à sauvegarder
        :param filename: Nom du fichier de sortie
        """
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# FDs sauvegardées: {len(rules)}\n")
            f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for i, rule in enumerate(rules, 1):
                rule_type = type(rule).__name__
                rule_str = str(rule)
                rule_display = getattr(rule, 'display', rule_str)
                
                f.write(f"{i}. [{rule_type}] {rule_display}\n")
                
                # Ajouter des détails supplémentaires si disponibles
                if hasattr(rule, 'accuracy'):
                    f.write(f"   Support: {rule.accuracy}\n")
                if hasattr(rule, 'confidence'):
                    f.write(f"   Confiance: {rule.confidence}\n")
                f.write("\n")
    
    def _save_common_rules_to_file(self, common_rules: List[Tuple[Rule, Rule]], filename: str) -> None:
        """
        Sauvegarde une liste de règles communes dans un fichier texte.
        
        :param common_rules: Liste des paires de règles communes
        :param filename: Nom du fichier de sortie
        """
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Règles communes sauvegardées: {len(common_rules)}\n")
            f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for i, (rule1, rule2) in enumerate(common_rules, 1):
                f.write(f"{i}. {rule1} <=> {rule2}\n")
                f.write("\n")
    
    def _save_rules_as_json(self, rules: List[Rule], filename: str) -> None:
        """
        Sauvegarde une liste de règles dans un fichier JSON.
        
        :param rules: Liste des règles à sauvegarder
        :param filename: Nom du fichier de sortie
        """
        output_path = self.output_dir / "json_results" / filename
        
        # Convertir les règles en format JSON-compatible
        rules_data = []
        for rule in rules:        
            rules_data.append(rule.to_dict())
        
        # Écrire dans le fichier JSON
        os.makedirs(self.output_dir / "json_results", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(rules_data, f, indent=4)
        
        self.logger.debug(f"Règles sauvegardées au format JSON: {output_path}")
    
    def _save_all_rules_as_json(self) -> None:
        """
        Sauvegarde toutes les règles découvertes au format JSON.
        """
        # Créer le répertoire de sortie
        json_dir = self.output_dir / "json_results"
        json_dir.mkdir(exist_ok=True)
        
        # Sauvegarder chaque ensemble de règles
        for algo_name, rules in self.discovered_rules.items():
            # Ne sauvegarder que s'il y a des règles
            if rules:
                self._save_rules_as_json(rules, f"{algo_name}_rules.json")
        
        # Sauvegarder les statistiques de comparaison
        if hasattr(self, 'statistics') and self.statistics:
            stats_path = json_dir / "statistics.json"
            
            # Préparer les statistiques pour la sérialisation JSON
            serializable_stats = {}
            for key, value in self.statistics.items():
                if isinstance(value, dict):
                    serializable_stats[key] = value
                else:
                    serializable_stats[key] = str(value)
            
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_stats, f, indent=4)
            
            self.logger.info(f"Statistiques sauvegardées au format JSON: {stats_path}")

    def run_all_algorithms(self, settings: Dict[str, Any] = None) -> Dict[str, List[Rule]]:
        """
        Exécute tous les algorithmes de découverte de FDs et stocke leurs résultats.
        
        :param settings: Paramètres à utiliser pour tous les algorithmes
        :return: Dictionnaire contenant les règles découvertes par chaque algorithme
        """
        settings = settings or {}
        
        # Paramètres communs pour les algorithmes FD
        fd_settings = {
            'max_lhs_size': settings.get('max_lhs_size', 3),
            'min_confidence': settings.get('min_confidence', 0.9),
            'timeout': self.timeout,  # Ajouter un paramètre de timeout
        }
        
        # Pour MATILDA, approche minimaliste pour éviter les conflits de paramètres
        matilda_settings = {
            'max_table':2,# settings.get('max_table', 2),
            'max_vars':2,# settings.get('max_vars', 2),
            'compatibility_mode': 'only_one_table',
            'timeout': self.timeout,  # Ajouter un paramètre de timeout
        }
        
        # Exécuter MATILDA uniquement pour les FDs
        try:
            self.logger.info("Exécution de MATILDA pour découvrir les FDs")
            start_time_fd = time.time()
            
            fd_rules = []
            with AlchemyUtility(self.db_uri, database_path=str(self.database_path), create_index=False) as db_util:
                algo = MATILDA(db_util, settings=matilda_settings)
                # Découvrir les FDs avec un timeout
                try:
                    with TimeoutHandler(self.timeout):
                        # Suivre la progression
                        total_rules = 0
                        last_progress_time = time.time()
                        for rule in algo.discover_rules(dependency_type='fd'):
                            fd_rules.append(rule)
                            total_rules += 1
                            
                            # Afficher la progression toutes les 3 secondes
                            current_time = time.time()
                            if current_time - last_progress_time > 3:
                                self.logger.info(f"MATILDA: {total_rules} FDs découvertes jusqu'à présent...")
                                last_progress_time = current_time
                except TimeoutError:
                    self.logger.warning(f"MATILDA a dépassé le délai imparti de {self.timeout} secondes.")
                    self.algorithm_errors['MATILDA_FDs'] = f"Timeout après {self.timeout} secondes"
            
            execution_time_fd = time.time() - start_time_fd
            self.logger.info(f"MATILDA FD terminé en {execution_time_fd:.2f} secondes, {len(fd_rules)} règles découvertes")
            
            self.discovered_rules['MATILDA_FDs'] = fd_rules
            self.execution_times['MATILDA_FDs'] = execution_time_fd
            
            # Sauvegarder les règles dans un fichier
            self._save_rules_to_file(fd_rules, "MATILDA_fd_rules.txt")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de MATILDA pour les FDs: {e}", exc_info=True)
            self.discovered_rules['MATILDA_FDs'] = []
            self.execution_times['MATILDA_FDs'] = 0.0
            self.algorithm_errors['MATILDA_FDs'] = str(e)
        
        # Exécuter les autres algorithmes normalement ou en parallèle
        algorithms_to_run = [
            (Tane, "TANE", fd_settings),
            (FastFDs, "FastFDs", fd_settings),
            (FDep, "FDep", fd_settings),
            (DFD, "DFD", fd_settings),
            # Nouveaux algorithmes ajoutés
            (AIDFD, "AIDFD", fd_settings),
            (Pyro, "Pyro", fd_settings)
        ]
        
        if self.use_parallel and self.cpu_count > 1:
            self.logger.info(f"Exécution parallèle des algorithmes sur {min(self.cpu_count, len(algorithms_to_run))} cœurs")
            with ProcessPoolExecutor(max_workers=min(self.cpu_count, len(algorithms_to_run))) as executor:
                futures = {executor.submit(self.run_algorithm, algo_class, algo_name, **algo_settings): 
                          algo_name for algo_class, algo_name, algo_settings in algorithms_to_run}
                
                for future in futures:
                    algo_name = futures[future]
                    try:
                        rules = future.result(timeout=self.timeout + 30)  # Ajouter une marge de 30s
                        self.discovered_rules[algo_name] = rules
                    except Exception as e:
                        self.logger.error(f"Erreur avec l'exécution parallèle de {algo_name}: {e}")
                        self.discovered_rules[algo_name] = []
                        self.algorithm_errors[algo_name] = str(e)
        else:
            # Exécution séquentielle
            self.logger.info("Exécution séquentielle des algorithmes")
            for algo_class, algo_name, algo_settings in algorithms_to_run:
                self.discovered_rules[algo_name] = self.run_algorithm(algo_class, algo_name, **algo_settings)
        
        # Sauvegarder les règles découvertes au format JSON
        self._save_all_rules_as_json()
        return self.discovered_rules
        
    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyse les résultats de tous les algorithmes exécutés.
        
        :return: Dictionnaire contenant les statistiques d'analyse
        """
        self.logger.info("Analyse des résultats...")
        
        # Statistiques globales
        analysis = {
            'total_rules_by_algorithm': {
                name: len(rules) for name, rules in self.discovered_rules.items()
            },
            'execution_times': self.execution_times,
            'comparisons': {},
            'unique_rules': {},
            'common_rules': {},
            'errors': self.algorithm_errors
        }
        
        # Comparer MATILDA FDs avec chaque algorithme de FDs
        fd_algorithms = ['TANE', 'FastFDs', 'FDep', 'DFD', 'AIDFD', 'Pyro']  # Ajout des nouveaux algorithmes
        # fd_algorithms = ['TANE', 'FastFDs', 'DFD']

        matilda_fds = self.discovered_rules.get('MATILDA_FDs', [])
        
        # Log pour vérification
        for algo_name in fd_algorithms:
            if algo_name in self.discovered_rules:
                self.logger.info(f"{algo_name} a découvert {len(self.discovered_rules[algo_name])} règles")
        
        for algo_name in fd_algorithms:
            if algo_name not in self.discovered_rules:
                self.logger.warning(f"Algorithme {algo_name} non exécuté ou aucune règle découverte")
                continue
            
            algo_rules = self.discovered_rules[algo_name]
            if not algo_rules:
                self.logger.warning(f"{algo_name} n'a trouvé aucune règle")
                continue
                
            if not matilda_fds:
                self.logger.warning("MATILDA n'a pas découvert de FDs à comparer")
                continue
                
            try:
                self.logger.info(f"Comparaison de {len(matilda_fds)} FDs MATILDA avec {len(algo_rules)} règles {algo_name}")
                comparison = self.rule_comparator.compare_rule_sets(matilda_fds, algo_rules)
                
                analysis['comparisons'][f"MATILDA_vs_{algo_name}"] = comparison
                
                # Trouver les règles uniques à chaque algorithme
                unique_to_matilda = [rule for rule in matilda_fds if not any(
                    self.rule_comparator.are_equivalent(rule, algo_rule) for algo_rule in algo_rules
                )]
                unique_to_algo = [rule for rule in algo_rules if not any(
                    self.rule_comparator.are_equivalent(rule, matilda_rule) for matilda_rule in matilda_fds
                )]
                
                # Trouver les règles communes
                common_rules = []
                max_common_rules = min(len(matilda_fds), len(algo_rules))
                for matilda_rule in matilda_fds:
                    for algo_rule in algo_rules:
                        if self.rule_comparator.are_equivalent(matilda_rule, algo_rule):
                            common_rules.append((matilda_rule, algo_rule))
                            break
                
                analysis['unique_rules'][f"unique_to_MATILDA_vs_{algo_name}"] = len(unique_to_matilda)
                analysis['unique_rules'][f"unique_to_{algo_name}_vs_MATILDA"] = len(unique_to_algo)
                analysis['common_rules'][f"MATILDA_and_{algo_name}"] = min(len(common_rules), max_common_rules)
                
                # Sauvegarder les règles uniques et communes dans des fichiers
                self._save_rules_to_file(unique_to_matilda, f"unique_to_MATILDA_vs_{algo_name}.txt")
                self._save_rules_to_file(unique_to_algo, f"unique_to_{algo_name}_vs_MATILDA.txt")
                self._save_common_rules_to_file(common_rules, f"common_MATILDA_and_{algo_name}.txt")
                
            except Exception as e:
                self.logger.error(f"Erreur lors de la comparaison entre MATILDA et {algo_name}: {e}", exc_info=True)
                
        # Comparer entre les algorithmes de FDs
        for i, algo1 in enumerate(fd_algorithms):
            if algo1 not in self.discovered_rules:
                continue
                
            for algo2 in fd_algorithms[i+1:]:
                if algo2 not in self.discovered_rules:
                    continue
                    
                rules1 = self.discovered_rules[algo1]
                rules2 = self.discovered_rules[algo2]
                        
                # Éviter les comparaisons inutiles si l'un des ensembles est vide
                if not rules1 or not rules2:
                    self.logger.warning(f"Comparaison {algo1} vs {algo2} ignorée car au moins un ensemble de règles est vide")
                    continue
                    
                try:
                    comparison = self.rule_comparator.compare_rule_sets(rules1, rules2)
                    analysis['comparisons'][f"{algo1}_vs_{algo2}"] = comparison
                    
                    # Calculer les règles uniques et communes
                    unique_to_algo1 = [rule for rule in rules1 if not any(
                        self.rule_comparator.are_equivalent(rule, rule2) for rule2 in rules2
                    )]
                    unique_to_algo2 = [rule for rule in rules2 if not any(
                        self.rule_comparator.are_equivalent(rule, rule1) for rule1 in rules1
                    )]
                    
                    common_rules = []
                    max_common_rules = min(len(rules1), len(rules2))
                    for rule1 in rules1:
                        for rule2 in rules2:
                            if self.rule_comparator.are_equivalent(rule1, rule2):
                                common_rules.append((rule1, rule2))
                                break
                        # Limiter le nombre de règles communes au minimum des deux ensembles
                        if len(common_rules) >= max_common_rules:
                            break
                            
                    analysis['unique_rules'][f"unique_to_{algo1}_vs_{algo2}"] = len(unique_to_algo1)
                    analysis['unique_rules'][f"unique_to_{algo2}_vs_{algo1}"] = len(unique_to_algo2)
                    analysis['common_rules'][f"{algo1}_and_{algo2}"] = len(common_rules)
                except Exception as e:
                    self.logger.error(f"Erreur lors de la comparaison entre {algo1} et {algo2}: {e}", exc_info=True)
        
        # Sauvegarder l'analyse dans un fichier
        self._save_analysis_to_file(analysis)
        
        return analysis
    
    def _save_analysis_to_file(self, analysis: Dict[str, Any]) -> None:
        """
        Sauvegarde l'analyse dans un fichier texte avec un format amélioré.
        
        :param analysis: Dictionnaire contenant les résultats de l'analyse
        """
        output_path = self.output_dir / "fd_analysis_results.txt"
        
        # Calcul de métriques supplémentaires
        performance_metrics = {}
        for algo, rules_count in analysis.get('total_rules_by_algorithm', {}).items():
            exec_time = analysis.get('execution_times', {}).get(algo, 0.01)  # Éviter division par zéro
            if exec_time > 0:
                rules_per_second = rules_count / exec_time
                performance_metrics[algo] = {
                    'rules_per_second': rules_per_second,
                    'time_per_rule': 1000 * exec_time / max(1, rules_count)  # ms par règle
                }
        
        # Trouver le meilleur algorithme pour différentes métriques
        best_performers = {}
        if performance_metrics:
            # Meilleur pour la vitesse (règles par seconde)
            best_speed = max(
                performance_metrics.items(), 
                key=lambda x: x[1]['rules_per_second'], 
                default=(None, {'rules_per_second': 0})
            )
            best_performers['speed'] = best_speed[0]
            
            # Meilleur pour l'efficacité (moins de temps par règle)
            best_efficiency = min(
                performance_metrics.items(), 
                key=lambda x: x[1]['time_per_rule'], 
                default=(None, {'time_per_rule': float('inf')})
            )
            best_performers['efficiency'] = best_efficiency[0]
            
            # Plus grand nombre de règles
            most_rules = max(
                analysis.get('total_rules_by_algorithm', {}).items(),
                key=lambda x: x[1],
                default=(None, 0)
            )
            best_performers['most_rules'] = most_rules[0]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # En-tête et informations générales
            f.write(f"# Rapport d'Analyse des Algorithmes de Découverte de Dépendances Fonctionnelles\n")
            f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Base de données: {self.database_name}\n\n")
            
            # Ajouter une section sur les erreurs rencontrées
            if analysis.get('errors'):
                f.write("## Erreurs et avertissements\n\n")
                f.write("| Algorithme | Erreur/Avertissement |\n")
                f.write("|------------|----------------------|\n")
                for algo, error in analysis.get('errors', {}).items():
                    f.write(f"| {algo} | {error} |\n")
                f.write("\n")
            
            # Résumé des performances
            f.write("## Résumé des performances\n\n")
            if best_performers:
                f.write(f"Meilleur algorithme en termes de vitesse: {best_performers.get('speed', 'N/A')}\n")
                f.write(f"Meilleur algorithme en termes d'efficacité: {best_performers.get('efficiency', 'N/A')}\n")
                f.write(f"Algorithme découvrant le plus de règles: {best_performers.get('most_rules', 'N/A')}\n\n")
            
            # Statistiques globales
            f.write("## Statistiques globales\n\n")
            f.write("### Nombre de FDs découvertes par algorithme\n")
            
            # Tableau formaté pour les règles
            f.write("| Algorithme | Nombre de FDs |\n")
            f.write("|------------|---------------|\n")
            for algo, count in sorted(
                analysis.get('total_rules_by_algorithm', {}).items(),
                key=lambda x: x[1], 
                reverse=True
            ):
                f.write(f"| {algo} | {count} |\n")
            f.write("\n")
            
            # Tableau formaté pour les temps d'exécution
            f.write("### Temps d'exécution par algorithme\n")
            f.write("| Algorithme | Temps (s) | FDs/s | Temps/FD (ms) |\n")
            f.write("|------------|-----------|-------|---------------|\n")
            for algo, time_taken in sorted(
                analysis.get('execution_times', {}).items(),
                key=lambda x: x[1]
            ):
                rules_count = analysis.get('total_rules_by_algorithm', {}).get(algo, 0)
                fds_per_sec = "N/A"
                time_per_fd = "N/A"
                
                if algo in performance_metrics:
                    fds_per_sec = f"{performance_metrics[algo]['rules_per_second']:.2f}"
                    time_per_fd = f"{performance_metrics[algo]['time_per_rule']:.2f}"
                        
                f.write(f"| {algo} | {time_taken:.2f} | {fds_per_sec} | {time_per_fd} |\n")
            f.write("\n")
            
            # Comparaisons détaillées entre algorithmes
            f.write("## Comparaisons détaillées entre algorithmes\n\n")
            for comp_name, stats in analysis.get('comparisons', {}).items():
                f.write(f"### {comp_name}\n")
                total_set1 = stats.get('total_rules_set1', 0)
                total_set2 = stats.get('total_rules_set2', 0)
                common = stats.get('common_rules', 0)
                unique_set1 = stats.get('unique_to_set1', 0)
                unique_set2 = stats.get('unique_to_set2', 0)
                
                f.write(f"- Total FDs ensemble 1: {total_set1}\n")
                f.write(f"- Total FDs ensemble 2: {total_set2}\n")
                f.write(f"- FDs communes: {common} ({(common/max(1, total_set1)*100):.1f}% de l'ensemble 1, {(common/max(1, total_set2)*100):.1f}% de l'ensemble 2)\n")
                f.write(f"- FDs uniques à l'ensemble 1: {unique_set1} ({(unique_set1/max(1, total_set1)*100):.1f}% de l'ensemble 1)\n")
                f.write(f"- FDs uniques à l'ensemble 2: {unique_set2} ({(unique_set2/max(1, total_set2)*100):.1f}% de l'ensemble 2)\n")
                
                # Calculer le coefficient de Jaccard (mesure de similarité entre ensembles)
                union_size = total_set1 + total_set2 - common
                jaccard = common / max(1, union_size)
                f.write(f"- Coefficient de Jaccard (similarité): {jaccard:.4f}\n\n")
            
            # Section pour les recommandations
            f.write("## Analyse et recommandations\n\n")
            
            # Recommandations basées sur les résultats
            f.write("### Recommandations\n\n")
            
            if best_performers:
                f.write(f"1. Pour les applications nécessitant une exécution rapide, privilégiez l'algorithme {best_performers.get('speed', 'N/A')}.\n")
                f.write(f"2. Pour les bases de données volumineuses où l'efficacité est cruciale, {best_performers.get('efficiency', 'N/A')} est recommandé.\n")
                f.write(f"3. Pour une découverte plus exhaustive des dépendances, {best_performers.get('most_rules', 'N/A')} offre le meilleur résultat.\n\n")
            
            f.write("### Notes supplémentaires\n\n")
            f.write("- Les résultats peuvent varier selon la structure et la taille de la base de données.\n")
            f.write("- Un grand nombre de règles n'est pas nécessairement synonyme de qualité ; vérifiez la pertinence des dépendances découvertes.\n")
            f.write("- Pour les bases de données de production, envisagez d'exécuter plusieurs algorithmes et de combiner leurs résultats.\n")
            
            # Pied de page
            f.write("\n---\n")
            f.write("Rapport généré automatiquement par le Comparateur d'Algorithmes FD.\n")

    def generate_html_report(self) -> str:
        """
        Génère un rapport HTML détaillé de la comparaison des algorithmes.
        
        :return: Chemin vers le rapport HTML généré
        """
        # Construire le chemin du rapport HTML
        report_path = self.output_dir / "fd_comparison_report.html"
        
        # Extraire les données pour le rapport
        rule_names = list(self.discovered_rules.keys())
        rule_counts = [len(rules) for rules in self.discovered_rules.values()]
        exec_times = [self.execution_times.get(name, 0) for name in rule_names]
        
        # Calculer des métriques supplémentaires
        performance_data = {}
        for algo, rules in self.discovered_rules.items():
            time_taken = self.execution_times.get(algo, 0.01)
            if time_taken > 0 and rules:
                rules_per_sec = len(rules) / time_taken
                time_per_rule = 1000 * time_taken / max(1, len(rules))
                performance_data[algo] = {
                    'rules': len(rules),
                    'time': time_taken,
                    'rules_per_sec': rules_per_sec,
                    'time_per_rule': time_per_rule,
                }
        
        # En-tête HTML
        html_content = """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Comparaison des Algorithmes de Découverte de Dépendances Fonctionnelles</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
                h1, h2, h3 { color: #333; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .chart-container { width: 600px; height: 400px; margin: 20px 0; }
                .good { color: green; }
                .bad { color: red; }
                .warning { color: orange; }
                .section { margin-bottom: 30px; padding: 15px; border: 1px solid #eee; border-radius: 5px; }
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>Rapport de Comparaison des Algorithmes de Découverte de Dépendances Fonctionnelles</h1>
            <p>Date: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """</p>
            <p>Base de données: """ + str(self.database_name) + """</p>
        """
        
        # Ajouter une section pour les erreurs s'il y en a
        if self.algorithm_errors:
            html_content += """
            <div class="section" style="border-color: #ffcccc;">
                <h2>⚠️ Erreurs et avertissements</h2>
                <table>
                    <tr>
                        <th>Algorithme</th>
                        <th>Erreur/Avertissement</th>
                    </tr>
            """
            
            for algo, error in self.algorithm_errors.items():
                html_content += f"""
                    <tr>
                        <td>{algo}</td>
                        <td class="warning">{error}</td>
                    </tr>
                """
                
            html_content += """
                </table>
            </div>
            """
        
        # Résumé des algorithmes
        html_content += """
            <div class="section">
                <h2>Résumé des Algorithmes</h2>
                <table>
                    <tr>
                        <th>Algorithme</th>
                        <th>FDs Découvertes</th>
                        <th>Temps d'Exécution (s)</th>
                        <th>FDs par seconde</th>
                    </tr>
        """
        
        for algo_name in rule_names:
            rules_count = len(self.discovered_rules.get(algo_name, []))
            exec_time = self.execution_times.get(algo_name, "N/A")
            
            if isinstance(exec_time, (int, float)):
                exec_time_fmt = f"{exec_time:.2f}"
                rules_per_sec = f"{rules_count / max(0.01, exec_time):.2f}" if exec_time > 0 else "N/A"
            else:
                exec_time_fmt = exec_time
                rules_per_sec = "N/A"
                
            html_content += f"""
                    <tr>
                        <td>{algo_name}</td>
                        <td>{rules_count}</td>
                        <td>{exec_time_fmt}</td>
                        <td>{rules_per_sec}</td>
                    </tr>
            """
            
        html_content += """
                </table>
            </div>
        """
        
        # Graphique de comparaison du nombre de règles
        html_content += """
            <div class="section">
                <h2>Comparaison du Nombre de FDs Découvertes</h2>
                <div class="chart-container">
                    <canvas id="rulesChart"></canvas>
                </div>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        const rulesCtx = document.getElementById('rulesChart').getContext('2d');
                        const rulesChart = new Chart(rulesCtx, {
                            type: 'bar',
                            data: {
                                labels: """ + json.dumps(rule_names) + """,
                                datasets: [{
                                    label: 'Nombre de FDs',
                                    data: """ + json.dumps(rule_counts) + """,
                                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                                    borderColor: 'rgba(54, 162, 235, 1)',
                                    borderWidth: 1
                                }]
                            },
                            options: {
                                responsive: true,
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Nombre de dépendances fonctionnelles'
                                        }
                                    }
                                }
                            }
                        });
                    });
                </script>
            </div>
        """
        
        # Graphique de comparaison des temps d'exécution
        html_content += """
            <div class="section">
                <h2>Comparaison des Temps d'Exécution</h2>
                <div class="chart-container">
                    <canvas id="timeChart"></canvas>
                </div>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        const timeCtx = document.getElementById('timeChart').getContext('2d');
                        const timeChart = new Chart(timeCtx, {
                            type: 'bar',
                            data: {
                                labels: """ + json.dumps(rule_names) + """,
                                datasets: [{
                                    label: 'Temps d\\'exécution (s)',
                                    data: """ + json.dumps(exec_times) + """,
                                    backgroundColor: 'rgba(255, 99, 132, 0.5)',
                                    borderColor: 'rgba(255, 99, 132, 1)',
                                    borderWidth: 1
                                }]
                            },
                            options: {
                                responsive: true,
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Secondes'
                                        }
                                    }
                                }
                            }
                        });
                    });
                </script>
            </div>
        """
        
        # Section de comparaison entre algorithmes
        if hasattr(self, 'statistics') and self.statistics and 'comparisons' in self.statistics:
            html_content += """
            <div class="section">
                <h2>Comparaisons entre Algorithmes</h2>
                <table>
                    <tr>
                        <th>Comparaison</th>
                        <th>FDs communes</th>
                        <th>FDs uniques (A)</th>
                        <th>FDs uniques (B)</th>
                        <th>Similarité (Jaccard)</th>
                    </tr>
            """
            
            for comp_name, stats in self.statistics['comparisons'].items():
                total_set1 = stats.get('total_rules_set1', 0)
                total_set2 = stats.get('total_rules_set2', 0)
                common = stats.get('common_rules', 0)
                unique_a = stats.get('unique_to_set1', 0)
                unique_b = stats.get('unique_to_set2', 0)
                
                # Calculer le coefficient de Jaccard
                union_size = total_set1 + total_set2 - common
                jaccard = common / max(1, union_size)
                
                html_content += f"""
                    <tr>
                        <td>{comp_name}</td>
                        <td>{common} ({(common/max(1, total_set1)*100):.1f}%)</td>
                        <td>{unique_a} ({(unique_a/max(1, total_set1)*100):.1f}%)</td>
                        <td>{unique_b} ({(unique_b/max(1, total_set2)*100):.1f}%)</td>
                        <td>{jaccard:.4f}</td>
                    </tr>
                """
                
            html_content += """
                </table>
            </div>
            """
        
        # Recommandations
        html_content += """
            <div class="section">
                <h2>Recommandations</h2>
                <p>Basées sur les performances observées des algorithmes :</p>
                <ul>
        """
        
        # Identifier les meilleurs algorithmes
        if performance_data:
            best_speed = max(performance_data.items(), key=lambda x: x[1]['rules_per_sec'], default=(None, {}))
            best_efficiency = min(performance_data.items(), key=lambda x: x[1]['time_per_rule'], default=(None, {}))
            most_rules = max(performance_data.items(), key=lambda x: x[1]['rules'], default=(None, {}))
            
            if best_speed[0]:
                html_content += f"<li><strong>Pour les applications nécessitant une exécution rapide:</strong> {best_speed[0]} ({best_speed[1]['rules_per_sec']:.2f} FDs/seconde)</li>\n"
                
            if best_efficiency[0]:
                html_content += f"<li><strong>Pour l'efficacité de traitement:</strong> {best_efficiency[0]} ({best_efficiency[1]['time_per_rule']:.2f} ms/FD)</li>\n"
                
            if most_rules[0]:
                html_content += f"<li><strong>Pour une découverte exhaustive:</strong> {most_rules[0]} ({most_rules[1]['rules']} FDs découvertes)</li>\n"
        
        html_content += """
                </ul>
                <p><em>Note: Les performances peuvent varier en fonction des caractéristiques de la base de données.</em></p>
            </div>
        """
        
        # Pied de page
        html_content += """
            <div class="footer" style="margin-top: 20px; padding-top: 10px; border-top: 1px solid #eee; text-align: center;">
                <p>Rapport généré automatiquement par le comparateur d'algorithmes FD.</p>
            </div>
        </body>
        </html>
        """
        
        # Écrire le contenu HTML dans le fichier
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        self.logger.info(f"Rapport HTML généré: {report_path}")
        
        return str(report_path)


def main():
    parser = argparse.ArgumentParser(description='Comparer les résultats de différents algorithmes de découverte de dépendances fonctionnelles')
    parser.add_argument('--db-path', default='../../data/db', help='Chemin vers le répertoire de la base de données')
    parser.add_argument('--db-name', default='Bupa.db', help='Nom de la base de données')
    parser.add_argument('--output', default='fd_comparison_results', help='Répertoire de sortie pour les résultats')
    parser.add_argument('--max-lhs', type=int, default=3, help='Taille maximale du déterminant (partie gauche) pour les FDs')
    parser.add_argument('--min-conf', type=float, default=0.9, help='Confiance minimale pour les règles')
    parser.add_argument('--max-table', type=int, default=2, help='Nombre maximal de tables pour MATILDA')
    parser.add_argument('--max-vars', type=int, default=1, help='Nombre maximal de variables pour MATILDA')
    
    # Options pour la création de données de test
    parser.add_argument('--create-test-db', action='store_true', help='Créer une petite base de données de test')
    parser.add_argument('--test-db-name', default='test_small.db', help='Nom de la base de données de test')
    parser.add_argument('--test-rows', type=int, default=100, help='Nombre de lignes par table dans la DB de test')
    parser.add_argument('--test-cols', type=int, default=5, help='Nombre de colonnes par table dans la DB de test')
    parser.add_argument('--test-tables', type=int, default=1, help='Nombre de tables dans la DB de test')
    parser.add_argument('--test-fd-density', type=float, default=0.3, help='Densité des FDs dans la DB de test (0-1)')
    
    # Options pour l'exécution
    parser.add_argument('--timeout', type=int, default=300, help='Timeout en secondes pour chaque algorithme (0 = sans limite)')
    parser.add_argument('--parallel', action='store_true', help='Exécuter les algorithmes en parallèle si possible')
    
    args = parser.parse_args()
    
    # Création de la base de données de test si demandé
    db_path = Path(args.db_path)
    db_name = args.db_name
    
    if args.create_test_db:
        db_name = args.test_db_name
        create_test_database(
            db_path, 
            db_name, 
            num_rows=args.test_rows, 
            columns_per_table=args.test_cols,
            num_tables=args.test_tables,
            fd_density=args.test_fd_density
        )
    
    # Initialisation du comparateur avec options de timeout et parallélisation
    comparer = FDAlgorithmComparer(
        args.db_path, 
        db_name, 
        args.output, 
        timeout=args.timeout if args.timeout > 0 else None,
        use_parallel=args.parallel
    )
    
    # Configurer les paramètres des algorithmes
    settings = {
        'max_lhs_size':0,# args.max_lhs,
        'min_confidence':0,# args.min_conf,
        'max_table': args.max_table,
        'max_vars': args.max_vars,
        'compatibility_mode': 'fd',
        'min_support': 0.0,  # Pas de filtrage par support pour l'analyse
        'filter_redundant': True,
    }
    
    # Exécuter tous les algorithmes FD
    comparer.run_all_algorithms(settings)
    
    # Analyser les résultats
    analysis_results = comparer.analyze_results()
    comparer.statistics = analysis_results
    
    # Générer un rapport HTML
    report_path = comparer.generate_html_report()
    
    print(f"\nExécution terminée. Résultats sauvegardés dans: {args.output}")
    print(f"Rapport HTML généré: {report_path}")
    
    # Afficher les erreurs éventuelles
    if comparer.algorithm_errors:
        print("\nAttention: Certains algorithmes ont rencontré des erreurs:")
        for algo, error in comparer.algorithm_errors.items():
            print(f" - {algo}: {error}")


if __name__ == "__main__":
    main()
