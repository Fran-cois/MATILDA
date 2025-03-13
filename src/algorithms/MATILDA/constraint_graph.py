from database.alchemy_utility import AlchemyUtility
# import networkx as nx
# import numpy as np
from algorithms.MATILDA.compatibility_checker import CompatibilityChecker


class Attribute:
    def __init__(
            self,
            table: str,
            name: str,
            is_key: bool = False,
            domain: str = None,
    ):
        """
        Initialize an Attribute with table and attribute name.
        """

        self.table = table
        self.name = name
        self.domain = domain
        self.is_key = is_key

    def is_compatible(
            self,
            other_attribute: "Attribute",
            threshold_jaccard=0.05,
            threshold_overlap=10,
            domain_overlap: bool = True,
            value_overlap: bool = True,
            user_defined_rules: dict[tuple[tuple[str, str, str, str], bool]] = None,
            database_constraints: bool = True,
            db_inspector: AlchemyUtility = None,
    ):
        """
        Determine if two attributes are compatible. Use to generate a list of JoinableIndexedAttributes.

        :param other_attribute: Second attribute
        :param threshold_jaccard: Threshold for Jaccard similarity
        :param threshold_overlap: Threshold for value overlap
        :param domain_overlap: Flag indicating if domain overlap should be considered
        :param value_overlap: Flag indicating if value overlap should be considered
        :param user_defined_rules: User specified compatibility rules
        :param database_constraints: Use Database constraints like foreign keys
        :param db_inspector: Database inspector utility
        :return: Boolean indicating compatibility
        """
        # Check if attributes are from the same table
        if self.table == other_attribute.table:
            return True
            
        # Check if db_inspector is provided
        if db_inspector is None:
            return False
            
        # Create a CompatibilityChecker instance
        checker = CompatibilityChecker(
            engine=db_inspector.engine,
            metadata=db_inspector.metadata
        )
        
        # Determine the compatibility mode based on parameters
        mode = CompatibilityChecker.MODE_HYBRID
        
        if database_constraints and not value_overlap:
            # Only use foreign keys
            mode = CompatibilityChecker.MODE_FK
        elif database_constraints and value_overlap:
            # Use both foreign keys and overlap
            mode = CompatibilityChecker.MODE_HYBRID
        elif not database_constraints and value_overlap:
            # Only check value overlap
            mode = CompatibilityChecker.MODE_OVERLAP
        
        # Check if the domain constraint is satisfied
        if domain_overlap and self.domain and other_attribute.domain and self.domain != other_attribute.domain:
            return False
        
        # First check using compatibility mode
        if checker.is_compatible(
            table1=self.table,
            column1=self.name,
            table2=other_attribute.table,
            column2=other_attribute.name,
            mode=mode,
            sample_size=threshold_overlap
        ):
            return True
            
        # If not compatible by mode but value_overlap is requested, try specific overlap checks
        if value_overlap:
            # Check for common elements above threshold
            if checker.check_common_elements_above_threshold(
                self.table, self.name, 
                other_attribute.table, other_attribute.name,
                threshold_overlap
            ):
                return True
                
            # Check for Jaccard similarity
            if checker.check_jaccard_similarity_above_threshold(
                self.table, self.name,
                other_attribute.table, other_attribute.name,
                threshold_jaccard
            ):
                return True
                
        return False

    @classmethod
    def generate_attributes(cls, db_inspector: AlchemyUtility) -> list["Attribute"]:
        """
        Generate all attributes in the database.
        """
        table_names = db_inspector.get_table_names()
        attributes = []
        for table_name in table_names:
            attribute_names = db_inspector.get_attribute_names(table_name)
            for attribute_name in attribute_names:
                domain = db_inspector.get_attribute_domain(table_name, attribute_name)
                is_key = db_inspector.get_attribute_is_key(table_name, attribute_name)
                attribute = cls(
                    table_name,
                    attribute_name,
                    is_key,
                    domain,
                )
                attributes.append(attribute)
        return attributes


class IndexedAttribute:
    def __init__(self, i: int, j: int, k: int):
        """
        Initialize an IndexedAttribute with table index i, table occurrence j, and attribute index k.
        """
        if not all(isinstance(x, int) and x >= 0 for x in [i, j, k]):
            raise ValueError("All parameters must be non-negative integers")

        self.i = i
        self.j = j
        self.k = k

    def __eq__(self, other: "IndexedAttribute") -> bool:
        """
        Check if two indexed attributes are equal.
        """
        if not isinstance(other, IndexedAttribute):
            return NotImplemented
        return self.i == other.i and self.j == other.j and self.k == other.k

    def __lt__(self, other: "IndexedAttribute") -> bool:
        """
        Implement the total order between two indexed attributes.
        """
        if not isinstance(other, IndexedAttribute):
            return NotImplemented
        if self.i < other.i:
            return True
        if self.i == other.i and self.j < other.j:
            return True
        if self.i == other.i and self.j == other.j and self.k < other.k:
            return True
        return False

    def __le__(self, other: "IndexedAttribute") -> bool:
        """
        Check if an indexed attribute is less than or equal to another.
        """
        return self < other or self == other

    def __repr__(self) -> str:
        """
        String representation of the indexed attribute.
        """
        return f"(i={self.i}, j={self.j}, k={self.k})"

    def __hash__(self) -> int:
        """
        Generate a hash value for an indexed attribute.
        """
        return hash((self.i, self.j, self.k))

    def is_connected(self, other: "IndexedAttribute") -> bool:
        """
        Check if two indexed attributes are connected.
        """
        if not isinstance(other, IndexedAttribute):
            return NotImplemented
        return self.i == other.i and self.j == other.j


