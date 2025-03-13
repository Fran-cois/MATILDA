"""
Algorithme de recherche en largeur (BFS) avec mise en cache et calcul parallèle.

Cette implémentation optimisée utilise:
- Un système de cache pour éviter de réévaluer les mêmes règles
- Du calcul parallèle pour traiter plusieurs branches simultanément
- Une gestion optimisée de la mémoire pour les grands graphes
"""

import time
import logging
import pickle
import hashlib
from collections import deque, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import lru_cache, partial
from typing import Dict, Set, List, Tuple, Callable, Iterator, Optional, Any
from tqdm import tqdm

from algorithms.MATILDA.constraint_graph import (
    AttributeMapper,
    ConstraintGraph,
    JoinableIndexedAttributes,
)
from algorithms.MATILDA.discovery_algorithms.common import (
    CandidateRule,
    next_node_test,
    calculate_beam_score
)
from database.alchemy_utility import AlchemyUtility
from algorithms.MATILDA.rule_types.tgd_discovery import (
    split_candidate_rule,
    split_pruning,
    extract_table_occurrences
)


# Classe pour stocker et récupérer efficacement les résultats d'évaluation
class RuleEvaluationCache:
    """Cache pour les évaluations de règles pour éviter les calculs redondants."""
    
    def __init__(self, max_size: int = 100000):
        """
        Initialise le cache avec une taille maximale.
        
        :param max_size: Nombre maximum d'entrées dans le cache
        """
        self.cache: Dict[str, bool] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def _get_key(self, rule: CandidateRule) -> str:
        """
        Génère une clé de cache pour une règle.
        
        :param rule: Règle candidate
        :return: Clé unique pour la règle
        """
        # Utiliser un hash stable basé sur la représentation string de la règle
        rule_str = str(sorted(str(node) for node in rule))
        return hashlib.md5(rule_str.encode()).hexdigest()
    
    def get(self, rule: CandidateRule) -> Optional[bool]:
        """
        Récupère le résultat de l'évaluation de règle depuis le cache.
        
        :param rule: Règle candidate
        :return: Résultat d'évaluation ou None si pas en cache
        """
        key = self._get_key(rule)
        result = self.cache.get(key)
        
        if result is not None:
            self.hits += 1
        else:
            self.misses += 1
            
        return result
    
    def put(self, rule: CandidateRule, result: bool) -> None:
        """
        Stocke le résultat d'évaluation de règle dans le cache.
        
        :param rule: Règle candidate
        :param result: Résultat d'évaluation à stocker
        """
        # Si le cache est plein, supprimer des entrées
        if len(self.cache) >= self.max_size:
            # Supprimer 10% des entrées les plus anciennes
            entries_to_remove = int(self.max_size * 0.1)
            for _ in range(entries_to_remove):
                if self.cache:
                    self.cache.pop(next(iter(self.cache)))
        
        key = self._get_key(rule)
        self.cache[key] = result
    
    def stats(self) -> Dict[str, int]:
        """
        Renvoie les statistiques du cache.
        
        :return: Dictionnaire avec les statistiques
        """
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }


