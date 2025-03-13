"""
Algorithme hybride combinant algorithmes génétiques et recherche locale.

Cette approche utilise des stratégies évolutionnaires pour explorer globalement
l'espace des règles, puis affine les meilleurs candidats avec une recherche 
best-first locale pour maximiser leur qualité.
"""

import logging
import random
import copy
import heapq
from collections.abc import Callable, Iterator
from typing import List, Set, Dict, Tuple
from tqdm import tqdm
from queue import PriorityQueue

from algorithms.MATILDA.constraint_graph import (
    AttributeMapper, 
    ConstraintGraph,
    JoinableIndexedAttributes
)
from algorithms.MATILDA.discovery_algorithms.common import (
    CandidateRule,
    next_node_test,
    calculate_beam_score, 
    PrioritizedRule
)
from algorithms.MATILDA.discovery_algorithms.genetic_search import (
    initialize_population,
    evaluate_fitness,
    tournament_selection,
    crossover,
    mutate
)
from database.alchemy_utility import AlchemyUtility
from algorithms.MATILDA.rule_types.tgd_discovery import (
    extract_table_occurrences,
    split_candidate_rule, 
    split_pruning,
    prediction
)


def genetic_local_search(
    cg: ConstraintGraph,
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    population_size: int = 40,
    generations: int = 15,
    elite_size: int = 5,
    tournament_size: int = 3,
    crossover_rate: float = 0.8,
    mutation_rate: float = 0.2,
    local_search_depth: int = 3,
    local_search_candidates: int = 3,
    refinement_iterations: int = 2,
    max_table: int = 3,
    max_vars: int = 6,
) -> Iterator[CandidateRule]:
    """
    Algorithme combinant algorithmes génétiques pour l'exploration globale avec une recherche locale
    pour affiner les meilleurs candidats.
    
    :param cg: Graphe de contraintes
    :param pruning_prediction: Fonction pour déterminer si une règle doit être élaguée
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param population_size: Taille de la population dans chaque génération
    :param generations: Nombre de générations à faire évoluer
    :param elite_size: Nombre des meilleurs individus à préserver entre les générations
    :param tournament_size: Taille du tournoi pour la sélection des parents
    :param crossover_rate: Probabilité d'occurrence du croisement
    :param mutation_rate: Probabilité d'occurrence de la mutation
    :param local_search_depth: Profondeur maximale de la recherche locale
    :param local_search_candidates: Nombre de meilleurs candidats à affiner par recherche locale
    :param refinement_iterations: Nombre d'itérations de raffinement par recherche locale
    :param max_table: Nombre maximum de tables dans une règle
    :param max_vars: Nombre maximum de variables dans une règle
    :yield: Règles candidates optimisées
    """
    logging.info(f"Starting genetic-local search hybrid algorithm")
    
    # Phase 1 : Initialisation - Créer une population initiale
    population = initialize_population(
        cg, pruning_prediction, db_inspector, mapper, 
        population_size, max_table, max_vars
    )
    
    # Suivre les meilleures règles trouvées et le meilleur score global
    best_rules = {}  # Dict[str, Tuple[CandidateRule, float]]
    best_fitness_ever = float('-inf')
    best_rule_ever = None
    
    # Éviter les doublons en gardant trace des règles déjà découvertes
    discovered_rules = set()
    
    # Compteur pour savoir quand appliquer la recherche locale
    generations_since_local_search = 0
    
    # Phase 2 : Évolution sur plusieurs générations
    for generation in range(generations):
        logging.info(f"Generation {generation + 1}/{generations}")
        
        # Évaluer la fitness de la population actuelle
        fitness_scores = [
            evaluate_fitness(individual, db_inspector, mapper) 
            for individual in population
        ]
        
        # Identifier le meilleur individu de cette génération
        best_idx = fitness_scores.index(max(fitness_scores))
        best_individual = population[best_idx]
        best_fitness = fitness_scores[best_idx]
        
        # Mettre à jour le meilleur individu global si nécessaire
        if best_fitness > best_fitness_ever:
            best_fitness_ever = best_fitness
            best_rule_ever = best_individual
        
        # Phase 3 : Recherche locale périodique pour affiner les meilleurs individus
        generations_since_local_search += 1
        if generations_since_local_search >= 3 or generation == generations - 1:
            generations_since_local_search = 0
            
            # Sélectionner les meilleurs candidats pour la recherche locale
            sorted_indices = sorted(
                range(len(fitness_scores)), 
                key=lambda i: fitness_scores[i], 
                reverse=True
            )
            top_candidates = [
                population[i] for i in sorted_indices[:local_search_candidates]
            ]
            
            logging.info(f"Starting local search refinement for {len(top_candidates)} candidates")
            
            # Appliquer la recherche locale à chaque candidat
            for candidate in top_candidates:
                refined_candidates = best_first_local_search(
                    cg, candidate, pruning_prediction, db_inspector, mapper,
                    max_depth=local_search_depth, 
                    max_iterations=refinement_iterations,
                    max_table=max_table, 
                    max_vars=max_vars
                )
                
                # Ajouter les candidats raffinés à la population
                for refined in refined_candidates:
                    refined_str = str(refined)
                    
                    # Éviter les doublons
                    if refined_str not in discovered_rules:
                        discovered_rules.add(refined_str)
                        
                        # Évaluer le candidat raffiné
                        refined_fitness = evaluate_fitness(refined, db_inspector, mapper)
                        
                        # Stocker dans best_rules si assez bon
                        if refined_fitness > 0.3:  # Seuil de qualité minimal
                            best_rules[refined_str] = (refined, refined_fitness)
                            
                            # Remplacer un individu faible dans la population
                            weakest_idx = fitness_scores.index(min(fitness_scores))
                            population[weakest_idx] = refined
                            fitness_scores[weakest_idx] = refined_fitness
                            
                            # Retourner ce candidat raffiné
                            yield refined
        
        # Phase 4 : Sélection et création de la nouvelle génération
        next_generation = []
        
        # Élitisme - conserver les meilleurs individus
        elites = [population[i] for i in sorted_indices[:elite_size]]
        next_generation.extend(elites)
        
        # Remplir le reste de la population avec les enfants
        while len(next_generation) < population_size:
            # Sélection par tournoi des parents
            parent1 = tournament_selection(population, fitness_scores, tournament_size)
            parent2 = tournament_selection(population, fitness_scores, tournament_size)
            
            # Appliquer le croisement avec une certaine probabilité
            if random.random() < crossover_rate:
                child1, child2 = crossover(
                    parent1, parent2, cg, pruning_prediction, 
                    db_inspector, mapper, max_table, max_vars
                )
                
                # Appliquer la mutation avec une certaine probabilité
                if random.random() < mutation_rate:
                    child1 = mutate(child1, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
                if random.random() < mutation_rate:
                    child2 = mutate(child2, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
                
                # Ajouter les enfants valides à la nouvelle génération
                if child1 and pruning_prediction(child1, mapper, db_inspector) and len(next_generation) < population_size:
                    next_generation.append(child1)
                if child2 and pruning_prediction(child2, mapper, db_inspector) and len(next_generation) < population_size:
                    next_generation.append(child2)
            else:
                # Si pas de croisement, ajouter le parent (possiblement muté)
                if random.random() < mutation_rate:
                    parent1 = mutate(parent1, cg, pruning_prediction, db_inspector, mapper, max_table, max_vars)
                if parent1 and len(next_generation) < population_size:
                    next_generation.append(parent1)
        
        # Remplacer la population avec la nouvelle génération
        population = next_generation
        
        # Retourner le meilleur individu de cette génération s'il n'a pas déjà été découvert
        best_str = str(best_individual)
        if best_str not in discovered_rules:
            discovered_rules.add(best_str)
            best_rules[best_str] = (best_individual, best_fitness)
            yield best_individual
    
    # Phase 5 : Final refinement - Affiner le meilleur individu trouvé
    if best_rule_ever:
        logging.info("Performing final intensive local search on best rule")
        final_refined = best_first_local_search(
            cg, best_rule_ever, pruning_prediction, db_inspector, mapper,
            max_depth=local_search_depth + 1,  # Profondeur supplémentaire pour la recherche finale
            max_iterations=refinement_iterations + 2,  # Plus d'itérations pour la recherche finale
            max_table=max_table, 
            max_vars=max_vars
        )
        
        # Retourner les candidats raffinés finaux
        for refined in final_refined:
            refined_str = str(refined)
            if refined_str not in discovered_rules:
                discovered_rules.add(refined_str)
                yield refined
    
    # Retourner les meilleures règles stockées, triées par score décroissant
    best_sorted = sorted(
        best_rules.values(), 
        key=lambda x: x[1],  # Tri par score
        reverse=True
    )
    
    for rule, _ in best_sorted[:10]:  # Limiter aux 10 meilleures règles
        rule_str = str(rule)
        if rule_str not in discovered_rules:
            discovered_rules.add(rule_str)
            yield rule


def best_first_local_search(
    cg: ConstraintGraph,
    start_rule: CandidateRule,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_depth: int = 3,
    max_iterations: int = 2,
    max_table: int = 3,
    max_vars: int = 6,
) -> List[CandidateRule]:
    """
    Effectue une recherche locale de type "best-first" autour d'une règle donnée.
    
    :param cg: Graphe de contraintes
    :param start_rule: Règle de départ pour la recherche locale
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_depth: Profondeur maximale de recherche à partir de la règle de départ
    :param max_iterations: Nombre d'itérations de recherche
    :param max_table: Nombre maximum de tables dans une règle
    :param max_vars: Nombre maximum de variables dans une règle
    :return: Liste des meilleures règles raffinées trouvées
    """
    if not start_rule:
        return []
    
    # Structures pour stocker les résultats et suivre la recherche
    discovered = []
    visited = set([str(start_rule)])
    frontier = PriorityQueue()
    
    # Évaluer la règle de départ
    start_score = evaluate_rule_quality(start_rule, db_inspector, mapper)
    frontier.put((-start_score, start_rule))  # Négatif car PriorityQueue est un min-heap
    
    # Meilleure règle trouvée jusqu'ici
    best_rule = start_rule
    best_score = start_score
    
    iteration = 0
    explored_count = 0
    
    # Effectuer la recherche best-first
    while not frontier.empty() and iteration < max_iterations:
        iteration += 1
        
        # Extraire le nœud actuel avec le meilleur score
        current_score, current_rule = frontier.get()
        current_score = -current_score  # Convertir en score positif
        
        # Si cette règle est meilleure que la meilleure connue, la stocker
        if current_score > best_score:
            best_score = current_score
            best_rule = current_rule
            discovered.append(current_rule)
        
        # Limiter le nombre de nœuds explorés par itération
        explored_this_iteration = 0
        max_explore_per_iteration = 10
        
        # Explorer les variantes de la règle actuelle
        for variant in generate_rule_variants(current_rule, cg, max_table, max_vars):
            variant_str = str(variant)
            
            # Éviter les règles déjà visitées
            if variant_str in visited:
                continue
                
            visited.add(variant_str)
            explored_count += 1
            explored_this_iteration += 1
            
            # Vérifier si la règle est valide selon l'élagage
            if pruning_prediction(variant, mapper, db_inspector):
                # Évaluer la qualité de cette variante
                variant_score = evaluate_rule_quality(variant, mapper, db_inspector)
                
                # Ajouter à la frontière si le score est assez bon
                if variant_score > 0.2:  # Seuil minimal de qualité
                    frontier.put((-variant_score, variant))
                
                # Si cette variante est meilleure que la meilleure règle actuelle, la stocker
                if variant_score > best_score:
                    best_score = variant_score
                    best_rule = variant
                    discovered.append(variant)
            
            # Limiter l'exploration par itération pour éviter d'explorer trop loin
            if explored_this_iteration >= max_explore_per_iteration:
                break
    
    # S'assurer que la meilleure règle est incluse dans les découvertes
    if best_rule not in discovered:
        discovered.append(best_rule)
    
    # Retourner les règles trouvées
    return discovered


def generate_rule_variants(
    rule: CandidateRule,
    cg: ConstraintGraph,
    max_table: int,
    max_vars: int
) -> List[CandidateRule]:
    """
    Génère des variantes d'une règle en ajoutant, supprimant ou remplaçant des nœuds.
    
    :param rule: Règle de départ
    :param cg: Graphe de contraintes
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :return: Liste des variantes générées
    """
    variants = []
    
    # 1. Variantes par ajout d'un nœud
    if len(rule) < max_vars:
        # Collecter tous les voisins valides de tous les nœuds dans la règle
        neighbors = set()
        visited = set(rule)
        
        for node in rule:
            for neighbor in cg.neighbors(node):
                if neighbor not in visited and next_node_test(rule, neighbor, visited, max_table, max_vars):
                    neighbors.add(neighbor)
        
        # Ajouter jusqu'à 3 variantes par ajout
        for neighbor in list(neighbors)[:3]:
            variants.append(rule + [neighbor])
    
    # 2. Variantes par suppression d'un nœud
    if len(rule) > 2:  # Garder au moins 2 nœuds
        for i in range(len(rule)):
            variant = rule[:i] + rule[i+1:]
            variants.append(variant)
    
    # 3. Variantes par remplacement d'un nœud
    if len(rule) > 0:
        for i in range(min(len(rule), 2)):  # Limiter à 2 remplacements pour ne pas générer trop de variantes
            # Trouver des voisins potentiels pour remplacer ce nœud
            neighbors = set()
            remaining = [rule[j] for j in range(len(rule)) if j != i]
            visited = set(remaining)
            
            for node in remaining:
                for neighbor in cg.neighbors(node):
                    if neighbor not in visited:
                        neighbors.add(neighbor)
            
            # Créer des variantes par remplacement
            for neighbor in list(neighbors)[:2]:
                variant = rule.copy()
                variant[i] = neighbor
                variants.append(variant)
    
    return variants


def evaluate_rule_quality(
    rule: CandidateRule,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper
) -> float:
    """
    Évalue la qualité d'une règle candidate pour la recherche locale.
    
    :param rule: Règle à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :return: Score de qualité
    """
    # Utiliser le score beam comme base
    beam_score = calculate_beam_score(rule, mapper, db_inspector)
    
    # Facteurs supplémentaires pour évaluer la règle
    splits = split_candidate_rule(rule)
    if not splits:
        return 0.0
    
    # Calculer les métriques pour les divisions possibles
    split_scores = []
    for split in splits:
        body, head = split
        if not body or not head:
            continue
        
        try:
            valid, support, confidence = split_pruning(rule, body, head, db_inspector, mapper)
            if valid:
                # Score combiné pour cette division
                combined = 0.5 * support + 0.5 * confidence
                split_scores.append(combined)
        except Exception:
            continue
    
    # Si aucune division valide, retourner un score minimal
    if not split_scores:
        return 0.0
    
    # Utiliser le meilleur score de division
    best_split_score = max(split_scores)
    
    # Facteur d'équilibre entre simplicité et complexité (on préfère des règles de taille moyenne)
    complexity_factor = 1.0
    if len(rule) <= 1:
        complexity_factor = 0.5  # Pénaliser les règles trop simples
    elif len(rule) > 4:
        complexity_factor = max(0.8 - 0.1 * (len(rule) - 4), 0.4)  # Pénalité croissante pour les règles trop complexes
    
    # Score final
    return (0.6 * beam_score + 0.4 * best_split_score) * complexity_factor
