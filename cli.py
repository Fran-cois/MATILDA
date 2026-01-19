#!/usr/bin/env python3
"""
🚀 MATILDA - CLI Principal
Interface en ligne de commande pour toutes les opérations MATILDA

Usage:
    python cli.py <command> [options]
    
Commands:
    validate    Valider la cohérence des métriques
    analyze     Analyser et comparer les résultats
    benchmark   Lancer les benchmarks
    heuristics  Benchmark heuristiques de traversal
    sensitivity Analyse sensibilité paramètre N
    dataset     Gérer datasets large-scale
    stress      Stress test scalabilité
    scalability Tests complets scalabilité (T3.2)
    metrics     Calculer les métriques
    test        Lancer les tests
    clean       Nettoyer le projet
    report      Générer rapports et tableaux
    info        Afficher informations du projet
    
Examples:
    python cli.py validate --auto
    python cli.py analyze --compare spider popper
    python cli.py dataset generate --tuples 1000000
    python cli.py stress --quick
    python cli.py heuristics --quick
    python cli.py sensitivity --quick
    python cli.py benchmark --algorithm spider
    python cli.py metrics --all
    python cli.py test --coverage
    python cli.py report --latex
"""

import sys
import argparse
from pathlib import Path
import subprocess
import os

# Configuration des chemins
ROOT_DIR = Path(__file__).parent.absolute()
SCRIPTS_DIR = ROOT_DIR / "scripts"
TESTS_DIR = ROOT_DIR / "tests"
DOCS_DIR = ROOT_DIR / "docs"

# Couleurs pour le terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(text):
    """Affiche un en-tête stylisé"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}🚀 {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_success(text):
    """Affiche un message de succès"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    """Affiche un message d'erreur"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    """Affiche un avertissement"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    """Affiche une information"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

def run_python_script(script_path, args=None):
    """Exécute un script Python avec des arguments"""
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, cwd=ROOT_DIR, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print_error(f"Erreur lors de l'exécution: {e}")
        return False
    except FileNotFoundError:
        print_error(f"Script non trouvé: {script_path}")
        return False

def run_shell_script(script_path, args=None):
    """Exécute un script shell"""
    cmd = [str(script_path)]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, cwd=ROOT_DIR, shell=True, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print_error(f"Erreur lors de l'exécution: {e}")
        return False

# ============================================================================
# COMMANDE: validate
# ============================================================================

def cmd_validate(args):
    """Valider la cohérence des métriques"""
    print_header("VALIDATION DES MÉTRIQUES")
    
    script = SCRIPTS_DIR / "utils" / "validate_metrics.py"
    
    script_args = []
    if args.auto:
        script_args.append('--auto')
    elif args.interactive:
        script_args.append('--interactive')
    elif args.report:
        script_args.append('--report')
    
    if args.algorithm:
        script_args.extend(['--algorithm', args.algorithm])
    
    if args.output:
        script_args.extend(['--output', args.output])
    
    if run_python_script(script, script_args):
        print_success("Validation terminée")
        return 0
    else:
        print_error("Validation échouée")
        return 1

# ============================================================================
# COMMANDE: benchmark
# ============================================================================

def cmd_benchmark(args):
    """Lancer les benchmarks"""
    print_header("BENCHMARK MATILDA")
    
    if args.full:
        script = ROOT_DIR / "run_complete_benchmark.sh"
        print_info("Lancement du benchmark complet...")
        if run_shell_script(script):
            print_success("Benchmark complet terminé")
            return 0
        else:
            print_error("Benchmark complet échoué")
            return 1
    
    elif args.algorithm:
        algo = args.algorithm.lower()
        script_map = {
            'spider': SCRIPTS_DIR / "benchmarks" / "run_spider_with_metrics.py",
            'bupa': SCRIPTS_DIR / "benchmarks" / "run_bupa_experiments.py",
            'all': SCRIPTS_DIR / "benchmarks" / "run_full_benchmark.py"
        }
        
        if algo in script_map:
            print_info(f"Lancement benchmark {algo.upper()}...")
            if run_python_script(script_map[algo]):
                print_success(f"Benchmark {algo.upper()} terminé")
                return 0
        else:
            print_error(f"Algorithme inconnu: {algo}")
            print_info("Algorithmes disponibles: spider, bupa, all")
            return 1
    
    else:
        # Benchmark par défaut
        script = SCRIPTS_DIR / "benchmarks" / "run_benchmark.py"
        if run_python_script(script):
            print_success("Benchmark terminé")
            return 0
        else:
            print_error("Benchmark échoué")
            return 1

# ============================================================================
# COMMANDE: heuristics
# ============================================================================

