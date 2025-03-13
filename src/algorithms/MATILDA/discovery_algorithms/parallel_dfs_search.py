"""
Algorithme de recherche en profondeur (DFS) avec mise en cache et calcul parallèle.

Cette implémentation optimisée utilise:
- Un système de cache pour éviter de réévaluer les mêmes règles
- Du traitement parallèle des branches indépendantes
- Une pile explicite au lieu de la récursion pour éviter les dépassements de pile
- Une gestion optimisée de la mémoire pour les grands graphes
"""

import time
import logging
import pickle
import hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
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
    extract_table_occurrences,
    instantiate_tgd
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
    
    def stats(self) -> Dict[str, Any]:
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


def parallel_dfs_search(
    graph: ConstraintGraph,
    start_node: Optional[JoinableIndexedAttributes],
    pruning_prediction: Callable[[CandidateRule, AttributeMapper, AlchemyUtility], bool],
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int = 3,
    max_vars: int = 6,
    max_workers: int = None,  # None utilise le nombre de processeurs disponibles
    cache_size: int = 100000,
    batch_size: int = 20,  # Taille des lots pour l'évaluation parallèle
    checkpoint_interval: int = 1000,  # Intervalle entre les points de contrôle
    checkpoint_path: Optional[str] = None,  # Chemin pour sauvegarder les points de contrôle
    max_depth: int = None  # Profondeur maximale, None pour illimité
) -> Iterator[CandidateRule]:
    """
    Recherche en profondeur (DFS) parallèle avec mise en cache et traitement par lots.
    
    :param graph: Graphe de contraintes
    :param start_node: Nœud de départ ou None pour commencer depuis tous les nœuds
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :param max_workers: Nombre maximum de processus parallèles
    :param cache_size: Taille maximale du cache
    :param batch_size: Taille des lots pour traitement parallèle
    :param checkpoint_interval: Intervalle entre les points de contrôle
    :param checkpoint_path: Chemin pour sauvegarder les points de contrôle
    :param max_depth: Profondeur maximale d'exploration
    :yield: Règles candidates valides
    """
    logging.info("Starting parallel DFS search")
    start_time = time.time()
    
    # Initialiser le cache d'évaluation
    evaluation_cache = RuleEvaluationCache(max_size=cache_size)
    
    # Ensemble pour suivre les règles visitées
    visited_rules = set()
    
    # Compteur de règles traitées
    processed_count = 0
    
    # Créer une fonction partielle pour l'évaluation parallèle
    evaluation_function = partial(
        evaluate_rule_batch,
        pruning_fn_name='pruning_prediction'
    )
    
    # Pile de travail pour la DFS non récursive
    # Chaque élément est un tuple: (règle, ensemble des nœuds visités, profondeur)
    work_stack = []
    
    # Initialiser la pile avec le nœud de départ ou tous les nœuds si None
    if start_node is None:
        # Collecter tous les nœuds de départ valides
        start_nodes = []
        for node in tqdm(graph.nodes, desc="Collecting valid start nodes"):
            if next_node_test([], node, set(), max_table, max_vars):
                start_nodes.append(node)
        
        logging.info(f"Collected {len(start_nodes)} valid start nodes")
        
        # Évaluer les nœuds de départ en parallèle
        initial_candidates = []
        for node in start_nodes:
            rule = [node]
            cached_result = evaluation_cache.get(rule)
            
            if cached_result is None:
                initial_candidates.append((rule, {node}, 1))
            elif cached_result:
                rule_str = str(rule)
                if rule_str not in visited_rules:
                    visited_rules.add(rule_str)
                    work_stack.append((rule, {node}, 1))
                    yield rule
        
        # Évaluer les candidats initiaux en lots parallèles
        if initial_candidates:
            process_batch_for_dfs(
                initial_candidates,
                evaluation_function,
                db_inspector,
                mapper,
                work_stack,
                visited_rules,
                evaluation_cache
            )
    else:
        # Commencer avec le nœud spécifié
        rule = [start_node]
        cached_result = evaluation_cache.get(rule)
        
        if cached_result is None:
            # Évaluer la règle
            if pruning_prediction(rule, mapper, db_inspector):
                evaluation_cache.put(rule, True)
                rule_str = str(rule)
                visited_rules.add(rule_str)
                work_stack.append((rule, {start_node}, 1))
                yield rule
            else:
                evaluation_cache.put(rule, False)
        elif cached_result:
            rule_str = str(rule)
            visited_rules.add(rule_str)
            work_stack.append((rule, {start_node}, 1))
            yield rule
    
    # Traitement principal DFS avec pile explicite
    pending_batches = []  # Liste des lots en attente d'évaluation
    current_batch = []  # Lot actuel en cours de construction
    
    while work_stack:
        # Si nous avons un lot complet, planifier son évaluation
        if len(current_batch) >= batch_size:
            pending_batches.append(current_batch)
            current_batch = []
            
            # Traiter les lots en attente en parallèle
            if len(pending_batches) >= max_workers if max_workers else 2:
                process_pending_batches(
                    pending_batches,
                    evaluation_function,
                    db_inspector,
                    mapper,
                    work_stack,
                    visited_rules,
                    evaluation_cache
                )
                pending_batches = []
                
                # Afficher les statistiques
                processed_count += batch_size * len(pending_batches)
                elapsed = time.time() - start_time
                rate = processed_count / elapsed if elapsed > 0 else 0
                cache_stats = evaluation_cache.stats()
                logging.info(
                    f"Processed: {processed_count}, Queue size: {len(work_stack)}, "
                    f"Rate: {rate:.2f}/s, Cache hit rate: {cache_stats['hit_rate']:.2%}"
                )
                
                # Checkpoint
                if checkpoint_path and processed_count % checkpoint_interval == 0:
                    save_dfs_checkpoint(
                        checkpoint_path,
                        work_stack,
                        visited_rules,
                        evaluation_cache,
                        processed_count
                    )
        
        # Extraire le prochain élément de la pile
        current_rule, current_visited, current_depth = work_stack.pop()
        processed_count += 1
        
        # Vérifier la profondeur maximale
        if max_depth and current_depth >= max_depth:
            continue
            
        # Si la règle a atteint la taille maximale, ne pas explorer plus loin
        if len(current_rule) >= max_vars:
            continue
        
        # Collecter tous les voisins valides
        neighbors = []
        for node in current_rule:
            for neighbor in graph.neighbors(node):
                if (neighbor not in current_visited and 
                    next_node_test(current_rule, neighbor, current_visited, max_table, max_vars)):
                    neighbors.append(neighbor)
        
        # Ajouter les voisins à la file de traitement
        for neighbor in neighbors:
            new_rule = current_rule + [neighbor]
            new_visited = current_visited.union({neighbor})
            rule_str = str(new_rule)
            
            # Vérifier si cette règle a déjà été visitée
            if rule_str in visited_rules:
                continue
            
            # Vérifier le cache
            cached_result = evaluation_cache.get(new_rule)
            if cached_result is None:
                # Ajouter au lot pour évaluation parallèle
                current_batch.append((new_rule, new_visited, current_depth + 1))
            elif cached_result:
                # Règle valide dans le cache
                visited_rules.add(rule_str)
                work_stack.append((new_rule, new_visited, current_depth + 1))
                yield new_rule
    
    # Traiter les derniers lots en attente
    if current_batch:
        pending_batches.append(current_batch)
    
    if pending_batches:
        process_pending_batches(
            pending_batches,
            evaluation_function,
            db_inspector,
            mapper,
            work_stack,
            visited_rules,
            evaluation_cache
        )
        
        # Vider la pile de travail pour les dernières règles
        while work_stack:
            current_rule, current_visited, current_depth = work_stack.pop()
            rule_str = str(current_rule)
            
            if rule_str not in visited_rules:
                visited_rules.add(rule_str)
                yield current_rule
    
    # Statistiques finales
    elapsed = time.time() - start_time
    cache_stats = evaluation_cache.stats()
    logging.info(
        f"Parallel DFS completed. "
        f"Processed: {processed_count}, "
        f"Time: {elapsed:.2f}s, "
        f"Rate: {processed_count / elapsed:.2f}/s, "
        f"Cache hit rate: {cache_stats['hit_rate']:.2%}"
    )


