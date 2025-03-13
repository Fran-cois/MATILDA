"""
Algorithme génétique pour la découverte de règles.
"""

import logging
import random
from collections.abc import Callable, Iterator
from tqdm import tqdm

from algorithms.MATILDA.constraint_graph import (
    AttributeMapper,
    ConstraintGraph,
)
from algorithms.MATILDA.discovery_algorithms.common import (
    CandidateRule,
    next_node_test,
    calculate_beam_score
)
from database.alchemy_utility import AlchemyUtility
from algorithms.MATILDA.rule_types.tgd_discovery import (
    extract_table_occurrences,
    split_candidate_rule,
    split_pruning,
    prediction,
    CandidateRuleChains,
    build_minimal_chain
)

def genetic_search(
    cg: ConstraintGraph,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    population_size: int = 50,
    generations: int = 20,
    elite_size: int = 5,
    tournament_size: int = 3,
    crossover_rate: float = 0.8,
    mutation_rate: float = 0.2,
    max_table: int = 3,
    max_vars: int = 6,
) -> Iterator[CandidateRule]:
    """
    Implémente un algorithme génétique pour la découverte de règles.
    
    :param cg: Graphe de contrainte contenant tous les nœuds et arêtes
    :param pruning_prediction: Fonction pour déterminer si une règle doit être élaguée
    :param db_inspector: Inspecteur de base de données pour évaluer les règles
    :param mapper: Mappeur d'attributs
    :param population_size: Taille de la population dans chaque génération
    :param generations: Nombre de générations à faire évoluer
    :param elite_size: Nombre des meilleurs individus à préserver entre les générations
    :param tournament_size: Taille du tournoi pour la sélection des parents
    :param crossover_rate: Probabilité d'occurrence du croisement
    :param mutation_rate: Probabilité d'occurrence de la mutation
    :param max_table: Nombre maximum de tables dans une règle
    :param max_vars: Nombre maximum de variables dans une règle
    :yield: Règles découvertes pendant le processus d'évolution
    """
    logging.info(f"Starting genetic algorithm with population size {population_size}, {generations} generations")
    
    # Initial population generation
    population = initialize_population(
        cg, pruning_prediction, db_inspector, mapper, 
        population_size, max_table, max_vars
    )
    
    best_fitness_history = []
    best_individual_ever = None
    best_fitness_ever = float('-inf')
    
    # Track all individuals yielded to avoid duplicates
    yielded_individuals = set()
    
    for generation in range(generations):
        logging.info(f"Generation {generation + 1}/{generations}")
        
        # Evaluate fitness for current population
        fitness_scores = [
            evaluate_fitness(individual, db_inspector, mapper) 
            for individual in population
        ]
        
        # Track best individual in this generation
        best_idx = fitness_scores.index(max(fitness_scores))
        best_individual = population[best_idx]
        best_fitness = fitness_scores[best_idx]
        best_fitness_history.append(best_fitness)
        
        # Update best individual ever found
        if best_fitness > best_fitness_ever:
            best_fitness_ever = best_fitness
            best_individual_ever = best_individual
            
            # Yield the best individual if not seen before
            if str(best_individual) not in yielded_individuals:
                yielded_individuals.add(str(best_individual))
                yield best_individual
        
        # Select individuals for the next generation
        next_generation = []
        
        # Elitism - keep the best individuals
        sorted_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i], reverse=True)
        elites = [population[i] for i in sorted_indices[:elite_size]]
        next_generation.extend(elites)
        
        # Fill the rest of the population with offspring
        while len(next_generation) < population_size:
            # Tournament selection for parents
            parent1 = tournament_selection(population, fitness_scores, tournament_size)
            parent2 = tournament_selection(population, fitness_scores, tournament_size)
            
            # Apply crossover with probability
            if random.random() < crossover_rate:
                child1, child2 = crossover(
                    parent1, parent2, cg, pruning_prediction, 
                    db_inspector, mapper, max_table, max_vars
                )
                
                # Apply mutation with probability
                if random.random() < mutation_rate:
                    child1 = mutate(child1, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
                if random.random() < mutation_rate:
                    child2 = mutate(child2, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
                
                # Add valid children to next generation
                if child1 and pruning_prediction(child1, mapper, db_inspector) and len(next_generation) < population_size:
                    next_generation.append(child1)
                if child2 and pruning_prediction(child2, mapper, db_inspector) and len(next_generation) < population_size:
                    next_generation.append(child2)
            else:
                # If no crossover, add parents with possible mutation
                if random.random() < mutation_rate:
                    parent1 = mutate(parent1, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
                if len(next_generation) < population_size:
                    next_generation.append(parent1)
        
        # Replace population with new generation
        population = next_generation
        
        # Log progress
        logging.info(f"Generation {generation + 1} complete. Best fitness: {best_fitness}")
    
    # Final yield of best individual ever if not already yielded
    if best_individual_ever and str(best_individual_ever) not in yielded_individuals:
        yield best_individual_ever

def initialize_population(
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    population_size: int,
    max_table: int,
    max_vars: int
) -> list[CandidateRule]:
    """
    Initialize a diverse population of candidate rules.
    
    :param cg: Constraint graph
    :param pruning_prediction: Function to determine if a rule should be pruned
    :param db_inspector: Database inspector
    :param mapper: Attribute mapper
    :param population_size: Size of the population to generate
    :param max_table: Maximum number of tables in a rule
    :param max_vars: Maximum number of variables in a rule
    :return: List of candidate rules forming the initial population
    """
    population = []
    all_nodes = list(cg.nodes)
    
    # Ensure we have enough nodes for initialization
    if not all_nodes:
        logging.warning("No nodes in constraint graph for population initialization")
        return []
    
    attempts = 0
    max_attempts = population_size * 10  # Limit attempts to prevent infinite loops
    
    while len(population) < population_size and attempts < max_attempts:
        attempts += 1
        
        # Start with a random node
        start_node = random.choice(all_nodes)
        if not next_node_test([], start_node, set(), max_table, max_vars):
            continue
        
        # Create a candidate rule of random length
        candidate = [start_node]
        visited = {start_node}
        rule_length = random.randint(1, min(max_vars, 4))  # Random length between 1 and min(max_vars, 4)
        
        # Try to grow the rule to the desired length
        for _ in range(rule_length - 1):
            # Find viable neighbors for current nodes in the candidate
            neighbors = []
            for node in candidate:
                for neighbor in cg.neighbors(node):
                    if neighbor not in visited and next_node_test(candidate, neighbor, visited, max_table, max_vars):
                        neighbors.append(neighbor)
            
            if not neighbors:
                break  # No valid neighbors to add
                
            # Add a random viable neighbor
            next_node = random.choice(neighbors)
            candidate.append(next_node)
            visited.add(next_node)
        
        # Check if the candidate passes pruning
        if candidate and len(candidate) > 0 and pruning_prediction(candidate, mapper, db_inspector):
            # Avoid duplicates
            if not any(str(existing) == str(candidate) for existing in population):
                population.append(candidate)
    
    logging.info(f"Initialized population with {len(population)} individuals after {attempts} attempts")
    return population

def evaluate_fitness(
    candidate: CandidateRule,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper
) -> float:
    """
    Evaluate the fitness of a candidate rule based on its best split.
    
    :param candidate: Candidate rule to evaluate
    :param db_inspector: Database inspector
    :param mapper: Attribute mapper
    :return: Fitness score, higher is better
    """
    if not candidate:
        return 0.0
    
    # Use the existing beam score calculation which considers support and confidence
    score = calculate_beam_score(candidate, mapper, db_inspector)
    
    # Additional factors for fitness:
    # - Rule length penalty to prefer simpler rules
    # - Coverage bonus to prefer rules that cover more data
    length_penalty = 0.05 * len(candidate)
    
    # Calculate coverage for the best split
    coverage = 0.0
    splits = split_candidate_rule(candidate)
    if splits:
        try:
            for split in splits:
                body, head = split
                if not body or not head:
                    continue
                
                valid, support, confidence = split_pruning(candidate, body, head, db_inspector, mapper)
                if valid:
                    # Get total tuples in the join
                    join_coverage = prediction(candidate, mapper, db_inspector)
                    if join_coverage > 0:
                        # Coverage is normalized by total database size (approximation)
                        coverage = max(coverage, join_coverage / 1000.0)  # Normalize by an approximate database size
        except Exception as e:
            logging.error(f"Error calculating coverage for fitness: {e}")
    
    # Final fitness score
    fitness = score - length_penalty + (0.2 * coverage)
    return max(0.0, fitness)  # Ensure non-negative fitness

def tournament_selection(
    population: list[CandidateRule],
    fitness_scores: list[float],
    tournament_size: int
) -> CandidateRule:
    """
    Select an individual using tournament selection.
    
    :param population: Current population of candidate rules
    :param fitness_scores: List of fitness scores corresponding to population
    :param tournament_size: Number of individuals in each tournament
    :return: Selected individual
    """
    # Select tournament_size random individuals
    tournament_indices = random.sample(range(len(population)), min(tournament_size, len(population)))
    
    # Find the best individual in the tournament
    best_idx = tournament_indices[0]
    for idx in tournament_indices:
        if fitness_scores[idx] > fitness_scores[best_idx]:
            best_idx = idx
    
    return population[best_idx]

def crossover(
    parent1: CandidateRule,
    parent2: CandidateRule,
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int,
    max_vars: int
) -> tuple[CandidateRule, CandidateRule]:
    """
    Perform crossover between two parent rules.
    
    :param parent1: First parent rule
    :param parent2: Second parent rule
    :param cg: Constraint graph
    :param pruning_prediction: Function to determine if a rule should be pruned
    :param db_inspector: Database inspector
    :param mapper: Attribute mapper
    :param max_table: Maximum number of tables in a rule
    :param max_vars: Maximum number of variables in a rule
    :return: Two child rules created through crossover
    """
    if not parent1 or not parent2:
        return parent1, parent2
    
    # Choose random crossover points
    point1 = random.randint(0, len(parent1))
    point2 = random.randint(0, len(parent2))
    
    # Create children by combining segments
    child1_candidate = parent1[:point1] + parent2[point2:]
    child2_candidate = parent2[:point2] + parent1[point1:]
    
    # Validate and return children
    child1 = validate_rule(child1_candidate, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
    child2 = validate_rule(child2_candidate, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
    
    return child1, child2

def mutate(
    rule: CandidateRule,
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int,
    max_vars: int
) -> CandidateRule:
    """
    Apply mutation to a rule.
    
    :param rule: Rule to mutate
    :param cg: Constraint graph
    :param pruning_prediction: Function to determine if a rule should be pruned
    :param db_inspector: Database inspector
    :param mapper: Attribute mapper
    :param max_table: Maximum number of tables in a rule
    :param max_vars: Maximum number of variables in a rule
    :return: Mutated rule
    """
    if not rule:
        return rule
    
    # Choose mutation type randomly
    mutation_type = random.choice(["add", "remove", "replace"])
    
    if mutation_type == "add" and len(rule) < max_vars:
        # Add a new node
        neighbors = set()
        for node in rule:
            for neighbor in cg.neighbors(node):
                if neighbor not in rule:
                    neighbors.add(neighbor)
        
        if neighbors:
            neighbor = random.choice(list(neighbors))
            if next_node_test(rule, neighbor, set(rule), max_table, max_vars):
                mutated = rule + [neighbor]
                return validate_rule(mutated, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
    
    elif mutation_type == "remove" and len(rule) > 1:
        # Remove a random node
        remove_idx = random.randint(0, len(rule) - 1)
        mutated = rule[:remove_idx] + rule[remove_idx + 1:]
        return validate_rule(mutated, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
    
    elif mutation_type == "replace" and len(rule) > 0:
        # Replace a node with a new one
        replace_idx = random.randint(0, len(rule) - 1)
        
        # Get neighbors for all other nodes
        neighbors = set()
        for i, node in enumerate(rule):
            if i != replace_idx:
                for neighbor in cg.neighbors(node):
                    if neighbor not in rule:
                        neighbors.add(neighbor)
        
        if neighbors:
            new_node = random.choice(list(neighbors))
            mutated = rule.copy()
            mutated[replace_idx] = new_node
            return validate_rule(mutated, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
    
    # If mutation failed or wasn't possible, return original rule
    return rule

def validate_rule(
    rule: CandidateRule,
    cg: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int,
    max_vars: int
) -> CandidateRule:
    """
    Validate a candidate rule and repair if necessary.
    
    :param rule: Rule to validate
    :param cg: Constraint graph
    :param pruning_prediction: Function to determine if a rule should be pruned
    :param db_inspector: Database inspector
    :param mapper: Attribute mapper
    :param max_table: Maximum number of tables in a rule
    :param max_vars: Maximum number of variables in a rule
    :return: Validated rule or None if invalid and unrepairable
    """
    # Check for empty rule
    if not rule or len(rule) == 0:
        return None
    
    # Check for duplicates in the rule
    unique_nodes = []
    for node in rule:
        if node not in unique_nodes:
            unique_nodes.append(node)
    
    if len(unique_nodes) != len(rule):
        rule = unique_nodes
    
    # Check table occurrence limits
    if not check_table_occurrences_limit(rule, max_table):
        return None
    
    # Check variable limit
    if len(rule) > max_vars:
        rule = rule[:max_vars]  # Trim to max vars
    
    # Check if rule passes pruning
    if not pruning_prediction(rule, mapper, db_inspector):
        return None
    
    # Check if rule is minimal
    if not is_rule_minimal(rule):
        # Try to repair by finding a minimal equivalent
        minimal_rule = create_minimal_rule(rule, cg)
        if minimal_rule and pruning_prediction(minimal_rule, mapper, db_inspector):
            return minimal_rule
        return None
    
    return rule

def check_table_occurrences_limit(rule: CandidateRule, max_table: int) -> bool:
    """
    Check if a rule satisfies the maximum table occurrence limit.
    
    :param rule: Rule to check
    :param max_table: Maximum number of tables allowed
    :return: True if rule satisfies the limit, False otherwise
    """
    table_occurrences = extract_table_occurrences(rule)
    unique_tables = {occurrence[0] for occurrence in table_occurrences}
    return len(unique_tables) <= max_table

def is_rule_minimal(rule: CandidateRule) -> bool:
    """
    Check if a rule is minimal (cannot be made smaller while preserving its meaning).
    
    :param rule: Rule to check
    :return: True if rule is minimal, False otherwise
    """
    cr_chains = CandidateRuleChains(rule).cr_chains
    min_candidate_rule = []
    
    for chain in cr_chains:
        for jia in build_minimal_chain(chain):
            min_candidate_rule.append(jia)
    
    # Compare if current rule equals the minimal version
    return sorted(str(jia) for jia in rule) == sorted(str(jia) for jia in min_candidate_rule)

def create_minimal_rule(rule: CandidateRule, cg: ConstraintGraph) -> CandidateRule:
    """
    Create a minimal version of the rule.
    
    :param rule: Rule to minimize
    :param cg: Constraint graph
    :return: Minimal version of the rule or None if not possible
    """
    cr_chains = CandidateRuleChains(rule).cr_chains
    min_candidate_rule = []
    
    for chain in cr_chains:
        for jia in build_minimal_chain(chain):
            # Check if jia exists in constraint graph
            if jia in cg.nodes:
                min_candidate_rule.append(jia)
    
    return min_candidate_rule if min_candidate_rule else None