def cmd_heuristics(args):
    """Benchmark des heuristiques de traversal"""
    print_header("BENCHMARK HEURISTIQUES")
    
    script = SCRIPTS_DIR / "benchmarks" / "benchmark_traversal.py"
    
    if args.quick:
        # Quick benchmark with limited rules
        print_info("Benchmark rapide (20 règles max, 60s timeout)...")
        script_args = [
            args.database,
            '--max-rules', '20',
            '--timeout', '60'
        ]
    elif args.algorithm:
        # Single algorithm benchmark
        print_info(f"Benchmark {args.algorithm.upper()}" + 
                  (f" avec heuristique {args.heuristic}" if args.heuristic else ""))
        script_args = [
            args.database,
            '--algorithm', args.algorithm
        ]
        if args.heuristic:
            script_args.extend(['--heuristic', args.heuristic])
        if args.max_rules:
            script_args.extend(['--max-rules', str(args.max_rules)])
        if args.timeout:
            script_args.extend(['--timeout', str(args.timeout)])
    else:
        # Full benchmark suite
        print_info("Benchmark complet de tous les algorithmes...")
        script_args = [args.database]
        if args.max_rules:
            script_args.extend(['--max-rules', str(args.max_rules)])
        if args.timeout:
            script_args.extend(['--timeout', str(args.timeout)])
    
    if args.output_dir:
        script_args.extend(['--output-dir', args.output_dir])
    
    if run_python_script(script, script_args):
        print_success("Benchmark heuristiques terminé")
        return 0
    else:
        print_error("Benchmark heuristiques échoué")
        return 1

# ============================================================================
# COMMANDE: sensitivity
# ============================================================================

def cmd_sensitivity(args):
    """Analyse de sensibilité du paramètre N"""
    print_header("SENSITIVITY ANALYSIS - Paramètre N")
    
    script = SCRIPTS_DIR / "benchmarks" / "sensitivity_analysis_N.py"
    
    script_args = [args.database]
    
    if args.quick:
        print_info("Analyse rapide (N=1,2,3, timeout 120s)...")
        script_args.append('--quick')
    else:
        if args.n_min:
            script_args.extend(['--n-min', str(args.n_min)])
        if args.n_max:
            script_args.extend(['--n-max', str(args.n_max)])
        if args.algorithms:
            script_args.extend(['--algorithms'] + args.algorithms)
        if args.heuristic:
            script_args.extend(['--heuristic', args.heuristic])
        if args.timeout:
            script_args.extend(['--timeout', str(args.timeout)])
    
    if args.output_dir:
        script_args.extend(['--output-dir', args.output_dir])
    
    if run_python_script(script, script_args):
        print_success("Analyse de sensibilité terminée")
        
        # Offer to generate visualizations
        if args.visualize:
            print_info("Génération des visualisations...")
            viz_script = SCRIPTS_DIR / "utils" / "visualize_sensitivity.py"
            # Find the latest result file
            import glob
            output_dir = args.output_dir if args.output_dir else 'results/sensitivity_analysis'
            result_files = glob.glob(f"{output_dir}/sensitivity_N_*.json")
            if result_files:
                latest_result = max(result_files, key=lambda x: x)
                viz_args = [latest_result]
                if args.output_dir:
                    viz_args.extend(['--output-dir', args.output_dir])
                if run_python_script(viz_script, viz_args):
                    print_success("Visualisations générées")
        
        return 0
    else:
        print_error("Analyse de sensibilité échouée")
        return 1

# ============================================================================
# COMMANDE: dataset
# ============================================================================

def cmd_dataset(args):
    """Gérer les datasets large-scale"""
    print_header("GESTION DATASETS LARGE-SCALE")
    
    if args.action == 'generate':
        # Generate dataset
        script = SCRIPTS_DIR / "utils" / "generate_large_dataset.py"
        
        if not args.output:
            # Auto-generate output path
            size_label = f"{args.tuples // 1000000}M" if args.tuples >= 1000000 else f"{args.tuples // 1000}K"
            output_path = ROOT_DIR / f"data/large_scale/dataset_{size_label}.db"
        else:
            output_path = args.output
        
        print_info(f"Génération dataset: {args.tuples:,} tuples...")
        print_info(f"Output: {output_path}")
        
        script_args = [str(output_path)]
        
        if args.tuples:
            script_args.extend(['--tuples', str(args.tuples)])
        if args.tables:
            script_args.extend(['--tables', str(args.tables)])
        if args.columns:
            script_args.extend(['--columns', str(args.columns)])
        if args.no_relationships:
            script_args.append('--no-relationships')
        if args.seed:
            script_args.extend(['--seed', str(args.seed)])
        
        if run_python_script(script, script_args):
            print_success("Dataset généré avec succès")
            return 0
        else:
            print_error("Génération du dataset échouée")
            return 1
    
    elif args.action == 'stats':
        # Show statistics
        script = SCRIPTS_DIR / "utils" / "generate_large_dataset.py"
        
        if not args.database:
            print_error("Spécifiez un fichier de base de données avec --database")
            return 1
        
        print_info(f"Statistiques: {args.database}")
        script_args = [args.database, '--stats-only']
        
        if run_python_script(script, script_args):
            return 0
        else:
            print_error("Échec de récupération des statistiques")
            return 1
    
    elif args.action == 'list':
        # List available datasets
        print_info("Datasets disponibles:")
        large_scale_dir = ROOT_DIR / "data" / "large_scale"
        
        if not large_scale_dir.exists():
            print_warning("Aucun dataset trouvé dans data/large_scale/")
            print_info("Générez-en un avec: python cli.py dataset generate")
            return 0
        
        datasets = list(large_scale_dir.glob("*.db"))
        
        if not datasets:
            print_warning("Aucun dataset trouvé")
            return 0
        
        import os
        print(f"\n{'Fichier':<30} {'Taille':<15} {'Tables':<10}")
        print("-" * 55)
        
        for dataset in sorted(datasets):
            size_mb = os.path.getsize(dataset) / (1024 * 1024)
            
            # Quick count tables
            try:
                import sqlite3
                conn = sqlite3.connect(dataset)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                num_tables = cursor.fetchone()[0]
                conn.close()
            except:
                num_tables = "?"
            
            print(f"{dataset.name:<30} {size_mb:>10.2f} MB   {num_tables:<10}")
        
        print()
        return 0
    
    else:
        print_error("Action inconnue. Utilisez: generate, stats, ou list")
        return 1

