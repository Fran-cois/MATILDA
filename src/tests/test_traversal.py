"""
Tests for graph_traversal.py — DFS, BFS, A*, and get_traversal_algorithm.

Fixtures build a small synthetic ConstraintGraph from real
IndexedAttribute / JoinableIndexedAttributes objects so every branch of
each traversal algorithm is exercised without touching the database.
"""

from unittest.mock import MagicMock

import pytest

from algorithms.MATILDA.constraint_graph import (
    ConstraintGraph,
    IndexedAttribute,
    JoinableIndexedAttributes,
)
from algorithms.MATILDA.graph_traversal import astar, bfs, dfs, get_traversal_algorithm

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _ia(i, j, k):
    return IndexedAttribute(i, j, k)


def _jia(a, b):
    return JoinableIndexedAttributes(a, b)


def _noop_pruning(candidate_rule, mapper, db_inspector):
    """Accept every candidate rule (no pruning)."""
    return True


def _reject_all(candidate_rule, mapper, db_inspector):
    """Reject every candidate rule."""
    return False


def _accept_len_lte(n):
    """Accept only candidate rules with length <= n."""
    return lambda cr, m, db: len(cr) <= n


def _always_allow(candidate_rule, next_node, visited, max_table, max_vars):
    """next_node_test_func that always allows adding the next node."""
    return next_node not in visited


@pytest.fixture()
def mock_deps():
    """Minimal mocks for db_inspector and mapper (only passed through)."""
    return MagicMock(), MagicMock()


@pytest.fixture()
def linear_graph():
    """
    Three-node linear graph:   jia_ab  --  jia_bc  --  jia_cd

    Each JIA shares one IndexedAttribute (same i, j) with its neighbour,
    which is the connectivity criterion in ConstraintGraph.

      a = IA(0,0,0)   b = IA(1,0,0)   c = IA(2,0,0)   d = IA(3,0,0)
      jia_ab = JIA(a, b)
      jia_bc = JIA(b, c)
      jia_cd = JIA(c, d)
    """
    a, b, c, d = _ia(0, 0, 0), _ia(1, 0, 0), _ia(2, 0, 0), _ia(3, 0, 0)
    jia_ab = _jia(a, b)
    jia_bc = _jia(b, c)
    jia_cd = _jia(c, d)

    cg = ConstraintGraph()
    for jia in (jia_ab, jia_bc, jia_cd):
        cg.add_node(jia)
    # add_edge requires source < target
    cg.add_edge(jia_ab, jia_bc)
    cg.add_edge(jia_bc, jia_cd)

    return cg, jia_ab, jia_bc, jia_cd


@pytest.fixture()
def single_node_graph():
    """Graph with a single isolated node."""
    jia = _jia(_ia(0, 0, 0), _ia(1, 0, 0))
    cg = ConstraintGraph()
    cg.add_node(jia)
    return cg, jia


# ---------------------------------------------------------------------------
# get_traversal_algorithm
# ---------------------------------------------------------------------------


class TestGetTraversalAlgorithm:
    def test_returns_dfs(self):
        assert get_traversal_algorithm("dfs") is dfs

    def test_returns_bfs(self):
        assert get_traversal_algorithm("bfs") is bfs

    def test_returns_astar_variants(self):
        for name in ("astar", "a-star", "a_star", "ASTAR", "A-STAR"):
            assert get_traversal_algorithm(name) is astar

    def test_case_insensitive(self):
        assert get_traversal_algorithm("DFS") is dfs
        assert get_traversal_algorithm("BFS") is bfs

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown traversal algorithm"):
            get_traversal_algorithm("invalid")


# ---------------------------------------------------------------------------
# DFS
# ---------------------------------------------------------------------------