class AttributeMapper:
    def __init__(
            self,
            table_name_to_index: dict[str, int],
            attribute_name_to_index: dict[str, dict[str, int]],
    ):
        """
        Initialize the mapper with dictionaries mapping table names to indices and attribute names to indices.
        """
        self.table_name_to_index = table_name_to_index
        self.attribute_name_to_index = attribute_name_to_index
        # create reverse mappings
        self.index_to_table_name: dict[int, str] = {
            v: k for k, v in table_name_to_index.items()
        }
        self.index_to_attribute_name: dict[tuple[int, int], str] = {
            (table_name_to_index[table], v): k
            for table, attributes in attribute_name_to_index.items()
            for k, v in attributes.items()
        }

    def indexed_attribute_to_attribute(
            self, indexed_attribute: IndexedAttribute
    ) -> Attribute:
        """
        Convert an IndexedAttribute to an Attribute.
        """
        attribute = self.index_to_attribute_name[
            (indexed_attribute.i, indexed_attribute.k)
        ]
        table = self.index_to_table_name[indexed_attribute.i]
        return Attribute(table, attribute)

    def attribute_to_indexed(
            self, attribute: Attribute, table_occurrence: int
    ) -> IndexedAttribute:
        """
        Convert an Attribute to an IndexedAttribute.
        """
        return IndexedAttribute(
            self.table_name_to_index[attribute.table],
            table_occurrence,
            self.attribute_name_to_index[attribute.table][attribute.name],
        )



class JoinableIndexedAttributes:
    def __init__(
            self,
            attr1: IndexedAttribute,
            attr2: IndexedAttribute,
    ):
        self.pair = (attr1, attr2) if attr1 < attr2 else (attr2, attr1)

    def __hash__(self):
        return hash(self.pair)

    def __eq__(self, other: "JoinableIndexedAttributes") -> bool:
        if not isinstance(other, JoinableIndexedAttributes):
            return NotImplemented
        return self.pair == other.pair

    def __lt__(self, other: "JoinableIndexedAttributes") -> bool:
        if not isinstance(other, JoinableIndexedAttributes):
            return NotImplemented
        attr1, attr2 = self.pair
        attr1_other, attr2_other = other.pair

        if attr1 < attr1_other:
            return True
        if attr1 == attr1_other and attr2 < attr2_other:
            return True
        return False

    def __le__(self, other: "JoinableIndexedAttributes") -> bool:
        return self < other or self == other

    def __repr__(self) -> str:
        return f"JIA{self.pair}"

    def __hash__(self) -> int:
        return hash(self.pair)

    def is_connected(self, other: "JoinableIndexedAttributes") -> bool:
        if not isinstance(other, JoinableIndexedAttributes):
            return NotImplemented
        attr1, attr2 = self.pair
        attr1_other, attr2_other = other.pair

        return (
                attr1.is_connected(attr1_other)
                or attr1.is_connected(attr2_other)
                or attr2.is_connected(attr1_other)
                or attr2.is_connected(attr2_other)
        )

    def __iter__(self):
        """
        Make the class iterable, allowing it to be unpacked or iterated over in a for loop.
        """
        return iter(self.pair)


