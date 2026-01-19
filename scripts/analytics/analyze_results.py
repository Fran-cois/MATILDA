#!/usr/bin/env python3
"""
Analyse des résultats MATILDA
Génère des statistiques descriptives et comparaisons entre algorithmes

Usage:
    python analyze_results.py --dataset Bupa
    python analyze_results.py --algorithm spider --detailed
    python analyze_results.py --compare spider popper anyburl
    python analyze_results.py --all --visualize
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ajouter le répertoire racine au path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from metrics_constants import *
except ImportError:
    logger.warning("metrics_constants.py non trouvé")


class ResultsAnalyzer:
    """Analyseur de résultats MATILDA"""
    
    def __init__(self, data_dir: Path = None, results_dir: Path = None):
        self.root_dir = ROOT_DIR
        self.data_dir = data_dir or self.root_dir / "data" / "results"
        self.results_dir = results_dir or self.root_dir / "results"
        self.algorithms = ['spider', 'popper', 'anyburl', 'amie3']
    
    def find_results_files(self, algorithm: str = None, dataset: str = None) -> Dict[str, List[Path]]:
        """Trouve les fichiers de résultats"""
        files = defaultdict(list)
        
        if not self.data_dir.exists():
            logger.warning(f"Dossier {self.data_dir} non trouvé")
            return files
        
        for file in self.data_dir.glob("*.json"):
            name = file.name.lower()
            
            # Filtre par dataset
            if dataset and dataset.lower() not in name:
                continue
            
            # Détection algorithme
            for algo in self.algorithms:
                if algo in name:
                    if not algorithm or algorithm == algo:
                        files[algo].append(file)
                    break
        
        return dict(files)
    
    def load_results(self, file_path: Path) -> List[Dict]:
        """Charge les résultats depuis un fichier JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else [data]
        except Exception as e:
            logger.error(f"Erreur lecture {file_path}: {e}")
            return []
    
    def compute_statistics(self, rules: List[Dict]) -> Dict[str, Any]:
        """Calcule les statistiques sur un ensemble de règles"""
        if not rules:
            return {'error': 'Aucune règle'}
        
        stats = {
            'total_rules': len(rules),
            'confidence': {},
            'support': {},
            'head_coverage': {},
            'metrics_summary': {}
        }
        
        # Collecte des métriques
        confidences = [r.get('confidence', 0) for r in rules if r.get('confidence') is not None]
        supports = [r.get('support', 0) for r in rules if r.get('support') is not None]
        coverages = [r.get('head_coverage', 0) for r in rules if r.get('head_coverage') is not None]
        
        # Statistiques confidence
        if confidences:
            stats['confidence'] = {
                'mean': sum(confidences) / len(confidences),
                'min': min(confidences),
                'max': max(confidences),
                'median': sorted(confidences)[len(confidences) // 2],
                'std': self._std(confidences)
            }
        
        # Statistiques support
        if supports:
            stats['support'] = {
                'mean': sum(supports) / len(supports),
                'min': min(supports),
                'max': max(supports),
                'median': sorted(supports)[len(supports) // 2],
                'std': self._std(supports)
            }
        
        # Statistiques head_coverage
        if coverages:
            stats['head_coverage'] = {
                'mean': sum(coverages) / len(coverages),
                'min': min(coverages),
                'max': max(coverages),
                'median': sorted(coverages)[len(coverages) // 2],
                'std': self._std(coverages)
            }
        
        # Comptage par qualité
        if confidences:
            high_conf = len([c for c in confidences if c >= 0.8])
            med_conf = len([c for c in confidences if 0.5 <= c < 0.8])
            low_conf = len([c for c in confidences if c < 0.5])
            
            stats['quality_distribution'] = {
                'high_confidence': high_conf,
                'medium_confidence': med_conf,
                'low_confidence': low_conf,
                'high_confidence_pct': (high_conf / len(confidences)) * 100
            }
        
        return stats
    
    def _std(self, values: List[float]) -> float:
        """Calcule l'écart-type"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def analyze_algorithm(self, algorithm: str, dataset: str = None, detailed: bool = False) -> Dict:
        """Analyse les résultats d'un algorithme"""
        print(f"\n{'='*80}")
        print(f"📊 ANALYSE: {algorithm.upper()}")
        if dataset:
            print(f"   Dataset: {dataset}")
        print(f"{'='*80}\n")
        
        files = self.find_results_files(algorithm, dataset)
        
        if algorithm not in files or not files[algorithm]:
            print(f"❌ Aucun fichier trouvé pour {algorithm}")
            return {'error': 'No files found'}
        
        all_stats = []
        
        for file_path in files[algorithm]:
            print(f"📄 Fichier: {file_path.name}")
            rules = self.load_results(file_path)
            
            if not rules:
                print(f"   ⚠️  Fichier vide ou invalide")
                continue
            
            stats = self.compute_statistics(rules)
            stats['file'] = file_path.name
            all_stats.append(stats)
            
            # Affichage des statistiques
            print(f"   📈 Nombre de règles: {stats['total_rules']}")
            
            if 'confidence' in stats and stats['confidence']:
                conf = stats['confidence']
                print(f"   🎯 Confidence:")
                print(f"      Mean: {conf['mean']:.4f} ± {conf['std']:.4f}")
                print(f"      Range: [{conf['min']:.4f}, {conf['max']:.4f}]")
                print(f"      Median: {conf['median']:.4f}")
            
            if 'support' in stats and stats['support']:
                supp = stats['support']
                print(f"   📊 Support:")
                print(f"      Mean: {supp['mean']:.4f} ± {supp['std']:.4f}")
                print(f"      Range: [{supp['min']:.4f}, {supp['max']:.4f}]")
            
            if 'quality_distribution' in stats:
                qual = stats['quality_distribution']
                print(f"   ✨ Qualité:")
                print(f"      Haute conf (≥0.8): {qual['high_confidence']} ({qual['high_confidence_pct']:.1f}%)")
                print(f"      Moyenne conf [0.5-0.8): {qual['medium_confidence']}")
                print(f"      Basse conf (<0.5): {qual['low_confidence']}")
            
            if detailed:
                self._print_detailed_analysis(rules, stats)
            
            print()
        
        return {'algorithm': algorithm, 'statistics': all_stats}
    
    def _print_detailed_analysis(self, rules: List[Dict], stats: Dict):
        """Affiche une analyse détaillée"""
        print(f"\n   📋 Analyse détaillée:")
        
        # Top 5 règles par confidence
        sorted_rules = sorted(rules, key=lambda r: r.get('confidence', 0), reverse=True)
        print(f"\n   🏆 Top 5 règles (confidence):")
        for i, rule in enumerate(sorted_rules[:5], 1):
            conf = rule.get('confidence', 0)
            supp = rule.get('support', 0)
            rule_str = self._format_rule(rule)
            print(f"      {i}. {rule_str}")
            print(f"         Conf: {conf:.4f}, Supp: {supp:.4f}")
    
    def _format_rule(self, rule: Dict) -> str:
        """Formate une règle pour affichage"""
        if 'rule' in rule:
            return rule['rule']
        elif 'head' in rule and 'body' in rule:
            return f"{rule['body']} => {rule['head']}"
        elif 'type' in rule:
            return f"{rule['type']}: {rule.get('left', '')} ⊆ {rule.get('right', '')}"
        return "Rule"
    
    def compare_algorithms(self, algorithms: List[str], dataset: str = None) -> Dict:
        """Compare plusieurs algorithmes"""
        print(f"\n{'='*80}")
        print(f"🔬 COMPARAISON D'ALGORITHMES")
        if dataset:
            print(f"   Dataset: {dataset}")
        print(f"{'='*80}\n")
        
        comparison = {}
        
        for algo in algorithms:
            files = self.find_results_files(algo, dataset)
            if algo not in files or not files[algo]:
                print(f"⚠️  {algo.upper()}: Aucun résultat")
                continue
            
            all_rules = []
            for file_path in files[algo]:
                rules = self.load_results(file_path)
                all_rules.extend(rules)
            
            if all_rules:
                stats = self.compute_statistics(all_rules)
                comparison[algo] = stats
        
        # Affichage du tableau comparatif
        self._print_comparison_table(comparison)
        
        return comparison
    
    def _print_comparison_table(self, comparison: Dict):
        """Affiche un tableau comparatif"""
        if not comparison:
            print("❌ Aucune donnée à comparer")
            return
        
        print(f"\n📊 Tableau comparatif:\n")
        
        # En-têtes
        algos = sorted(comparison.keys())
        print(f"{'Métrique':<25} | " + " | ".join(f"{a.upper():>12}" for a in algos))
        print("-" * (25 + 3 + (15 * len(algos))))
        
        # Nombre de règles
        print(f"{'Nombre de règles':<25} | " + 
              " | ".join(f"{comparison[a]['total_rules']:>12}" for a in algos))
        
        # Confidence moyenne
        if all('confidence' in comparison[a] for a in algos):
            print(f"{'Confidence (mean)':<25} | " + 
                  " | ".join(f"{comparison[a]['confidence']['mean']:>12.4f}" for a in algos))
            print(f"{'Confidence (std)':<25} | " + 
                  " | ".join(f"{comparison[a]['confidence']['std']:>12.4f}" for a in algos))
        
        # Support moyen
        if all('support' in comparison[a] and comparison[a]['support'] for a in algos):
            print(f"{'Support (mean)':<25} | " + 
                  " | ".join(f"{comparison[a]['support']['mean']:>12.4f}" for a in algos))
        
        # Qualité
        if all('quality_distribution' in comparison[a] for a in algos):
            print(f"{'Haute conf (≥0.8)':<25} | " + 
                  " | ".join(f"{comparison[a]['quality_distribution']['high_confidence']:>12}" for a in algos))
        
        print()
        
        # Verdict
        print("💡 Observations:")
        best_conf = max(algos, key=lambda a: comparison[a].get('confidence', {}).get('mean', 0))
        best_rules = max(algos, key=lambda a: comparison[a]['total_rules'])
        print(f"   • Meilleure confidence: {best_conf.upper()} "
              f"({comparison[best_conf]['confidence']['mean']:.4f})")
        print(f"   • Plus de règles: {best_rules.upper()} "
              f"({comparison[best_rules]['total_rules']} règles)")
    
    def analyze_all(self, dataset: str = None, visualize: bool = False) -> Dict:
        """Analyse tous les algorithmes"""
        print(f"\n{'='*80}")
        print(f"🔍 ANALYSE COMPLÈTE")
        if dataset:
            print(f"   Dataset: {dataset}")
        print(f"{'='*80}\n")
        
        results = {}
        
        for algo in self.algorithms:
            result = self.analyze_algorithm(algo, dataset, detailed=False)
            if 'error' not in result:
                results[algo] = result
        
        # Comparaison globale
        if len(results) > 1:
            comparison = self.compare_algorithms(list(results.keys()), dataset)
            results['comparison'] = comparison
        
        if visualize:
            self._create_visualizations(results)
        
        return results
    
    def _create_visualizations(self, results: Dict):
        """Crée des visualisations (placeholder pour matplotlib)"""
        print("\n📈 Génération de visualisations...")
        print("   ⚠️  Matplotlib non implémenté - Placeholder")
        print("   TODO: Ajouter graphiques de comparaison")


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Analyse des résultats MATILDA",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--dataset', '-d', type=str,
                       help='Dataset à analyser (ex: Bupa)')
    parser.add_argument('--algorithm', '-a', 
                       choices=['spider', 'popper', 'anyburl', 'amie3'],
                       help='Analyser un algorithme spécifique')
    parser.add_argument('--compare', nargs='+', 
                       choices=['spider', 'popper', 'anyburl', 'amie3'],
                       help='Comparer plusieurs algorithmes')
    parser.add_argument('--all', action='store_true',
                       help='Analyser tous les algorithmes')
    parser.add_argument('--detailed', action='store_true',
                       help='Analyse détaillée avec top règles')
    parser.add_argument('--visualize', action='store_true',
                       help='Générer des visualisations')
    parser.add_argument('--output', '-o', type=Path,
                       help='Fichier de sortie pour les résultats')
    
    args = parser.parse_args()
    
    analyzer = ResultsAnalyzer()
    
    # Exécution
    if args.compare:
        results = analyzer.compare_algorithms(args.compare, args.dataset)
    elif args.all:
        results = analyzer.analyze_all(args.dataset, args.visualize)
    elif args.algorithm:
        results = analyzer.analyze_algorithm(args.algorithm, args.dataset, args.detailed)
    else:
        # Par défaut, analyser tout
        results = analyzer.analyze_all(args.dataset, args.visualize)
    
    # Sauvegarde des résultats
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Résultats sauvegardés: {args.output}")
    
    print(f"\n{'='*80}")
    print("✅ Analyse terminée")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
