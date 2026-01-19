#!/usr/bin/env python3
"""
Script unifié pour calculer les métriques MATILDA sur tous les résultats d'algorithmes.

Ce script détecte automatiquement le type de résultats (Spider, Popper, AnyBURL, etc.) et
applique le calculateur de métriques approprié.

Usage:
    python compute_all_metrics.py                        # Traite tous les résultats trouvés
    python compute_all_metrics.py <results_file>         # Traite un fichier spécifique
    python compute_all_metrics.py --algorithm spider     # Traite seulement Spider
    python compute_all_metrics.py --algorithm popper     # Traite seulement Popper
    python compute_all_metrics.py --algorithm anyburl    # Traite seulement AnyBURL
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importer les calculateurs
try:
    from compute_spider_metrics import SpiderMetricsCalculator, find_spider_results
    SPIDER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Spider metrics calculator not available: {e}")
    SPIDER_AVAILABLE = False

try:
    from compute_popper_metrics import PopperMetricsCalculator, find_popper_results
    POPPER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Popper metrics calculator not available: {e}")
    POPPER_AVAILABLE = False

try:
    from compute_anyburl_metrics import AnyBURLMetricsCalculator, find_anyburl_results
    ANYBURL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AnyBURL metrics calculator not available: {e}")
    ANYBURL_AVAILABLE = False

try:
    from compute_amie3_metrics import AMIE3MetricsCalculator, find_amie3_results
    AMIE3_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AMIE3 metrics calculator not available: {e}")
    AMIE3_AVAILABLE = False


def detect_algorithm(file_path):
    """
    Détecter quel algorithme a généré le fichier de résultats.
    
    Args:
        file_path: Chemin vers le fichier de résultats
        
    Returns:
        str: 'spider', 'popper', 'ilp', 'anyburl', ou None
    """
    file_name = Path(file_path).name.lower()
    
    if 'spider' in file_name:
        return 'spider'
    elif 'popper' in file_name or 'ilp' in file_name:
        return 'popper'
    elif 'anyburl' in file_name:
        return 'anyburl'
    elif 'amie3' in file_name or 'amie' in file_name:
        return 'amie3'
    
    # Essayer de deviner en lisant le fichier
    try:
        import json
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        if isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, dict):
                rule_type = first_item.get('type', '')
                if rule_type == 'InclusionDependency':
                    return 'spider'
                elif rule_type in ['HornRule', 'TGDRule']:
                    return 'anyburl'  # AnyBURL also produces TGDRules
    except Exception as e:
        logger.warning(f"Could not detect algorithm from file content: {e}")
    
    return None


def infer_database_name(file_path, algorithm):
    """
    Inférer le nom de la base de données depuis le nom du fichier.
    
    Args:
        file_path: Chemin vers le fichier de résultats
        algorithm: Type d'algorithme ('spider', 'popper', 'anyburl', 'amie3')
        
    Returns:
        str: Nom de la base de données (sans extension)
    """
    filename = Path(file_path).stem
    
    # Supprimer les suffixes générés (_with_metrics, _results, etc.)
    cleaned = filename.replace('_with_metrics', '').replace('_results', '').replace('_example', '')
    
    if algorithm == 'spider':
        # Format: spider_Bupa ou spider_Bupa_example
        if 'spider_' in cleaned:
            parts = cleaned.split('_')
            if len(parts) >= 2:
                return parts[1]
    
    elif algorithm == 'popper':
        # Format: popper_Bupa ou ilp_Bupa
        if 'popper_' in cleaned or 'ilp_' in cleaned:
            parts = cleaned.split('_')
            if len(parts) >= 2:
                return parts[1]
    
    elif algorithm == 'anyburl':
        # Format: anyburl_Bupa
        if 'anyburl_' in cleaned:
            parts = cleaned.split('_')
            if len(parts) >= 2:
                return parts[1]
    
    elif algorithm == 'amie3':
        # Format: amie3_Bupa
        if 'amie3_' in cleaned:
            parts = cleaned.split('_')
            if len(parts) >= 2:
                db_name = parts[1]
                # Remove .db suffix if present
                if db_name.endswith('.db'):
                    db_name = db_name[:-3]
                return db_name
    
    # Valeur par défaut
    return 'Bupa.db'


def process_spider_file(file_path, database_path="data/db/", output_dir="data/output"):
    """Traiter un fichier de résultats Spider."""
    if not SPIDER_AVAILABLE:
        logger.error("Spider metrics calculator not available!")
        return False
    
    logger.info("=" * 80)
    logger.info(f"Traitement Spider: {file_path}")
    logger.info("=" * 80)
    
    try:
        db_name = infer_database_name(file_path, 'spider')
        calculator = SpiderMetricsCalculator(database_path, db_name, output_dir)
        calculator.process_file(file_path)
        logger.info(f"✓ Spider: {file_path} traité avec succès")
        return True
    except Exception as e:
        logger.error(f"✗ Erreur Spider: {e}", exc_info=True)
        return False


def process_popper_file(file_path, database_path="data/db/", output_dir="data/output"):
    """Traiter un fichier de résultats Popper/ILP."""
    if not POPPER_AVAILABLE:
        logger.error("Popper metrics calculator not available!")
        return False
    
    logger.info("=" * 80)
    logger.info(f"Traitement Popper: {file_path}")
    logger.info("=" * 80)
    
    try:
        db_name = infer_database_name(file_path, 'popper')
        calculator = PopperMetricsCalculator(database_path, db_name, output_dir)
        calculator.process_file(file_path)
        logger.info(f"✓ Popper: {file_path} traité avec succès")
        return True
    except Exception as e:
        logger.error(f"✗ Erreur Popper: {e}", exc_info=True)
        return False


def process_anyburl_file(file_path, database_path="data/db/", output_dir="data/output"):
    """Traiter un fichier de résultats AnyBURL."""
    if not ANYBURL_AVAILABLE:
        logger.error("AnyBURL metrics calculator not available!")
        return False
    
    logger.info("=" * 80)
    logger.info(f"Traitement AnyBURL: {file_path}")
    logger.info("=" * 80)
    
    try:
        db_name = infer_database_name(file_path, 'anyburl')
        calculator = AnyBURLMetricsCalculator(database_path, db_name, output_dir)
        calculator.process_file(file_path)
        logger.info(f"✓ AnyBURL: {file_path} traité avec succès")
        return True
    except Exception as e:
        logger.error(f"✗ Erreur AnyBURL: {e}", exc_info=True)
        return False


def process_amie3_file(file_path, database_path="data/db/", output_dir="data/output"):
    """Traiter un fichier de résultats AMIE3."""
    if not AMIE3_AVAILABLE:
        logger.error("AMIE3 metrics calculator not available!")
        return False
    
    logger.info("=" * 80)
    logger.info(f"Traitement AMIE3: {file_path}")
    logger.info("=" * 80)
    
    try:
        db_name = infer_database_name(file_path, 'amie3')
        calculator = AMIE3MetricsCalculator(database_path, db_name, output_dir)
        calculator.initialize_db_utility(db_name)
        rules = calculator.load_amie3_results(file_path)
        enriched_rules = calculator.calculate_metrics(rules)
        calculator.save_results(enriched_rules, os.path.basename(file_path))
        logger.info(f"✓ AMIE3: {file_path} traité avec succès")
        return True
    except Exception as e:
        logger.error(f"✗ Erreur AMIE3: {e}", exc_info=True)
        return False


def process_file(file_path, algorithm=None):
    """
    Traiter un fichier de résultats en détectant automatiquement l'algorithme.
    
    Args:
        file_path: Chemin vers le fichier à traiter
        algorithm: Type d'algorithme (optionnel, sinon auto-détection)
        
    Returns:
        bool: True si traitement réussi
    """
    if not os.path.exists(file_path):
        logger.error(f"Fichier non trouvé: {file_path}")
        return False
    
    # Détecter l'algorithme si non spécifié
    if algorithm is None:
        algorithm = detect_algorithm(file_path)
        if algorithm is None:
            logger.error(f"Impossible de détecter l'algorithme pour: {file_path}")
            return False
        logger.info(f"Algorithme détecté: {algorithm}")
    
    # Traiter selon l'algorithme
    if algorithm == 'spider':
        return process_spider_file(file_path)
    elif algorithm in ['popper', 'ilp']:
        return process_popper_file(file_path)
    elif algorithm == 'anyburl':
        return process_anyburl_file(file_path)
    elif algorithm == 'amie3':
        return process_amie3_file(file_path)
    else:
        logger.error(f"Algorithme non supporté: {algorithm}")
        return False


def find_all_results(data_dir="data"):
    """
    Trouver tous les fichiers de résultats (Spider, Popper, AnyBURL, AMIE3).
    
    Returns:
        dict: {'spider': [...], 'popper': [...], 'anyburl': [...], 'amie3': [...]}
    """
    results = {
        'spider': [],
        'popper': [],
        'anyburl': [],
        'amie3': []
    }
    
    if SPIDER_AVAILABLE:
        try:
            results['spider'] = find_spider_results(data_dir)
        except Exception as e:
            logger.warning(f"Erreur lors de la recherche Spider: {e}")
    
    if POPPER_AVAILABLE:
        try:
            results['popper'] = find_popper_results(data_dir)
        except Exception as e:
            logger.warning(f"Erreur lors de la recherche Popper: {e}")
    
    if ANYBURL_AVAILABLE:
        try:
            results['anyburl'] = find_anyburl_results(data_dir)
        except Exception as e:
            logger.warning(f"Erreur lors de la recherche AnyBURL: {e}")
    
    if AMIE3_AVAILABLE:
        try:
            results['amie3'] = find_amie3_results(data_dir)
        except Exception as e:
            logger.warning(f"Erreur lors de la recherche AMIE3: {e}")
    
    return results


def generate_database_report(output_dir="data/output"):
    """
    Générer un rapport récapitulatif par database.
    
    Scanne les fichiers de metrics générés et crée un rapport consolidé.
    """
    import json
    from collections import defaultdict
    
    # Structures pour agréger les données
    db_stats = defaultdict(lambda: {
        'spider': {'accuracy': [], 'confidence': [], 'support': [], 'count': 0},
        'popper': {'accuracy': [], 'confidence': [], 'support': [], 'count': 0},
        'anyburl': {'accuracy': [], 'confidence': [], 'support': [], 'count': 0},
        'amie3': {'accuracy': [], 'confidence': [], 'support': [], 'count': 0}
    })
    
    algorithms = ['spider', 'popper', 'anyburl', 'amie3']
    
    # Parcourir les fichiers de metrics
    if not os.path.exists(output_dir):
        return None
    
    for filename in os.listdir(output_dir):
        # Accept both _results_with_metrics_ and _results files, plus _example_results files
        if not filename.endswith('.json'):
            continue
        
        # Check if it's a metrics file, regular results file, or example results file
        is_metrics_file = '_results_with_metrics_' in filename
        is_results_file = filename.endswith('_results.json') or '_results' in filename
        is_example_file = '_example_results' in filename
        
        if not (is_metrics_file or is_results_file or is_example_file):
            continue
        
        filepath = os.path.join(output_dir, filename)
        
        # Déterminer l'algorithme et la database
        algo = None
        db_name = None
        
        for alg in algorithms:
            if filename.startswith(alg):
                algo = alg
                break
        
        if not algo:
            continue
        
        # Extraire le nom de la database
        parts = filename.split('_')
        if len(parts) >= 2:
            db_name = parts[1]
            # Nettoyer les extensions .db multiples
            while db_name.endswith('.db'):
                db_name = db_name[:-3]
            db_name = db_name.strip()
        
        if not db_name:
            continue
        
        # Charger et analyser le fichier
        try:
            with open(filepath, 'r') as f:
                rules = json.load(f)
            
            if not isinstance(rules, list):
                continue
            
            # Collecter les valeurs (accuracy, confidence, support)
            for rule in rules:
                accuracy = rule.get('accuracy', -1)
                confidence = rule.get('confidence', 0)
                support = rule.get('support', 0)
                
                if accuracy >= 0:  # Only collect if accuracy is defined
                    db_stats[db_name][algo]['accuracy'].append(accuracy)
                
                if confidence >= 0:  # Collect confidence always (0 is valid)
                    db_stats[db_name][algo]['confidence'].append(confidence)
                
                if support >= 0:  # Collect support always (0 is valid)
                    db_stats[db_name][algo]['support'].append(support)
            
            # ACCUMULATE the count, don't replace it
            db_stats[db_name][algo]['count'] += len(rules)
            
        except Exception as e:
            logger.debug(f"Erreur lors de la lecture {filepath}: {e}")
    
    # Générer le rapport
    if not db_stats:
        logger.info("Aucune données de metrics trouvées")
        return None
    
    report = "\n" + "=" * 100 + "\n"
    report += "RAPPORT RÉCAPITULATIF PAR DATABASE\n"
    report += "=" * 100 + "\n\n"
    
    for db_name in sorted(db_stats.keys()):
        report += f"## DATABASE: {db_name}\n\n"
        report += "| Algorithme | Règles | Accuracy Moy | Confidence Moy | Support Moy |\n"
        report += "|-----------|--------|--------|---------|----------|\n"
        
        db_data = db_stats[db_name]
        total_rules = sum(d['count'] for d in db_data.values())
        
        # Listes pour moyennes globales
        all_accuracy = []
        all_confidence = []
        all_support = []
        
        for algo in algorithms:
            data = db_data[algo]
            if data['count'] == 0:
                continue
            
            # Calculer les moyennes
            avg_accuracy = sum(data['accuracy']) / len(data['accuracy']) if data['accuracy'] else -1
            avg_confidence = sum(data['confidence']) / len(data['confidence']) if data['confidence'] else 0
            avg_support = sum(data['support']) / len(data['support']) if data['support'] else 0
            
            # Collecter pour la moyenne globale (sauf accuracy pour Spider)
            if avg_accuracy >= 0:
                all_accuracy.append(avg_accuracy)
            all_confidence.append(avg_confidence)
            all_support.append(avg_support)
            
            # Afficher les statistiques
            acc_str = f"{avg_accuracy:.4f}" if avg_accuracy >= 0 else "N/A"
            conf_str = f"{avg_confidence:.4f}"
            supp_str = f"{avg_support:.4f}"
            report += f"| {algo.upper():12} | {data['count']:6} | {acc_str:12} | {conf_str:14} | {supp_str:11} |\n"
        
        if total_rules > 0:
            global_acc = sum(all_accuracy) / len(all_accuracy) if all_accuracy else -1
            global_conf = sum(all_confidence) / len(all_confidence) if all_confidence else 0
            global_supp = sum(all_support) / len(all_support) if all_support else 0
            
            acc_str = f"{global_acc:.4f}" if global_acc >= 0 else "N/A"
            conf_str = f"{global_conf:.4f}"
            supp_str = f"{global_supp:.4f}"
            report += f"|-------------|--------|--------|---------|----------|\n"
            report += f"| **TOTAL**   | {total_rules:6} | {acc_str:12} | {conf_str:14} | {supp_str:11} |\n"
        
        report += "\n"
    
    # Résumé global
    report += "\n" + "=" * 100 + "\n"
    report += "RÉSUMÉ GLOBAL\n"
    report += "=" * 100 + "\n\n"
    
    # Collecter toutes les statistiques globales
    all_rules = 0
    all_accuracy_list = []
    all_confidence_list = []
    all_support_list = []
    
    for db_data in db_stats.values():
        for algo_data in db_data.values():
            all_rules += algo_data['count']
            all_accuracy_list.extend(algo_data['accuracy'])
            all_confidence_list.extend(algo_data['confidence'])
            all_support_list.extend(algo_data['support'])
    
    report += f"Nombre de databases: {len(db_stats)}\n"
    report += f"Nombre total de règles: {all_rules}\n"
    
    if all_accuracy_list:
        avg_acc = sum(all_accuracy_list) / len(all_accuracy_list)
        report += f"Accuracy moyen global: {avg_acc:.4f}\n"
    
    if all_confidence_list:
        avg_conf = sum(all_confidence_list) / len(all_confidence_list)
        report += f"Confidence moyen global: {avg_conf:.4f}\n"
    
    if all_support_list:
        avg_supp = sum(all_support_list) / len(all_support_list)
        report += f"Support moyen global: {avg_supp:.4f}\n"
    
    report += "\n" + "=" * 100 + "\n"
    
    # Afficher et sauvegarder le rapport
    logger.info(report)
    
    # Sauvegarder dans un fichier
    report_path = os.path.join(output_dir, f"RAPPORT_GLOBAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info(f"\nRapport sauvegardé: {report_path}\n")
    
    return report_path


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Calculer les métriques MATILDA sur les résultats d'algorithmes"
    )
    parser.add_argument(
        'file',
        nargs='?',
        help='Fichier de résultats à traiter (optionnel)'
    )
    parser.add_argument(
        '--algorithm',
        choices=['spider', 'popper', 'ilp', 'anyburl', 'amie3', 'all'],
        help='Type d\'algorithme à traiter'
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Répertoire racine des données (défaut: data)'
    )
    
    args = parser.parse_args()
    
    # Mode 1: Fichier spécifique fourni
    if args.file:
        success = process_file(args.file, args.algorithm)
        sys.exit(0 if success else 1)
    
    # Mode 2: Traiter tous les fichiers trouvés
    logger.info("Recherche de fichiers de résultats...")
    all_results = find_all_results(args.data_dir)
    
    # Filtrer selon l'algorithme demandé
    if args.algorithm and args.algorithm != 'all':
        if args.algorithm == 'ilp':
            all_results = {'popper': all_results.get('popper', [])}
        else:
            all_results = {args.algorithm: all_results.get(args.algorithm, [])}
    
    # Compter le total
    total_files = sum(len(files) for files in all_results.values())
    
    if total_files == 0:
        logger.error("Aucun fichier de résultats trouvé!")
        logger.info("\nPour générer des résultats:")
        if SPIDER_AVAILABLE:
            logger.info("  Spider: python src/main.py -c config_spider.yaml")
        if POPPER_AVAILABLE:
            logger.info("  Popper: python src/main.py -c config_popper.yaml")
        sys.exit(1)
    
    logger.info(f"\nTrouvé {total_files} fichier(s) de résultats:")
    for algo, files in all_results.items():
        if files:
            logger.info(f"\n{algo.upper()} ({len(files)} fichiers):")
            for f in files:
                logger.info(f"  - {f}")
    
    # Traiter tous les fichiers
    logger.info("\n" + "=" * 80)
    logger.info("DÉBUT DU TRAITEMENT")
    logger.info("=" * 80 + "\n")
    
    successes = 0
    failures = 0
    
    for algo, files in all_results.items():
        for file_path in files:
            if process_file(file_path, algo):
                successes += 1
            else:
                failures += 1
    
    # Résumé final
    logger.info("\n" + "=" * 80)
    logger.info("RÉSUMÉ FINAL")
    logger.info("=" * 80)
    logger.info(f"✓ Succès: {successes}/{total_files}")
    logger.info(f"✗ Échecs: {failures}/{total_files}")
    logger.info("=" * 80 + "\n")
    
    # Générer le rapport par database si traitement terminé avec succès
    if successes > 0:
        logger.info("\nGénération du rapport par database...")
        generate_database_report('data/output')
    
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