# ============================================================================
# COMMANDE: stress
# ============================================================================

def cmd_stress(args):
    """Stress test de scalabilité"""
    print_header("STRESS TEST SCALABILITÉ")
    
    script = SCRIPTS_DIR / "benchmarks" / "stress_test.py"
    
    if args.quick:
        # Quick test with small dataset
        print_info("Test rapide avec dataset 1M...")
        dataset_path = ROOT_DIR / "data/large_scale/dataset_1M.db"
        
        # Check if dataset exists
        if not dataset_path.exists():
            print_warning(f"Dataset non trouvé: {dataset_path}")
            print_info("Génération du dataset 1M...")
            
            gen_script = SCRIPTS_DIR / "utils" / "generate_large_dataset.py"
            gen_args = [str(dataset_path), '--tuples', '1000000']
            
            if not run_python_script(gen_script, gen_args):
                print_error("Échec de génération du dataset")
                return 1
        
        script_args = [str(dataset_path)]
    else:
        # Custom test
        if not args.database:
            print_error("Spécifiez un fichier de base de données")
            return 1
        
        script_args = [args.database]
    
    # Add options
    if args.output:
        script_args.extend(['--output', args.output])
    if args.algorithm:
        script_args.extend(['--algorithm', args.algorithm])
    if args.heuristic:
        script_args.extend(['--heuristic', args.heuristic])
    if args.max_table:
        script_args.extend(['--max-table', str(args.max_table)])
    if args.max_vars:
        script_args.extend(['--max-vars', str(args.max_vars)])
    if args.timeout:
        script_args.extend(['--timeout', str(args.timeout)])
    if args.compare_all:
        script_args.append('--compare-all')
    if args.baselines:
        script_args.extend(['--baselines'] + args.baselines)
    
    if run_python_script(script, script_args):
        print_success("Stress test terminé")
        return 0
    else:
        print_error("Stress test échoué")
        return 1

# ============================================================================
# COMMANDE: 
# ============================================================================
# COMMANDE: scalability
# ============================================================================

def cmd_scalability(args):
    """Tests complets de scalabilité (T3.2)"""
    print_header("SCALABILITY TESTS (T3.2)")
    
    script = SCRIPTS_DIR / "benchmarks" / "run_scalability_tests.py"
    
    script_args = []
    
    if args.output:
        script_args.extend(['--output', args.output])
    
    if args.skip_generation:
        script_args.append('--skip-generation')
    
    if args.full:
        print_info("Lancement de la suite complète de tests de scalabilité...")
        print_info("Cela va:")
        print_info("  1. Générer les datasets (1M, 5M, 10M tuples)")
        print_info("  2. Exécuter les stress tests avec config optimale")
        print_info("  3. Agréger les résultats")
        print_info("  4. Générer les visualisations")
        print_info("\nCeci peut prendre plusieurs heures...")
    
    if run_python_script(script, script_args):
        print_success("Tests de scalabilité terminés")
        
        # Offer to show results
        output_dir = args.output if args.output else 'results/scalability'
        summary_file = ROOT_DIR / output_dir / 'scalability_summary.json'
        
        if summary_file.exists():
            print_info(f"\nRésultats disponibles:")
            print_info(f"  - JSON: {summary_file}")
            print_info(f"  - Graphiques: {output_dir}/*.png")
        
        return 0
    else:
        print_error("Tests de scalabilité échoués")
        return 1

# ============================================================================
# COMMANDE: metrics
# ============================================================================

def cmd_metrics(args):
    """Calculer les métriques"""
    print_header("CALCUL DES MÉTRIQUES")
    
    if args.all:
        script = SCRIPTS_DIR / "metrics" / "compute_all_metrics.py"
        print_info("Calcul de toutes les métriques...")
        if run_python_script(script):
            print_success("Métriques calculées")
            return 0
        else:
            print_error("Calcul des métriques échoué")
            return 1
    
    elif args.algorithm:
        algo = args.algorithm.lower()
        script_map = {
            'spider': SCRIPTS_DIR / "metrics" / "compute_spider_metrics.py",
            'popper': SCRIPTS_DIR / "metrics" / "compute_popper_metrics.py",
            'anyburl': SCRIPTS_DIR / "metrics" / "compute_anyburl_metrics.py",
            'amie3': SCRIPTS_DIR / "metrics" / "compute_amie3_metrics.py",
            'coverage': SCRIPTS_DIR / "metrics" / "compute_coverage_metrics.py"
        }
        
        if algo in script_map:
            print_info(f"Calcul métriques {algo.upper()}...")
            if run_python_script(script_map[algo]):
                print_success(f"Métriques {algo.upper()} calculées")
                return 0
        else:
            print_error(f"Algorithme inconnu: {algo}")
            print_info("Algorithmes disponibles: spider, popper, anyburl, amie3, coverage")
            return 1
    
    elif args.compare:
        script = SCRIPTS_DIR / "metrics" / "compare_matilda_benchmark.py"
        print_info("Comparaison des métriques...")
        if run_python_script(script):
            print_success("Comparaison terminée")
            return 0
    
    else:
        print_error("Spécifiez --all, --algorithm <algo>, ou --compare")
        return 1

