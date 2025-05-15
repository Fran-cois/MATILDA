import argparse
import json
import logging
import os
import sqlite3
import time
import random
import string
import signal
import glob
import multiprocessing
import re
import pandas as pd
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
from database.alchemy_utility import AlchemyUtility
from utils.rule_comparator import RuleComparator
from utils.rules import Rule, FunctionalDependency
from utils.logging_utils import configure_global_logger
from compare_algorithms_fd_only import FDAlgorithmComparer, TimeoutHandler, get_memory_usage

class BatchFDComparison:
    """
    Classe pour exécuter et comparer des algorithmes de découverte de dépendances fonctionnelles
    sur plusieurs bases de données en séquence, avec génération de rapports consolidés.
    """
    
    def __init__(self, 
                 db_path: str, 
                 output_dir: str, 
                 patterns: List[str] = None, 
                 timeout: int = 300, 
                 use_parallel: bool = False,
                 max_lhs: int = 3,
                 min_conf: float = 0.9):
        """
        Initialise le comparateur d'algorithmes en lot.
        
        :param db_path: Chemin vers le répertoire contenant les bases de données
        :param output_dir: Répertoire où sauvegarder les résultats
        :param patterns: Liste de motifs pour filtrer les bases de données
        :param timeout: Timeout en secondes pour chaque algorithme (défaut: 300s)
        :param use_parallel: Utiliser le traitement parallèle pour les algorithmes
        :param max_lhs: Taille maximale du déterminant (partie gauche) pour les FDs
        :param min_conf: Confiance minimale pour les règles
        """
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.use_parallel = use_parallel
        self.max_lhs = max_lhs
        self.min_conf = min_conf
        
        # Liste des patterns pour filtrer les bases de données
        self.patterns = patterns or ["*.db", "*.sqlite", "*.sqlite3"]
        
        # Configuration du logger central
        log_dir = self.output_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Correction de l'appel à configure_global_logger
        log_filename = "batch_comparison"
        self.logger = logging.getLogger(log_filename)
        self.logger.setLevel(logging.INFO)
        # Dictionnaires pour stocker les résultats agrégés
        self.all_results = {}
        self.comparisons = {}
        self.error_databases = {}
    
    def find_databases(self) -> List[Path]:
        """
        Trouve toutes les bases de données correspondant aux motifs spécifiés.
        
        :return: Liste des chemins vers les bases de données trouvées
        """
        all_dbs = []
        for pattern in self.patterns:
            pattern_results = list(self.db_path.glob(pattern))
            all_dbs.extend(pattern_results)
        
        # Trier par taille pour traiter d'abord les petites bases de données
        all_dbs.sort(key=lambda p: p.stat().st_size if p.exists() else 0)
        
        self.logger.info(f"Trouvé {len(all_dbs)} bases de données à analyser")
        for db in all_dbs:
            size_mb = db.stat().st_size / (1024 * 1024)
            self.logger.info(f" - {db.name} ({size_mb:.2f} Mo)")
        
        return all_dbs
    
    def compare_database(self, db_file: Path) -> Dict[str, Any]:
        """
        Compare les algorithmes sur une base de données spécifique.
        
        :param db_file: Chemin vers la base de données
        :return: Dictionnaire contenant les résultats de la comparaison
        """
        db_name = db_file.name
        db_path = db_file.parent
        
        self.logger.info(f"Démarrage de la comparaison pour {db_name}")
        
        # Créer un sous-répertoire pour cette base de données
        db_output_dir = self.output_dir / db_name.replace('.', '_')
        db_output_dir.mkdir(exist_ok=True)
        
        # Initialiser le comparateur pour cette base de données
        try:
            comparer = FDAlgorithmComparer(
                str(db_path), 
                db_name, 
                str(db_output_dir),
                timeout=self.timeout,
                use_parallel=self.use_parallel
            )
            
            # Configurer les paramètres des algorithmes
            settings = {
                'max_lhs_size': self.max_lhs,
                'min_confidence': self.min_conf,
                'max_table': 2,
                'max_vars': 2,
                'compatibility_mode': 'only_one_table',
                'min_support': 0.0,
                'filter_redundant': True,
            }
            
            # Exécuter les algorithmes
            start_time = time.time()
            discovered_rules = comparer.run_all_algorithms(settings)
            total_time = time.time() - start_time
            
            # Analyser les résultats
            analysis = comparer.analyze_results()
            
            # Générer un rapport HTML
            html_report = comparer.generate_html_report()
            
            # Collecter les statistiques
            stats = {
                'database': db_name,
                'total_time': total_time,
                'total_rules': sum(len(rules) for rules in discovered_rules.values()),
                'rules_by_algorithm': {algo: len(rules) for algo, rules in discovered_rules.items()},
                'execution_times': comparer.execution_times,
                'errors': comparer.algorithm_errors,
                'html_report': html_report
            }
            
            self.logger.info(f"Comparaison terminée pour {db_name} en {total_time:.2f} secondes")
            return stats
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la comparaison de {db_name}: {e}", exc_info=True)
            self.error_databases[db_name] = str(e)
            return {
                'database': db_name,
                'error': str(e),
                'status': 'failed'
            }
    
    def run_comparisons(self) -> Dict[str, Dict[str, Any]]:
        """
        Exécute les comparaisons sur toutes les bases de données trouvées.
        
        :return: Dictionnaire contenant les résultats de toutes les comparaisons
        """
        databases = self.find_databases()
        if not databases:
            self.logger.warning("Aucune base de données trouvée avec les patterns spécifiés")
            return {}
        
        results = {}
        start_time_global = time.time()
        
        for i, db_file in enumerate(databases):
            self.logger.info(f"[{i+1}/{len(databases)}] Analyse de {db_file.name}")
            try:
                db_results = self.compare_database(db_file)
                results[db_file.name] = db_results
            except Exception as e:
                self.logger.error(f"Échec de l'analyse pour {db_file.name}: {e}", exc_info=True)
                results[db_file.name] = {'status': 'error', 'error': str(e)}
        
        total_time_global = time.time() - start_time_global
        
        # Ajouter le temps total d'exécution
        results['_meta'] = {
            'total_time': total_time_global,
            'databases_count': len(databases),
            'failed_databases': len(self.error_databases),
            'completion_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.all_results = results
        
        # Générer un rapport consolidé
        self._generate_consolidated_reports()
        
        return results
    
    def _generate_consolidated_reports(self):
        """Génère des rapports consolidés pour toutes les comparaisons."""
        if not self.all_results:
            self.logger.warning("Aucun résultat à consolider")
            return
        
        self._generate_csv_report()
        self._generate_html_summary()
        self._generate_performance_charts()
    
    def _generate_csv_report(self):
        """Génère un rapport CSV avec les résultats agrégés."""
        csv_data = []
        
        # Préparer les données pour le CSV
        for db_name, results in self.all_results.items():
            if db_name == '_meta':  # Ignorer les métadonnées
                continue
            
            row = {'database': db_name}
            
            if 'error' in results:
                row['status'] = 'error'
                row['error'] = results['error']
            else:
                row['status'] = 'success'
                row['total_time'] = results.get('total_time', 0)
                row['total_rules'] = results.get('total_rules', 0)
                
                # Ajouter les temps d'exécution par algorithme
                exec_times = results.get('execution_times', {})
                for algo, time_taken in exec_times.items():
                    row[f'{algo}_time'] = time_taken
                
                # Ajouter le nombre de règles par algorithme
                rules_by_algo = results.get('rules_by_algorithm', {})
                for algo, count in rules_by_algo.items():
                    row[f'{algo}_rules'] = count
            
            csv_data.append(row)
        
        # Créer un DataFrame pandas et l'exporter en CSV
        if csv_data:
            df = pd.DataFrame(csv_data)
            csv_path = self.output_dir / 'consolidated_results.csv'
            df.to_csv(csv_path, index=False)
            self.logger.info(f"Rapport CSV généré: {csv_path}")
        else:
            self.logger.warning("Pas de données à exporter en CSV")
    
    def _generate_html_summary(self):
        """Génère un rapport HTML résumant tous les résultats."""
        html_path = self.output_dir / 'batch_comparison_summary.html'
        
        # Extraire les informations nécessaires
        total_dbs = len(self.all_results) - 1  # -1 pour exclure '_meta'
        success_count = sum(1 for db, res in self.all_results.items() 
                          if db != '_meta' and res.get('status') != 'error')
        error_count = len(self.error_databases)
        
        algorithms = set()
        for db, res in self.all_results.items():
            if db != '_meta' and 'rules_by_algorithm' in res:
                algorithms.update(res['rules_by_algorithm'].keys())
        
        # Calculer les moyennes
        avg_times = {algo: [] for algo in algorithms}
        avg_rules = {algo: [] for algo in algorithms}
        
        for db, res in self.all_results.items():
            if db != '_meta' and 'execution_times' in res:
                for algo, time_taken in res['execution_times'].items():
                    if algo in avg_times:
                        avg_times[algo].append(time_taken)
            
            if db != '_meta' and 'rules_by_algorithm' in res:
                for algo, count in res['rules_by_algorithm'].items():
                    if algo in avg_rules:
                        avg_rules[algo].append(count)
        
        # Calculer les moyennes
        avg_time_by_algo = {algo: sum(times)/max(1, len(times)) for algo, times in avg_times.items()}
        avg_rules_by_algo = {algo: sum(counts)/max(1, len(counts)) for algo, counts in avg_rules.items()}
        
        # Générer le HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Rapport de Comparaison par Lots - Algorithmes FD</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                h1, h2, h3 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .good {{ color: green; }}
                .bad {{ color: red; }}
                .warning {{ color: orange; }}
                .section {{ margin-bottom: 30px; padding: 15px; border: 1px solid #eee; border-radius: 5px; }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>Rapport de Comparaison par Lots - Algorithmes de Découverte de Dépendances Fonctionnelles</h1>
            <p>Date: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="section">
                <h2>Résumé</h2>
                <ul>
                    <li><strong>Bases de données analysées:</strong> {total_dbs}</li>
                    <li><strong>Analyses réussies:</strong> {success_count}</li>
                    <li><strong>Analyses échouées:</strong> {error_count}</li>
                    <li><strong>Temps total d'exécution:</strong> {self.all_results.get('_meta', {}).get('total_time', 0):.2f} secondes</li>
                </ul>
            </div>
            
            <div class="section">
                <h2>Performance Moyenne par Algorithme</h2>
                <table>
                    <tr>
                        <th>Algorithme</th>
                        <th>Temps moyen (s)</th>
                        <th>Règles découvertes (moyenne)</th>
                    </tr>
        """
        
        # Ajouter les lignes pour chaque algorithme
        for algo in sorted(algorithms):
            avg_time = avg_time_by_algo.get(algo, 0)
            avg_rule_count = avg_rules_by_algo.get(algo, 0)
            html_content += f"""
                    <tr>
                        <td>{algo}</td>
                        <td>{avg_time:.2f}</td>
                        <td>{avg_rule_count:.1f}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h2>Résultats par Base de Données</h2>
                <table>
                    <tr>
                        <th>Base de données</th>
                        <th>Statut</th>
                        <th>Temps total (s)</th>
                        <th>Total règles</th>
                        <th>Rapport détaillé</th>
                    </tr>
        """
        
        # Ajouter les lignes pour chaque base de données
        for db_name, results in sorted(self.all_results.items()):
            if db_name == '_meta':
                continue
                
            if 'error' in results:
                status = f'<span class="bad">Erreur: {results["error"]}</span>'
                total_time = "N/A"
                total_rules = "N/A"
                report_link = "N/A"
            else:
                status = '<span class="good">Succès</span>'
                total_time = f"{results.get('total_time', 0):.2f}"
                total_rules = results.get('total_rules', 0)
                
                # Créer un lien vers le rapport détaillé s'il existe
                html_report = results.get('html_report')
                if html_report:
                    report_path = Path(html_report)
                    report_link = f'<a href="{report_path.name}" target="_blank">Voir le rapport</a>'
                else:
                    report_link = "Non disponible"
            
            html_content += f"""
                    <tr>
                        <td>{db_name}</td>
                        <td>{status}</td>
                        <td>{total_time}</td>
                        <td>{total_rules}</td>
                        <td>{report_link}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h2>Comparaison des Performances</h2>
                <div style="width: 800px; height: 400px;">
                    <canvas id="performanceChart"></canvas>
                </div>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        const perfCtx = document.getElementById('performanceChart').getContext('2d');
                        const perfChart = new Chart(perfCtx, {
                            type: 'bar',
                            data: {
                                labels: """ + json.dumps(list(avg_time_by_algo.keys())) + """,
                                datasets: [{
                                    label: 'Temps moyen (s)',
                                    data: """ + json.dumps(list(avg_time_by_algo.values())) + """,
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
                                            text: 'Secondes'
                                        }
                                    }
                                }
                            }
                        });
                    });
                </script>
            </div>
            
            <div class="section">
                <h2>Comparaison des Règles Découvertes</h2>
                <div style="width: 800px; height: 400px;">
                    <canvas id="rulesChart"></canvas>
                </div>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        const rulesCtx = document.getElementById('rulesChart').getContext('2d');
                        const rulesChart = new Chart(rulesCtx, {
                            type: 'bar',
                            data: {
                                labels: """ + json.dumps(list(avg_rules_by_algo.keys())) + """,
                                datasets: [{
                                    label: 'Règles découvertes (moyenne)',
                                    data: """ + json.dumps(list(avg_rules_by_algo.values())) + """,
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
                                            text: 'Nombre moyen de règles'
                                        }
                                    }
                                }
                            }
                        });
                    });
                </script>
            </div>
            
            <div class="footer" style="margin-top: 20px; padding-top: 10px; border-top: 1px solid #eee; text-align: center;">
                <p>Rapport généré automatiquement par le comparateur d'algorithmes FD en lot.</p>
            </div>
        </body>
        </html>
        """
        
        # Écrire le contenu dans le fichier HTML
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"Rapport HTML de synthèse généré: {html_path}")
    
    def _generate_performance_charts(self):
        """Génère des graphiques de performance comparant les algorithmes."""
        # Ce code pourrait être étendu pour générer des graphiques plus détaillés
        # avec matplotlib ou d'autres bibliothèques, puis les enregistrer sous forme d'images
        pass
    
    def generate_findings_report(self):
        """
        Génère un rapport textuel d'analyse contenant les conclusions principales 
        et des recommandations basées sur les résultats.
        """
        if not self.all_results:
            self.logger.warning("Aucun résultat à analyser")
            return
        
        report_path = self.output_dir / 'findings_report.md'
        
        # Calculer les statistiques pour chaque algorithme
        algorithms = set()
        for db, res in self.all_results.items():
            if db != '_meta' and 'rules_by_algorithm' in res:
                algorithms.update(res['rules_by_algorithm'].keys())
        
        algo_stats = {}
        for algo in algorithms:
            algo_stats[algo] = {
                'times': [],
                'rule_counts': [],
                'timeouts': 0,
                'errors': 0,
                'success_rate': 0
            }
        
        total_dbs = len(self.all_results) - 1  # -1 pour exclure '_meta'
        
        for db, res in self.all_results.items():
            if db == '_meta':
                continue
                
            if 'execution_times' in res:
                for algo, time_taken in res['execution_times'].items():
                    if algo in algo_stats:
                        algo_stats[algo]['times'].append(time_taken)
                        
                        # Vérifier si c'est un timeout
                        if abs(time_taken - self.timeout) <= 1:  # Marge d'1 seconde pour les timeouts
                            algo_stats[algo]['timeouts'] += 1
            
            if 'rules_by_algorithm' in res:
                for algo, count in res['rules_by_algorithm'].items():
                    if algo in algo_stats:
                        algo_stats[algo]['rule_counts'].append(count)
            
            if 'errors' in res:
                for algo, error in res.get('errors', {}).items():
                    if algo in algo_stats:
                        algo_stats[algo]['errors'] += 1
        
        # Calculer les taux de réussite
        for algo in algo_stats:
            successes = len(algo_stats[algo]['times']) - algo_stats[algo]['timeouts'] - algo_stats[algo]['errors']
            algo_stats[algo]['success_rate'] = (successes / total_dbs) * 100 if total_dbs else 0
        
        # Déterminer le "meilleur" algorithme selon différents critères
        best_time = None
        best_discovery = None
        most_reliable = None
        
        for algo, stats in algo_stats.items():
            avg_time = sum(stats['times']) / max(len(stats['times']), 1)
            avg_rules = sum(stats['rule_counts']) / max(len(stats['rule_counts']), 1)
            
            if not best_time or avg_time < algo_stats[best_time]['avg_time']:
                best_time = algo
                algo_stats[best_time]['avg_time'] = avg_time
            
            if not best_discovery or avg_rules > algo_stats[best_discovery]['avg_rules']:
                best_discovery = algo
                algo_stats[best_discovery]['avg_rules'] = avg_rules
            
            if not most_reliable or stats['success_rate'] > algo_stats[most_reliable]['success_rate']:
                most_reliable = algo
        
        # Générer le rapport Markdown
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Rapport d'Analyse des Algorithmes de Découverte de Dépendances Fonctionnelles\n\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Résumé des Résultats\n\n")
            f.write(f"- **Bases de données analysées:** {total_dbs}\n")
            f.write(f"- **Analyses réussies:** {total_dbs - len(self.error_databases)}\n")
            f.write(f"- **Analyses échouées:** {len(self.error_databases)}\n\n")
            
            f.write("## Performances des Algorithmes\n\n")
            f.write("| Algorithme | Temps moyen (s) | Règles découvertes (moy) | Taux de réussite (%) | Timeouts | Erreurs |\n")
            f.write("|------------|----------------|-------------------------|---------------------|----------|--------|\n")
            
            for algo in sorted(algorithms):
                stats = algo_stats[algo]
                avg_time = sum(stats['times']) / max(len(stats['times']), 1)
                avg_rules = sum(stats['rule_counts']) / max(len(stats['rule_counts']), 1)
                
                f.write(f"| {algo} | {avg_time:.2f} | {avg_rules:.1f} | {stats['success_rate']:.1f} | {stats['timeouts']} | {stats['errors']} |\n")
            
            f.write("\n## Conclusions Principales\n\n")
            
            if best_time:
                f.write(f"- **Algorithme le plus rapide:** {best_time} (temps moyen: {algo_stats[best_time]['avg_time']:.2f}s)\n")
            if best_discovery:
                f.write(f"- **Algorithme découvrant le plus de règles:** {best_discovery} (moyenne: {algo_stats[best_discovery]['avg_rules']:.1f} règles)\n")
            if most_reliable:
                f.write(f"- **Algorithme le plus fiable:** {most_reliable} (taux de réussite: {algo_stats[most_reliable]['success_rate']:.1f}%)\n")
            
            f.write("\n## Recommandations\n\n")
            f.write("Basées sur l'analyse des performances des algorithmes sur l'ensemble des bases de données testées:\n\n")
            
            if best_time:
                f.write(f"1. **Pour les applications nécessitant un traitement rapide:** Privilégiez l'algorithme {best_time}.\n")
            if most_reliable:
                f.write(f"2. **Pour les applications nécessitant une haute fiabilité:** Optez pour l'algorithme {most_reliable}.\n")
            if best_discovery:
                f.write(f"3. **Pour une découverte exhaustive des dépendances:** L'algorithme {best_discovery} offre les meilleurs résultats.\n")
            
            f.write("\n## Limites et Considérations\n\n")
            f.write("- Les performances peuvent varier selon les caractéristiques spécifiques des bases de données.\n")
            f.write("- Un grand nombre de règles découvertes n'est pas nécessairement synonyme d'une meilleure qualité de résultats.\n")
            f.write("- Pour les applications critiques, il est recommandé de tester les algorithmes sur des échantillons représentatifs de vos données.\n")
            
            f.write("\n---\n")
            f.write("*Ce rapport a été généré automatiquement par le comparateur d'algorithmes FD en lot.*\n")
        
        self.logger.info(f"Rapport d'analyse généré: {report_path}")


def main():
    parser = argparse.ArgumentParser(description='Comparer les résultats de différents algorithmes FD sur plusieurs bases de données')
    parser.add_argument('--db-path', default='../../data/metanome_fd/databases/', help='Chemin vers le répertoire des bases de données')
    parser.add_argument('--output', default='batch_results_bench', help='Répertoire de sortie pour les résultats')
    parser.add_argument('--patterns', nargs='+', default=['*.db', '*.sqlite', '*.sqlite3'], 
                       help='Motifs pour trouver les bases de données (ex: "*.db")')
    parser.add_argument('--max-lhs', type=int, default=3, help='Taille maximale du déterminant (partie gauche) pour les FDs')
    parser.add_argument('--min-conf', type=float, default=0.9, help='Confiance minimale pour les règles')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout en secondes pour chaque algorithme (0 = sans limite)')
    parser.add_argument('--parallel', action='store_true', help='Exécuter les algorithmes en parallèle si possible')
    
    args = parser.parse_args()
    
    # Initialiser le comparateur en lot
    batch_comparer = BatchFDComparison(
        db_path=args.db_path,
        output_dir=args.output,
        patterns=args.patterns,
        timeout=args.timeout if args.timeout > 0 else None,
        use_parallel=args.parallel,
        max_lhs=args.max_lhs,
        min_conf=args.min_conf
    )
    
    # Exécuter les comparaisons sur toutes les bases de données
    results = batch_comparer.run_comparisons()
    
    # Générer un rapport d'analyse
    batch_comparer.generate_findings_report()
    
    print(f"\nExécution terminée. Résultats sauvegardés dans: {args.output}")
    print(f"Nombre total de bases de données analysées: {len(results) - 1}")  # -1 pour exclure '_meta'
    
    if batch_comparer.error_databases:
        print(f"\nAttention: {len(batch_comparer.error_databases)} bases de données ont rencontré des erreurs:")
        for db, error in list(batch_comparer.error_databases.items())[:5]:  # Afficher les 5 premières erreurs
            print(f" - {db}: {error}")
        if len(batch_comparer.error_databases) > 5:
            print(f"   (et {len(batch_comparer.error_databases) - 5} autres)")


if __name__ == "__main__":
    main()