def parallel_bfs_search(
    graph: ConstraintGraph,
    start_node: Optional[JoinableIndexedAttributes],
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int = 3,
    max_vars: int = 6,
    batch_size: int = 100,
    max_workers: int = None,  # None utilise le nombre de processeurs disponibles
    cache_size: int = 100000,
    checkpoint_interval: int = 1000,  # Intervalle entre les points de contrôle
    checkpoint_path: Optional[str] = None  # Chemin pour sauvegarder les points de contrôle
) -> Iterator[CandidateRule]:
    """
    Recherche en largeur (BFS) parallèle avec mise en cache des évaluations.
    
    :param graph: Graphe de contraintes
    :param start_node: Nœud de départ ou None pour commencer depuis tous les nœuds
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :param batch_size: Taille des lots pour le traitement parallèle
    :param max_workers: Nombre maximum de processus à utiliser
    :param cache_size: Taille maximale du cache d'évaluation
    :param checkpoint_interval: Intervalle entre les points de contrôle
    :param checkpoint_path: Chemin pour sauvegarder les points de contrôle
    :yield: Règles candidates valides
    """
    logging.info("Starting parallel BFS search")
    start_time = time.time()
    
    # Initialiser le cache d'évaluation
    evaluation_cache = RuleEvaluationCache(max_size=cache_size)
    
    # File d'attente pour le BFS
    queue = deque()
    
    # Ensemble pour suivre les règles visitées
    visited_rules = set()
    
    # Compteur de règles traitées
    processed_count = 0
    
    # Créer une fonction partielle pour évaluer les règles (utilisée dans le calcul parallèle)
    # Pour contourner les problèmes de sérialisation avec pickle, on transmet uniquement les données nécessaires
    evaluation_function = partial(
        evaluate_rule_batch,
        pruning_fn_name='pruning_prediction'
    )
    
    # Si aucun nœud de départ n'est spécifié, initialiser avec tous les nœuds valides
    if start_node is None:
        logging.info("Initializing BFS from all valid nodes")
        initial_candidates = []
        
        for node in tqdm(graph.nodes, desc="Finding valid starting nodes"):
            if next_node_test([], node, set(), max_table, max_vars):
                initial_rule = [node]
                rule_key = str(initial_rule)
                
                # Vérifier le cache avant d'ajouter à la file
                cached_result = evaluation_cache.get(initial_rule)
                if cached_result is None:
                    initial_candidates.append((initial_rule, {node}))
                elif cached_result:
                    visited_rules.add(rule_key)
                    queue.append((initial_rule, {node}))
                    yield initial_rule
        
        # Évaluation parallèle des candidats initiaux par lots
        process_and_queue_candidates(
            initial_candidates,
            evaluation_function, 
            db_inspector, 
            mapper,
            queue, 
            visited_rules,
            evaluation_cache,
            batch_size,
            max_workers
        )
    else:
        # Commencer avec le nœud spécifié
        initial_rule = [start_node]
        rule_key = str(initial_rule)
        
        # Vérifier le cache d'abord
        cached_result = evaluation_cache.get(initial_rule)
        if cached_result is None:
            # Évaluer la règle
            if pruning_prediction(initial_rule, mapper, db_inspector):
                evaluation_cache.put(initial_rule, True)
                visited_rules.add(rule_key)
                queue.append((initial_rule, {start_node}))
                yield initial_rule
            else:
                evaluation_cache.put(initial_rule, False)
        elif cached_result:
            visited_rules.add(rule_key)
            queue.append((initial_rule, {start_node}))
            yield initial_rule
    
    # Traitement principal BFS
    level = 0
    current_level_size = len(queue)
    
    while queue:
        # Calculer le taux de progression et les statistiques
        if processed_count % 100 == 0:
            elapsed = time.time() - start_time
            rate = processed_count / elapsed if elapsed > 0 else 0
            cache_stats = evaluation_cache.stats()
            logging.info(
                f"Level {level}, Queue size: {len(queue)}, "
                f"Processed: {processed_count}, "
                f"Rate: {rate:.2f}/s, "
                f"Cache hit rate: {cache_stats['hit_rate']:.2%}"
            )
        
        # Traiter tous les nœuds du niveau actuel avant de passer au niveau suivant
        new_level = current_level_size == 0
        if new_level:
            level += 1
            current_level_size = len(queue)
            logging.info(f"Starting BFS level {level}, size: {current_level_size}")
        
        # Préparer un lot de nœuds à traiter
        batch_candidates = []
        batch_count = min(batch_size, current_level_size)
        
        for _ in range(batch_count):
            if not queue:
                break
                
            current_rule, current_visited = queue.popleft()
            current_level_size -= 1
            processed_count += 1
            
            # Si limite maximale atteinte, ne pas explorer plus loin
            if len(current_rule) >= max_vars:
                continue
            
            # Collecter les voisins valides
            neighbors = get_valid_neighbors(
                graph, current_rule, current_visited, max_table, max_vars
            )
            
            # Générer des candidats et filtrer ceux déjà visités
            for neighbor in neighbors:
                new_rule = current_rule + [neighbor]
                new_visited = current_visited.union({neighbor})
                rule_key = str(new_rule)
                
                if rule_key in visited_rules:
                    continue
                
                # Vérifier le cache
                cached_result = evaluation_cache.get(new_rule)
                if cached_result is None:
                    batch_candidates.append((new_rule, new_visited))
                elif cached_result:
                    # Règle valide dans le cache
                    visited_rules.add(rule_key)
                    queue.append((new_rule, new_visited))
                    yield new_rule
        
        # Traiter le lot en parallèle
        if batch_candidates:
            process_and_queue_candidates(
                batch_candidates,
                evaluation_function, 
                db_inspector, 
                mapper,
                queue, 
                visited_rules,
                evaluation_cache,
                batch_size,
                max_workers
            )
        
        # Sauvegarde de point de contrôle périodique
        if checkpoint_path and processed_count % checkpoint_interval == 0:
            save_checkpoint(
                checkpoint_path, 
                queue, 
                visited_rules, 
                evaluation_cache,
                processed_count,
                level
            )
    
    # Statistiques finales
    elapsed = time.time() - start_time
    cache_stats = evaluation_cache.stats()
    logging.info(
        f"Parallel BFS completed. "
        f"Processed: {processed_count}, "
        f"Time: {elapsed:.2f}s, "
        f"Rate: {processed_count / elapsed:.2f}/s, "
        f"Cache hit rate: {cache_stats['hit_rate']:.2%}"
    )


