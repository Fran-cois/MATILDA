"""
Unit tests for heuristic functions in path_search.py

Tests cover:
- Heuristic initialization
- Each heuristic function (naive, table_size, join_selectivity, hybrid)
- Factory function
- Edge cases (empty rules, missing data)
"""

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from heuristics.path_search import PathSearchHeuristics, create_heuristic


class MockIndexedAttribute:
    """Mock IndexedAttribute for testing."""

    def __init__(self, i: int, j: int, k: int):
        self.i = i  # table index
        self.j = j  # occurrence
        self.k = k  # attribute index


class MockAttributeMapper:
    """Mock AttributeMapper for testing."""

    def __init__(self):
        self.tables = ["table1", "table2", "table3"]


class MockDBInspector:
    """Mock database inspector for testing."""

    def __init__(self):
        self._tables = ["table1", "table2", "table3"]

    def get_tables(self):
        return self._tables

    def execute_query(self, query):
        # Return mock counts
        if "table1" in query:
            return [{"cnt": 1000}]
        elif "table2" in query:
            return [{"cnt": 5000}]
        elif "table3" in query:
            return [{"cnt": 500}]
        return [{"cnt": 0}]


class TestPathSearchHeuristics(unittest.TestCase):
    """Test suite for PathSearchHeuristics class."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_inspector = MockDBInspector()
        self.mapper = MockAttributeMapper()
        self.heuristics = PathSearchHeuristics(self.db_inspector, self.mapper)

        # Create mock candidate rules
        self.empty_rule = []
        self.single_table_rule = [[MockIndexedAttribute(0, 0, 0), MockIndexedAttribute(0, 0, 1)]]
        self.two_table_rule = [[MockIndexedAttribute(0, 0, 0), MockIndexedAttribute(1, 1, 0)]]
        self.three_table_rule = [
            [MockIndexedAttribute(0, 0, 0), MockIndexedAttribute(1, 1, 0)],
            [MockIndexedAttribute(1, 1, 1), MockIndexedAttribute(2, 2, 0)],
        ]

    def test_initialization(self):
        """Test that heuristics initialize correctly."""
        self.assertIsNotNone(self.heuristics)
        self.assertEqual(len(self.heuristics._table_sizes), 3)
        self.assertEqual(self.heuristics._table_sizes["table1"], 1000)
        self.assertEqual(self.heuristics._table_sizes["table2"], 5000)
        self.assertEqual(self.heuristics._table_sizes["table3"], 500)

    def test_naive_heuristic_empty_rule(self):
        """Test naive heuristic with empty rule."""
        cost = self.heuristics.naive_heuristic(self.empty_rule, self.mapper, self.db_inspector)
        self.assertEqual(cost, 0.0)

    def test_naive_heuristic_single_table(self):
        """Test naive heuristic with single table."""
        cost = self.heuristics.naive_heuristic(
            self.single_table_rule, self.mapper, self.db_inspector
        )
        self.assertEqual(cost, 1.0)  # One unique table

    def test_naive_heuristic_multiple_tables(self):
        """Test naive heuristic with multiple tables."""
        cost = self.heuristics.naive_heuristic(self.two_table_rule, self.mapper, self.db_inspector)
        self.assertEqual(cost, 2.0)  # Two unique tables

        cost = self.heuristics.naive_heuristic(
            self.three_table_rule, self.mapper, self.db_inspector
        )
        self.assertEqual(cost, 3.0)  # Three unique tables

    def test_table_size_heuristic_empty_rule(self):
        """Test table size heuristic with empty rule."""
        cost = self.heuristics.table_size_heuristic(self.empty_rule, self.mapper, self.db_inspector)
        self.assertEqual(cost, 0.0)

    def test_table_size_heuristic_single_table(self):
        """Test table size heuristic with single table."""
        cost = self.heuristics.table_size_heuristic(
            self.single_table_rule, self.mapper, self.db_inspector
        )
        # Should be normalized by 1 table: 1000 / 1 = 1000
        self.assertEqual(cost, 1000.0)

    def test_table_size_heuristic_multiple_tables(self):
        """Test table size heuristic considers table sizes."""
        # table1 (1000) + table2 (5000) = 6000, normalized by 2 = 3000
        cost = self.heuristics.table_size_heuristic(
            self.two_table_rule, self.mapper, self.db_inspector
        )
        self.assertEqual(cost, 3000.0)

    def test_join_selectivity_heuristic_empty_rule(self):
        """Test join selectivity heuristic with empty rule."""
        cost = self.heuristics.join_selectivity_heuristic(
            self.empty_rule, self.mapper, self.db_inspector
        )
        self.assertEqual(cost, 0.0)

    def test_join_selectivity_heuristic_single_table(self):
        """Test join selectivity with single table (no joins)."""
        cost = self.heuristics.join_selectivity_heuristic(
            self.single_table_rule, self.mapper, self.db_inspector
        )
        # Should be just the size of table1
        self.assertEqual(cost, 1000.0)

    def test_join_selectivity_heuristic_with_joins(self):
        """Test join selectivity considers join selectivity factor."""
        cost = self.heuristics.join_selectivity_heuristic(
            self.two_table_rule, self.mapper, self.db_inspector
        )
        # table1 (1000) * table2 (5000) * selectivity (0.1) = 500,000
        self.assertGreater(cost, 1000.0)  # Should be larger than single table

    def test_hybrid_heuristic(self):
        """Test hybrid heuristic combines multiple factors."""
        cost_empty = self.heuristics.hybrid_heuristic(
            self.empty_rule, self.mapper, self.db_inspector
        )
        cost_single = self.heuristics.hybrid_heuristic(
            self.single_table_rule, self.mapper, self.db_inspector
        )
        cost_two = self.heuristics.hybrid_heuristic(
            self.two_table_rule, self.mapper, self.db_inspector
        )

        # Hybrid should produce different costs for different complexities
        self.assertNotEqual(cost_empty, cost_single)
        self.assertNotEqual(cost_single, cost_two)

        # Generally, more complex rules should have higher cost
        self.assertLess(cost_empty, cost_single)
        self.assertLess(cost_single, cost_two)

    def test_get_heuristic_function(self):
        """Test getting heuristic functions by name."""
        naive_func = self.heuristics.get_heuristic_function("naive")
        self.assertIsNotNone(naive_func)
        self.assertTrue(callable(naive_func))

        table_size_func = self.heuristics.get_heuristic_function("table_size")
        self.assertIsNotNone(table_size_func)

        hybrid_func = self.heuristics.get_heuristic_function("hybrid")
        self.assertIsNotNone(hybrid_func)

        # Unknown name should return hybrid as default
        default_func = self.heuristics.get_heuristic_function("unknown")
        self.assertEqual(default_func, self.heuristics.hybrid_heuristic)

    def test_factory_function(self):
        """Test create_heuristic factory function."""
        heuristic_func = create_heuristic(self.db_inspector, self.mapper, "naive")
        self.assertIsNotNone(heuristic_func)
        self.assertTrue(callable(heuristic_func))

        # Test that factory function returns working heuristic
        cost = heuristic_func(self.single_table_rule, self.mapper, self.db_inspector)
        self.assertIsInstance(cost, float)
        self.assertGreaterEqual(cost, 0.0)

    def test_heuristic_consistency(self):
        """Test that heuristics return consistent results."""
        # Same rule should give same cost
        cost1 = self.heuristics.naive_heuristic(self.two_table_rule, self.mapper, self.db_inspector)
        cost2 = self.heuristics.naive_heuristic(self.two_table_rule, self.mapper, self.db_inspector)
        self.assertEqual(cost1, cost2)

        # Test for all heuristics
        for heuristic_name in ["naive", "table_size", "join_selectivity", "hybrid"]:
            func = self.heuristics.get_heuristic_function(heuristic_name)
            c1 = func(self.single_table_rule, self.mapper, self.db_inspector)
            c2 = func(self.single_table_rule, self.mapper, self.db_inspector)
            self.assertEqual(c1, c2, f"{heuristic_name} not consistent")

    def test_heuristic_ordering(self):
        """Test that heuristics produce meaningful ordering."""
        # Naive heuristic should prefer shorter rules
        naive_func = self.heuristics.get_heuristic_function("naive")
        cost_single = naive_func(self.single_table_rule, self.mapper, self.db_inspector)
        cost_three = naive_func(self.three_table_rule, self.mapper, self.db_inspector)
        self.assertLess(cost_single, cost_three, "Naive should prefer shorter rules")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.db_inspector = MockDBInspector()
        self.mapper = MockAttributeMapper()
        self.heuristics = PathSearchHeuristics(self.db_inspector, self.mapper)

    def test_unknown_table(self):
        """Test handling of unknown table indices."""
        # Create rule with table index outside mapper range
        rule = [[MockIndexedAttribute(99, 0, 0)]]

        # Should not crash, use default penalty
        cost = self.heuristics.table_size_heuristic(rule, self.mapper, self.db_inspector)
        self.assertGreater(cost, 0.0)

    def test_all_heuristics_non_negative(self):
        """Test that all heuristics return non-negative costs."""
        rule = [[MockIndexedAttribute(0, 0, 0), MockIndexedAttribute(1, 1, 0)]]

        for name in ["naive", "table_size", "join_selectivity", "hybrid"]:
            func = self.heuristics.get_heuristic_function(name)
            cost = func(rule, self.mapper, self.db_inspector)
            self.assertGreaterEqual(cost, 0.0, f"{name} returned negative cost")


class TestCoverageCompletion(unittest.TestCase):
    """Tests targeting previously uncovered lines in path_search.py."""

    def setUp(self):
        self.mapper = MockAttributeMapper()

    # ------------------------------------------------------------------
    # Lines 45-46: exception in _cache_table_sizes
    # ------------------------------------------------------------------

    def test_cache_table_sizes_exception_is_swallowed(self):
        """_cache_table_sizes prints a warning but does not raise (lines 45-46)."""

        class FailingDB:
            def get_tables(self):
                raise RuntimeError("DB connection failed")

            def execute_query(self, query):
                return []

        h = PathSearchHeuristics(FailingDB(), self.mapper)
        # Should have silently swallowed the error, leaving _table_sizes empty
        self.assertEqual(h._table_sizes, {})

    # ------------------------------------------------------------------
    # Line 120: join_selectivity_heuristic returns float('inf')
    # ------------------------------------------------------------------

    def test_join_selectivity_empty_first_jia_returns_inf(self):
        """candidate_rule[0] is empty → return float('inf') (line 120)."""
        db = MockDBInspector()
        h = PathSearchHeuristics(db, self.mapper)
        cost = h.join_selectivity_heuristic([[]], self.mapper, db)
        self.assertEqual(cost, float("inf"))

    # ------------------------------------------------------------------
    # Lines 128-132: join-selectivity loop body (multi-JIA rule)
    # ------------------------------------------------------------------

    def test_join_selectivity_multi_jia_executes_loop(self):
        """A rule with 2 JIA elements exercises the loop on lines 128-132."""
        db = MockDBInspector()
        h = PathSearchHeuristics(db, self.mapper)
        # Two separate JIAs → loop runs once (i=1)
        multi_jia_rule = [
            [MockIndexedAttribute(0, 0, 0)],
            [MockIndexedAttribute(1, 1, 0)],
        ]
        cost = h.join_selectivity_heuristic(multi_jia_rule, self.mapper, db)
        # table1(1000) * table2(5000) * 0.1 = 500_000
        self.assertGreater(cost, 1000.0)

    # ------------------------------------------------------------------
    # Lines 187-188: _get_table_name exception fallback
    # ------------------------------------------------------------------

    def test_get_table_name_attribute_error_fallback(self):
        """attr without .i attribute triggers except branch (lines 187-188)."""
        db = MockDBInspector()
        h = PathSearchHeuristics(db, self.mapper)

        class NoIAttr:
            pass

        result = h._get_table_name(NoIAttr(), self.mapper)
        self.assertEqual(result, "table_0")


def suite():
    """Create test suite."""
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestPathSearchHeuristics))
    test_suite.addTest(unittest.makeSuite(TestEdgeCases))
    test_suite.addTest(unittest.makeSuite(TestCoverageCompletion))
    return test_suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
