"""
Algorithme de recherche en faisceau (Beam Search) pour la découverte de règles.
"""

import logging
from collections.abc import Callable, Iterator
from tqdm import tqdm

from algorithms.MATILDA.constraint_graph import (
    AttributeMapper,
    ConstraintGraph,
    JoinableIndexedAttributes,
)
from algorithms.MATILDA.discovery_algorithms.common import (
    CandidateRule,
    calculate_beam_score,
    next_node_test
)
from database.alchemy_utility import AlchemyUtility

def beam_search(
    cg: ConstraintGraph,
    start_node: JoinableIndexedAttributes,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    beam_width: int = 10,
    max_table: int = 3,
    max_vars: int = 6,
) -> Iterator[CandidateRule]:
    """
    Effectue une recherche en faisceau (Beam Search), en gardant les B meilleures règles candidates à chaque étape.
    
    :param cg: Une instance de la classe ConstraintGraph.
    :param start_node: Le nœud à partir duquel commence la recherche en faisceau, ou None pour commencer à partir de tous les nœuds.
    :param pruning_prediction: Une fonction qui prend une règle candidate et décide s'il faut l'élaguer.
    :param db_inspector: Une instance d'AlchemyUtility pour l'inspection de la base de données.
    :param mapper: Une instance d'AttributeMapper pour la correspondance des attributs.
    :param beam_width: Le nombre maximum de candidats à conserver à chaque étape (B).
    :param max_table: Nombre maximum de tables autorisées dans une règle candidate.
    :param max_vars: Nombre maximum de variables autorisées dans une règle candidate.
    :yield: Règles candidates par ordre décroissant de qualité.
    """
    # Initialize beam
    beam = []
    visited_rules = set()
    
    # Start either from a specific node or consider all nodes as starting points
    if start_node is not None:
        initial_candidates = [([start_node], {start_node})]
    else:
        logging.info(f"Starting beam search with beam width: {beam_width}")
        initial_candidates = []
        for node in tqdm(cg.nodes, desc="Initializing beam with nodes"):
            if next_node_test([], node, set(), max_table, max_vars):
                initial_candidates.append(([node], {node}))
    
    for candidate, candidate_visited in initial_candidates:
        if pruning_prediction(candidate, mapper, db_inspector):
            # Score the candidate rule
            score = calculate_beam_score(candidate, mapper, db_inspector)
            beam.append((score, candidate, candidate_visited))
    
    # Sort and trim beam to top B candidates
    beam.sort(reverse=True)
    beam = beam[:beam_width]
    
    # Yield initial promising candidates
    for score, candidate, _ in beam:
        candidate_key = str(candidate)
        if candidate_key not in visited_rules:
            visited_rules.add(candidate_key)
            yield candidate
    
    # Continue refining until beam is empty or no more refinements can be made
    iteration = 0
    while beam:
        iteration += 1
        logging.info(f"Beam search iteration {iteration}, candidates: {len(beam)}")
        new_beam = []
        
        # Generate all possible refinements of candidates in the beam
        for score, candidate, candidate_visited in tqdm(beam, desc=f"Processing beam (width={len(beam)})"):
            # Find all viable neighbors for each node in the candidate
            neighbors = set()
            for node in candidate:
                for neighbor in cg.neighbors(node):
                    if neighbor not in candidate_visited:
                        neighbors.add(neighbor)
            
            # Try extending the candidate with each viable neighbor
            for node in neighbors:
                if next_node_test(candidate, node, candidate_visited, max_table, max_vars):
                    new_candidate = candidate + [node]
                    new_visited = candidate_visited.union({node})
                    
                    if pruning_prediction(new_candidate, mapper, db_inspector):
                        score = calculate_beam_score(new_candidate, mapper, db_inspector)
                        new_beam.append((score, new_candidate, new_visited))
        
        # Sort and trim the new beam to top B candidates
        new_beam.sort(reverse=True)
        new_beam = new_beam[:beam_width]
        
        # Update beam and yield new candidates
        beam = new_beam
        for score, candidate, _ in beam:
            candidate_key = str(candidate)
            if candidate_key not in visited_rules:
                visited_rules.add(candidate_key)
                yield candidate
        
        if not new_beam:
            logging.info("No more refinements found, ending beam search")
            break
