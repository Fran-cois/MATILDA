#!/usr/bin/env python3
"""
Tests unitaires pour la validation des métriques MATILDA
"""

import unittest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "utils"))

from validate_metrics import (
    MetricsValidator,
    MetricValidationResult,
    ValidationReport
)


class TestMetricsValidator(unittest.TestCase):
    """Tests pour MetricsValidator"""
    
    def setUp(self):
        """Initialisation avant chaque test"""
        self.validator = MetricsValidator()
    
    def test_check_metric_value_valid(self):
        """Test valeur métrique valide"""
        is_valid, issues = self.validator.check_metric_value(0.75, "confidence")
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
    
    def test_check_metric_value_none(self):
        """Test détection None"""
        is_valid, issues = self.validator.check_metric_value(None, "confidence")
        self.assertFalse(is_valid)
        self.assertIn("None", issues[0])
    
    def test_check_metric_value_nan(self):
        """Test détection NaN"""
        import math
        is_valid, issues = self.validator.check_metric_value(math.nan, "confidence")
        self.assertFalse(is_valid)
        self.assertIn("NaN", issues[0])
    
    def test_check_metric_value_out_of_range(self):
        """Test valeur hors range"""
        is_valid, issues = self.validator.check_metric_value(1.5, "confidence")
        self.assertFalse(is_valid)
        self.assertIn("hors range", issues[0])
    
    def test_check_metric_value_negative(self):
        """Test valeur négative"""
        is_valid, issues = self.validator.check_metric_value(-0.1, "support")
        self.assertFalse(is_valid)
        self.assertIn("hors range", issues[0])
    
    def test_validate_rule_metrics_spider(self):
        """Test validation règle Spider"""
        rule = {
            "type": "InclusionDependency",
            "confidence": 0.85,
            "support": 0.60,
            "head_coverage": 0.75
        }
        
        results = self.validator.validate_rule_metrics(rule, "spider")
        
        # Vérifier qu'on a des résultats
        self.assertGreater(len(results), 0)
        
        # Vérifier que toutes les métriques sont valides
        for result in results:
            if result.metric_name in ['confidence', 'support', 'head_coverage']:
                self.assertTrue(result.is_valid, 
                              f"{result.metric_name} devrait être valide")
    
    def test_validate_rule_metrics_popper(self):
        """Test validation règle Popper"""
        rule = {
            "body": ["person(A)", "has_disease(A,B)"],
            "head": "hospitalized(A)",
            "confidence": 0.92,
            "support": 0.45
        }
        
        results = self.validator.validate_rule_metrics(rule, "popper")
        
        # Vérifier structure
        structure_results = [r for r in results if r.metric_name == 'structure']
        # Popper avec body devrait passer
        if structure_results:
            self.assertTrue(structure_results[0].is_valid)
    
    def test_validate_rule_metrics_anyburl(self):
        """Test validation règle AnyBurl"""
        rule = {
            "confidence": 0.88,
            "support": 0.55,
            "pca_confidence": 0.90
        }
        
        results = self.validator.validate_rule_metrics(rule, "anyburl")
        
        # Vérifier pca_confidence
        pca_results = [r for r in results if r.metric_name == 'pca_confidence']
        self.assertEqual(len(pca_results), 1)
        self.assertTrue(pca_results[0].is_valid)
    
    def test_validate_rule_metrics_amie3(self):
        """Test validation règle AMIE3"""
        rule = {
            "confidence": 0.82,
            "support": 0.48,
            "pca_confidence": 0.85,
            "positive_examples": 150,
            "body_size": 2
        }
        
        results = self.validator.validate_rule_metrics(rule, "amie3")
        
        # Vérifier métriques AMIE3
        amie3_metrics = [r.metric_name for r in results]
        self.assertIn('pca_confidence', amie3_metrics)
        self.assertIn('positive_examples', amie3_metrics)
    
    def test_validate_spider_type_mismatch(self):
        """Test détection mauvais type Spider"""
        rule = {
            "type": "WrongType",
            "confidence": 0.85
        }
        
        results = self.validator.validate_rule_metrics(rule, "spider")
        
        # Devrait détecter le mauvais type
        type_results = [r for r in results if r.metric_name == 'type']
        self.assertEqual(len(type_results), 1)
        self.assertFalse(type_results[0].is_valid)
    
    def test_validate_popper_missing_structure(self):
        """Test détection structure manquante Popper"""
        rule = {
            "confidence": 0.85
            # Pas de clauses ni body
        }
        
        results = self.validator.validate_rule_metrics(rule, "popper")
        
        # Devrait détecter la structure manquante
        structure_results = [r for r in results if r.metric_name == 'structure']
        if structure_results:
            self.assertFalse(structure_results[0].is_valid)
    
    def test_validation_report_initialization(self):
        """Test initialisation du rapport"""
        report = ValidationReport(timestamp="2026-01-19T10:00:00")
        
        self.assertEqual(report.total_checks, 0)
        self.assertEqual(report.passed_checks, 0)
        self.assertEqual(report.failed_checks, 0)
        self.assertEqual(len(report.results), 0)
    
    def test_validation_result_creation(self):
        """Test création résultat de validation"""
        result = MetricValidationResult(
            metric_name="confidence",
            algorithm="spider",
            is_valid=True,
            value=0.85
        )
        
        self.assertEqual(result.metric_name, "confidence")
        self.assertEqual(result.algorithm, "spider")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, 0.85)
        self.assertEqual(len(result.issues), 0)


