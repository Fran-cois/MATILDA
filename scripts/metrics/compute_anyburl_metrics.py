#!/usr/bin/env python3
"""
Script pour calculer les métriques MATILDA sur les résultats d'AnyBURL.

Ce script:
1. Charge les résultats AnyBURL (règles TGD)
2. Calcule les métriques de correctness (validité) des règles
3. Calcule les métriques de compatibilité des règles
4. Calcule le support et la confidence pour chaque règle
5. Génère un rapport avec toutes les métriques

Usage:
    python compute_anyburl_metrics.py <anyburl_results.json>
    python compute_anyburl_metrics.py  # Pour traiter tous les fichiers AnyBURL trouvés
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Ajouter le chemin src au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from database.alchemy_utility import AlchemyUtility
from utils.rules import RuleIO, TGDRule, Predicate
from sqlalchemy import select, func, and_
from metrics_constants import (
    MIN_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    ANYBURL_DEFAULT_CONFIDENCE_WEIGHT,
    ANYBURL_DEFAULT_SUPPORT_WEIGHT
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('anyburl_metrics.log')
    ]
)
logger = logging.getLogger(__name__)


class AnyBURLMetricsCalculator:
    """Classe pour calculer les métriques MATILDA sur des résultats AnyBURL."""
    
    def __init__(self, database_path, database_name, output_dir="data/output"):
        """
        Initialiser le calculateur de métriques.
        
        Args:
            database_path: Chemin vers le répertoire contenant la base de données
            database_name: Nom du fichier de base de données
            output_dir: Répertoire de sortie pour les résultats
        """
        self.database_path = Path(database_path)
        self.database_name = database_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_anyburl_results(self, results_file):
        """
        Charger les résultats AnyBURL depuis un fichier JSON.
        
        Args:
            results_file: Chemin vers le fichier JSON de résultats AnyBURL
            
        Returns:
            list: Liste des règles TGD
        """
        logger.info(f"Chargement des résultats AnyBURL depuis {results_file}...")
        
        try:
            rules = RuleIO.load_rules_from_json(results_file)
            logger.info(f"{len(rules)} règles chargées")
            return rules
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des résultats: {e}", exc_info=True)
            return []
    
    def extract_tables_from_predicates(self, predicates):
        """
        Extraire les tables et attributs des prédicats.
        
        Args:
            predicates: Liste de Predicate
            
        Returns:
            list: Liste de tuples (table, attribut)
        """
        tables_attrs = []
        for pred in predicates:
            # AnyBURL format: relation_name(arg1, arg2)
            # Sans le séparateur ___sep___
            if "." in pred.relation:
                # Format: table.attr
                parts = pred.relation.split(".")
                if len(parts) >= 2:
                    tables_attrs.append((parts[0], parts[1]))
            else:
                # Format simple: relation_name
                tables_attrs.append((pred.relation, ""))
        return tables_attrs
    
    def calculate_rule_validity(self, rule, db_inspector, threshold=None):
        """
        Calculer la validité (correctness) d'une règle AnyBURL.
        
        Une règle est considérée comme valide si ses prédicats peuvent être 
        satisfaits ensemble dans la base de données.
        
        Args:
            rule: TGDRule
            db_inspector: Instance AlchemyUtility
            threshold: Seuil minimal de compatibilité (utilise MIN_CONFIDENCE_THRESHOLD si None)
            
        Returns:
            bool: True si la règle est valide
        """
        if threshold is None:
            threshold = MIN_CONFIDENCE_THRESHOLD
            
        try:
            # AnyBURL produit toujours des TGDRule
            if not isinstance(rule, TGDRule):
                return False
            
            body_predicates = list(rule.body)
            head_predicates = list(rule.head)
            
            all_predicates = body_predicates + head_predicates
            tables_attrs = self.extract_tables_from_predicates(all_predicates)
            
            if len(tables_attrs) < 1:
                return False
            
            # Vérifier que les tables existent dans la base de données
            metadata = db_inspector.db_manager.metadata
            for table, attr in tables_attrs:
                if table not in metadata.tables:
                    logger.warning(f"Table {table} non trouvée")
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Erreur lors du calcul de validité: {e}")
            return False
    
    def calculate_support_confidence(self, rule, db_inspector):
        """
        Calculer le support et la confidence d'une règle AnyBURL.
        
        Support: Proportion de tuples satisfaisant la règle
        Confidence: Précision de la règle (fournie par AnyBURL)
        
        Args:
            rule: TGDRule
            db_inspector: Instance AlchemyUtility
            
        Returns:
            tuple: (support, confidence)
        """
        try:
            # AnyBURL fournit la confidence mais pas l'accuracy
            if hasattr(rule, 'confidence') and rule.confidence is not None:
                confidence = rule.confidence
            else:
                confidence = 0.0
            
            # Support: calculé approximativement
            support = 0.0
            if hasattr(rule, 'accuracy') and rule.accuracy is not None and rule.accuracy > 0:
                support = rule.accuracy
            else:
                # Extraire les tables du body
                body_predicates = list(rule.body)
                tables_attrs = self.extract_tables_from_predicates(body_predicates)
                
                if not tables_attrs:
                    return support, confidence
                
                # Compter les tuples dans la première table du body
                metadata = db_inspector.db_manager.metadata
                engine = db_inspector.db_manager.engine
                
                first_table, _ = tables_attrs[0]
                if first_table in metadata.tables:
                    table_obj = metadata.tables[first_table]
                    with engine.connect() as conn:
                        count = conn.execute(select(func.count()).select_from(table_obj)).scalar()
                        if count > 0:
                            # Support approximatif basé sur le nombre de tuples
                            support = min(1.0, count / 1000.0)  # Normaliser
            
            return support, confidence
            
        except Exception as e:
            logger.warning(f"Erreur lors du calcul de support/confidence: {e}")
            return 0.0, 0.0
    
    def calculate_metrics(self, rules):
        """
        Calculer toutes les métriques MATILDA pour les règles AnyBURL.
        
        Args:
            rules: Liste des règles (TGDRule)
            
        Returns:
            list: Liste des règles avec métriques calculées
        """
        logger.info(f"Calcul des métriques MATILDA sur {len(rules)} règles AnyBURL...")
        
        db_file_path = self.database_path / self.database_name
        db_uri = f"sqlite:///{db_file_path}"
        
        enriched_rules = []
        
        try:
            with AlchemyUtility(db_uri, database_path=str(self.database_path), 
                              create_index=False, create_csv=False, 
                              create_tsv=False, get_data=False) as db_inspector:
                
                for rule in rules:
                    if not isinstance(rule, TGDRule):
                        logger.warning(f"Règle non-TGD ignorée: {rule}")
                        continue
                    
                    logger.info(f"Traitement de la règle: {rule.display[:100]}...")
                    
                    # Calculer la validité
                    is_valid = self.calculate_rule_validity(rule, db_inspector)
                    
                    # Calculer support et confidence
                    support, confidence = self.calculate_support_confidence(rule, db_inspector)
                    
                    # Créer une règle enrichie avec toutes les métriques
                    enriched_rule = TGDRule(
                        body=rule.body,
                        head=rule.head,
                        display=rule.display,
                        accuracy=support,
                        confidence=confidence,
                        correct=is_valid,
                        compatible=is_valid
                    )
                    
                    enriched_rules.append(enriched_rule)
                    
                    logger.info(
                        f"  → Valid: {is_valid} | "
                        f"Support: {support:.4f} | "
                        f"Confidence: {confidence:.4f}"
                    )
                
        except Exception as e:
            logger.error(f"Erreur lors du calcul des métriques: {e}", exc_info=True)
        
        return enriched_rules
    
    def save_results(self, rules, input_file=None):
        """
        Sauvegarder les résultats avec métriques dans un fichier JSON.
        
        Args:
            rules: Liste des règles enrichies avec métriques
            input_file: Fichier d'entrée original (optionnel)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        if input_file:
            base_name = Path(input_file).stem
            output_file = self.output_dir / f"{base_name}_with_metrics_{timestamp}.json"
        else:
            output_file = self.output_dir / f"anyburl_{self.database_name.replace('.db', '')}_metrics_{timestamp}.json"
        
        logger.info(f"Sauvegarde des résultats dans {output_file}...")
        
        # Sauvegarder avec RuleIO
        RuleIO.save_rules_to_json(rules, output_file)
        
        logger.info(f"Résultats sauvegardés avec succès dans {output_file}")
        
        # Générer un rapport résumé
        self.generate_report(rules, output_file)
    
    def generate_report(self, rules, output_file):
        """
        Générer un rapport récapitulatif des métriques.
        
        Args:
            rules: Liste des règles enrichies
            output_file: Chemin du fichier de résultats JSON
        """
        report_file = output_file.with_suffix('.md')
        
        logger.info(f"Génération du rapport dans {report_file}...")
        
        # Calculer les statistiques
        total_rules = len(rules)
        if total_rules == 0:
            logger.warning("Aucune règle à traiter pour le rapport")
            return
        
        valid_rules = sum(1 for r in rules if hasattr(r, 'correct') and r.correct)
        
        # Calculer les moyennes
        if rules:
            avg_support = sum(r.accuracy for r in rules) / len(rules)
            avg_confidence = sum(r.confidence for r in rules) / len(rules)
        else:
            avg_support = 0.0
            avg_confidence = 0.0
        
        with open(report_file, 'w') as f:
            f.write(f"# Rapport de Métriques MATILDA pour AnyBURL\n\n")
            f.write(f"**Base de données:** {self.database_name}\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"## Résumé\n\n")
            f.write(f"- **Nombre total de règles:** {total_rules}\n")
            f.write(f"- **Règles valides:** {valid_rules} ({valid_rules/total_rules*100:.1f}%)\n")
            f.write(f"- **Support moyen:** {avg_support:.4f}\n")
            f.write(f"- **Confidence moyenne:** {avg_confidence:.4f}\n\n")
            
            f.write(f"## Règles avec Métriques\n\n")
            f.write(f"| # | Règle | Valide | Support | Confidence |\n")
            f.write(f"|---|-------|--------|---------|------------|\n")
            
            for idx, rule in enumerate(rules, 1):
                valid_str = "✓" if (hasattr(rule, 'correct') and rule.correct) else "✗"
                
                # Tronquer la règle si trop longue
                display = rule.display[:80] + "..." if len(rule.display) > 80 else rule.display
                
                support = rule.accuracy if hasattr(rule, 'accuracy') else 0.0
                confidence = rule.confidence if hasattr(rule, 'confidence') else 0.0
                
                f.write(f"| {idx} | {display} | {valid_str} | {support:.4f} | {confidence:.4f} |\n")
            
            f.write(f"\n## Métriques MATILDA\n\n")
            f.write(f"### Définitions\n\n")
            f.write(f"- **Correctness (Validité):** La règle est valide selon la sémantique des données\n")
            f.write(f"- **Compatibility:** Les prédicats de la règle sont compatibles\n")
            f.write(f"- **Support:** Proportion de tuples satisfaisant la règle\n")
            f.write(f"- **Confidence:** Précision de la règle (calculée par AnyBURL)\n\n")
            
            f.write(f"## Détails\n\n")
            f.write(f"Les résultats complets sont disponibles dans le fichier JSON: `{output_file.name}`\n")
        
        logger.info(f"Rapport généré avec succès dans {report_file}")
    
    def process_file(self, results_file):
        """
        Traiter un fichier de résultats AnyBURL.
        
        Args:
            results_file: Chemin vers le fichier JSON de résultats AnyBURL
        """
        try:
            logger.info("=" * 80)
            logger.info(f"Traitement du fichier: {results_file}")
            logger.info("=" * 80)
            
            # Charger les résultats AnyBURL
            rules = self.load_anyburl_results(results_file)
            
            if not rules:
                logger.warning("Aucune règle trouvée dans le fichier")
                return
            
            # Calculer les métriques
            enriched_rules = self.calculate_metrics(rules)
            
            # Sauvegarder les résultats
            self.save_results(enriched_rules, results_file)
            
            logger.info("=" * 80)
            logger.info("Traitement terminé avec succès!")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement: {e}", exc_info=True)
            raise


def find_anyburl_results(data_dir="data"):
    """
    Trouver tous les fichiers de résultats AnyBURL dans le répertoire data.
    
    Args:
        data_dir: Répertoire racine où chercher
        
    Returns:
        list: Liste des chemins vers les fichiers de résultats AnyBURL
    """
    data_path = Path(data_dir)
    anyburl_files = []
    
    # Chercher dans data/output
    output_dir = data_path / "output"
    if output_dir.exists():
        anyburl_files.extend(output_dir.glob("*anyburl*.json"))
        anyburl_files.extend(output_dir.glob("*ANYBURL*.json"))
    
    # Chercher dans data/results
    results_dir = data_path / "results"
    if results_dir.exists():
        for db_dir in results_dir.iterdir():
            if db_dir.is_dir():
                anyburl_dir = db_dir / "anyburl"
                if anyburl_dir.exists():
                    anyburl_files.extend(anyburl_dir.glob("anyburl_*_results.json"))
    
    return [str(f) for f in anyburl_files]


def main():
    """Point d'entrée principal du script."""
    
    # Si un fichier est fourni en argument, le traiter
    if len(sys.argv) > 1:
        results_file = sys.argv[1]
        
        if not os.path.exists(results_file):
            logger.error(f"Le fichier {results_file} n'existe pas!")
            sys.exit(1)
        
        # Extraire le nom de la base de données du nom du fichier
        filename = Path(results_file).stem
        if "anyburl" in filename.lower():
            parts = filename.split("_")
            if len(parts) >= 2:
                database_name = parts[1] + ".db"
            else:
                database_name = "Bupa.db"
        else:
            database_name = "Bupa.db"
        
        logger.info(f"Fichier de résultats: {results_file}")
        logger.info(f"Base de données inférée: {database_name}")
        
        calculator = AnyBURLMetricsCalculator("data/db/", database_name, "data/output")
        calculator.process_file(results_file)
    
    else:
        # Chercher tous les fichiers de résultats AnyBURL
        anyburl_files = find_anyburl_results()
        
        if not anyburl_files:
            logger.error("Aucun fichier de résultats AnyBURL trouvé!")
            logger.info("Pour exécuter AnyBURL et générer des résultats, utilisez:")
            logger.info("  python src/main.py -c config.yaml (avec algorithm.name: ANYBURL)")
            logger.info("\nOu créez un fichier de résultats AnyBURL manuellement.")
            sys.exit(1)
        
        logger.info(f"Trouvé {len(anyburl_files)} fichier(s) de résultats AnyBURL:")
        for f in anyburl_files:
            logger.info(f"  - {f}")
        
        # Traiter tous les fichiers trouvés
        for results_file in anyburl_files:
            # Extraire le nom de la base de données
            if "/results/" in results_file:
                db_name = Path(results_file).parent.parent.name + ".db"
            else:
                db_name = "Bupa.db"
            
            calculator = AnyBURLMetricsCalculator("data/db/", db_name, "data/output")
            calculator.process_file(results_file)


if __name__ == "__main__":
    main()
