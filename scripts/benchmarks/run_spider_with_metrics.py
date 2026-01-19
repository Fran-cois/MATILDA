#!/usr/bin/env python3
"""
Script pour exécuter Spider sur Bupa et calculer les métriques MATILDA.

Ce script:
1. Exécute Spider sur la base de données Bupa
2. Calcule les métriques de correctness (validité) des règles
3. Calcule les métriques de compatibilité des règles
4. Calcule le support et la confidence pour chaque règle
5. Génère un rapport avec toutes les métriques

Usage:
    python run_spider_with_metrics.py
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Ajouter le chemin src au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from algorithms.spider import Spider
from database.alchemy_utility import AlchemyUtility
from utils.rules import RuleIO, InclusionDependency
from utils.run_cmd import run_cmd
import ast

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('spider_metrics.log')
    ]
)
logger = logging.getLogger(__name__)


class SpiderMetricsCalculator:
    """Classe pour exécuter Spider et calculer les métriques MATILDA."""
    
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
        
        # Créer le répertoire results s'il n'existe pas
        Path("results").mkdir(exist_ok=True)
        
    def run_spider_direct(self):
        """
        Exécuter Spider directement avec Java (sans Docker).
        
        Returns:
            dict: Dictionnaire des règles découvertes par Spider
        """
        logger.info(f"Exécution de Spider (mode Java direct) sur {self.database_name}...")
        
        db_file_path = self.database_path / self.database_name
        db_uri = f"sqlite:///{db_file_path}"
        
        rules = {}
        
        try:
            with AlchemyUtility(db_uri, database_path=str(self.database_path), create_index=False) as db_util:
                # Obtenir les fichiers CSV de la base de données
                csv_dir = db_util.base_csv_dir
                csv_files = [
                    os.path.join(csv_dir, f)
                    for f in os.listdir(csv_dir)
                    if f.endswith('.csv')
                ]
                csv_files_str = " ".join(csv_files)
                
                logger.info(f"Fichiers CSV trouvés: {len(csv_files)}")
                
                # Préparer la commande Spider
                current_time = datetime.now()
                file_name = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}_SPIDER'
                
                # Chemin vers les JARs
                jar_path = "src/algorithms/bins/metanome/"
                
                cmd_string = (
                    f"java -cp {jar_path}metanome-cli-1.2-SNAPSHOT.jar:"
                    f"{jar_path}SPIDER-1.2-SNAPSHOT.jar de.metanome.cli.App "
                    f"--algorithm de.metanome.algorithms.spider.SPIDERFile "
                    f"--files {csv_files_str} --table-key INPUT_FILES "
                    f"--separator \",\" --output file:{file_name} --header"
                )
                
                logger.info(f"Exécution de: {cmd_string}")
                
                if not run_cmd(cmd_string):
                    logger.error("Échec de l'exécution de Spider")
                    return rules
                
                # Lire les résultats
                result_file_path = os.path.join("results", f"{file_name}_inds")
                logger.info(f"Lecture des résultats depuis: {result_file_path}")
                
                try:
                    with open(result_file_path, mode="r") as f:
                        raw_rules = [line for line in f if line.strip()]
                    
                    logger.info(f"Nombre de règles brutes trouvées: {len(raw_rules)}")
                    
                    # Parser les règles
                    for raw_rule in raw_rules:
                        try:
                            raw_rule = ast.literal_eval(raw_rule)
                            
                            table_dependant = raw_rule["dependant"]["columnIdentifiers"][0]["tableIdentifier"].replace(".csv", "")
                            columns_dependant = (
                                raw_rule["dependant"]["columnIdentifiers"][0]["columnIdentifier"],
                            )
                            table_referenced = raw_rule["referenced"]["columnIdentifiers"][0]["tableIdentifier"].replace(".csv", "")
                            columns_referenced = (
                                raw_rule["referenced"]["columnIdentifiers"][0]["columnIdentifier"],
                            )
                            
                            inclusion_dependency = InclusionDependency(
                                table_dependant=table_dependant,
                                columns_dependant=columns_dependant,
                                table_referenced=table_referenced,
                                columns_referenced=columns_referenced,
                            )
                            rules[inclusion_dependency] = (1, 1)
                            
                        except (ValueError, SyntaxError, KeyError, IndexError, AttributeError) as e:
                            logger.warning(f"Impossible de parser la règle: {e}")
                            continue
                    
                    # Nettoyer le fichier de résultats
                    if os.path.exists(result_file_path):
                        os.remove(result_file_path)
                    
                except FileNotFoundError:
                    logger.error(f"Fichier de résultats non trouvé: {result_file_path}")
                    return rules
                
                logger.info(f"Spider a découvert {len(rules)} règles")
                return rules
                
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de Spider: {e}", exc_info=True)
            return {}
    
    def run_spider(self):
        """
        Exécuter Spider sur la base de données (essaie Java direct).
        
        Returns:
            dict: Dictionnaire des règles découvertes par Spider
        """
        # Toujours utiliser le mode Java direct
        return self.run_spider_direct()
    
    def calculate_validity(self, rule, db_inspector, threshold=0.5):
        """
        Calculer la validité (correctness) d'une règle.
        
        Une règle est valide si l'overlap entre les attributs dépendants et référencés
        dépasse le seuil défini.
        
        Args:
            rule: InclusionDependency à valider
            db_inspector: Instance AlchemyUtility pour accéder à la base de données
            threshold: Seuil minimal de compatibilité (0.5 par défaut)
            
        Returns:
            bool: True si la règle est valide, False sinon
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
            logger.error(f"Erreur lors du calcul de validité: {e}")
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
            # Obtenir le nombre de tuples dans chaque table
            count_dependant = db_inspector.get_table_row_count(rule.table_dependant)
            count_referenced = db_inspector.get_table_row_count(rule.table_referenced)
            
            # Obtenir le nombre de valeurs qui se chevauchent
            overlap_result = db_inspector.check_threshold(
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
                threshold=0.0  # On veut tous les overlaps
            )
            
            # overlap_result contient le nombre de valeurs qui se chevauchent
            if overlap_result and count_dependant > 0:
                # Pour une IND, on veut le nombre de valeurs de la table dépendante
                # qui sont présentes dans la table référencée
                
                # Confidence: pourcentage de valeurs de A qui sont dans B
                confidence = overlap_result / count_dependant if count_dependant > 0 else 0.0
                
                # Support: pourcentage par rapport au total des tuples
                total_tuples = count_dependant + count_referenced
                support = overlap_result / total_tuples if total_tuples > 0 else 0.0
                
                return support, confidence
            else:
                return 0.0, 0.0
                
        except Exception as e:
            logger.error(f"Erreur lors du calcul de support/confidence: {e}")
            return 0.0, 0.0
    
    def calculate_metrics(self, rules_dict):
        """
        Calculer toutes les métriques MATILDA pour les règles Spider.
        
        Args:
            rules_dict: Dictionnaire des règles retournées par Spider
            
        Returns:
            list: Liste des règles avec métriques calculées
        """
        logger.info("Calcul des métriques MATILDA sur les règles Spider...")
        
        db_file_path = self.database_path / self.database_name
        db_uri = f"sqlite:///{db_file_path}"
        
        enriched_rules = []
        
        try:
            with AlchemyUtility(db_uri, database_path=str(self.database_path), 
                              create_index=False, create_csv=False, 
                              create_tsv=False, get_data=False) as db_inspector:
                
                for rule, (_, _) in rules_dict.items():
                    # Calculer la validité
                    is_valid = self.calculate_validity(rule, db_inspector)
                    
                    # Calculer support et confidence
                    support, confidence = self.calculate_support_confidence(rule, db_inspector)
                    
                    # Créer une règle enrichie avec toutes les métriques
                    enriched_rule = InclusionDependency(
                        table_dependant=rule.table_dependant,
                        columns_dependant=rule.columns_dependant,
                        table_referenced=rule.table_referenced,
                        columns_referenced=rule.columns_referenced,
                        display=f"{rule.table_dependant}[{rule.columns_dependant[0]}] ⊆ {rule.table_referenced}[{rule.columns_referenced[0]}]",
                        correct=is_valid,
                        compatible=is_valid,  # Pour Spider, correct et compatible sont similaires
                        accuracy=support,
                        confidence=confidence
                    )
                    
                    enriched_rules.append(enriched_rule)
                    
                    logger.info(
                        f"Règle: {enriched_rule.display} | "
                        f"Valid: {is_valid} | "
                        f"Support: {support:.4f} | "
                        f"Confidence: {confidence:.4f}"
                    )
                
        except Exception as e:
            logger.error(f"Erreur lors du calcul des métriques: {e}", exc_info=True)
        
        return enriched_rules
    
    def save_results(self, rules):
        """
        Sauvegarder les résultats avec métriques dans un fichier JSON.
        
        Args:
            rules: Liste des règles enrichies avec métriques
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
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
            f.write(f"# Rapport d'Exécution Spider avec Métriques MATILDA\n\n")
            f.write(f"**Base de données:** {self.database_name}\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"## Résumé\n\n")
            f.write(f"- **Nombre total de règles:** {total_rules}\n")
            f.write(f"- **Règles valides:** {valid_rules} ({valid_rules/total_rules*100:.1f}%)\n")
            f.write(f"- **Support moyen:** {avg_support:.4f}\n")
            f.write(f"- **Confidence moyenne:** {avg_confidence:.4f}\n\n")
            
            f.write(f"## Règles Découvertes\n\n")
            f.write(f"| # | Règle | Valide | Support | Confidence |\n")
            f.write(f"|---|-------|--------|---------|------------|\n")
            
            for idx, rule in enumerate(rules, 1):
                valid_str = "✓" if rule.correct else "✗"
                f.write(f"| {idx} | {rule.display} | {valid_str} | {rule.accuracy:.4f} | {rule.confidence:.4f} |\n")
            
            f.write(f"\n## Détails\n\n")
            f.write(f"Les résultats complets sont disponibles dans le fichier JSON: `{output_file.name}`\n")
        
        logger.info(f"Rapport généré avec succès dans {report_file}")
    
    def run(self):
        """Exécuter le pipeline complet: Spider + calcul des métriques."""
        try:
            logger.info("=" * 80)
            logger.info("Début de l'exécution de Spider avec calcul des métriques MATILDA")
            logger.info("=" * 80)
            
            # Étape 1: Exécuter Spider
            rules_dict = self.run_spider()
            
            if not rules_dict:
                logger.warning("Aucune règle découverte par Spider")
                return
            
            # Étape 2: Calculer les métriques
            enriched_rules = self.calculate_metrics(rules_dict)
            
            # Étape 3: Sauvegarder les résultats
            self.save_results(enriched_rules)
            
            logger.info("=" * 80)
            logger.info("Exécution terminée avec succès!")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution: {e}", exc_info=True)
            raise


def main():
    """Point d'entrée principal du script."""
    # Configuration par défaut pour Bupa
    database_path = "data/db/"
    database_name = "Bupa.db"
    output_dir = "data/output"
    
    # Permettre de passer la base de données en argument
    if len(sys.argv) > 1:
        database_name = sys.argv[1]
        if not database_name.endswith('.db'):
            database_name += '.db'
    
    logger.info(f"Configuration:")
    logger.info(f"  - Base de données: {database_name}")
    logger.info(f"  - Chemin: {database_path}")
    logger.info(f"  - Répertoire de sortie: {output_dir}")
    
    # Vérifier que la base de données existe
    db_path = Path(database_path) / database_name
    if not db_path.exists():
        logger.error(f"La base de données {db_path} n'existe pas!")
        logger.info(f"Bases de données disponibles dans {database_path}:")
        for db_file in Path(database_path).glob("*.db"):
            logger.info(f"  - {db_file.name}")
        sys.exit(1)
    
    # Exécuter le pipeline
    calculator = SpiderMetricsCalculator(database_path, database_name, output_dir)
    calculator.run()


if __name__ == "__main__":
    main()