def process_batch_for_dfs(
    batch: List[Tuple[CandidateRule, Set[JoinableIndexedAttributes], int]],
    eval_fn: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    work_stack: List,
    visited: Set[str],
    cache: RuleEvaluationCache
) -> None:
    """
    Traite un lot d'évaluations pour le DFS.
    
    :param batch: Liste de tuples (règle, ensemble visité, profondeur)
    :param eval_fn: Fonction d'évaluation
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param work_stack: Pile de travail DFS
    :param visited: Ensemble des règles visitées
    :param cache: Cache d'évaluation
    """
    # Extraire les règles pour évaluation
    batch_rules = [item[0] for item in batch]
    
    try:
        # Évaluer les règles en parallèle
        evaluation_results = eval_fn(batch_rules, db_inspector, mapper)
        
        # Traiter les résultats
        for idx, (rule, is_valid) in enumerate(evaluation_results):
            # Récupérer les informations originales
            _, visited_set, depth = batch[idx]
            rule_str = str(rule)
            
            # Mettre en cache le résultat
            cache.put(rule, is_valid)
            
            # Si valide, ajouter à la pile et aux visitées
            if is_valid and rule_str not in visited:
                visited.add(rule_str)
                work_stack.append((rule, visited_set, depth))
    except Exception as e:
        logging.error(f"Error processing batch: {str(e)}")


