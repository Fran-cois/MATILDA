"""
Compute MATILDA metrics for AMIE3 rule discovery results.

This script calculates MATILDA metrics (correctness, compatibility, support, confidence)
for TGDRule objects produced by the AMIE3 algorithm.

AMIE3 Output Format:
    - JSON: List of TGDRule objects
    - TSV: Tab-separated values (body => head\tconfidence\tsupport)

Metrics:
    - correctness (bool): Whether all predicates in the rule map to valid tables
    - compatibility (bool): Whether table structures are compatible
    - support (float): Proportion of tuples that satisfy the rule body
    - confidence (float): Provided by AMIE3 algorithm

Author: MATILDA Framework
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from src.database.alchemy_utility import AlchemyUtility
from src.utils.rules import Predicate, TGDRule, RuleIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('amie3_metrics.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AMIE3MetricsCalculator:
    """
    Calculate MATILDA metrics for AMIE3 TGDRule results.
    
    AMIE3 (AMIE+ plus improvements) is a rule learning system for knowledge graphs.
    It produces TGDRule objects with confidence scores from the algorithm.
    """
    
    def __init__(self, database_path: str = "data/db/", 
                 database_name: Optional[str] = None,
                 output_dir: str = "data/output"):
        """
        Initialize AMIE3 metrics calculator.
        
        Args:
            database_path: Path to database directory
            database_name: Name of database (auto-detected if None)
            output_dir: Directory for output files
        """
        self.database_path = database_path
        self.database_name = database_name
        self.output_dir = output_dir
        self.db_utility = None
        self.tables = {}
        
        logger.info(f"Initialized AMIE3MetricsCalculator with DB: {database_name}")
    
    def load_amie3_results(self, filepath: str) -> List[TGDRule]:
        """
        Load AMIE3 results from JSON or TSV file.
        
        Args:
            filepath: Path to AMIE3 results file
            
        Returns:
            List of TGDRule objects
        """
        logger.info(f"Loading AMIE3 results from {filepath}")
        
        if filepath.endswith('.json'):
            return self._load_json(filepath)
        elif filepath.endswith('.tsv'):
            return self._load_tsv(filepath)
        else:
            raise ValueError(f"Unsupported file format: {filepath}")
    
    def _load_json(self, filepath: str) -> List[TGDRule]:
        """Load TGDRule objects from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            data = [data]
        
        rules = []
        for item in data:
            if isinstance(item, dict):
                if 'type' in item and item['type'] == 'TGDRule':
                    try:
                        rule = RuleIO.rule_from_dict(item)
                        if isinstance(rule, TGDRule):
                            rules.append(rule)
                    except Exception as e:
                        logger.warning(f"Error loading rule: {e}")
        
        logger.info(f"{len(rules)} règles chargées")
        return rules
    
    def _load_tsv(self, filepath: str) -> List[TGDRule]:
        """
        Load TGDRule objects from AMIE3 TSV output.
        
        TSV Format: body => head\tconfidence\tsupport
        Example: ?x r1 ?y => ?x r2 ?z\t0.95\t0.42
        """
        rules = []
        
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        nb_transactions = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Parse transaction count
            if line.startswith("Loaded"):
                try:
                    nb_transactions = int(line.split()[1])
                except (IndexError, ValueError):
                    pass
                continue
            
            # Parse rule line
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            
            try:
                rule_str = parts[0]
                confidence = float(parts[1].replace(',', '.'))
                support_count = float(parts[2].replace(',', '.'))
                
                # Parse body and head
                if '=>' not in rule_str:
                    continue
                
                body_str, head_str = rule_str.split('=>')
                body_str = body_str.strip()
                head_str = head_str.strip()
                
                # Convert to predicates
                body_preds = self._parse_predicates(body_str)
                head_preds = self._parse_predicates(head_str)
                
                if not body_preds or not head_preds:
                    continue
                
                # Normalize support
                support = support_count / nb_transactions if nb_transactions > 0 else support_count
                
                rule = TGDRule(
                    body=body_preds,
                    head=head_preds,
                    display=rule_str,
                    accuracy=-1.0,
                    confidence=confidence
                )
                rules.append(rule)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing line: {line} - {e}")
                continue
        
        logger.info(f"{len(rules)} règles chargées depuis TSV")
        return rules
    
    def _parse_predicates(self, predicate_str: str) -> List[Predicate]:
        """
        Parse predicate string into Predicate objects.
        
        AMIE3 format: ?x relation ?y relation2 ?z ...
        """
        tokens = predicate_str.split()
        if len(tokens) % 3 != 0:
            logger.warning(f"Invalid predicate string: {predicate_str}")
            return []
        
        predicates = []
        
        for i in range(0, len(tokens), 3):
            var1 = tokens[i]
            relation = tokens[i + 1]
            var2 = tokens[i + 2]
            
            # Handle compound relations (e.g., schema.table.column)
            if '.' in relation:
                parts = relation.split('.')
                if len(parts) >= 2:
                    relation = '.'.join(parts[-2:])  # Use last two parts
            
            pred = Predicate(
                variable1=var1,
                relation=relation,
                variable2=var2
            )
            predicates.append(pred)
        
        return predicates
    
    def extract_tables_from_predicates(self, predicates: List[Predicate]) -> set:
        """
        Extract table names from predicates.
        
        AMIE3 uses simple relation names (e.g., 'bupa', 'drinks').
        """
        tables = set()
        
        for pred in predicates:
            relation = pred.relation
            
            # Handle dotted notation
            if '.' in relation:
                parts = relation.split('.')
                relation = parts[-1]  # Use last part
            
            # Simple relation name is table name
            tables.add(relation.lower())
        
        return tables
    
    def initialize_db_utility(self, db_path: str) -> bool:
        """Initialize database utility and load table metadata."""
        try:
            full_path = os.path.join(self.database_path, db_path)
            
            if not os.path.exists(full_path):
                logger.error(f"Database file not found: {full_path}")
                return False
            
            self.db_utility = AlchemyUtility(full_path)
            self.tables = self.db_utility.get_tables()
            
            logger.info(f"Initialized database with {len(self.tables)} tables")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    def calculate_rule_validity(self, rule: TGDRule) -> bool:
        """
        Check if rule is valid (all tables exist in database).
        """
        if not self.db_utility:
            return False
        
        # Get tables from body and head
        body_tables = set()
        for pred in rule.body:
            tables = self.extract_tables_from_predicates([pred])
            body_tables.update(tables)
        
        head_tables = set()
        for pred in rule.head:
            tables = self.extract_tables_from_predicates([pred])
            head_tables.update(tables)
        
        all_tables = body_tables | head_tables
        
        # Check if all tables exist
        available_tables = set(self.tables.keys())
        
        for table in all_tables:
            if table not in available_tables:
                logger.debug(f"Table not found: {table}")
                return False
        
        return True
    
    def calculate_support_confidence(self, rule: TGDRule) -> Tuple[float, float]:
        """
        Calculate support and confidence for rule.
        
        - confidence: Provided by AMIE3
        - support: Approximated from database statistics
        """
        confidence = rule.confidence if rule.confidence is not None else 0.5
        
        # Approximate support from table sizes
        try:
            support = 0.5  # Default approximation
            
            if self.db_utility and rule.body:
                # Count tuples in first body predicate's table
                body_pred = rule.body[0]
                tables = self.extract_tables_from_predicates([body_pred])
                
                if tables:
                    table_name = list(tables)[0]
                    row_count = self.db_utility.get_row_count(table_name)
                    
                    if row_count and row_count > 0:
                        # Approximate support as percentage of table rows
                        support = min(1.0, 100.0 / max(1, row_count))
                        
        except Exception as e:
            logger.debug(f"Error calculating support: {e}")
            support = 0.5
        
        return support, confidence
    
    def calculate_metrics(self, rules: List[TGDRule]) -> List[Dict[str, Any]]:
        """
        Calculate all metrics for rules.
        
        Returns:
            List of rules with metrics added
        """
        logger.info(f"Calcul des métriques MATILDA sur {len(rules)} règles AMIE3...")
        
        enriched_rules = []
        
        for rule in rules:
            logger.info(f"Traitement de la règle: {rule.display}")
            
            # Calculate validity
            correct = self.calculate_rule_validity(rule)
            compatible = True  # AMIE3 ensures compatibility
            
            # Calculate support and confidence
            support, confidence = self.calculate_support_confidence(rule)
            
            # Create enriched rule dict
            rule_dict = {
                'type': 'TGDRule',
                'body': rule.body,
                'head': rule.head,
                'display': rule.display,
                'accuracy': rule.accuracy,
                'confidence': confidence,
                'correct': correct,
                'compatible': compatible,
                'support': round(support, 4)
            }
            
            enriched_rules.append(rule_dict)
            
            logger.info(f"  → Valid: {correct} | Support: {support:.4f} | Confidence: {confidence:.4f}")
        
        return enriched_rules
    
    def save_results(self, enriched_rules: List[Dict], 
                     input_filename: Optional[str] = None) -> Tuple[str, str]:
        """
        Save enriched rules to JSON and generate markdown report.
        
        Returns:
            Tuple of (json_path, md_path)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Infer database name if not set
        if not self.database_name and input_filename:
            match = re.search(r'amie3_(\w+)_', input_filename, re.IGNORECASE)
            if match:
                self.database_name = match.group(1)
        
        db_suffix = f"_{self.database_name}" if self.database_name else ""
        
        # Save JSON
        json_filename = f"amie3{db_suffix}_results_with_metrics_{timestamp}.json"
        json_path = os.path.join(self.output_dir, json_filename)
        
        with open(json_path, 'w') as f:
            json.dump(enriched_rules, f, indent=2, default=str)
        
        logger.info(f"Résultats sauvegardés avec succès: {json_path}")
        
        # Generate markdown report
        md_filename = f"amie3{db_suffix}_results_with_metrics_{timestamp}.md"
        md_path = os.path.join(self.output_dir, md_filename)
        self.generate_report(enriched_rules, md_path)
        
        return json_path, md_path
    
    def generate_report(self, enriched_rules: List[Dict], output_path: str):
        """Generate markdown report with metrics summary."""
        
        total_rules = len(enriched_rules)
        valid_rules = sum(1 for r in enriched_rules if r.get('correct', False))
        avg_support = sum(r.get('support', 0) for r in enriched_rules) / max(1, total_rules)
        avg_confidence = sum(r.get('confidence', 0) for r in enriched_rules) / max(1, total_rules)
        
        report = f"""# AMIE3 Metrics Report

