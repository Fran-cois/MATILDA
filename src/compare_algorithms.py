import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

from algorithms.matilda import MATILDA
from algorithms.tane import Tane
from algorithms.fastfds import FastFDs
from algorithms.fdep import FDep
from algorithms.dfd import DFD
from database.alchemy_utility import AlchemyUtility
from utils.rule_comparator import RuleComparator
from utils.rules import Rule, FunctionalDependency, EGDRule, TGDRule
from utils.logging_utils import configure_global_logger


class AlgorithmComparer:
    """
    Classe pour exécuter et comparer différents algorithmes de découverte de règles.
    """
    
    def __init__(self, database_path: str, database_name: str, output_dir: str):
        """
        Initialise le comparateur d'algorithmes.
        
        :param database_path: Chemin vers le répertoire contenant la base de données
        :param database_name: Nom de la base de données
        :param output_dir: Répertoire où sauvegarder les résultats
        """
        self.database_path = Path(database_path)
        self.database_name = Path(database_name)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        rules = []
        try:
            # Extraire les paramètres d'initialisation
            settings = kwargs.pop('settings', {}) if 'settings' in kwargs else kwargs.copy()
            
            with AlchemyUtility(self.db_uri, database_path=str(self.database_path), create_index=False) as db_util:
                # Initialiser l'algorithme avec settings
                algo = algorithm_class(db_util, settings=settings)
                
                # Appeler discover_rules avec les paramètres restants
                for rule in algo.discover_rules(**kwargs):
                    rules.append(rule)
                    
            execution_time = time.time() - start_time
            self.execution_times[algorithm_name] = execution_time
            self.logger.info(f"{algorithm_name} terminé en {execution_time:.2f} secondes, {len(rules)} règles découvertes")
            
            # Sauvegarder les règles dans un fichier
            self._save_rules_to_file(rules, f"{algorithm_name}_rules.txt")
            
            return rules
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de {algorithm_name}: {e}", exc_info=True)
            self.execution_times[algorithm_name] = time.time() - start_time
            return []
    
    def _convert_egds_to_fds(self, egds: List[EGDRule]) -> List[FunctionalDependency]:
        """
        Convertit les EGDs en FDs en utilisant la méthode to_fd de EGDRule.
        
        :param egds: Liste des EGDs à convertir
        :return: Liste des FDs converties
        """
        fds = []
        self.logger.info(f"Tentative de conversion de {len(egds)} EGDs en FDs...")
        
        for egd in egds:
            try:
                if not isinstance(egd, EGDRule):
                    continue
                # Utiliser la méthode to_fd avec les attributs supplémentaires
                fd = egd.to_fd()
                
                # Ne plus utiliser setattr, mais créer une nouvelle instance avec les attributs corrects
                fd_with_tracking = FunctionalDependency(
                    table=fd.table,
                    determinant=fd.determinant,
                    dependent=fd.dependent,
                    correct=fd.correct,
                    compatible=fd.compatible,
                    converted_from_egd=True,
                    original_egd=egd.display if hasattr(egd, 'display') else str(egd)
                )
                
                fds.append(fd_with_tracking)
                self.logger.debug(f"EGD convertie en FD: {fd_with_tracking.table}.{fd_with_tracking.determinant} -> {fd_with_tracking.dependent}")
                
            except Exception as e:
                self.logger.warning(f"Erreur lors de la conversion d'un EGD en FD: {e}", exc_info=True)
                continue
        
        self.logger.info(f"{len(fds)} EGDs ont été convertis en FDs.")
        return fds

    def run_all_algorithms(self, settings: Dict[str, Any] = None) -> Dict[str, List[Rule]]:
        """
        Exécute tous les algorithmes et stocke leurs résultats.
        
        :param settings: Paramètres à utiliser pour tous les algorithmes
        :return: Dictionnaire contenant les règles découvertes par chaque algorithme
        """
        settings = settings or {}
        
        # Paramètres communs pour les algorithmes FD
        fd_settings = {
            'max_lhs_size': settings.get('max_lhs_size', 3),
            'min_confidence': settings.get('min_confidence', 0.9),
        }
        
        # Pour MATILDA, approche minimaliste pour éviter les conflits de paramètres
        matilda_settings = {
            'max_table': settings.get('max_table', 2),
            'max_vars': settings.get('max_vars', 1),
            'compatibility_mode': 'only_one_table'# settings.get('compatibility_mode', 'only_one_table'),
        }
        
        # Exécuter MATILDA pour EGDs, TGDs et FDs séparément
        try:
            # 1. Exécution pour les EGDs
            self.logger.info("Exécution de MATILDA pour découvrir les EGDs")
            start_time_egd = time.time()
            
            egd_rules = []
            with AlchemyUtility(self.db_uri, database_path=str(self.database_path), create_index=False) as db_util:
                algo = MATILDA(db_util, settings=matilda_settings)
                # Découvrir les EGDs
                for rule in algo.discover_rules(dependency_type='egd'):
                    egd_rules.append(rule)
            
            execution_time_egd = time.time() - start_time_egd
            self.logger.info(f"MATILDA EGD terminé en {execution_time_egd:.2f} secondes, {len(egd_rules)} règles découvertes")
            
            # 2. Exécution pour les TGDs
            self.logger.info("Exécution de MATILDA pour découvrir les TGDs")
            start_time_tgd = time.time()
            
            tgd_rules = []
            with AlchemyUtility(self.db_uri, database_path=str(self.database_path), create_index=False) as db_util:
                algo = MATILDA(db_util, settings=matilda_settings)
                # Découvrir les TGDs
                for rule in algo.discover_rules(dependency_type='tgd'):
                    tgd_rules.append(rule)
            
            execution_time_tgd = time.time() - start_time_tgd
            self.logger.info(f"MATILDA TGD terminé en {execution_time_tgd:.2f} secondes, {len(tgd_rules)} règles découvertes")
            
            # 3. Exécution pour les FDs
            self.logger.info("Exécution de MATILDA pour découvrir les FDs")
            start_time_fd = time.time()
            converted_fds = self._convert_egds_to_fds(egd_rules)

            fd_rules = []
            with AlchemyUtility(self.db_uri, database_path=str(self.database_path), create_index=False) as db_util:
                algo = MATILDA(db_util, settings=matilda_settings)
                # Découvrir les FDs
                for rule in algo.discover_rules(dependency_type='fd'):
                    fd_rules.append(rule)
            
            execution_time_fd = time.time() - start_time_fd
            self.logger.info(f"MATILDA FD terminé en {execution_time_fd:.2f} secondes, {len(fd_rules)} règles découvertes dont {len(converted_fds)} converties depuis EGDs")
            
            # Combiner les règles et le temps total
            all_rules = egd_rules + tgd_rules + fd_rules
            total_execution_time = execution_time_egd + execution_time_tgd + execution_time_fd
            
            self.discovered_rules['MATILDA'] = all_rules
            self.execution_times['MATILDA'] = total_execution_time
            
            # Stocker les différentes règles séparément pour la comparaison
            self.discovered_rules['MATILDA_FDs'] = fd_rules
            self.execution_times['MATILDA_FDs'] = execution_time_fd
            
            self.discovered_rules['MATILDA_EGDs'] = egd_rules
            self.execution_times['MATILDA_EGDs'] = execution_time_egd
            
            self.discovered_rules['MATILDA_TGDs'] = tgd_rules
            self.execution_times['MATILDA_TGDs'] = execution_time_tgd
            
            # Sauvegarder les différents types de règles dans des fichiers
            self._save_rules_to_file(all_rules, "MATILDA_all_rules.txt")
            self._save_rules_to_file(fd_rules, "MATILDA_fd_rules.txt")
            self._save_rules_to_file(egd_rules, "MATILDA_egd_rules.txt")
            self._save_rules_to_file(tgd_rules, "MATILDA_tgd_rules.txt")
            self._save_rules_to_file(converted_fds, "MATILDA_converted_fds.txt")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de MATILDA: {e}", exc_info=True)
            self.discovered_rules['MATILDA'] = []
            self.discovered_rules['MATILDA_FDs'] = []
            self.discovered_rules['MATILDA_EGDs'] = []
            self.discovered_rules['MATILDA_TGDs'] = []
            self.execution_times['MATILDA'] = 0.0
            self.execution_times['MATILDA_FDs'] = 0.0
            self.execution_times['MATILDA_EGDs'] = 0.0
            self.execution_times['MATILDA_TGDs'] = 0.0
        
        # Exécuter les autres algorithmes normalement
        self.discovered_rules['TANE'] = self.run_algorithm(Tane, "TANE", **fd_settings)
        self.discovered_rules['FastFDs'] = self.run_algorithm(FastFDs, "FastFDs", **fd_settings)
        self.discovered_rules['FDep'] = self.run_algorithm(FDep, "FDep", **fd_settings)
        self.discovered_rules['DFD'] = self.run_algorithm(DFD, "DFD", **fd_settings)
        
        return self.discovered_rules
    
    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyse les résultats de tous les algorithmes exécutés.
        
        :return: Dictionnaire contenant les statistiques d'analyse
        """
        self.logger.info("Analyse des résultats...")
        
        # Séparer les différents types de règles de MATILDA
        matilda_rules = self.discovered_rules.get('MATILDA', [])
        matilda_egds = self.discovered_rules.get('MATILDA_EGDs', [])
        matilda_tgds = self.discovered_rules.get('MATILDA_TGDs', [])
        matilda_fds = self.discovered_rules.get('MATILDA_FDs', [])
        
        # Si les règles séparées ne sont pas disponibles, les extraire de l'ensemble complet
        if not matilda_egds:
            matilda_egds = [rule for rule in matilda_rules if isinstance(rule, EGDRule)]
        
        if not matilda_tgds:
            matilda_tgds = [rule for rule in matilda_rules if isinstance(rule, TGDRule)]
            
        if not matilda_fds:
            matilda_fds = [rule for rule in matilda_rules if isinstance(rule, FunctionalDependency)]
        
        self.logger.info(f"MATILDA a découvert {len(matilda_egds)} EGDs, {len(matilda_tgds)} TGDs et {len(matilda_fds)} FDs")
        
        # Statistiques globales
        analysis = {
            'total_rules_by_algorithm': {
                name: len(rules) for name, rules in self.discovered_rules.items() 
                if name not in ['MATILDA_FDs', 'MATILDA_EGDs', 'MATILDA_TGDs']  # Exclure les sous-ensembles
            },
            'execution_times': self.execution_times,
            'comparisons': {},
            'unique_rules': {},
            'common_rules': {},
        }
        
        # Comparer MATILDA FDs avec chaque algorithme de FDs
        fd_algorithms = ['TANE', 'FastFDs', 'FDep', 'DFD']
        
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
                # Utiliser les FDs de MATILDA pour la comparaison, pas les EGDs
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
                analysis['common_rules'][f"MATILDA_and_{algo_name}"] = min(len(common_rules),max_common_rules)
                
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
        
        # Calculer les statistiques sur les différents types de règles
        analysis['egds'] = {
            'total': len(matilda_egds),
            'stats': self._calculate_rule_stats(matilda_egds)
        }
        
        analysis['tgds'] = {
            'total': len(matilda_tgds),
            'stats': self._calculate_rule_stats(matilda_tgds)
        }
        
        # Sauvegarder l'analyse dans un fichier
        self._save_analysis_to_file(analysis)
        
        return analysis
    
    def generate_html_report(self) -> str:
        """
        Génère un rapport HTML détaillé de la comparaison des algorithmes.
        
        :return: Chemin vers le rapport HTML généré
        """
        # Construire le chemin du rapport HTML
        report_path = self.output_dir / "comparison_report.html"
        
        # En-tête HTML
        html_content = """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Comparaison des Algorithmes de Découverte de Règles</title>
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
                .section { margin-bottom: 30px; padding: 15px; border: 1px solid #eee; border-radius: 5px; }
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>Rapport de Comparaison des Algorithmes de Découverte de Règles</h1>
            <p>Date: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """</p>
            <p>Base de données: """ + str(self.database_name) + """</p>
        """
        
        # Résumé des algorithmes
        html_content += """
            <div class="section">
                <h2>Résumé des Algorithmes</h2>
                <table>
                    <tr>
                        <th>Algorithme</th>
                        <th>Règles Découvertes</th>
                        <th>Temps d'Exécution (s)</th>
                    </tr>
        """
        
        for algo_name, rules in self.discovered_rules.items():
            exec_time = self.execution_times.get(algo_name, "N/A")
            if isinstance(exec_time, (int, float)):
                exec_time = f"{exec_time:.2f}"
                
            html_content += f"""
                    <tr>
                        <td>{algo_name}</td>
                        <td>{len(rules)}</td>
                        <td>{exec_time}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
        """
        
        # Suppression de la section "Comparaison des Temps d'Exécution" ici
        
        # Graphique de comparaison du nombre de règles
        rule_names = list(self.discovered_rules.keys())
        rule_counts = [len(rules) for rules in self.discovered_rules.values()]
        
        html_content += """
            <div class="section">
                <h2>Comparaison du Nombre de Règles Découvertes</h2>
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
                                    label: 'Nombre de Règles',
                                    data: """ + json.dumps(rule_counts) + """,
                                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                                    borderColor: 'rgba(75, 192, 192, 1)',
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
                                            text: 'Nombre de règles'
                                        }
                                    }
                                }
                            }
                        });
                    });
                </script>
            </div>
        """
        
        # Reste de la méthode sans changement
        # Pour MATILDA, ajouter une section sur les EGDs et TGDs découvertes
        if 'MATILDA' in self.discovered_rules:
            matilda_egds = self.discovered_rules.get('MATILDA_EGDs', [])
            matilda_tgds = self.discovered_rules.get('MATILDA_TGDs', [])
            
            if not matilda_egds:
                matilda_egds = [rule for rule in self.discovered_rules['MATILDA'] if isinstance(rule, EGDRule)]
                
            if not matilda_tgds:
                matilda_tgds = [rule for rule in self.discovered_rules['MATILDA'] if isinstance(rule, TGDRule)]
            
            html_content += f"""
                <div class="section">
                    <h2>Dépendances Génératrices d'Égalité (EGDs) Découvertes par MATILDA</h2>
                    <p>Nombre total d'EGDs: {len(matilda_egds)}</p>
                    
                    <h3>Liste des EGDs (top 10):</h3>
                    <ul>
            """
            
            for i, egd in enumerate(matilda_egds[:10]):
                html_content += f"<li>{egd.display}</li>\n"
                
            if len(matilda_egds) > 10:
                html_content += f"<li>... et {len(matilda_egds) - 10} autres EGDs</li>\n"
                
            html_content += """
                    </ul>
                </div>
                
                <div class="section">
                    <h2>Dépendances Génératrices de Tuples (TGDs) Découvertes par MATILDA</h2>
                    <p>Nombre total de TGDs: {0}</p>
                    
                    <h3>Liste des TGDs (top 10):</h3>
                    <ul>
            """.format(len(matilda_tgds))
            
            for i, tgd in enumerate(matilda_tgds[:10]):
                html_content += f"<li>{tgd.display}</li>\n"
                
            if len(matilda_tgds) > 10:
                html_content += f"<li>... et {len(matilda_tgds) - 10} autres TGDs</li>\n"
                
            html_content += """
                    </ul>
                </div>
            """
        
        # Pied de page
        html_content += """
            <div class="footer">
                <p>Rapport généré automatiquement par le comparateur d'algorithmes.</p>
            </div>
        </body>
        </html>
        """
        
        # Écrire le contenu HTML dans le fichier
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        self.logger.info(f"Rapport HTML généré: {report_path}")
        
        return str(report_path)
    
    def _save_rules_to_file(self, rules: List[Rule], filename: str) -> None:
        """
        Sauvegarde une liste de règles dans un fichier texte.
        
        :param rules: Liste des règles à sauvegarder
        :param filename: Nom du fichier de sortie
        """
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Règles sauvegardées: {len(rules)}\n")
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
    
    def _save_common_rules_to_file(self, rule_pairs: List[Tuple[Rule, Rule]], filename: str) -> None:
        """
        Sauvegarde les paires de règles équivalentes dans un fichier texte.
        
        :param rule_pairs: Liste de tuples de règles équivalentes
        :param filename: Nom du fichier de sortie
        """
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Paires de règles équivalentes sauvegardées: {len(rule_pairs)}\n")
            f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for i, (rule1, rule2) in enumerate(rule_pairs, 1):
                rule1_type = type(rule1).__name__
                rule2_type = type(rule2).__name__
                
                f.write(f"{i}. Paire de règles équivalentes:\n")
                f.write(f"   Règle 1 [{rule1_type}]: {getattr(rule1, 'display', str(rule1))}\n")
                f.write(f"   Règle 2 [{rule2_type}]: {getattr(rule2, 'display', str(rule2))}\n\n")
    
    def _save_analysis_to_file(self, analysis: Dict[str, Any]) -> None:
        """
        Sauvegarde l'analyse dans un fichier texte.
        
        :param analysis: Dictionnaire contenant les résultats de l'analyse
        """
        output_path = self.output_dir / "analysis_results.txt"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Analyse des résultats de découverte de règles\n")
            f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Base de données: {self.database_name}\n\n")
            
            # Statistiques globales
            f.write("## Statistiques globales\n\n")
            f.write("### Nombre de règles découvertes par algorithme\n")
            for algo, count in analysis.get('total_rules_by_algorithm', {}).items():
                f.write(f"{algo}: {count}\n")
            f.write("\n")
            
            f.write("### Temps d'exécution par algorithme (secondes)\n")
            for algo, time_taken in analysis.get('execution_times', {}).items():
                f.write(f"{algo}: {time_taken:.2f}\n")
            f.write("\n")
            
            # Comparaisons détaillées
            f.write("## Comparaisons détaillées\n\n")
            for comp_name, stats in analysis.get('comparisons', {}).items():
                f.write(f"### {comp_name}\n")
                f.write(f"Total règles ensemble 1: {stats.get('total_rules_set1', 'N/A')}\n")
                f.write(f"Total règles ensemble 2: {stats.get('total_rules_set2', 'N/A')}\n")
                f.write(f"Règles communes: {stats.get('common_rules', 'N/A')}\n")
                f.write(f"Règles uniques à l'ensemble 1: {stats.get('unique_to_set1', 'N/A')}\n")
                f.write(f"Règles uniques à l'ensemble 2: {stats.get('unique_to_set2', 'N/A')}\n\n")
            
            # Statistiques EGDs
            if 'egds' in analysis:
                f.write("## Statistiques sur les EGDs\n\n")
                f.write(f"Total EGDs: {analysis['egds'].get('total', 0)}\n")
                
                egd_stats = analysis['egds'].get('stats', {})
                if egd_stats:
                    f.write(f"Support moyen: {egd_stats.get('avg_support', 'N/A')}\n")
                    f.write(f"Confiance moyenne: {egd_stats.get('avg_confidence', 'N/A')}\n")
                    f.write(f"EGDs avec confiance = 1.0: {egd_stats.get('perfect_confidence', 0)}\n\n")
            
            # Statistiques TGDs
            if 'tgds' in analysis:
                f.write("## Statistiques sur les TGDs\n\n")
                f.write(f"Total TGDs: {analysis['tgds'].get('total', 0)}\n")
                
                tgd_stats = analysis['tgds'].get('stats', {})
                if tgd_stats:
                    f.write(f"Support moyen: {tgd_stats.get('avg_support', 'N/A')}\n")
                    f.write(f"Confiance moyenne: {tgd_stats.get('avg_confidence', 'N/A')}\n")
                    f.write(f"TGDs avec confiance = 1.0: {tgd_stats.get('perfect_confidence', 0)}\n")
    
    def _calculate_rule_stats(self, rules: List[Rule]) -> Dict[str, Any]:
        """
        Calcule des statistiques sur un ensemble de règles.
        
        :param rules: Liste des règles
        :return: Dictionnaire contenant les statistiques calculées
        """
        if not rules:
            return {
                'avg_support': 0,
                'avg_confidence': 0,
                'perfect_confidence': 0
            }
            
        support_sum = 0
        confidence_sum = 0
        perfect_confidence_count = 0
        
        for rule in rules:
            support = getattr(rule, 'accuracy', 0)
            confidence = getattr(rule, 'confidence', 0)
            
            support_sum += support
            confidence_sum += confidence
            
            if confidence >= 0.999:  # Considérer comme parfait si confiance ≥ 0.999
                perfect_confidence_count += 1
                
        return {
            'avg_support': support_sum / len(rules),
            'avg_confidence': confidence_sum / len(rules),
            'perfect_confidence': perfect_confidence_count
        }


def main():
    parser = argparse.ArgumentParser(description='Comparer les résultats de différents algorithmes de découverte de règles')
    parser.add_argument('--db-path', default='../../data/db', help='Chemin vers le répertoire de la base de données')
    parser.add_argument('--db-name', default='Bupa.db', help='Nom de la base de données')
    parser.add_argument('--output', default='comparison_results', help='Répertoire de sortie pour les résultats')
    parser.add_argument('--max-lhs', type=int, default=3, help='Taille maximale du déterminant (partie gauche) pour les FDs')
    parser.add_argument('--min-conf', type=float, default=0.9, help='Confiance minimale pour les règles')
    parser.add_argument('--max-table', type=int, default=3, help='Nombre maximal de tables pour MATILDA')
    parser.add_argument('--max-vars', type=int, default=6, help='Nombre maximal de variables pour MATILDA')
    parser.add_argument('--create-test-data', action='store_true', help='Créer des données de test si nécessaire')
    args = parser.parse_args()
    

    
    comparer = AlgorithmComparer(args.db_path, args.db_name, args.output)
    
    # Configurer les paramètres des algorithmes
    settings = {
        'max_lhs_size': args.max_lhs,
        'min_confidence': args.min_conf,
        'max_table': args.max_table,
        'max_vars': args.max_vars,
        "compatiblity_mode":"only_one_table",
        'min_support': 0.0,  # Pas de filtrage par support pour l'analyse
        'filter_redundant': True,
    }
    
    # Exécuter tous les algorithmes
    comparer.run_all_algorithms(settings)
    
    # Analyser les résultats
    analysis_results = comparer.analyze_results()
    comparer.statistics = analysis_results
    
    # Générer un rapport HTML
    report_path = comparer.generate_html_report()
    
    print(f"\nExécution terminée. Résultats sauvegardés dans: {args.output}")
    print(f"Rapport HTML généré: {report_path}")


if __name__ == "__main__":
    main()