def process_pending_batches(
    batches: List[List],
    eval_fn: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    work_stack: List,
    visited: Set[str],
    cache: RuleEvaluationCache
) -> None:
    """
    Traite plusieurs lots en parallèle.
    
    :param batches: Liste de lots à traiter
    :param eval_fn: Fonction d'évaluation
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param work_stack: Pile de travail DFS
    :param visited: Ensemble des règles visitées
    :param cache: Cache d'évaluation
    """
    with ProcessPoolExecutor(max_workers=None) as executor:
        # Soumettre les lots pour évaluation
        futures = []
        
        for batch in batches:
            batch_rules = [item[0] for item in batch]
            future = executor.submit(
                eval_fn,
                batch_rules=batch_rules,
                db_inspector=db_inspector,
                mapper=mapper
            )
            futures.append((future, batch))
        
        # Traiter les résultats
        for future, batch in futures:
            try:
                results = future.result()
                
                for idx, (rule, is_valid) in enumerate(results):
                    _, visited_set, depth = batch[idx]
                    rule_str = str(rule)
                    
                    # Mettre en cache
                    cache.put(rule, is_valid)
                    
                    # Si valide, ajouter à la pile
                    if is_valid and rule_str not in visited:
                        visited.add(rule_str)
                        work_stack.append((rule, visited_set, depth))
            except Exception as e:
                logging.error(f"Error processing batch result: {str(e)}")


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


def save_dfs_checkpoint(
    path: str,
    work_stack: List[Tuple[CandidateRule, Set[JoinableIndexedAttributes], int]],
    visited: Set[str],
    cache: RuleEvaluationCache,
    processed_count: int
) -> bool:
    """
    Sauvegarde l'état actuel de la recherche DFS.
    
    :param path: Chemin où sauvegarder le checkpoint
    :param work_stack: Pile de travail actuelle
    :param visited: Ensemble des règles visitées
    :param cache: Cache d'évaluation
    :param processed_count: Nombre de règles traitées
    :return: True si réussite, False sinon
    """
    try:
        checkpoint_data = {
            'work_stack': work_stack,
            'visited': visited,
            'cache': cache.cache,
            'processed_count': processed_count,
            'timestamp': time.time()
        }
        
        checkpoint_filename = f"{path}_dfs_count{processed_count}.pkl"
        with open(checkpoint_filename, 'wb') as f:
            pickle.dump(checkpoint_data, f)
            
        logging.info(f"DFS Checkpoint saved to {checkpoint_filename}")
        return True
    except Exception as e:
        logging.error(f"Error saving DFS checkpoint: {str(e)}")
        return False