def process_and_queue_candidates(
    candidates: List[Tuple[CandidateRule, Set]],
    eval_fn: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    queue: deque,
    visited: Set[str],
    cache: RuleEvaluationCache,
    batch_size: int,
    max_workers: int
) -> None:
    """
    Traite un lot de candidats en parallèle et ajoute les valides à la file d'attente.
    
    :param candidates: Liste des règles candidates à traiter
    :param eval_fn: Fonction d'évaluation à appliquer en parallèle
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param queue: File d'attente BFS
    :param visited: Ensemble des règles visitées
    :param cache: Cache d'évaluation
    :param batch_size: Taille des lots pour le traitement
    :param max_workers: Nombre maximum de processus à utiliser
    """
    if not candidates:
        return
    
    # Préparer les lots pour traitement parallèle
    batches = []
    current_batch = []
    
    for candidate, visited_set in candidates:
        current_batch.append((candidate, visited_set))
        if len(current_batch) >= batch_size:
            batches.append(current_batch)
            current_batch = []
    
    # Ajouter le dernier lot s'il n'est pas vide
    if current_batch:
        batches.append(current_batch)
    
    # Traiter les lots en parallèle
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Soumettre les lots pour évaluation parallèle
        futures = [
            executor.submit(
                eval_fn, 
                batch_rules=[pair[0] for pair in batch], 
                db_inspector=db_inspector, 
                mapper=mapper
            ) 
            for batch in batches
        ]
        
        # Traiter les résultats au fur et à mesure qu'ils sont disponibles
        for batch_idx, future in enumerate(as_completed(futures)):
            try:
                batch_results = future.result()
                
                # Traiter les résultats pour ce lot
                for result_idx, (rule, is_valid) in enumerate(batch_results):
                    rule_str = str(rule)
                    visited_set = batches[batch_idx][result_idx][1]
                    
                    # Mettre en cache le résultat
                    cache.put(rule, is_valid)
                    
                    # Si valide, ajouter à la file BFS et aux résultats
                    if is_valid and rule_str not in visited:
                        visited.add(rule_str)
                        queue.append((rule, visited_set))
            except Exception as e:
                logging.error(f"Error processing batch {batch_idx}: {str(e)}")


def get_valid_neighbors(
    graph: ConstraintGraph,
    rule: CandidateRule,
    visited_set: Set[JoinableIndexedAttributes],
    max_table: int,
    max_vars: int
) -> List[JoinableIndexedAttributes]:
    """
    Récupère tous les voisins valides pour une règle donnée.
    
    :param graph: Graphe de contraintes
    :param rule: Règle actuelle
    :param visited_set: Ensemble des nœuds déjà visités
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :return: Liste des voisins valides
    """
    valid_neighbors = []
    
    # Explorer les voisins de tous les nœuds dans la règle
    for node in rule:
        for neighbor in graph.neighbors(node):
            if (neighbor not in visited_set and 
                neighbor not in valid_neighbors and
                next_node_test(rule, neighbor, visited_set, max_table, max_vars)):
                valid_neighbors.append(neighbor)
    
    return valid_neighbors


def evaluate_rule_batch(
    batch_rules: List[CandidateRule],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    pruning_fn_name: str = 'pruning_prediction'
) -> List[Tuple[CandidateRule, bool]]:
    """
    Évalue un lot de règles candidates et renvoie les résultats.
    
    :param batch_rules: Liste des règles à évaluer
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param pruning_fn_name: Nom de la fonction d'élagage dans le module
    :return: Liste de tuples (règle, résultat d'évaluation)
    """
    # Import dans la fonction pour éviter les problèmes de sérialisation
    from algorithms.MATILDA.rule_types.tgd_discovery import pruning_prediction
    
    results = []
    for rule in batch_rules:
        try:
            # Évaluer la règle
            is_valid = pruning_prediction(rule, mapper, db_inspector)
            results.append((rule, is_valid))
        except Exception as e:
            # Gérer les erreurs d'évaluation
            logging.error(f"Error evaluating rule {rule}: {str(e)}")
            results.append((rule, False))
    
    return results