# ============================================================================
# COMMANDE: test
# ============================================================================

def cmd_test(args):
    """Lancer les tests"""
    print_header("TESTS MATILDA")
    
    if args.all:
        print_info("Lancement de tous les tests...")
        cmd = [sys.executable, "-m", "pytest", str(TESTS_DIR), "-v"]
        if args.coverage:
            cmd.extend(["--cov=src", "--cov-report=html"])
        result = subprocess.run(cmd, cwd=ROOT_DIR)
        return result.returncode
    
    elif args.unit:
        print_info("Lancement des tests unitaires...")
        cmd = [sys.executable, "-m", "pytest", str(ROOT_DIR / "src" / "tests"), "-v"]
        result = subprocess.run(cmd, cwd=ROOT_DIR)
        return result.returncode
    
    elif args.validation:
        script = TESTS_DIR / "test_metrics_validation.py"
        print_info("Tests de validation des métriques...")
        if run_python_script(script):
            print_success("Tests de validation passés")
            return 0
        else:
            print_error("Tests de validation échoués")
            return 1
    
    elif args.file:
        print_info(f"Lancement du test: {args.file}")
        test_file = TESTS_DIR / args.file
        if not test_file.exists():
            test_file = ROOT_DIR / args.file
        
        if test_file.exists():
            if run_python_script(test_file):
                print_success(f"Test {args.file} passé")
                return 0
            else:
                print_error(f"Test {args.file} échoué")
                return 1
        else:
            print_error(f"Fichier de test non trouvé: {args.file}")
            return 1
    
    else:
        print_error("Spécifiez --all, --unit, --validation, ou --file <fichier>")
        return 1

# ============================================================================
# COMMANDE: clean
# ============================================================================

def cmd_clean(args):
    """Nettoyer le projet"""
    print_header("NETTOYAGE DU PROJET")
    
    import shutil
    
    cleaned = []
    
    if args.cache or args.all:
        print_info("Suppression des caches Python...")
        for pycache in ROOT_DIR.rglob("__pycache__"):
            shutil.rmtree(pycache, ignore_errors=True)
            cleaned.append(str(pycache))
        
        for pyc in ROOT_DIR.rglob("*.pyc"):
            pyc.unlink(missing_ok=True)
            cleaned.append(str(pyc))
        
        print_success(f"{len(cleaned)} fichiers de cache supprimés")
    
    if args.logs or args.all:
        print_info("Nettoyage des logs...")
        logs_dir = ROOT_DIR / "logs"
        if logs_dir.exists():
            count = len(list(logs_dir.glob("*.log")))
            if args.force:
                for log_file in logs_dir.glob("*.log"):
                    log_file.unlink()
                print_success(f"{count} fichiers log supprimés")
            else:
                print_warning(f"{count} fichiers log trouvés (utilisez --force pour supprimer)")
    
    if args.results or args.all:
        print_warning("Nettoyage des résultats nécessite --force")
        if args.force:
            results_dir = ROOT_DIR / "results"
            if results_dir.exists():
                count = len(list(results_dir.rglob("*.json")))
                for result_file in results_dir.rglob("*.json"):
                    if "validation_report" not in result_file.name:  # Garder les rapports
                        result_file.unlink()
                print_success(f"{count} fichiers de résultats supprimés")
    
    if args.build or args.all:
        print_info("Suppression des artefacts de build...")
        for build_dir in ROOT_DIR.rglob("build"):
            if build_dir.is_dir():
                shutil.rmtree(build_dir, ignore_errors=True)
                cleaned.append(str(build_dir))
        
        for dist_dir in ROOT_DIR.rglob("dist"):
            if dist_dir.is_dir():
                shutil.rmtree(dist_dir, ignore_errors=True)
                cleaned.append(str(dist_dir))
        
        for egg_dir in ROOT_DIR.rglob("*.egg-info"):
            if egg_dir.is_dir():
                shutil.rmtree(egg_dir, ignore_errors=True)
                cleaned.append(str(egg_dir))
    
    if not any([args.cache, args.logs, args.results, args.build, args.all]):
        print_warning("Aucune option de nettoyage spécifiée")
        print_info("Options: --cache, --logs, --results, --build, --all")
        return 1
    
    print_success("Nettoyage terminé")
    return 0

# ============================================================================
# COMMANDE: report
# ============================================================================