def load_dfs_checkpoint(path: str) -> Dict[str, Any]:
    """
    Charge un point de contrôle DFS précédemment sauvegardé.
    
    :param path: Chemin du fichier de point de contrôle
    :return: Dictionnaire avec les données de point de contrôle
    """
    try:
        with open(path, 'rb') as f:
            checkpoint_data = pickle.load(f)
            
        # Reconstruire le cache
        cache = RuleEvaluationCache()
        cache.cache = checkpoint_data['cache']
        
        return {
            'work_stack': checkpoint_data['work_stack'],
            'visited': checkpoint_data['visited'],
            'cache': cache,
            'processed_count': checkpoint_data['processed_count']
        }
    except Exception as e:
        logging.error(f"Error loading DFS checkpoint: {str(e)}")
        return {}


def resume_parallel_dfs_search(
    checkpoint_path: str,
    graph: ConstraintGraph,
    pruning_prediction: Callable,
    db_inspector: AlchemyUtility,
    mapper: AttributeMapper,
    max_table: int = 3,
    max_vars: int = 6,
    max_workers: int = None,
    cache_size: int = 100000,
    batch_size: int = 20,
    checkpoint_interval: int = 1000,
    max_depth: int = None
) -> Iterator[CandidateRule]:
    """
    Reprend une recherche DFS parallèle à partir d'un point de contrôle.
    
    :param checkpoint_path: Chemin du fichier de point de contrôle
    :param graph: Graphe de contraintes
    :param pruning_prediction: Fonction d'élagage
    :param db_inspector: Inspecteur de base de données
    :param mapper: Mappeur d'attributs
    :param max_table: Nombre maximum de tables
    :param max_vars: Nombre maximum de variables
    :param max_workers: Nombre maximum de processus parallèles
    :param cache_size: Taille maximale du cache
    :param batch_size: Taille des lots pour traitement parallèle
    :param checkpoint_interval: Intervalle entre les points de contrôle
    :param max_depth: Profondeur maximale d'exploration
    :yield: Règles candidates valides
    """
    logging.info(f"Resuming parallel DFS search from checkpoint: {checkpoint_path}")
    
    # Charger les données du point de contrôle
    checkpoint_data = load_dfs_checkpoint(checkpoint_path)
    if not checkpoint_data:
        logging.error("Failed to load DFS checkpoint, starting new search")
        yield from parallel_dfs_search(
            graph, None, pruning_prediction, db_inspector, mapper,
            max_table, max_vars, max_workers, cache_size,
            batch_size, checkpoint_interval, checkpoint_path, max_depth
        )
        return
    
    work_stack = checkpoint_data['work_stack']
    visited_rules = checkpoint_data['visited']
    evaluation_cache = checkpoint_data['cache']
    processed_count = checkpoint_data['processed_count']
    
    logging.info(
        f"DFS Checkpoint loaded: "
        f"Stack size: {len(work_stack)}, "
        f"Visited: {len(visited_rules)}, "
        f"Cache size: {len(evaluation_cache.cache)}, "
        f"Processed count: {processed_count}"
    )
    
    # Continuer la recherche à partir de l'état chargé
    start_time = time.time()
    evaluation_function = partial(
        evaluate_rule_batch,
        pruning_fn_name='pruning_prediction'
    )
    
    # Reprendre le traitement DFS
    pending_batches = []
    current_batch = []
    
    # Processus principal
    while work_stack:
        # Logique similaire à parallel_dfs_search, adaptée pour reprendre depuis le point de contrôle
        # Pour éviter la duplication de code, on pourrait extraire la logique principale
        # dans des fonctions auxiliaires communes, mais pour cet exemple, on synthétise
        
        # Extraire le prochain élément de la pile
        current_rule, current_visited, current_depth = work_stack.pop()
        
        # Règle déjà traitée lors de la reprise
        rule_str = str(current_rule)
        if rule_str in visited_rules:
            yield current_rule  # Retourner la règle valide
        else:
            # Ajouter au lot pour ré-évaluation
            current_batch.append((current_rule, current_visited, current_depth))
            if len(current_batch) >= batch_size:
                pending_batches.append(current_batch)
                current_batch = []
                
                # Traiter les lots en attente
                if pending_batches:
                    process_pending_batches(
                        pending_batches,
                        evaluation_function,
                        db_inspector,
                        mapper,
                        work_stack,
                        visited_rules,
                        evaluation_cache
                    )
                    pending_batches = []
    
    # Continuer le processus de recherche comme dans parallel_dfs_search
    # Pour simplifier, on pourrait appeler directement cette fonction
    # après avoir correctement initialisé l'état