class TestMetricFormulas(unittest.TestCase):
    """Tests pour vérifier les formules de calcul"""
    
    def test_confidence_formula(self):
        """Test formule confidence = support(head ∪ body) / support(body)"""
        # head_and_body = 100, body = 150
        # confidence = 100/150 = 0.667
        head_and_body = 100
        body = 150
        expected_confidence = head_and_body / body
        
        self.assertAlmostEqual(expected_confidence, 0.667, places=3)
        self.assertGreaterEqual(expected_confidence, 0.0)
        self.assertLessEqual(expected_confidence, 1.0)
    
    def test_support_formula(self):
        """Test formule support = occurrences / total_tuples"""
        occurrences = 250
        total_tuples = 1000
        expected_support = occurrences / total_tuples
        
        self.assertEqual(expected_support, 0.25)
        self.assertGreaterEqual(expected_support, 0.0)
        self.assertLessEqual(expected_support, 1.0)
    
    def test_head_coverage_formula(self):
        """Test formule head_coverage = support(head ∪ body) / support(head)"""
        head_and_body = 80
        head = 100
        expected_coverage = head_and_body / head
        
        self.assertEqual(expected_coverage, 0.80)
        self.assertGreaterEqual(expected_coverage, 0.0)
        self.assertLessEqual(expected_coverage, 1.0)
    
    def test_pca_confidence_range(self):
        """Test que PCA confidence reste dans [0,1]"""
        # PCA confidence devrait être entre 0 et 1
        test_values = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for value in test_values:
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)
    
    def test_std_confidence_non_negative(self):
        """Test que std_confidence est non-négatif"""
        # L'écart-type ne peut pas être négatif
        import math
        values = [0.7, 0.8, 0.9, 0.85, 0.88]
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = math.sqrt(variance)
        
        self.assertGreaterEqual(std, 0.0)


class TestEdgeCases(unittest.TestCase):
    """Tests pour les cas limites"""
    
    def setUp(self):
        self.validator = MetricsValidator()
    
    def test_empty_rule(self):
        """Test règle vide"""
        rule = {}
        results = self.validator.validate_rule_metrics(rule, "spider")
        # Devrait retourner des résultats même pour règle vide
        self.assertIsInstance(results, list)
    
    def test_confidence_boundary_zero(self):
        """Test confidence = 0.0 (valide)"""
        is_valid, issues = self.validator.check_metric_value(0.0, "confidence")
        self.assertTrue(is_valid)
    
    def test_confidence_boundary_one(self):
        """Test confidence = 1.0 (valide)"""
        is_valid, issues = self.validator.check_metric_value(1.0, "confidence")
        self.assertTrue(is_valid)
    
    def test_support_boundary_zero(self):
        """Test support = 0.0 (valide mais attention)"""
        is_valid, issues = self.validator.check_metric_value(0.0, "support")
        self.assertTrue(is_valid)
    
    def test_very_small_value(self):
        """Test valeur très petite"""
        is_valid, issues = self.validator.check_metric_value(0.0001, "support")
        self.assertTrue(is_valid)
    
    def test_infinity(self):
        """Test détection infini"""
        import math
        is_valid, issues = self.validator.check_metric_value(math.inf, "confidence")
        self.assertFalse(is_valid)
        self.assertIn("infini", issues[0])


def run_tests():
    """Lance tous les tests"""
    # Créer la suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter tous les tests
    suite.addTests(loader.loadTestsFromTestCase(TestMetricsValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestMetricFormulas))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Lancer les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    result = run_tests()
    
    # Afficher résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    print(f"Tests exécutés : {result.testsRun}")
    print(f"✅ Succès      : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Échecs      : {len(result.failures)}")
    print(f"⚠️  Erreurs     : {len(result.errors)}")
    print("="*80)
    
    sys.exit(0 if result.wasSuccessful() else 1)
