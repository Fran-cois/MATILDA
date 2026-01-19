#!/usr/bin/env python3
"""
CLI Tool pour la validation des métriques MATILDA
Vérifie la cohérence entre AMIE3, AnyBurl, Spider, et Popper

Usage:
    python validate_metrics.py                  # Mode interactif
    python validate_metrics.py --auto           # Validation automatique
    python validate_metrics.py --check-formulas # Vérifier les formules
    python validate_metrics.py --compare        # Comparer les algorithmes
    python validate_metrics.py --report         # Générer rapport complet
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
import logging
from datetime import datetime

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter le répertoire racine au path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from metrics_constants import *
except ImportError:
    logger.warning("metrics_constants.py non trouvé, utilisation des valeurs par défaut")
    MIN_CONFIDENCE_THRESHOLD = 0.5
    MIN_SUPPORT_THRESHOLD = 0.1


@dataclass
class MetricValidationResult:
    """Résultat de validation d'une métrique"""
    metric_name: str
    algorithm: str
    is_valid: bool
    value: Any
    expected_range: Tuple[float, float] = None
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Rapport complet de validation"""
    timestamp: str
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warnings: int = 0
    results: List[MetricValidationResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class MetricsValidator:
    """Validateur de métriques MATILDA"""
    
    def __init__(self, data_dir: Path = None, results_dir: Path = None):
        self.root_dir = ROOT_DIR
        self.data_dir = data_dir or self.root_dir / "data" / "results"
        self.results_dir = results_dir or self.root_dir / "results"
        self.report = ValidationReport(timestamp=datetime.now().isoformat())
        
    def find_results_files(self) -> Dict[str, List[Path]]:
        """Trouve tous les fichiers de résultats par algorithme"""
        files = {
            'spider': [],
            'popper': [],
            'anyburl': [],
            'amie3': []
        }
        
        # Chercher dans data/results
        if self.data_dir.exists():
            for file in self.data_dir.glob("*.json"):
                name = file.name.lower()
                if 'spider' in name:
                    files['spider'].append(file)
                elif 'popper' in name or 'ilp' in name:
                    files['popper'].append(file)
                elif 'anyburl' in name:
                    files['anyburl'].append(file)
                elif 'amie3' in name or 'amie' in name:
                    files['amie3'].append(file)
        
        # Chercher dans results/
        if self.results_dir.exists():
            for file in self.results_dir.rglob("*.json"):
                if 'with_metrics' in file.name.lower():
                    name = file.name.lower()
                    if 'spider' in name:
                        files['spider'].append(file)
                    elif 'popper' in name:
                        files['popper'].append(file)
                    elif 'anyburl' in name:
                        files['anyburl'].append(file)
                    elif 'amie3' in name:
                        files['amie3'].append(file)
        
        return files
    
    def load_json_file(self, file_path: Path) -> Optional[List[Dict]]:
        """Charge un fichier JSON de résultats"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else [data]
        except Exception as e:
            logger.error(f"Erreur lecture {file_path}: {e}")
            return None
    
    def check_metric_value(self, value: Any, metric_name: str) -> Tuple[bool, List[str]]:
        """Vérifie qu'une valeur métrique est valide"""
        issues = []
        
        # Vérifier None
        if value is None:
            issues.append(f"{metric_name} est None")
            return False, issues
        
        # Vérifier NaN
        if isinstance(value, float):
            import math
            if math.isnan(value):
                issues.append(f"{metric_name} est NaN")
                return False, issues
            if math.isinf(value):
                issues.append(f"{metric_name} est infini")
                return False, issues
        
        # Vérifier les ranges pour métriques connues
        if 'confidence' in metric_name.lower() or 'support' in metric_name.lower():
            if not (0.0 <= value <= 1.0):
                issues.append(f"{metric_name}={value} hors range [0,1]")
                return False, issues
        
        return True, issues
    
    def validate_rule_metrics(self, rule: Dict, algorithm: str) -> List[MetricValidationResult]:
        """Valide les métriques d'une règle"""
        results = []
        
        # Métriques communes
        common_metrics = ['confidence', 'support', 'head_coverage', 'std_confidence']
        
        for metric in common_metrics:
            if metric in rule:
                value = rule[metric]
                is_valid, issues = self.check_metric_value(value, metric)
                
                result = MetricValidationResult(
                    metric_name=metric,
                    algorithm=algorithm,
                    is_valid=is_valid,
                    value=value,
                    issues=issues
                )
                results.append(result)
                self.report.total_checks += 1
                if is_valid:
                    self.report.passed_checks += 1
                else:
                    self.report.failed_checks += 1
        
        # Vérification spécifique par algorithme
        if algorithm == 'spider':
            self._validate_spider_specific(rule, results)
        elif algorithm == 'popper':
            self._validate_popper_specific(rule, results)
        elif algorithm == 'anyburl':
            self._validate_anyburl_specific(rule, results)
        elif algorithm == 'amie3':
            self._validate_amie3_specific(rule, results)
        
        return results
    
    def _validate_spider_specific(self, rule: Dict, results: List):
        """Validation spécifique Spider"""
        if 'type' in rule and rule['type'] != 'InclusionDependency':
            result = MetricValidationResult(
                metric_name='type',
                algorithm='spider',
                is_valid=False,
                value=rule['type'],
                issues=[f"Type attendu: InclusionDependency, trouvé: {rule['type']}"]
            )
            results.append(result)
            self.report.total_checks += 1
            self.report.failed_checks += 1
    
    def _validate_popper_specific(self, rule: Dict, results: List):
        """Validation spécifique Popper"""
        # Popper devrait avoir des clauses
        if 'clauses' not in rule and 'body' not in rule:
            result = MetricValidationResult(
                metric_name='structure',
                algorithm='popper',
                is_valid=False,
                value=None,
                issues=["Règle Popper sans 'clauses' ni 'body'"]
            )
            results.append(result)
            self.report.total_checks += 1
            self.report.failed_checks += 1
    
    def _validate_anyburl_specific(self, rule: Dict, results: List):
        """Validation spécifique AnyBurl"""
        # AnyBurl devrait avoir un pca_confidence
        if 'pca_confidence' in rule:
            value = rule['pca_confidence']
            is_valid, issues = self.check_metric_value(value, 'pca_confidence')
            result = MetricValidationResult(
                metric_name='pca_confidence',
                algorithm='anyburl',
                is_valid=is_valid,
                value=value,
                issues=issues
            )
            results.append(result)
            self.report.total_checks += 1
            if is_valid:
                self.report.passed_checks += 1
            else:
                self.report.failed_checks += 1
    
    def _validate_amie3_specific(self, rule: Dict, results: List):
        """Validation spécifique AMIE3"""
        # AMIE3 devrait avoir des métriques spécifiques
        amie3_metrics = ['pca_confidence', 'positive_examples', 'body_size']
        for metric in amie3_metrics:
            if metric in rule:
                value = rule[metric]
                is_valid, issues = self.check_metric_value(value, metric)
                result = MetricValidationResult(
                    metric_name=metric,
                    algorithm='amie3',
                    is_valid=is_valid,
                    value=value,
                    issues=issues
                )
                results.append(result)
                self.report.total_checks += 1
                if is_valid:
                    self.report.passed_checks += 1
                else:
                    self.report.failed_checks += 1
    
    def validate_all_files(self) -> ValidationReport:
        """Valide tous les fichiers de résultats"""
        files = self.find_results_files()
        
        print("\n" + "="*80)
        print("🔍 VALIDATION DES MÉTRIQUES MATILDA")
        print("="*80)
        
        for algorithm, file_list in files.items():
            if not file_list:
                print(f"\n⚠️  Aucun fichier trouvé pour {algorithm.upper()}")
                continue
            
            print(f"\n📊 Validation {algorithm.upper()} ({len(file_list)} fichiers)")
            print("-" * 80)
            
            for file_path in file_list:
                print(f"\n  Fichier: {file_path.name}")
                data = self.load_json_file(file_path)
                
                if not data:
                    print(f"    ❌ Impossible de charger le fichier")
                    continue
                
                file_results = []
                for rule in data:
                    rule_results = self.validate_rule_metrics(rule, algorithm)
                    file_results.extend(rule_results)
                    self.report.results.extend(rule_results)
                
                # Statistiques du fichier
                failed = [r for r in file_results if not r.is_valid]
                if failed:
                    print(f"    ❌ {len(failed)} échecs sur {len(file_results)} vérifications")
                    for fail in failed[:3]:  # Afficher les 3 premiers
                        print(f"       • {fail.metric_name}: {', '.join(fail.issues)}")
                else:
                    print(f"    ✅ Toutes les vérifications passées ({len(file_results)})")
        
        # Résumé global
        self._generate_summary()
        self._print_summary()
        
        return self.report
    
    def _generate_summary(self):
        """Génère le résumé de validation"""
        self.report.summary = {
            'total_checks': self.report.total_checks,
            'passed': self.report.passed_checks,
            'failed': self.report.failed_checks,
            'success_rate': (self.report.passed_checks / self.report.total_checks * 100) 
                           if self.report.total_checks > 0 else 0,
            'by_algorithm': {}
        }
        
        # Stats par algorithme
        for algo in ['spider', 'popper', 'anyburl', 'amie3']:
            algo_results = [r for r in self.report.results if r.algorithm == algo]
            if algo_results:
                passed = len([r for r in algo_results if r.is_valid])
                total = len(algo_results)
                self.report.summary['by_algorithm'][algo] = {
                    'total': total,
                    'passed': passed,
                    'failed': total - passed,
                    'success_rate': (passed / total * 100) if total > 0 else 0
                }
    
    def _print_summary(self):
        """Affiche le résumé de validation"""
        print("\n" + "="*80)
        print("📈 RÉSUMÉ DE VALIDATION")
        print("="*80)
        
        summary = self.report.summary
        success_rate = summary['success_rate']
        
        print(f"\n  Total vérifications : {summary['total_checks']}")
        print(f"  ✅ Réussies        : {summary['passed']}")
        print(f"  ❌ Échouées        : {summary['failed']}")
        print(f"  📊 Taux de succès  : {success_rate:.1f}%")
        
        # Par algorithme
        print("\n  Par algorithme:")
        for algo, stats in summary['by_algorithm'].items():
            icon = "✅" if stats['success_rate'] >= 95 else "⚠️" if stats['success_rate'] >= 80 else "❌"
            print(f"    {icon} {algo.upper():12} : {stats['passed']:3}/{stats['total']:3} ({stats['success_rate']:.1f}%)")
        
        # Verdict final
        print("\n" + "-"*80)
        if success_rate >= 95:
            print("  ✅ VALIDATION RÉUSSIE - Métriques cohérentes")
        elif success_rate >= 80:
            print("  ⚠️  VALIDATION PARTIELLE - Quelques problèmes détectés")
        else:
            print("  ❌ VALIDATION ÉCHOUÉE - Problèmes majeurs détectés")
        print("="*80 + "\n")
    
    def save_report(self, output_file: Path = None):
        """Sauvegarde le rapport de validation"""
        if output_file is None:
            output_file = self.root_dir / "results" / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convertir en dict sérialisable
        report_dict = {
            'timestamp': self.report.timestamp,
            'summary': self.report.summary,
            'total_checks': self.report.total_checks,
            'passed_checks': self.report.passed_checks,
            'failed_checks': self.report.failed_checks,
            'results': [
                {
                    'metric_name': r.metric_name,
                    'algorithm': r.algorithm,
                    'is_valid': r.is_valid,
                    'value': r.value,
                    'issues': r.issues,
                    'warnings': r.warnings
                }
                for r in self.report.results
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Rapport sauvegardé: {output_file}")
        return output_file


def interactive_mode():
    """Mode interactif pour la validation"""
    print("\n" + "="*80)
    print("🔧 VALIDATEUR DE MÉTRIQUES MATILDA - Mode Interactif")
    print("="*80)
    
    validator = MetricsValidator()
    
    while True:
        print("\nOptions:")
        print("  1. Valider tous les fichiers")
        print("  2. Afficher les fichiers trouvés")
        print("  3. Valider un algorithme spécifique")
        print("  4. Générer rapport complet")
        print("  5. Quitter")
        
        choice = input("\nVotre choix (1-5): ").strip()
        
        if choice == '1':
            validator.validate_all_files()
            save = input("\nSauvegarder le rapport? (o/n): ").strip().lower()
            if save == 'o':
                validator.save_report()
        
        elif choice == '2':
            files = validator.find_results_files()
            for algo, file_list in files.items():
                print(f"\n{algo.upper()}: {len(file_list)} fichiers")
                for f in file_list:
                    print(f"  - {f.name}")
        
        elif choice == '3':
            algo = input("Algorithme (spider/popper/anyburl/amie3): ").strip().lower()
            if algo in ['spider', 'popper', 'anyburl', 'amie3']:
                files = validator.find_results_files()
                if files[algo]:
                    for file_path in files[algo]:
                        data = validator.load_json_file(file_path)
                        if data:
                            for rule in data:
                                results = validator.validate_rule_metrics(rule, algo)
                                validator.report.results.extend(results)
                    validator._generate_summary()
                    validator._print_summary()
                else:
                    print(f"❌ Aucun fichier trouvé pour {algo}")
            else:
                print("❌ Algorithme invalide")
        
        elif choice == '4':
            validator.validate_all_files()
            validator.save_report()
        
        elif choice == '5':
            print("\n👋 Au revoir!")
            break
        
        else:
            print("❌ Choix invalide")


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Validation des métriques MATILDA",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--auto', action='store_true',
                       help='Validation automatique complète')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Mode interactif (défaut)')
    parser.add_argument('--report', '-r', action='store_true',
                       help='Générer rapport et sauvegarder')
    parser.add_argument('--algorithm', '-a', choices=['spider', 'popper', 'anyburl', 'amie3'],
                       help='Valider un algorithme spécifique')
    parser.add_argument('--output', '-o', type=Path,
                       help='Fichier de sortie pour le rapport')
    
    args = parser.parse_args()
    
    validator = MetricsValidator()
    
    # Mode auto ou report
    if args.auto or args.report:
        validator.validate_all_files()
        if args.report or args.output:
            validator.save_report(args.output)
    
    # Mode algorithme spécifique
    elif args.algorithm:
        files = validator.find_results_files()
        if files[args.algorithm]:
            for file_path in files[args.algorithm]:
                data = validator.load_json_file(file_path)
                if data:
                    for rule in data:
                        results = validator.validate_rule_metrics(rule, args.algorithm)
                        validator.report.results.extend(results)
            validator._generate_summary()
            validator._print_summary()
        else:
            print(f"❌ Aucun fichier trouvé pour {args.algorithm}")
    
    # Mode interactif (défaut)
    else:
        interactive_mode()


if __name__ == '__main__':
    main()
