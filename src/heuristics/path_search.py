"""
Heuristics for MATILDA path search optimization.

This module provides heuristic functions for A-star search in constraint graph traversal.
Heuristics guide the search toward high-quality rules faster by estimating the promise of 
candidate rules based on database statistics.
"""

from typing import Tuple
from algorithms.MATILDA.constraint_graph import AttributeMapper, JoinableIndexedAttributes
from database.alchemy_utility import AlchemyUtility


CandidateRule = list[JoinableIndexedAttributes]


class PathSearchHeuristics:
    """
    Collection of heuristic functions for optimizing path search in MATILDA.
    
    Each heuristic estimates the "promise" of a candidate rule to guide the search
    toward higher-quality rules faster. Lower scores indicate more promising candidates.
    """
    
    def __init__(self, db_inspector: AlchemyUtility, mapper: AttributeMapper):
        """
        Initialize heuristics with database inspector and attribute mapper.
        
        :param db_inspector: Database inspector for querying database statistics.
        :param mapper: Attribute mapper for resolving indexed attributes.
        """
        self.db_inspector = db_inspector
        self.mapper = mapper
        self._table_sizes = {}
        self._cache_table_sizes()
    
    def _cache_table_sizes(self):
        """Cache table sizes for faster lookups."""
        try:
            tables = self.db_inspector.get_tables()
            for table in tables:
                count = self.db_inspector.execute_query(f"SELECT COUNT(*) as cnt FROM {table}")
                if count:
                    self._table_sizes[table] = count[0]['cnt']
        except Exception as e:
            print(f"Warning: Could not cache table sizes: {e}")
    
    def naive_heuristic(self, candidate_rule: CandidateRule, mapper: AttributeMapper, 
                        db_inspector: AlchemyUtility) -> float:
        """
        Naive heuristic: prefer shorter rules (fewer tables).
        
        This is the simplest heuristic that guides search toward simpler rules first.
        
        :param candidate_rule: Current candidate rule (path of JoinableIndexedAttributes).
        :param mapper: Attribute mapper (unused in naive version).
        :param db_inspector: Database inspector (unused in naive version).
        :return: Cost estimate (number of unique tables in the rule).
        """
        # Count unique tables in the rule
        tables = set()
        for jia in candidate_rule:
            for attr in jia:
                tables.add((attr.i, attr.j))  # (table_index, occurrence)
        return float(len(tables))
    
    def table_size_heuristic(self, candidate_rule: CandidateRule, mapper: AttributeMapper, 
                             db_inspector: AlchemyUtility) -> float:
        """
        Table size heuristic: prefer rules with smaller tables (faster to query).
        
        This heuristic estimates computational cost by favoring rules involving
        smaller tables, which are generally faster to evaluate.
        
        :param candidate_rule: Current candidate rule.
        :param mapper: Attribute mapper for resolving table names.
        :param db_inspector: Database inspector for table statistics.
        :return: Cost estimate based on total table sizes involved.
        """
        total_size = 0.0
        tables = set()
        
        for jia in candidate_rule:
            for attr in jia:
                table_key = (attr.i, attr.j)
                if table_key not in tables:
                    tables.add(table_key)
                    # Get actual table name from mapper
                    table_name = self._get_table_name(attr, mapper)
                    if table_name in self._table_sizes:
                        total_size += self._table_sizes[table_name]
                    else:
                        # Default penalty if size unknown
                        total_size += 1000
        
        # Normalize by number of tables to avoid biasing toward fewer tables
        num_tables = len(tables) if tables else 1
        return total_size / num_tables
    
    def join_selectivity_heuristic(self, candidate_rule: CandidateRule, mapper: AttributeMapper,
                                   db_inspector: AlchemyUtility) -> float:
        """
        Join selectivity heuristic: estimate result size after joins.
        
        This heuristic estimates the intermediate result size based on join selectivity.
        Rules with lower intermediate sizes are generally faster to evaluate.
        
        :param candidate_rule: Current candidate rule.
        :param mapper: Attribute mapper for resolving attributes.
        :param db_inspector: Database inspector for cardinality estimation.
        :return: Estimated cost based on join selectivity.
        """
        if not candidate_rule:
            return 0.0
        
        # Estimate result cardinality after all joins
        # Start with size of first table
        first_attr = candidate_rule[0][0] if candidate_rule[0] else None
        if not first_attr:
            return float('inf')
        
        first_table = self._get_table_name(first_attr, mapper)
        result_size = self._table_sizes.get(first_table, 1000)
        
        # Apply join selectivity for each additional table
        # Typical join selectivity is 0.1 (10% of Cartesian product remains)
        for i in range(1, len(candidate_rule)):
            join_selectivity = 0.1  # Conservative estimate
            for attr in candidate_rule[i]:
                table_name = self._get_table_name(attr, mapper)
                table_size = self._table_sizes.get(table_name, 1000)
                result_size = result_size * table_size * join_selectivity
        
        return result_size
    
    def hybrid_heuristic(self, candidate_rule: CandidateRule, mapper: AttributeMapper,
                        db_inspector: AlchemyUtility) -> float:
        """
        Hybrid heuristic: combines multiple factors for balanced search.
        
        This heuristic combines:
        1. Rule complexity (number of tables)
        2. Table sizes (computational cost)
        3. Join selectivity (intermediate result size)
        
        :param candidate_rule: Current candidate rule.
        :param mapper: Attribute mapper for resolving attributes.
        :param db_inspector: Database inspector for statistics.
        :return: Weighted cost estimate combining multiple factors.
        """
        # Weights for different components (tunable)
        w_complexity = 0.3
        w_table_size = 0.4
        w_selectivity = 0.3
        
        complexity_cost = self.naive_heuristic(candidate_rule, mapper, db_inspector)
        table_size_cost = self.table_size_heuristic(candidate_rule, mapper, db_inspector)
        selectivity_cost = self.join_selectivity_heuristic(candidate_rule, mapper, db_inspector)
        
        # Normalize costs to [0, 1] range for fair weighting
        # Use log scaling for selectivity due to exponential growth
        import math
        selectivity_cost_normalized = math.log10(max(selectivity_cost, 1))
        
        total_cost = (
            w_complexity * complexity_cost +
            w_table_size * (table_size_cost / 10000) +  # Normalize table sizes
            w_selectivity * (selectivity_cost_normalized / 10)  # Normalize selectivity
        )
        
        return total_cost
    
    def _get_table_name(self, attr, mapper: AttributeMapper) -> str:
        """
        Helper to get table name from indexed attribute.
        
        :param attr: IndexedAttribute object.
        :param mapper: Attribute mapper.
        :return: Table name as string.
        """
        try:
            # Get table name from mapper
            table_idx = attr.i
            if table_idx < len(mapper.tables):
                return mapper.tables[table_idx]
            return f"table_{table_idx}"
        except Exception:
            return f"table_{getattr(attr, 'i', 0)}"
    
    def get_heuristic_function(self, name: str = 'hybrid'):
        """
        Get a heuristic function by name.
        
        :param name: Name of the heuristic ('naive', 'table_size', 'join_selectivity', 'hybrid').
        :return: Heuristic function that can be passed to A-star.
        """
        heuristics = {
            'naive': self.naive_heuristic,
            'table_size': self.table_size_heuristic,
            'join_selectivity': self.join_selectivity_heuristic,
            'hybrid': self.hybrid_heuristic,
        }
        return heuristics.get(name.lower(), self.hybrid_heuristic)


def create_heuristic(db_inspector: AlchemyUtility, mapper: AttributeMapper, 
                     heuristic_name: str = 'hybrid'):
    """
    Factory function to create a heuristic function.
    
    :param db_inspector: Database inspector instance.
    :param mapper: Attribute mapper instance.
    :param heuristic_name: Name of heuristic to create.
    :return: Heuristic function ready to be used with A-star.
    """
    heuristics = PathSearchHeuristics(db_inspector, mapper)
    return heuristics.get_heuristic_function(heuristic_name)