def cmd_report(args):
    """Générer rapports et tableaux"""
    print_header("GÉNÉRATION DE RAPPORTS")
    
    if args.latex:
        script = SCRIPTS_DIR / "utils" / "generate_latex_table.py"
        print_info("Génération des tableaux LaTeX...")
        if run_python_script(script):
            print_success("Tableaux LaTeX générés")
            return 0
        else:
            print_error("Génération LaTeX échouée")
            return 1
    
    elif args.statistics:
        script = SCRIPTS_DIR / "utils" / "generate_statistics_report.py"
        print_info("Génération du rapport statistique...")
        if run_python_script(script):
            print_success("Rapport statistique généré")
            return 0
        else:
            print_error("Génération du rapport échouée")
            return 1
    
    elif args.validation:
        script = SCRIPTS_DIR / "utils" / "validate_metrics.py"
        print_info("Génération du rapport de validation...")
        if run_python_script(script, ['--report']):
            print_success("Rapport de validation généré")
            return 0
        else:
            print_error("Génération du rapport échouée")
            return 1
    
    elif args.all:
        print_info("Génération de tous les rapports...")
        success = True
        
        # LaTeX
        script = SCRIPTS_DIR / "utils" / "generate_latex_table.py"
        if not run_python_script(script):
            success = False
        
        # Statistics
        script = SCRIPTS_DIR / "utils" / "generate_statistics_report.py"
        if not run_python_script(script):
            success = False
        
        # Validation
        script = SCRIPTS_DIR / "utils" / "validate_metrics.py"
        if not run_python_script(script, ['--report']):
            success = False
        
        if success:
            print_success("Tous les rapports générés")
            return 0
        else:
            print_error("Certains rapports ont échoué")
            return 1
    
    else:
        print_error("Spécifiez --latex, --statistics, --validation, ou --all")
        return 1

# ============================================================================
# COMMANDE: analyze
# ============================================================================

def cmd_analyze(args):
    """Analyser les résultats"""
    print_header("ANALYSE DES RÉSULTATS")
    
    script = SCRIPTS_DIR / "analytics" / "analyze_results.py"
    
    if not script.exists():
        print_error(f"Script d'analyse non trouvé: {script}")
        return 1
    
    script_args = []
    
    if args.dataset:
        script_args.extend(['--dataset', args.dataset])
    
    if args.algorithm:
        script_args.extend(['--algorithm', args.algorithm])
    
    if args.compare:
        script_args.append('--compare')
        script_args.extend(args.compare)
    
    if args.all:
        script_args.append('--all')
    
    if args.detailed:
        script_args.append('--detailed')
    
    if args.visualize:
        script_args.append('--visualize')
    
    if args.output:
        script_args.extend(['--output', args.output])
    
    if run_python_script(script, script_args):
        print_success("Analyse terminée")
        return 0
    else:
        print_error("Analyse échouée")
        return 1

# ============================================================================
# COMMANDE: info
# ============================================================================