class TestDFS:
    def test_with_explicit_start_node_yields_single_node_rule(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            dfs(
                cg,
                jia_ab,
                _noop_pruning,
                db,
                mapper,
                visited=set(),
                candidate_rule=[],
                next_node_test_func=_always_allow,
            )
        )
        # First yield is [jia_ab]
        assert results[0] == [jia_ab]

    def test_dfs_from_none_visits_all_start_nodes(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(dfs(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow))
        # Every node must appear as the first element of at least one result
        first_nodes = {r[0] for r in results}
        assert first_nodes == {jia_ab, jia_bc, jia_cd}

    def test_dfs_explores_depth(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        # DFS yields a mutable reference; copy each rule as it is emitted.
        results = [
            list(r)
            for r in dfs(
                cg,
                jia_ab,
                _noop_pruning,
                db,
                mapper,
                visited=set(),
                candidate_rule=[],
                next_node_test_func=_always_allow,
            )
        ]
        lengths = {len(r) for r in results}
        # Starting at jia_ab should produce rules of length 1, 2, 3
        assert 1 in lengths
        assert 2 in lengths
        assert 3 in lengths

    def test_dfs_pruning_stops_at_length_1(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            dfs(cg, None, _accept_len_lte(1), db, mapper, next_node_test_func=_always_allow)
        )
        assert all(len(r) == 1 for r in results)

    def test_dfs_reject_all_pruning_yields_nothing(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            dfs(
                cg,
                jia_ab,
                _reject_all,
                db,
                mapper,
                visited=set(),
                candidate_rule=[],
                next_node_test_func=_always_allow,
            )
        )
        assert results == []

    def test_dfs_reject_all_from_none_yields_nothing(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(dfs(cg, None, _reject_all, db, mapper, next_node_test_func=_always_allow))
        assert results == []

    def test_dfs_no_revisit(self, linear_graph, mock_deps):
        """Each node should appear at most once per candidate rule."""
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        for rule in dfs(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow):
            assert len(rule) == len(set(id(n) for n in rule))

    def test_dfs_single_node_graph(self, single_node_graph, mock_deps):
        cg, jia = single_node_graph
        db, mapper = mock_deps
        results = list(dfs(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow))
        assert results == [[jia]]

    def test_dfs_default_visited_and_candidate_rule(self, single_node_graph, mock_deps):
        """Calling dfs without explicit visited/candidate_rule uses defaults."""
        cg, jia = single_node_graph
        db, mapper = mock_deps
        results = list(dfs(cg, jia, _noop_pruning, db, mapper, next_node_test_func=_always_allow))
        assert results == [[jia]]

    def test_dfs_empty_graph_yields_nothing(self, mock_deps):
        db, mapper = mock_deps
        cg = ConstraintGraph()
        results = list(dfs(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow))
        assert results == []


# ---------------------------------------------------------------------------
# BFS
# ---------------------------------------------------------------------------


class TestBFS:
    def test_bfs_from_none_visits_all_start_nodes(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(bfs(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow))
        first_nodes = {r[0] for r in results}
        assert first_nodes == {jia_ab, jia_bc, jia_cd}

    def test_bfs_from_explicit_start_node(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            bfs(cg, jia_ab, _noop_pruning, db, mapper, next_node_test_func=_always_allow)
        )
        assert results[0] == [jia_ab]

    def test_bfs_finds_shorter_rules_first(self, linear_graph, mock_deps):
        """BFS property: shorter rules appear before longer ones per start node."""
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            bfs(cg, jia_ab, _noop_pruning, db, mapper, next_node_test_func=_always_allow)
        )
        lengths = [len(r) for r in results]
        # lengths should be non-decreasing (BFS level order)
        assert lengths == sorted(lengths)

    def test_bfs_pruning_stops_exploration(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            bfs(cg, None, _accept_len_lte(1), db, mapper, next_node_test_func=_always_allow)
        )
        assert all(len(r) == 1 for r in results)

    def test_bfs_reject_all_from_none_yields_nothing(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(bfs(cg, None, _reject_all, db, mapper, next_node_test_func=_always_allow))
        assert results == []

    def test_bfs_reject_all_from_start_yields_nothing(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(bfs(cg, jia_ab, _reject_all, db, mapper, next_node_test_func=_always_allow))
        assert results == []

    def test_bfs_no_revisit(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        for rule in bfs(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow):
            assert len(rule) == len(set(id(n) for n in rule))

    def test_bfs_single_node_graph(self, single_node_graph, mock_deps):
        cg, jia = single_node_graph
        db, mapper = mock_deps
        results = list(bfs(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow))
        assert results == [[jia]]

    def test_bfs_empty_graph_yields_nothing(self, mock_deps):
        db, mapper = mock_deps
        cg = ConstraintGraph()
        results = list(bfs(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow))
        assert results == []


# ---------------------------------------------------------------------------
# A*
# ---------------------------------------------------------------------------


class TestAstar:
    def test_astar_from_none_visits_all_start_nodes(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            astar(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow)
        )
        first_nodes = {r[0] for r in results}
        assert first_nodes == {jia_ab, jia_bc, jia_cd}

    def test_astar_from_explicit_start_node(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            astar(cg, jia_ab, _noop_pruning, db, mapper, next_node_test_func=_always_allow)
        )
        assert results[0] == [jia_ab]

    def test_astar_with_custom_heuristic(self, linear_graph, mock_deps):
        """Custom heuristic is called and influences ordering."""
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        calls = []

        def counting_heuristic(cr, m, db_i):
            calls.append(len(cr))
            return 0.0

        list(
            astar(
                cg,
                None,
                _noop_pruning,
                db,
                mapper,
                next_node_test_func=_always_allow,
                heuristic_func=counting_heuristic,
            )
        )
        assert len(calls) > 0

    def test_astar_default_heuristic(self, linear_graph, mock_deps):
        """No heuristic_func provided — default (length-based) is used."""
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            astar(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow)
        )
        assert len(results) > 0

    def test_astar_pruning_stops_exploration(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            astar(cg, None, _accept_len_lte(1), db, mapper, next_node_test_func=_always_allow)
        )
        assert all(len(r) == 1 for r in results)

    def test_astar_reject_all_from_none_yields_nothing(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(astar(cg, None, _reject_all, db, mapper, next_node_test_func=_always_allow))
        assert results == []

    def test_astar_reject_all_from_start_yields_nothing(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        results = list(
            astar(cg, jia_ab, _reject_all, db, mapper, next_node_test_func=_always_allow)
        )
        assert results == []

    def test_astar_no_revisit(self, linear_graph, mock_deps):
        cg, jia_ab, jia_bc, jia_cd = linear_graph
        db, mapper = mock_deps
        for rule in astar(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow):
            assert len(rule) == len(set(id(n) for n in rule))

    def test_astar_single_node_graph(self, single_node_graph, mock_deps):
        cg, jia = single_node_graph
        db, mapper = mock_deps
        results = list(
            astar(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow)
        )
        assert results == [[jia]]

    def test_astar_empty_graph_yields_nothing(self, mock_deps):
        db, mapper = mock_deps
        cg = ConstraintGraph()
        results = list(
            astar(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow)
        )
        assert results == []


# ---------------------------------------------------------------------------
# Consistency across algorithms
# ---------------------------------------------------------------------------


class TestAlgorithmConsistency:
    """DFS, BFS, and A* on the same graph should yield the same set of rules."""

    def test_all_algorithms_yield_same_rule_sets(self, linear_graph, mock_deps):
        cg, *_ = linear_graph
        db, mapper = mock_deps

        def freeze(results):
            return {frozenset(id(n) for n in r) for r in results}

        # DFS yields a mutable reference — snapshot each rule.
        dfs_rules = freeze(
            [
                list(r)
                for r in dfs(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow)
            ]
        )
        bfs_rules = freeze(
            list(bfs(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow))
        )
        astar_rules = freeze(
            list(astar(cg, None, _noop_pruning, db, mapper, next_node_test_func=_always_allow))
        )
        assert dfs_rules == bfs_rules == astar_rules