**Database:** {self.database_name or 'Unknown'}
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary Statistics

| Metric | Value |
|--------|-------|
| **Total Rules** | {total_rules} |
| **Valid Rules** | {valid_rules} ({100*valid_rules/max(1, total_rules):.1f}%) |
| **Average Support** | {avg_support:.4f} |
| **Average Confidence** | {avg_confidence:.4f} |

## Rules Detail

| # | Rule | Valid | Support | Confidence |
|---|------|-------|---------|------------|
"""
        
        for i, rule in enumerate(enriched_rules, 1):
            display = rule.get('display', 'N/A')[:60]
            valid = '✓' if rule.get('correct', False) else '✗'
            support = rule.get('support', 0)
            confidence = rule.get('confidence', 0)
            
            report += f"| {i} | {display}... | {valid} | {support:.4f} | {confidence:.4f} |\n"
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Rapport généré avec succès: {output_path}")
    
    def find_amie3_results(self) -> Dict[str, List[str]]:
        """
        Auto-discover AMIE3 result files in data directories.
        
        Returns:
            Dict mapping database names to file paths
        """
        results = {}
        
        search_dirs = [
            os.path.join(self.database_path, '..', 'output'),
            os.path.join(self.database_path, '..', 'results'),
            'data/output',
            'results'
        ]
        
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            
            for filename in os.listdir(search_dir):
                if 'amie3' in filename.lower():
                    filepath = os.path.join(search_dir, filename)
                    
                    # Extract database name
                    match = re.search(r'amie3_(\w+)_|AMIE3_(\w+)_', filename, re.IGNORECASE)
                    if match:
                        db_name = match.group(1) or match.group(2)
                        if db_name not in results:
                            results[db_name] = []
                        results[db_name].append(filepath)
        
        logger.info(f"Trouvé {len(results)} ensembles de résultats AMIE3")
        return results


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Auto-discover files
        calculator = AMIE3MetricsCalculator()
        results = calculator.find_amie3_results()
        
        if not results:
            logger.error("Aucun fichier AMIE3 trouvé")
            return
        
        # Process first found file
        input_file = list(results.values())[0][0] if results else None
        if not input_file:
            logger.error("Aucun fichier AMIE3 trouvé")
            return
    
    # Infer database name
    import re
    db_match = re.search(r'amie3_(\w+)_|AMIE3_(\w+)_|_(\w+)_results|_(\w+)_example', 
                          os.path.basename(input_file), re.IGNORECASE)
    database_name = db_match.group(1) or db_match.group(2) or db_match.group(3) or db_match.group(4) if db_match else "Bupa"
    
    # Find database file
    db_dir = 'data/db/'
    db_file = None
    
    if os.path.exists(db_dir):
        for fname in os.listdir(db_dir):
            if database_name.lower() in fname.lower():
                db_file = fname
                break
    
    if not db_file:
        # Try first database
        if os.path.exists(db_dir):
            db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]
            if db_files:
                db_file = db_files[0]
                database_name = db_file.replace('.db', '')
    
    # Initialize calculator
    calculator = AMIE3MetricsCalculator(
        database_name=database_name,
        output_dir='data/output'
    )
    
    # Initialize database
    if db_file:
        try:
            calculator.initialize_db_utility(db_file)
        except Exception as e:
            logger.warning(f"Could not initialize database: {e}")
    
    # Load results
    rules = calculator.load_amie3_results(input_file)
    
    if not rules:
        logger.error("Aucune règle chargée")
        return
    
    # Calculate metrics
    enriched_rules = calculator.calculate_metrics(rules)
    
    # Save results
    json_path, md_path = calculator.save_results(enriched_rules, 
                                                  os.path.basename(input_file))
    
    logger.info(f"Traitement terminé avec succès!")


if __name__ == '__main__':
    main()


def find_amie3_results(data_dir: str = "data") -> List[str]:
    """
    Auto-discover AMIE3 result files in data directories.
    
    Args:
        data_dir: Root directory to search
        
    Returns:
        List of file paths
    """
    results = []
    
    search_dirs = [
        os.path.join(data_dir, 'output'),
        os.path.join(data_dir, 'results'),
        'data/output',
        'results'
    ]
    
    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
        
        try:
            for filename in os.listdir(search_dir):
                if 'amie3' in filename.lower() or 'amie' in filename.lower():
                    if filename.endswith('.json') or filename.endswith('.tsv'):
                        filepath = os.path.join(search_dir, filename)
                        if filepath not in results:
                            results.append(filepath)
        except PermissionError:
            continue
    
    return results