def save_checkpoint(
    path: str,
    queue: deque,
    visited: Set[str],
    cache: RuleEvaluationCache,
    processed_count: int,
    level: int
) -> bool:
    """
    Sauvegarde l'état actuel de la recherche BFS dans un fichier de point de contrôle.
    
    :param path: Chemin où sauvegarder le point de contrôle
    :param queue: File d'attente BFS actuelle
    :param visited: Ensemble des règles visitées
    :param cache: Cache d'évaluation
    :param processed_count: Nombre de règles traitées
    :param level: Niveau BFS actuel
    :return: True si la sauvegarde a réussi, False sinon
    """
    try:
        checkpoint_data = {
            'queue': list(queue),
            'visited': visited,
            'cache': cache.cache,
            'processed_count': processed_count,
            'level': level,
            'timestamp': time.time()
        }
        
        checkpoint_filename = f"{path}_level{level}_count{processed_count}.pkl"
        with open(checkpoint_filename, 'wb') as f:
            pickle.dump(checkpoint_data, f)
            
        logging.info(f"Checkpoint saved to {checkpoint_filename}")
        return True
    except Exception as e:
        logging.error(f"Error saving checkpoint: {str(e)}")
        return False


def load_checkpoint(path: str) -> Dict[str, Any]:
    """
    Charge un point de contrôle précédemment sauvegardé.
    
    :param path: Chemin du fichier de point de contrôle
    :return: Dictionnaire avec les données de point de contrôle
    """
    try:
        with open(path, 'rb') as f:
            checkpoint_data = pickle.load(f)
            
        # Reconstruire la file d'attente
        queue = deque(checkpoint_data['queue'])
        
        # Reconstruire le cache
        cache = RuleEvaluationCache()
        cache.cache = checkpoint_data['cache']
        
        return {
            'queue': queue,
            'visited': checkpoint_data['visited'],
            'cache': cache,
            'processed_count': checkpoint_data['processed_count'],
            'level': checkpoint_data['level']
        }
    except Exception as e:
        logging.error(f"Error loading checkpoint: {str(e)}")
        return {}


def resume_parallel_bfs_search(
    checkpoint_path: str,
    graph: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int = 3,
    max_vars: int = 6,
    batch_size: int = 100,
    max_workers: int = None,
    cache_size: int = 100000,
    checkpoint_interval: int = 1000
) -> Iterator[CandidateRule]:
    """
    Reprend une recherche BFS parallèle à partir d'un point de contrôle.
    
    :param checkpoint_path: Chemin du fichier de point de contrôle
    :param graph: Graphe de contraintes
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :param batch_size: Taille des lots pour le traitement parallèle
    :param max_workers: Nombre maximum de processus à utiliser
    :param cache_size: Taille maximale du cache d'évaluation
    :param checkpoint_interval: Intervalle entre les points de contrôle
    :yield: Règles candidates valides
    """
    logging.info(f"Resuming parallel BFS search from checkpoint: {checkpoint_path}")
    
    # Charger les données du point de contrôle
    checkpoint_data = load_checkpoint(checkpoint_path)
    if not checkpoint_data:
        logging.error("Failed to load checkpoint, starting new search")
        yield from parallel_bfs_search(
            graph, None, pruning_prediction, db_inspector, mapper,
            max_table, max_vars, batch_size, max_workers,
            cache_size, checkpoint_interval, checkpoint_path
        )
        return
    
    queue = checkpoint_data['queue']
    visited_rules = checkpoint_data['visited']
    evaluation_cache = checkpoint_data['cache']
    processed_count = checkpoint_data['processed_count']
    level = checkpoint_data['level']
    
    logging.info(
        f"Checkpoint loaded: Level {level}, "
        f"Queue size: {len(queue)}, "
        f"Visited: {len(visited_rules)}, "
        f"Cache size: {len(evaluation_cache.cache)}"
    )
    
    # Continuer la recherche BFS à partir de l'état chargé
    start_time = time.time()
    evaluation_function = partial(
        evaluate_rule_batch,
        pruning_fn_name='pruning_prediction'
    )
    
    # Reprendre le traitement BFS comme dans la fonction principale
    current_level_size = len(queue)
    
    while queue:
        # Code similaire à celui de parallel_bfs_search, mais reprenant à partir du point de contrôle
        # ... (reprendre le code de la boucle principale)
        
        # Pour éviter de dupliquer tout le code, vous pouvez extraire la logique principale
        # dans une fonction helper commune et l'appeler ici aussi
        pass