def cmd_info(args):
    """Afficher informations du projet"""
    print_header("INFORMATIONS MATILDA")
    
    print(f"{Colors.BOLD}Projet:{Colors.END} MATILDA")
    print(f"{Colors.BOLD}Racine:{Colors.END} {ROOT_DIR}")
    print()
    
    # Structure
    print(f"{Colors.BOLD}📁 Structure:{Colors.END}")
    dirs = {
        'Scripts': SCRIPTS_DIR,
        'Tests': TESTS_DIR,
        'Documentation': DOCS_DIR,
        'Source': ROOT_DIR / "src",
        'Données': ROOT_DIR / "data",
        'Résultats': ROOT_DIR / "results",
        'Logs': ROOT_DIR / "logs"
    }
    
    for name, path in dirs.items():
        exists = "✅" if path.exists() else "❌"
        if path.exists():
            if path.is_dir():
                count = len(list(path.iterdir()))
                print(f"  {exists} {name:15} : {path.name:20} ({count} items)")
            else:
                print(f"  {exists} {name:15} : {path.name}")
        else:
            print(f"  {exists} {name:15} : {path.name} (non trouvé)")
    
    print()
    
    # Scripts disponibles
    parser_dataset.add_argument('--output', '-o',
                               help='Chemin du fichier de sortie (pour generate)')
    parser_dataset.add_argument('--database', '-d',
                               help='Chemin de la base de données (pour stats)')
    parser_dataset.add_argument('--tuples', '-t', type=int, default=1000000,
                               help='Nombre de tuples (défaut: 1M)')
    parser_dataset.add_argument('--tables', '-T', type=int, default=5,
                               help='Nombre de tables (défaut: 5)')
    parser_dataset.add_argument('--columns', '-c', type=int, default=5,
                               help='Colonnes par table (défaut: 5)')
    parser_dataset.add_argument('--no-relationships', action='store_true',
                               help='Désactiver les foreign keys')
    parser_dataset.add_argument('--seed', type=int, default=42,
                               help='Seed aléatoire (défaut: 42)')
    parser_dataset.set_defaults(func=cmd_dataset)
    
    # ========== stress ==========
    parser_stress = subparsers.add_parser('stress',
                                         help='Stress test scalabilité')
    parser_stress.add_argument('--database', '-d',
                              help='Chemin de la base de données')
    parser_stress.add_argument('--quick', action='store_true',
                              help='Test rapide avec dataset 1M (auto-généré si besoin)')
    parser_stress.add_argument('--output', '-o', default='results/stress_test',
                              help='Dossier de sortie (défaut: results/stress_test)')
    parser_stress.add_argument('--algorithm', default='astar',
                              choices=['dfs', 'bfs', 'astar'],
                              help='Algorithme MATILDA (défaut: astar)')
    parser_stress.add_argument('--heuristic', default='hybrid',
                              choices=['naive', 'table_size', 'join_selectivity', 'hybrid'],
                              help='Heuristique A-star (défaut: hybrid)')
    parser_stress.add_argument('--max-table', '-N', type=int, default=3,
                              help='Paramètre N max (défaut: 3)')
    parser_stress.add_argument('--max-vars', type=int, default=6,
                              help='Variables max (défaut: 6)')
    parser_stress.add_argument('--timeout', type=int,
                              help='Timeout en secondes')
    parser_stress.add_argument('--compare-all', action='store_true',
                              help='Comparer toutes les configurations')
    parser_stress.add_argument('--baselines', nargs='+',
                              choices=['amie3', 'anyburl', 'popper', 'spider'],
                              help='Baselines à comparer')
    parser_stress.set_defaults(func=cmd_stress)
    
    # ========== (f"  {exists} {name:15} : {path.name} (non trouvé)")
    
    print()
    
    # Scripts disponibles
    if args.scripts:
        print(f"{Colors.BOLD}📜 Scripts disponibles:{Colors.END}")
        
        if (SCRIPTS_DIR / "benchmarks").exists():
            print(f"\n  {Colors.CYAN}Benchmarks:{Colors.END}")
            for script in sorted((SCRIPTS_DIR / "benchmarks").glob("*.py")):
                print(f"    • {script.name}")
        
        if (SCRIPTS_DIR / "metrics").exists():
            print(f"\n  {Colors.CYAN}Métriques:{Colors.END}")
            for script in sorted((SCRIPTS_DIR / "metrics").glob("*.py")):
                print(f"    • {script.name}")
        
        if (SCRIPTS_DIR / "utils").exists():
            print(f"\n  {Colors.CYAN}Utilitaires:{Colors.END}")
            for script in sorted((SCRIPTS_DIR / "utils").glob("*.py")):
                print(f"    • {script.name}")
    
    # Fichiers de résultats
    if args.results:
        print(f"\n{Colors.BOLD}📊 Résultats:{Colors.END}")
        results_dir = ROOT_DIR / "data" / "results"
        if results_dir.exists():
            for algo in ['spider', 'popper', 'anyburl', 'amie3']:
                files = list(results_dir.glob(f"{algo}*.json"))
                if files:
                    print(f"  {algo.upper():10} : {len(files)} fichiers")
        
        results_dir = ROOT_DIR / "results"
        if results_dir.exists():
            json_files = list(results_dir.rglob("*.json"))
            print(f"  Rapports    : {len(json_files)} fichiers")
    
    # Documentation
    if args.docs:
        print(f"\n{Colors.BOLD}📚 Documentation:{Colors.END}")
        if DOCS_DIR.exists():
            md_files = list(DOCS_DIR.glob("*.md"))
            print(f"  {len(md_files)} fichiers Markdown")
            if args.verbose:
                for doc in sorted(md_files)[:10]:
                    print(f"    • {doc.name}")
                if len(md_files) > 10:
                    print(f"    ... et {len(md_files) - 10} autres")
    
    print()
    print_success("Informations affichées")
    return 0

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="🚀 MATILDA CLI - Interface de commande principale",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s validate --auto
  %(prog)s benchmark --algorithm spider
  %(prog)s metrics --all
  %(prog)s test --all --coverage
  %(prog)s clean --cache --logs
  %(prog)s report --latex
  %(prog)s info --scripts --results

