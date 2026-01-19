#!/usr/bin/env python3
"""
CLI pour calculer Precision et Recall des règles découvertes
Compare avec un ground truth (FK, Inclusion Dependencies, etc.)

Usage:
    python precision_recall.py --ground-truth fk_ground_truth.json --results spider_Bupa_results.json
    python precision_recall.py --dataset Bupa --algorithm spider --auto-generate-gt
    python precision_recall.py --all --interactive
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass, field
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ajouter le répertoire racine au path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))


@dataclass
class PRMetrics:
    """Métriques de Precision/Recall"""
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    matched_rules: List[Tuple[str, str]] = field(default_factory=list)
    missing_rules: List[str] = field(default_factory=list)
    extra_rules: List[str] = field(default_factory=list)


class GroundTruthManager:
    """Gestion du ground truth (FK, IDs, etc.)"""
    
    def __init__(self, gt_file: Path = None):
        self.gt_file = gt_file
        self.ground_truth = []
        
        if gt_file and gt_file.exists():
            self.load_ground_truth(gt_file)
    
    def load_ground_truth(self, gt_file: Path):
        """Charge le ground truth depuis un fichier"""
        try:
            with open(gt_file, 'r', encoding='utf-8') as f:
                self.ground_truth = json.load(f)
            logger.info(f"Ground truth chargé: {len(self.ground_truth)} règles")
        except Exception as e:
            logger.error(f"Erreur chargement ground truth: {e}")
            self.ground_truth = []
    
    def save_ground_truth(self, gt_file: Path):
        """Sauvegarde le ground truth"""
        gt_file.parent.mkdir(parents=True, exist_ok=True)
        with open(gt_file, 'w', encoding='utf-8') as f:
            json.dump(self.ground_truth, f, indent=2, ensure_ascii=False)
        logger.info(f"Ground truth sauvegardé: {gt_file}")
    
    def generate_fk_ground_truth_bupa(self) -> List[Dict]:
        """Génère le ground truth pour Bupa (Foreign Keys connus)"""
        # Exemple pour Bupa - À adapter selon votre schéma
        ground_truth = [
            {
                "type": "ForeignKey",
                "left": ["Member", "policy_id"],
                "right": ["Policy", "policy_id"],
                "description": "Member.policy_id -> Policy.policy_id"
            },
            {
                "type": "InclusionDependency",
                "left": ["Claim", "member_id"],
                "right": ["Member", "member_id"],
                "description": "Claim.member_id ⊆ Member.member_id"
            },
            # Ajoutez d'autres FKs/IDs connus
        ]
        self.ground_truth = ground_truth
        return ground_truth
    
    def create_interactive(self):
        """Mode interactif pour créer le ground truth"""
        print("\n" + "="*80)
        print("🎯 CRÉATION INTERACTIVE DU GROUND TRUTH")
        print("="*80)
        
        while True:
            print("\nOptions:")
            print("  1. Ajouter une Foreign Key")
            print("  2. Ajouter une Inclusion Dependency")
            print("  3. Afficher le ground truth actuel")
            print("  4. Sauvegarder et quitter")
            print("  5. Quitter sans sauvegarder")
            
            choice = input("\nVotre choix (1-5): ").strip()
            
            if choice == '1':
                self._add_fk_interactive()
            elif choice == '2':
                self._add_id_interactive()
            elif choice == '3':
                self._display_ground_truth()
            elif choice == '4':
                output = Path(input("Fichier de sortie: ").strip())
                self.save_ground_truth(output)
                break
            elif choice == '5':
                break
    
    def _add_fk_interactive(self):
        """Ajoute une FK interactivement"""
        print("\n📌 Ajouter Foreign Key")
        left_table = input("  Table source: ").strip()
        left_col = input("  Colonne source: ").strip()
        right_table = input("  Table cible: ").strip()
        right_col = input("  Colonne cible: ").strip()
        
        rule = {
            "type": "ForeignKey",
            "left": [left_table, left_col],
            "right": [right_table, right_col],
            "description": f"{left_table}.{left_col} -> {right_table}.{right_col}"
        }
        
        self.ground_truth.append(rule)
        print("  ✅ FK ajoutée")
    
    def _add_id_interactive(self):
        """Ajoute une ID interactivement"""
        print("\n📌 Ajouter Inclusion Dependency")
        left_table = input("  Table gauche: ").strip()
        left_col = input("  Colonne gauche: ").strip()
        right_table = input("  Table droite: ").strip()
        right_col = input("  Colonne droite: ").strip()
        
        rule = {
            "type": "InclusionDependency",
            "left": [left_table, left_col],
            "right": [right_table, right_col],
            "description": f"{left_table}.{left_col} ⊆ {right_table}.{right_col}"
        }
        
        self.ground_truth.append(rule)
        print("  ✅ ID ajoutée")
    
    def _display_ground_truth(self):
        """Affiche le ground truth actuel"""
        print(f"\n📋 Ground Truth ({len(self.ground_truth)} règles):")
        for i, rule in enumerate(self.ground_truth, 1):
            print(f"  {i}. {rule.get('description', rule)}")


class PrecisionRecallCalculator:
    """Calcule Precision et Recall"""
    
    def __init__(self, ground_truth: List[Dict]):
        self.ground_truth = ground_truth
        self.gt_normalized = self._normalize_ground_truth()
    
    def _normalize_ground_truth(self) -> Set[str]:
        """Normalise le ground truth en ensemble de signatures"""
        normalized = set()
        for rule in self.ground_truth:
            sig = self._rule_to_signature(rule)
            if sig:
                normalized.add(sig)
        return normalized
    
    def _rule_to_signature(self, rule: Dict) -> str:
        """Convertit une règle en signature normalisée"""
        if 'left' in rule and 'right' in rule:
            left = self._normalize_part(rule['left'])
            right = self._normalize_part(rule['right'])
            return f"{left}=>{right}"
        return None
    
    def _normalize_part(self, part) -> str:
        """Normalise une partie de règle"""
        if isinstance(part, list):
            return ".".join(str(p).lower() for p in part)
        return str(part).lower()
    
    def _discovered_rule_to_signature(self, rule: Dict) -> str:
        """Convertit une règle découverte en signature"""
        # Pour Spider (format avec table_dependant/table_referenced)
        if 'table_dependant' in rule and 'table_referenced' in rule:
            left_table = rule.get('table_dependant', '')
            left_cols = rule.get('columns_dependant', [])
            right_table = rule.get('table_referenced', '')
            right_cols = rule.get('columns_referenced', [])
            
            if left_cols and right_cols:
                left_sig = f"{left_table.lower()}.{'.'.join(str(c).lower() for c in left_cols)}"
                right_sig = f"{right_table.lower()}.{'.'.join(str(c).lower() for c in right_cols)}"
                return f"{left_sig}=>{right_sig}"
        
        # Pour Spider (Inclusion Dependencies ancien format)
        if rule.get('type') == 'InclusionDependency':
            left = rule.get('left', [])
            right = rule.get('right', [])
            if left and right:
                left_sig = self._normalize_part(left)
                right_sig = self._normalize_part(right)
                return f"{left_sig}=>{right_sig}"
        
        # Pour d'autres formats
        if 'head' in rule and 'body' in rule:
            # Simplification pour règles TGD
            head = self._normalize_part(rule['head'])
            body = self._normalize_part(rule['body'])
            return f"{body}=>{head}"
        
        return None
    
    def calculate(self, discovered_rules: List[Dict]) -> PRMetrics:
        """Calcule Precision et Recall"""
        metrics = PRMetrics()
        
        # Normaliser les règles découvertes
        discovered_sigs = set()
        for rule in discovered_rules:
            sig = self._discovered_rule_to_signature(rule)
            if sig:
                discovered_sigs.add(sig)
        
        # True Positives: règles découvertes qui sont dans le GT
        tp_sigs = discovered_sigs.intersection(self.gt_normalized)
        metrics.true_positives = len(tp_sigs)
        metrics.matched_rules = [(sig, sig) for sig in tp_sigs]
        
        # False Positives: règles découvertes qui ne sont PAS dans le GT
        fp_sigs = discovered_sigs - self.gt_normalized
        metrics.false_positives = len(fp_sigs)
        metrics.extra_rules = list(fp_sigs)
        
        # False Negatives: règles du GT qui n'ont PAS été découvertes
        fn_sigs = self.gt_normalized - discovered_sigs
        metrics.false_negatives = len(fn_sigs)
        metrics.missing_rules = list(fn_sigs)
        
        # Calcul Precision et Recall
        if metrics.true_positives + metrics.false_positives > 0:
            metrics.precision = metrics.true_positives / (metrics.true_positives + metrics.false_positives)
        
        if metrics.true_positives + metrics.false_negatives > 0:
            metrics.recall = metrics.true_positives / (metrics.true_positives + metrics.false_negatives)
        
        # F1-Score
        if metrics.precision + metrics.recall > 0:
            metrics.f1_score = 2 * (metrics.precision * metrics.recall) / (metrics.precision + metrics.recall)
        
        return metrics


def print_metrics(metrics: PRMetrics, algorithm: str = None):
    """Affiche les métriques P/R"""
    print("\n" + "="*80)
    if algorithm:
        print(f"📊 PRECISION / RECALL - {algorithm.upper()}")
    else:
        print("📊 PRECISION / RECALL")
    print("="*80)
    
    print(f"\n✅ True Positives (TP):  {metrics.true_positives}")
    print(f"❌ False Positives (FP): {metrics.false_positives}")
    print(f"⚠️  False Negatives (FN): {metrics.false_negatives}")
    
    print(f"\n📈 Métriques:")
    print(f"   Precision: {metrics.precision:.4f} ({metrics.precision*100:.2f}%)")
    print(f"   Recall:    {metrics.recall:.4f} ({metrics.recall*100:.2f}%)")
    print(f"   F1-Score:  {metrics.f1_score:.4f}")
    
    if metrics.matched_rules:
        print(f"\n✅ Règles correctement découvertes ({len(metrics.matched_rules)}):")
        for sig, _ in metrics.matched_rules[:5]:
            print(f"   • {sig}")
        if len(metrics.matched_rules) > 5:
            print(f"   ... et {len(metrics.matched_rules) - 5} autres")
    
    if metrics.missing_rules:
        print(f"\n⚠️  Règles manquées ({len(metrics.missing_rules)}):")
        for sig in metrics.missing_rules[:5]:
            print(f"   • {sig}")
        if len(metrics.missing_rules) > 5:
            print(f"   ... et {len(metrics.missing_rules) - 5} autres")
    
    if metrics.extra_rules:
        print(f"\n❌ Règles en trop ({len(metrics.extra_rules)}):")
        for sig in metrics.extra_rules[:5]:
            print(f"   • {sig}")
        if len(metrics.extra_rules) > 5:
            print(f"   ... et {len(metrics.extra_rules) - 5} autres")
    
    print("="*80)


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Calcul de Precision et Recall pour règles découvertes",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--ground-truth', '--gt', type=Path,
                       help='Fichier ground truth (JSON)')
    parser.add_argument('--results', '-r', type=Path,
                       help='Fichier de résultats à évaluer')
    parser.add_argument('--dataset', '-d', type=str,
                       help='Dataset (ex: Bupa)')
    parser.add_argument('--algorithm', '-a',
                       choices=['spider', 'popper', 'anyburl', 'amie3'],
                       help='Algorithme à évaluer')
    parser.add_argument('--auto-generate-gt', action='store_true',
                       help='Générer automatiquement le ground truth pour Bupa')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Mode interactif pour créer ground truth')
    parser.add_argument('--all', action='store_true',
                       help='Évaluer tous les algorithmes')
    parser.add_argument('--output', '-o', type=Path,
                       help='Sauvegarder les résultats')
    
    args = parser.parse_args()
    
    # Gestion du ground truth
    gt_manager = GroundTruthManager(args.ground_truth)
    
    if args.interactive:
        gt_manager.create_interactive()
        return 0
    
    if args.auto_generate_gt:
        print("\n🔧 Génération automatique du ground truth pour Bupa...")
        gt = gt_manager.generate_fk_ground_truth_bupa()
        print(f"✅ {len(gt)} règles générées")
        
        # Sauvegarder
        output = args.output or ROOT_DIR / "data" / "ground_truth_bupa.json"
        gt_manager.save_ground_truth(output)
        return 0
    
    # Vérifier qu'on a un ground truth
    if not gt_manager.ground_truth:
        print("❌ Aucun ground truth disponible")
        print("   Utilisez --ground-truth, --auto-generate-gt, ou --interactive")
        return 1
    
    # Charger les résultats
    if args.results:
        with open(args.results, 'r') as f:
            discovered_rules = json.load(f)
        
        # Calculer P/R
        calculator = PrecisionRecallCalculator(gt_manager.ground_truth)
        metrics = calculator.calculate(discovered_rules)
        
        # Afficher
        algo_name = args.algorithm or args.results.stem
        print_metrics(metrics, algo_name)
    
    elif args.all:
        print("\n🔍 Évaluation de tous les algorithmes...")
        data_dir = ROOT_DIR / "data" / "results"
        
        all_metrics = {}
        for algo in ['spider', 'popper', 'anyburl', 'amie3']:
            files = list(data_dir.glob(f"{algo}*.json"))
            if files:
                with open(files[0], 'r') as f:
                    rules = json.load(f)
                
                calculator = PrecisionRecallCalculator(gt_manager.ground_truth)
                metrics = calculator.calculate(rules)
                all_metrics[algo] = metrics
                
                print_metrics(metrics, algo)
        
        # Tableau comparatif
        if len(all_metrics) > 1:
            print("\n📊 Comparaison Precision/Recall:")
            print(f"\n{'Algorithme':<15} | {'Precision':>10} | {'Recall':>10} | {'F1-Score':>10}")
            print("-" * 55)
            for algo, metrics in all_metrics.items():
                print(f"{algo.upper():<15} | {metrics.precision:>10.4f} | "
                      f"{metrics.recall:>10.4f} | {metrics.f1_score:>10.4f}")
    
    else:
        print("❌ Spécifiez --results, --all, --auto-generate-gt, ou --interactive")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
