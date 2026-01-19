#!/usr/bin/env python3
"""
Script pour calculer les métriques MATILDA sur des résultats Spider existants.

Ce script prend un fichier JSON de résultats Spider et calcule:
- La validité (correctness) de chaque règle
- La compatibilité de chaque règle  
- Le support de chaque règle
- La confidence de chaque règle

Usage:
    python compute_spider_metrics.py <spider_results.json>
    
Ou pour traiter tous les fichiers de résultats Spider:
    python compute_spider_metrics.py
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
from utils.rules import RuleIO, InclusionDependency

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('spider_metrics_computation.log')
    ]
)
logger = logging.getLogger(__name__)


class SpiderMetricsCalculator:
    """Classe pour calculer les métriques MATILDA sur des résultats Spider."""
    
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
    
    def load_spider_results(self, results_file):
        """
        Charger les résultats Spider depuis un fichier JSON.
        
        Args:
            results_file: Chemin vers le fichier JSON de résultats Spider
            
        Returns:
            list: Liste des règles InclusionDependency
        """
        logger.info(f"Chargement des résultats Spider depuis {results_file}...")
        
        try:
            with open(results_file, 'r') as f:
                data = json.load(f)
            
            rules = []
            for rule_dict in data:
                # Créer une InclusionDependency depuis le dictionnaire
                rule = InclusionDependency(
                    table_dependant=rule_dict.get('table_dependant'),
                    columns_dependant=tuple(rule_dict.get('columns_dependant', [])),
                    table_referenced=rule_dict.get('table_referenced'),
                    columns_referenced=tuple(rule_dict.get('columns_referenced', [])),
                    display=rule_dict.get('display'),
                    correct=rule_dict.get('correct'),
                    compatible=rule_dict.get('compatible'),
                    accuracy=rule_dict.get('accuracy', rule_dict.get('support')),
                    confidence=rule_dict.get('confidence')
                )
                rules.append(rule)
            
            logger.info(f"{len(rules)} règles chargées")
            return rules
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des résultats: {e}", exc_info=True)
            return []
    
    def calculate_validity(self, rule, db_inspector, threshold=0.5):
        """
        Calculer la validité (correctness) d'une règle.
        
        Args:
            rule: InclusionDependency à valider
            db_inspector: Instance AlchemyUtility
            threshold: Seuil minimal de compatibilité
            
        Returns:
            bool: True si la règle est valide
        """
        try:
            results = db_inspector.check_threshold(
                [(
                    rule.table_dependant,
                    0,
                    rule.columns_dependant[0],
                    rule.table_referenced,
                    1,
                    rule.columns_referenced[0],
                )],
                disjoint_semantics=False,
                flag="compatibility",
                threshold=threshold
            )
            return bool(results)
        except Exception as e:
            logger.warning(f"Erreur lors du calcul de validité: {e}")
            return False
    
    def calculate_support_confidence(self, rule, db_inspector):
        """
        Calculer le support et la confidence d'une règle d'inclusion.
        
        Support: |A ∩ B| / |Total tuples|
        Confidence: |A ∩ B| / |A|
        
        Args:
            rule: InclusionDependency
            db_inspector: Instance AlchemyUtility
            
        Returns:
            tuple: (support, confidence)
        """
        try:
            # Obtenir le nombre de tuples via l'engine et les métadonnées
            from sqlalchemy import select, func
            
            metadata = db_inspector.db_manager.metadata
            engine = db_inspector.db_manager.engine
            
            table_dep = metadata.tables.get(rule.table_dependant)
            table_ref = metadata.tables.get(rule.table_referenced)
            
            if table_dep is None or table_ref is None:
                logger.warning(f"Table not found: {rule.table_dependant} or {rule.table_referenced}")
                return 0.0, 0.0
            
            col_dep = rule.columns_dependant[0]
            col_ref = rule.columns_referenced[0]
            
            if col_dep not in table_dep.columns or col_ref not in table_ref.columns:
                logger.warning(f"Column not found: {col_dep} in {rule.table_dependant} or {col_ref} in {rule.table_referenced}")
                return 0.0, 0.0
            
            with engine.connect() as conn:
                # Compter les tuples dans chaque table
                count_dep = conn.execute(select(func.count()).select_from(table_dep)).scalar()
                count_ref = conn.execute(select(func.count()).select_from(table_ref)).scalar()
                
                # Compter les valeurs distinctes qui se chevauchent
                # Pour une IND A[x] ⊆ B[y], on veut COUNT(DISTINCT A.x) WHERE A.x IN (SELECT B.y)
                overlap_query = select(func.count(func.distinct(table_dep.columns[col_dep]))).select_from(
                    table_dep.join(
                        table_ref,
                        table_dep.columns[col_dep] == table_ref.columns[col_ref]
                    )
                )
                overlap_count = conn.execute(overlap_query).scalar()
                
                # Confidence: pourcentage de valeurs de A qui sont dans B
                confidence = overlap_count / count_dep if count_dep > 0 else 0.0
                
                # Support: pourcentage par rapport au total des tuples
                total_tuples = count_dep + count_ref
                support = overlap_count / total_tuples if total_tuples > 0 else 0.0
                
                return support, confidence
            
        except Exception as e:
            logger.warning(f"Erreur lors du calcul de support/confidence pour {rule.table_dependant}[{rule.columns_dependant[0]}]: {e}")
            return 0.0, 0.0
    
    def calculate_metrics(self, rules):
        """
        Calculer toutes les métriques MATILDA pour les règles Spider.
        
        Args:
            rules: Liste des règles InclusionDependency
            
        Returns:
            list: Liste des règles avec métriques calculées
        """
        logger.info(f"Calcul des métriques MATILDA sur {len(rules)} règles Spider...")
        
        db_file_path = self.database_path / self.database_name
        db_uri = f"sqlite:///{db_file_path}"
        
        enriched_rules = []
        
        try:
            with AlchemyUtility(db_uri, database_path=str(self.database_path), 
                              create_index=False, create_csv=False, 
                              create_tsv=False, get_data=False) as db_inspector:
                
                for rule in rules:
                    logger.info(f"Traitement de la règle: {rule.table_dependant}[{rule.columns_dependant[0]}] → {rule.table_referenced}[{rule.columns_referenced[0]}]")
                    
                    # Calculer la validité
                    is_valid = self.calculate_validity(rule, db_inspector)
                    
                    # Calculer support et confidence
                    support, confidence = self.calculate_support_confidence(rule, db_inspector)
                    
                    # Créer une règle enrichie avec toutes les métriques
                    display = f"{rule.table_dependant}[{rule.columns_dependant[0]}] ⊆ {rule.table_referenced}[{rule.columns_referenced[0]}]"
                    
                    enriched_rule = InclusionDependency(
                        table_dependant=rule.table_dependant,
                        columns_dependant=rule.columns_dependant,
                        table_referenced=rule.table_referenced,
                        columns_referenced=rule.columns_referenced,
                        display=display,
                        correct=is_valid,
                        compatible=is_valid,  # Pour Spider, correct et compatible sont similaires
                        accuracy=support,
                        confidence=confidence
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
            output_file = self.output_dir / f"spider_{self.database_name.replace('.db', '')}_metrics_{timestamp}.json"
        
        logger.info(f"Sauvegarde des résultats dans {output_file}...")
        
        # Convertir les règles en dictionnaires
        rules_data = []
        for rule in rules:
            rule_dict = {
                "table_dependant": rule.table_dependant,
                "columns_dependant": list(rule.columns_dependant),
                "table_referenced": rule.table_referenced,
                "columns_referenced": list(rule.columns_referenced),
                "display": rule.display,
                "correct": rule.correct,
                "compatible": rule.compatible,
                "support": rule.accuracy,
                "confidence": rule.confidence
            }
            rules_data.append(rule_dict)
        
        with open(output_file, 'w') as f:
            json.dump(rules_data, f, indent=2)
        
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
        valid_rules = sum(1 for r in rules if r.correct)
        avg_support = sum(r.accuracy for r in rules) / total_rules if total_rules > 0 else 0
        avg_confidence = sum(r.confidence for r in rules) / total_rules if total_rules > 0 else 0
        
        with open(report_file, 'w') as f:
            f.write(f"# Rapport de Métriques MATILDA pour Spider\n\n")
            f.write(f"**Base de données:** {self.database_name}\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"## Résumé\n\n")
            f.write(f"- **Nombre total de règles:** {total_rules}\n")
            f.write(f"- **Règles valides:** {valid_rules} ({valid_rules/total_rules*100:.1f}% si total > 0)\n")
            f.write(f"- **Support moyen:** {avg_support:.4f}\n")
            f.write(f"- **Confidence moyenne:** {avg_confidence:.4f}\n\n")
            
            f.write(f"## Règles avec Métriques\n\n")
            f.write(f"| # | Règle | Valide | Support | Confidence |\n")
            f.write(f"|---|-------|--------|---------|------------|\n")
            
            for idx, rule in enumerate(rules, 1):
                valid_str = "✓" if rule.correct else "✗"
                f.write(f"| {idx} | {rule.display} | {valid_str} | {rule.accuracy:.4f} | {rule.confidence:.4f} |\n")
            
            f.write(f"\n## Métriques MATILDA\n\n")
            f.write(f"### Définitions\n\n")
            f.write(f"- **Correctness (Validité):** La règle est valide selon la sémantique des données\n")
            f.write(f"- **Compatibility:** Les attributs sont compatibles selon un seuil de similarité\n")
            f.write(f"- **Support:** Proportion de tuples satisfaisant la règle par rapport au total\n")
            f.write(f"- **Confidence:** Proportion de tuples de la table dépendante satisfaisant la règle\n\n")
            
            f.write(f"## Détails\n\n")
            f.write(f"Les résultats complets sont disponibles dans le fichier JSON: `{output_file.name}`\n")
        
        logger.info(f"Rapport généré avec succès dans {report_file}")
    
    def process_file(self, results_file):
        """
        Traiter un fichier de résultats Spider.
        
        Args:
            results_file: Chemin vers le fichier JSON de résultats Spider
        """
        try:
            logger.info("=" * 80)
            logger.info(f"Traitement du fichier: {results_file}")
            logger.info("=" * 80)
            
            # Charger les résultats Spider
            rules = self.load_spider_results(results_file)
            
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


def find_spider_results(data_dir="data"):
    """
    Trouver tous les fichiers de résultats Spider dans le répertoire data.
    
    Args:
        data_dir: Répertoire racine où chercher
        
    Returns:
        list: Liste des chemins vers les fichiers de résultats Spider
    """
    data_path = Path(data_dir)
    spider_files = []
    
    # Chercher dans data/output
    output_dir = data_path / "output"
    if output_dir.exists():
        spider_files.extend(output_dir.glob("*spider*.json"))
    
    # Chercher dans data/results
    results_dir = data_path / "results"
    if results_dir.exists():
        for db_dir in results_dir.iterdir():
            if db_dir.is_dir():
                spider_dir = db_dir / "spider"
                if spider_dir.exists():
                    spider_files.extend(spider_dir.glob("spider_*_results.json"))
    
    return [str(f) for f in spider_files]


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
        if "spider_" in filename:
            parts = filename.split("_")
            if len(parts) >= 2:
                database_name = parts[1] + ".db"
            else:
                database_name = "Bupa.db"
        else:
            database_name = "Bupa.db"
        
        logger.info(f"Fichier de résultats: {results_file}")
        logger.info(f"Base de données inférée: {database_name}")
        
        calculator = SpiderMetricsCalculator("data/db/", database_name, "data/output")
        calculator.process_file(results_file)
    
    else:
        # Chercher tous les fichiers de résultats Spider
        spider_files = find_spider_results()
        
        if not spider_files:
            logger.error("Aucun fichier de résultats Spider trouvé!")
            logger.info("Pour exécuter Spider et générer des résultats, utilisez:")
            logger.info("  python src/main.py -c config.yaml (avec algorithm.name: SPIDER)")
            logger.info("\nOu créez un fichier de résultats Spider manuellement.")
            sys.exit(1)
        
        logger.info(f"Trouvé {len(spider_files)} fichier(s) de résultats Spider:")
        for f in spider_files:
            logger.info(f"  - {f}")
        
        # Traiter tous les fichiers trouvés
        for results_file in spider_files:
            # Extraire le nom de la base de données
            if "/results/" in results_file:
                db_name = Path(results_file).parent.parent.name + ".db"
            else:
                db_name = "Bupa.db"
            
            calculator = SpiderMetricsCalculator("data/db/", db_name, "data/output")
            calculator.process_file(results_file)


if __name__ == "__main__":
    main()