class ConstraintGraph:
    def __init__(self):
        """
        Initialize a ConstraintGraph with an empty set of nodes and edges.
        """
        self.nodes: set[JoinableIndexedAttributes] = (
            set()
        )  # Set of JoinableIndexedAttributes instances
        self.edges: dict[
            JoinableIndexedAttributes,
            set[JoinableIndexedAttributes],
        ] = {}  # Dictionary mapping a node to its connected nodes

    @classmethod
    def from_jia_list(
            cls, jia_list: list[JoinableIndexedAttributes]
    ) -> "ConstraintGraph":
        instance = cls()
        for jia in jia_list:
            instance.add_node(jia)
            for i, jia in enumerate(jia_list):
                for jia2 in jia_list[i + 1:]:
                    if jia != jia2 and jia.is_connected(jia2):
                        instance.add_node(jia2)
                        instance.add_edge(jia, jia2)
        # Add edges based on your logic
        return instance

    def add_node(self, compatible_pair: JoinableIndexedAttributes):
        """
        Add a node to the graph if it is not already present.

        :param compatible_pair: A JoinableIndexedAttributes instance representing a node
        """
        self.nodes.add(compatible_pair)

    def add_edge(
            self,
            source: JoinableIndexedAttributes,
            target: JoinableIndexedAttributes,
    ):
        """
        Add a directed edge from source to target if both nodes are in the graph
        and the edge does not introduce a cycle.

        :param source: The source node
        :param target: The target node
        """
        if source in self.nodes and target in self.nodes:
            if source > target:
                raise Exception(
                    "Source node must be less than target node. We should not have this case."
                )
            if source not in self.edges:
                self.edges[source] = set()
            self.edges[source].add(target)

    def is_connected(
            self,
            source: JoinableIndexedAttributes,
            target: JoinableIndexedAttributes,
    ) -> bool:
        """
        Determine if two nodes are directly connected in the graph.

        :param source: The source node
        :param target: The target node
        :return: True if there is a direct edge from source to target, False otherwise
        """
        if source in self.edges:
            return target in self.edges[source]
        return False

    def __repr__(self) -> str:  # pragma: no cover
        """
        String representation of the ConstraintGraph.
        """
        edges_repr = [
            f"{source} -> {target}"
            for source, targets in self.edges.items()
            for target in targets
        ]
        return (
                f"ConstraintGraph(Nodes: {len(self.nodes)}, Edges: {len(edges_repr)})\n"
                + "\n".join(edges_repr)
        )

    def neighbors(self, node):
        """
        Get the neighbors of a node in the graph.

        :param node: The node for which to get the neighbors.
        :return: A set of nodes that are neighbors of the given node.
        """
        return sorted(self.edges.get(node, set()))
        # return self.edges.get(node, set())

    def compute_metrics(self):
        # Convert the ConstraintGraph to a networkx graph
        G = nx.DiGraph()
        for node in self.nodes:
            G.add_node(node)
        for source, targets in self.edges.items():
            for target in targets:
                G.add_edge(source, target)

        # Convert the directed graph to an undirected graph
        G = G.to_undirected()
        if G.number_of_nodes() == 0 or G.number_of_edges() == 0:
            print("The graph is empty. Cannot compute metrics.")
            return
        # Compute the metrics
        self.metrics = self.compute_graph_metrics(G)
        # Output the metrics to a JSON file
        return self.metrics

    def compute_graph_metrics(self, graph):

        metrics = {}

        # Diameter and Average Path Length
        if nx.is_connected(graph):
            metrics['diameter'] = nx.diameter(graph)
            metrics['average_path_length'] = nx.average_shortest_path_length(graph)
        else:
            metrics['diameter'] = float('inf')  # Undefined for disconnected graphs
            metrics['average_path_length'] = float('inf')  # Undefined for disconnected graphs

        # Clustering Coefficient
        metrics['global_clustering_coefficient'] = nx.transitivity(graph)
        metrics['average_clustering_coefficient'] = nx.average_clustering(graph)

        # Connected Components
        components = list(nx.connected_components(graph))
        metrics['number_of_connected_components'] = len(components)
        metrics['size_of_largest_connected_component'] = len(max(components, key=len))

        # Betweenness Centrality
        betweenness = nx.betweenness_centrality(graph)
        metrics['average_betweenness_centrality'] = np.mean(list(betweenness.values()))

        # Degree Distribution
        degrees = [degree for node, degree in graph.degree()]
        metrics['degree_distribution'] = degrees

        # Eigenvector Centrality
        eigenvector_centrality = nx.eigenvector_centrality(graph)
        metrics['average_eigenvector_centrality'] = np.mean(list(eigenvector_centrality.values()))

        # Assortativity
        metrics['assortativity'] = nx.degree_assortativity_coefficient(graph)

        # Graph Density
        metrics['density'] = nx.density(graph)

        # Spectral Properties
        laplacian = nx.laplacian_matrix(graph).todense()
        eigenvalues = np.linalg.eigvals(laplacian)
        eigenvalues.sort()
        metrics['algebraic_connectivity'] = eigenvalues[1] if len(eigenvalues) > 1 else 0
        adjacency_matrix = nx.adjacency_matrix(graph).todense()
        adjacency_eigenvalues = np.linalg.eigvals(adjacency_matrix)
        adjacency_eigenvalues.sort()
        # metrics['spectral_gap'] = adjacency_eigenvalues[-1] - adjacency_eigenvalues[-2] if len(
        # adjacency_eigenvalues) > 1 else 0
        metrics['number_of_nodes'] = graph.number_of_nodes()
        metrics['number_of_edges'] = graph.number_of_edges()

        # Modularity (requires community detection)
        try:
            from community import community_louvain
            partition = community_louvain.best_partition(graph)
            metrics['modularity'] = community_louvain.modularity(partition, graph)
        except ImportError:
            metrics['modularity'] = 'community-louvain not installed'

        return metrics
