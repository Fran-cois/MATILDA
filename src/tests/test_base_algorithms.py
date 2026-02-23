"""
Tests for BaseAlgorithm and RuleDiscoveryAlgorithm abstract base classes.

Covers the `pass` body of the abstract discover_rules() method (line 22 in
each file) by calling super() from concrete subclasses.
"""

from unittest.mock import MagicMock

from algorithms.base_algorithm import BaseAlgorithm
from algorithms.rule_discovery_algorithm import RuleDiscoveryAlgorithm


class _ConcreteBase(BaseAlgorithm):
    """Minimal concrete subclass that delegates to the abstract body."""

    def discover_rules(self, **kwargs):
        super().discover_rules(**kwargs)  # covers base_algorithm.py line 22
        return []


class _ConcreteRuleDiscovery(RuleDiscoveryAlgorithm):
    """Minimal concrete subclass that delegates to the abstract body."""

    def discover_rules(self, **kwargs):
        super().discover_rules(**kwargs)  # covers rule_discovery_algorithm.py line 22
        return []


def test_base_algorithm_init_stores_database():
    db = MagicMock()
    algo = _ConcreteBase(database=db)
    assert algo.database is db


def test_base_algorithm_abstract_pass_is_reachable():
    """super().discover_rules() returns None (the pass body) without error."""
    db = MagicMock()
    algo = _ConcreteBase(database=db)
    result = algo.discover_rules()
    assert result == []


def test_rule_discovery_algorithm_init_stores_database():
    db = MagicMock()
    algo = _ConcreteRuleDiscovery(database=db)
    assert algo.database is db


def test_rule_discovery_algorithm_abstract_pass_is_reachable():
    """super().discover_rules() returns None (the pass body) without error."""
    db = MagicMock()
    algo = _ConcreteRuleDiscovery(database=db)
    result = algo.discover_rules()
    assert result == []