Pour plus d'aide sur une commande:
  %(prog)s <command> --help
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commande à exécuter')
    
    # ========== validate ==========
    parser_validate = subparsers.add_parser('validate', help='Valider les métriques')
    parser_validate.add_argument('--auto', action='store_true', help='Validation automatique')
    parser_validate.add_argument('--interactive', '-i', action='store_true', help='Mode interactif')
    parser_validate.add_argument('--report', '-r', action='store_true', help='Générer rapport')
    parser_validate.add_argument('--algorithm', '-a', choices=['spider', 'popper', 'anyburl', 'amie3'],
                                help='Valider un algorithme spécifique')
    parser_validate.add_argument('--output', '-o', help='Fichier de sortie')
    parser_validate.set_defaults(func=cmd_validate)
    
    # ========== analyze ==========
    parser_analyze = subparsers.add_parser('analyze', help='Analyser les résultats')
    parser_analyze.add_argument('--dataset', '-d', type=str,
                               help='Dataset à analyser (ex: Bupa)')
    parser_analyze.add_argument('--algorithm', '-a',
                               choices=['spider', 'popper', 'anyburl', 'amie3'],
                               help='Analyser un algorithme spécifique')
    parser_analyze.add_argument('--compare', nargs='+',
                               choices=['spider', 'popper', 'anyburl', 'amie3'],
                               help='Comparer plusieurs algorithmes')
    parser_analyze.add_argument('--all', action='store_true',
                               help='Analyser tous les algorithmes')
    parser_analyze.add_argument('--detailed', action='store_true',
                               help='Analyse détaillée avec top règles')
    parser_analyze.add_argument('--visualize', action='store_true',
                               help='Générer des visualisations')
    parser_analyze.add_argument('--output', '-o',
                               help='Fichier de sortie pour les résultats')
    parser_analyze.set_defaults(func=cmd_analyze)
    
    # ========== benchmark ==========
    parser_benchmark = subparsers.add_parser('benchmark', help='Lancer les benchmarks')
    parser_benchmark.add_argument('--full', action='store_true', help='Benchmark complet')
    parser_benchmark.add_argument('--algorithm', '-a', choices=['spider', 'bupa', 'all'],
                                 help='Algorithme à benchmarker')
    parser_benchmark.set_defaults(func=cmd_benchmark)
    
    # ========== heuristics ==========
    parser_heuristics = subparsers.add_parser('heuristics', 
                                             help='Benchmark heuristiques de traversal')
    parser_heuristics.add_argument('database', nargs='?', 
                                  default='data/db/BupaImperfect.db',
                                  help='Chemin vers la base de données (défaut: data/db/BupaImperfect.db)')
    parser_heuristics.add_argument('--quick', action='store_true',
                                  help='Benchmark rapide (20 règles, 60s)')
    parser_heuristics.add_argument('--algorithm', choices=['dfs', 'bfs', 'astar'],
                                  help='Benchmarker un seul algorithme')
    parser_heuristics.add_argument('--heuristic', 
                                  choices=['naive', 'table_size', 'join_selectivity', 'hybrid'],
                                  help='Heuristique pour A-star')
    parser_heuristics.add_argument('--max-rules', type=int, default=50,
                                  help='Nombre max de règles (défaut: 50)')
    parser_heuristics.add_argument('--timeout', type=int, default=300,
                                  help='Timeout en secondes (défaut: 300)')
    parser_heuristics.add_argument('--output-dir', 
                                  default='results/benchmarks',
                                  help='Dossier de sortie (défaut: results/benchmarks)')
    parser_heuristics.set_defaults(func=cmd_heuristics)
    
    # ========== sensitivity ==========
    parser_sensitivity = subparsers.add_parser('sensitivity',
                                              help='Analyse sensibilité paramètre N')
    parser_sensitivity.add_argument('database', nargs='?',
                                   default='data/db/BupaImperfect.db',
                                   help='Chemin vers la base de données (défaut: data/db/BupaImperfect.db)')
    parser_sensitivity.add_argument('--quick', action='store_true',
                                   help='Analyse rapide (N=1,2,3, 120s timeout)')
    parser_sensitivity.add_argument('--n-min', type=int,
                                   help='Valeur minimum de N (défaut: 1)')
    parser_sensitivity.add_argument('--n-max', type=int,
                                   help='Valeur maximum de N (défaut: 5)')
    parser_sensitivity.add_argument('--algorithms', nargs='+',
                                   choices=['dfs', 'bfs', 'astar'],
                                   help='Algorithmes à tester (défaut: dfs astar)')
    parser_sensitivity.add_argument('--heuristic',
                                   choices=['naive', 'table_size', 'join_selectivity', 'hybrid'],
                                   help='Heuristique pour A-star (défaut: hybrid)')
    parser_sensitivity.add_argument('--timeout', type=int,
                                   help='Timeout par run en secondes (défaut: 600)')
    parser_sensitivity.add_argument('--output-dir',
                                   help='Dossier de sortie (défaut: results/sensitivity_analysis)')
    parser_sensitivity.add_argument('--visualize', action='store_true',
                                   help='Générer les visualisations automatiquement')
    parser_sensitivity.set_defaults(func=cmd_sensitivity)
    
    # ========== dataset ==========
    parser_dataset = subparsers.add_parser('dataset',
                                          help='Gérer datasets large-scale')
    parser_dataset.add_argument('action', choices=['generate', 'stats', 'list'],
                               help='Action à effectuer')
    parser_dataset.add_argument('--output', '-o',
                               help='Chemin du fichier de sortie (pour generate)')
    parser_dataset.add_argument('--database', '-d',
                               help='Chemin de la base de données (pour stats)')
    parser_dataset.add_argument('--tuples', '-t', type=int, default=1000000,
                               help='Nombre de tuples (défaut: 1M)')
    parser_dataset.add_argument('--tables', '-T', type=int, default=5,
                               help='Nombre de tables (défaut: 5)')
    parser_dataset.add_argument('--columns', '-c', type=int, default=5,
                               help='Colonnes par table (défaut: 5)')
    parser_dataset.add_argument('--no-relationships', action='store_true',
                               help='Désactiver les foreign keys')
    parser_dataset.add_argument('--seed', type=int, default=42,
                               help='Seed aléatoire (défaut: 42)')
    parser_dataset.set_defaults(func=cmd_dataset)
    
    # ========== scalability ==========
    parser_scalability = subparsers.add_parser('scalability',
                                               help='Tests complets scalabilité (T3.2)')
    parser_scalability.add_argument('--full', action='store_true',
                                   help='Lancer la suite complète (génération + tests + viz)')
    parser_scalability.add_argument('--output', '-o', default='results/scalability',
                                   help='Dossier de sortie (défaut: results/scalability)')
    parser_scalability.add_argument('--skip-generation', action='store_true',
                                   help='Ne pas générer les datasets (s\'ils existent déjà)')
    parser_scalability.set_defaults(func=cmd_scalability)
    
    # ========== stress ==========
    parser_stress = subparsers.add_parser('stress',
                                         help='Stress test scalabilité')
    parser_stress.add_argument('--database', '-d',
                              help='Chemin de la base de données')
    parser_stress.add_argument('--quick', action='store_true',
                              help='Test rapide avec dataset 1M (auto-généré si besoin)')
    parser_stress.add_argument('--output', '-o', default='results/stress_test',
                              help='Dossier de sortie (défaut: results/stress_test)')
    parser_stress.add_argument('--algorithm', default='astar',
                              choices=['dfs', 'bfs', 'astar'],
                              help='Algorithme MATILDA (défaut: astar)')
    parser_stress.add_argument('--heuristic', default='hybrid',
                              choices=['naive', 'table_size', 'join_selectivity', 'hybrid'],
                              help='Heuristique A-star (défaut: hybrid)')
    parser_stress.add_argument('--max-table', '-N', type=int, default=3,
                              help='Paramètre N max (défaut: 3)')
    parser_stress.add_argument('--max-vars', type=int, default=6,
                              help='Variables max (défaut: 6)')
    parser_stress.add_argument('--timeout', type=int,
                              help='Timeout en secondes')
    parser_stress.add_argument('--compare-all', action='store_true',
                              help='Comparer toutes les configurations')
    parser_stress.add_argument('--baselines', nargs='+',
                              choices=['amie3', 'anyburl', 'popper', 'spider'],
                              help='Baselines à comparer')
    parser_stress.set_defaults(func=cmd_stress)
    
    # ========== metrics ==========
    parser_metrics = subparsers.add_parser('metrics', help='Calculer les métriques')
    parser_metrics.add_argument('--all', action='store_true', help='Toutes les métriques')
    parser_metrics.add_argument('--algorithm', '-a', 
                               choices=['spider', 'popper', 'anyburl', 'amie3', 'coverage'],
                               help='Métriques pour un algorithme')
    parser_metrics.add_argument('--compare', action='store_true', help='Comparer les métriques')
    parser_metrics.set_defaults(func=cmd_metrics)
    
    # ========== test ==========
    parser_test = subparsers.add_parser('test', help='Lancer les tests')
    parser_test.add_argument('--all', action='store_true', help='Tous les tests')
    parser_test.add_argument('--unit', action='store_true', help='Tests unitaires')
    parser_test.add_argument('--validation', action='store_true', help='Tests de validation')
    parser_test.add_argument('--file', help='Fichier de test spécifique')
    parser_test.add_argument('--coverage', action='store_true', help='Avec couverture de code')
    parser_test.set_defaults(func=cmd_test)
    
    # ========== clean ==========
    parser_clean = subparsers.add_parser('clean', help='Nettoyer le projet')
    parser_clean.add_argument('--all', action='store_true', help='Tout nettoyer')
    parser_clean.add_argument('--cache', action='store_true', help='Caches Python')
    parser_clean.add_argument('--logs', action='store_true', help='Fichiers log')
    parser_clean.add_argument('--results', action='store_true', help='Résultats')
    parser_clean.add_argument('--build', action='store_true', help='Artefacts de build')
    parser_clean.add_argument('--force', action='store_true', help='Forcer la suppression')
    parser_clean.set_defaults(func=cmd_clean)
    
    # ========== report ==========
    parser_report = subparsers.add_parser('report', help='Générer rapports')
    parser_report.add_argument('--all', action='store_true', help='Tous les rapports')
    parser_report.add_argument('--latex', action='store_true', help='Tableaux LaTeX')
    parser_report.add_argument('--statistics', action='store_true', help='Rapport statistique')
    parser_report.add_argument('--validation', action='store_true', help='Rapport de validation')
    parser_report.set_defaults(func=cmd_report)
    
    # ========== info ==========
    parser_info = subparsers.add_parser('info', help='Informations projet')
    parser_info.add_argument('--scripts', action='store_true', help='Lister les scripts')
    parser_info.add_argument('--results', action='store_true', help='Lister les résultats')
    parser_info.add_argument('--docs', action='store_true', help='Lister la documentation')
    parser_info.add_argument('--verbose', '-v', action='store_true', help='Mode verbeux')
    parser_info.set_defaults(func=cmd_info)
    
    # Parser les arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        print(f"\n{Colors.YELLOW}💡 Utilisez 'python cli.py <command> --help' pour plus d'informations{Colors.END}")
        return 0
    
    # Exécuter la commande
    try:
        return args.func(args)
    except Exception as e:
        print_error(f"Erreur: {e}")
        if '--verbose' in sys.argv or '-v' in sys.argv:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
