"""
Module de statistiques pour l'analyse des performances des algorithmes de découverte de règles.

Ce module fournit des outils pour collecter, analyser et comparer les performances
des différents algorithmes de découverte de règles dans MATILDA.
"""

import time
import logging
import json
import os
import threading
import psutil
from typing import Dict, List, Any, Optional, Set, Union
import matplotlib.pyplot as plt
import numpy as np
from dataclasses import dataclass, field, asdict


@dataclass
class IterationStats:
    """Statistiques collectées pour chaque itération d'un algorithme de recherche."""
    iteration_number: int
    time_start: float
    time_end: float = 0.0
    candidates_expanded: int = 0
    queries_executed: int = 0
    rules_discovered: int = 0
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    candidates_pruned: int = 0
    backtracking_steps: int = 0  # Pertinent pour DFS
    backtracking_time: float = 0.0  # Pertinent pour DFS
    level_width: int = 0  # Nombre de candidats à un niveau (pertinent pour BFS)
    search_depth: int = 0  # Profondeur actuelle (DFS) ou niveau (BFS)
    batch_size: int = 0  # Taille du lot de requêtes (pertinent pour les approches par lots)
    
    @property
    def duration(self) -> float:
        """Durée de l'itération en secondes."""
        return self.time_end - self.time_start if self.time_end > 0 else 0.0
    
    def complete(self) -> None:
        """Complète l'enregistrement de l'itération avec la fin du temps et utilisation mémoire/CPU."""
        self.time_end = time.time()
        self.memory_usage_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        self.cpu_percent = psutil.Process(os.getpid()).cpu_percent(interval=0.1)


@dataclass
class QueryStats:
    """Statistiques détaillées sur les requêtes exécutées."""
    total_queries: int = 0
    total_query_time: float = 0.0
    batch_queries: int = 0
    individual_queries: int = 0
    skipped_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_query_time: float = 0.0
    max_query_time: float = 0.0
    min_query_time: float = float('inf')
    
    def add_query(self, duration: float, is_batch: bool = False, batch_size: int = 1) -> None:
        """Ajoute les statistiques d'une requête."""
        self.total_queries += batch_size if is_batch else 1
        self.total_query_time += duration
        if is_batch:
            self.batch_queries += 1
        else:
            self.individual_queries += 1
        
        # Mise à jour du temps moyen, min, max
        self.avg_query_time = self.total_query_time / (self.batch_queries + self.individual_queries)
        self.max_query_time = max(self.max_query_time, duration)
        self.min_query_time = min(self.min_query_time, duration)


@dataclass
class CacheStats:
    """Statistiques sur l'utilisation du cache."""
    hits: int = 0
    misses: int = 0
    memory_usage_mb: float = 0.0
    entries_count: int = 0
    evictions: int = 0
    computation_time_saved: float = 0.0  # Temps économisé grâce au cache (estimé)
    
    @property
    def hit_rate(self) -> float:
        """Taux de succès du cache."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


@dataclass
class RuleStats:
    """Statistiques sur les règles découvertes."""
    total_discovered: int = 0
    valid_rules: int = 0  # Règles qui passent tous les critères de qualité
    avg_support: float = 0.0
    avg_confidence: float = 0.0
    avg_rule_length: float = 0.0
    unique_structures: int = 0  # Nombre de structures de règles uniques
    discovery_times: List[float] = field(default_factory=list)  # Temps pour chaque découverte
    rule_complexity: Dict[int, int] = field(default_factory=dict)  # Longueur de règle -> nombre
    rule_qualities: List[Dict[str, float]] = field(default_factory=list)  # Liste des métriques par règle
    
    def add_rule(
        self, 
        support: float, 
        confidence: float, 
        length: int, 
        discovery_time: float,
        is_valid: bool = True
    ) -> None:
        """Ajoute les statistiques d'une règle découverte."""
        self.total_discovered += 1
        if is_valid:
            self.valid_rules += 1
            
        # Mettre à jour les moyennes de façon incrémentale
        if self.valid_rules > 0:
            self.avg_support = ((self.avg_support * (self.valid_rules - 1)) + support) / self.valid_rules
            self.avg_confidence = ((self.avg_confidence * (self.valid_rules - 1)) + confidence) / self.valid_rules
            self.avg_rule_length = ((self.avg_rule_length * (self.valid_rules - 1)) + length) / self.valid_rules
        
        self.discovery_times.append(discovery_time)
        
        # Comptage de la complexité/longueur des règles
        self.rule_complexity[length] = self.rule_complexity.get(length, 0) + 1
        
        # Stocker les métriques détaillées
        self.rule_qualities.append({
            'support': support,
            'confidence': confidence,
            'length': length,
            'discovery_time': discovery_time,
            'is_valid': is_valid
        })


@dataclass
class MemoryStats:
    """Statistiques détaillées sur l'utilisation de la mémoire."""
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    memory_samples: List[float] = field(default_factory=list)
    memory_per_rule_mb: float = 0.0
    memory_for_candidates_mb: float = 0.0
    memory_for_cache_mb: float = 0.0
    
    def update(self, current_memory_mb: float, rules_count: int, cache_memory_mb: float = 0.0) -> None:
        """Met à jour les statistiques de mémoire."""
        self.memory_samples.append(current_memory_mb)
        self.peak_memory_mb = max(self.peak_memory_mb, current_memory_mb)
        self.avg_memory_mb = sum(self.memory_samples) / len(self.memory_samples)
        self.memory_per_rule_mb = self.avg_memory_mb / rules_count if rules_count > 0 else 0.0
        self.memory_for_cache_mb = cache_memory_mb
        self.memory_for_candidates_mb = self.avg_memory_mb - cache_memory_mb


@dataclass
class ParallelismStats:
    """Statistiques sur les performances de parallélisation."""
    worker_count: int = 0
    speedup_factor: float = 1.0  # Facteur d'accélération par rapport à une exécution séquentielle
    efficiency: float = 1.0  # Efficacité du parallélisme (speedup / worker_count)
    thread_time: Dict[int, float] = field(default_factory=dict)  # Temps de calcul par thread
    batch_processing_time: float = 0.0
    sequential_equivalent_time: float = 0.0  # Temps estimé pour une exécution séquentielle
    
    def set_speedup(self, sequential_time: float, parallel_time: float, workers: int) -> None:
        """Calcule le facteur d'accélération et l'efficacité."""
        self.speedup_factor = sequential_time / parallel_time if parallel_time > 0 else 1.0
        self.worker_count = workers
        self.efficiency = self.speedup_factor / workers if workers > 0 else 0.0
        self.sequential_equivalent_time = sequential_time


@dataclass
class AlgorithmStats:
    """Statistiques complètes pour un algorithme de découverte de règles."""
    algorithm_name: str
    start_time: float
    end_time: float = 0.0
    total_duration: float = 0.0
    total_rules_discovered: int = 0
    iterations: List[IterationStats] = field(default_factory=list)
    query_stats: QueryStats = field(default_factory=QueryStats)
    cache_stats: CacheStats = field(default_factory=CacheStats)
    rule_stats: RuleStats = field(default_factory=RuleStats)
    memory_stats: MemoryStats = field(default_factory=MemoryStats)
    parallelism_stats: ParallelismStats = field(default_factory=ParallelismStats)
    
    # Statistiques spécifiques aux différents algorithmes
    backtracking_overhead: Dict[str, float] = field(default_factory=dict)  # Pour DFS
    search_width_depth: Dict[str, List[int]] = field(default_factory=lambda: {"width": [], "depth": []})  # Pour comparer BFS/DFS
    early_termination_stats: Dict[str, Any] = field(default_factory=dict)
    first_rule_time: float = 0.0
    
    def complete(self) -> None:
        """Finalise les statistiques de l'algorithme."""
        self.end_time = time.time()
        self.total_duration = self.end_time - self.start_time
        
        if self.iterations:
            # Calculer le temps moyen par itération
            iteration_times = [it.duration for it in self.iterations]
            self.avg_iteration_time = sum(iteration_times) / len(iteration_times) if iteration_times else 0.0
            
            # Calculer le temps moyen par règle
            self.time_per_rule = self.total_duration / self.total_rules_discovered if self.total_rules_discovered > 0 else 0.0
            
            # Calculer des statistiques spécifiques aux algorithmes
            if "dfs" in self.algorithm_name.lower():
                self._compute_dfs_specific_stats()
            elif "bfs" in self.algorithm_name.lower():
                self._compute_bfs_specific_stats()
    
    def _compute_dfs_specific_stats(self) -> None:
        """Calcule des statistiques spécifiques à l'algorithme DFS."""
        total_backtracking = sum(it.backtracking_steps for it in self.iterations)
        total_backtracking_time = sum(it.backtracking_time for it in self.iterations)
        
        self.backtracking_overhead = {
            "total_steps": total_backtracking,
            "total_time": total_backtracking_time,
            "percent_time": (total_backtracking_time / self.total_duration) * 100 if self.total_duration > 0 else 0.0
        }
        
        # Profondeur moyenne des explorations DFS
        depths = [it.search_depth for it in self.iterations if it.search_depth > 0]
        self.search_width_depth["depth"] = depths
        self.search_width_depth["avg_depth"] = sum(depths) / len(depths) if depths else 0.0
    
    def _compute_bfs_specific_stats(self) -> None:
        """Calcule des statistiques spécifiques à l'algorithme BFS."""
        # Largeur moyenne des niveaux BFS
        widths = [it.level_width for it in self.iterations if it.level_width > 0]
        self.search_width_depth["width"] = widths
        self.search_width_depth["avg_width"] = sum(widths) / len(widths) if widths else 0.0
        
        # Profondeur (nombre de niveaux) de l'exploration BFS
        max_level = max([it.search_depth for it in self.iterations]) if self.iterations else 0
        self.search_width_depth["max_level"] = max_level
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit les statistiques en dictionnaire pour la sérialisation JSON."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convertit les statistiques en chaîne JSON formatée."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save_to_file(self, filepath: str) -> None:
        """Sauvegarde les statistiques dans un fichier JSON."""
        with open(filepath, 'w') as f:
            f.write(self.to_json())


class DiscoveryStats:
    """
    Gestionnaire central pour collecter et analyser les statistiques des algorithmes de découverte.
    """
    
    def __init__(self, enable_memory_tracking: bool = True):
        """
        Initialise le gestionnaire de statistiques.
        
        :param enable_memory_tracking: Activer le suivi détaillé de la mémoire (légèrement plus coûteux)
        """
        self.algorithms_stats: Dict[str, AlgorithmStats] = {}
        self.current_algorithm: Optional[str] = None
        self.enable_memory_tracking = enable_memory_tracking
        self._memory_tracker_thread = None
        self._tracking_active = False
        self._monitor_interval = 1.0  # Intervalle de mesure de la mémoire en secondes
    
    def start_algorithm(self, algorithm_name: str) -> None:
        """
        Commence le suivi des statistiques pour un algorithme.
        
        :param algorithm_name: Nom de l'algorithme
        """
        self.current_algorithm = algorithm_name
        start_time = time.time()
        self.algorithms_stats[algorithm_name] = AlgorithmStats(algorithm_name=algorithm_name, start_time=start_time)
        
        # Démarrer le suivi de la mémoire si activé
        if self.enable_memory_tracking and not self._tracking_active:
            self._start_memory_tracking()
    
    def start_iteration(self, iteration_number: int, search_depth: int = 0, level_width: int = 0) -> None:
        """
        Commence le suivi d'une itération.
        
        :param iteration_number: Numéro de l'itération
        :param search_depth: Profondeur actuelle pour DFS ou niveau pour BFS
        :param level_width: Largeur du niveau actuel (pertinent pour BFS)
        """
        if not self.current_algorithm or self.current_algorithm not in self.algorithms_stats:
            logging.warning("No active algorithm tracking. Call start_algorithm first.")
            return
        
        iteration_stats = IterationStats(
            iteration_number=iteration_number,
            time_start=time.time(),
            search_depth=search_depth,
            level_width=level_width
        )
        self.algorithms_stats[self.current_algorithm].iterations.append(iteration_stats)
    
    def end_iteration(
        self, 
        candidates_expanded: int = 0, 
        queries_executed: int = 0,
        rules_discovered: int = 0,
        cache_hits: int = 0,
        cache_misses: int = 0,
        candidates_pruned: int = 0,
        backtracking_steps: int = 0,
        backtracking_time: float = 0.0,
        batch_size: int = 0
    ) -> None:
        """
        Finalise le suivi d'une itération avec les statistiques détaillées.
        
        :param candidates_expanded: Nombre de candidats explorés dans cette itération
        :param queries_executed: Nombre de requêtes exécutées
        :param rules_discovered: Nombre de règles découvertes dans cette itération
        :param cache_hits: Nombre d'accès au cache réussis
        :param cache_misses: Nombre d'accès au cache manqués
        :param candidates_pruned: Nombre de candidats élimés par élagage
        :param backtracking_steps: Nombre d'étapes de retour en arrière (DFS)
        :param backtracking_time: Temps passé en retour en arrière (DFS)
        :param batch_size: Taille du lot traité (pour approches en lots)
        """
        if not self.current_algorithm or self.current_algorithm not in self.algorithms_stats:
            logging.warning("No active algorithm tracking. Call start_algorithm first.")
            return
        
        if not self.algorithms_stats[self.current_algorithm].iterations:
            logging.warning("No active iteration to end. Call start_iteration first.")
            return
        
        current_iteration = self.algorithms_stats[self.current_algorithm].iterations[-1]
        current_iteration.complete()  # Met à jour time_end et mesures de mémoire/CPU
        
        # Mettre à jour les statistiques de l'itération
        current_iteration.candidates_expanded = candidates_expanded
        current_iteration.queries_executed = queries_executed
        current_iteration.rules_discovered = rules_discovered
        current_iteration.cache_hits = cache_hits
        current_iteration.cache_misses = cache_misses
        current_iteration.candidates_pruned = candidates_pruned
        current_iteration.backtracking_steps = backtracking_steps
        current_iteration.backtracking_time = backtracking_time
        current_iteration.batch_size = batch_size
        
        # Mettre à jour le nombre total de règles découvertes
        self.algorithms_stats[self.current_algorithm].total_rules_discovered += rules_discovered
        
        # Mettre à jour les statistiques de cache
        cache_stats = self.algorithms_stats[self.current_algorithm].cache_stats
        cache_stats.hits += cache_hits
        cache_stats.misses += cache_misses
        
        # Si c'est la première règle découverte, enregistrer le temps
        if (rules_discovered > 0 and 
            self.algorithms_stats[self.current_algorithm].total_rules_discovered == rules_discovered):
            self.algorithms_stats[self.current_algorithm].first_rule_time = time.time() - self.algorithms_stats[self.current_algorithm].start_time
    
    def record_query(
        self, 
        duration: float, 
        is_batch: bool = False, 
        batch_size: int = 1,
        was_skipped: bool = False
    ) -> None:
        """
        Enregistre les métriques d'une requête exécutée.
        
        :param duration: Durée d'exécution de la requête en secondes
        :param is_batch: True si c'est une requête par lot, False pour requête individuelle
        :param batch_size: Nombre de requêtes dans le lot (pour requêtes par lot)
        :param was_skipped: True si la requête a été évitée (optimisation)
        """
        if not self.current_algorithm or self.current_algorithm not in self.algorithms_stats:
            return
            
        query_stats = self.algorithms_stats[self.current_algorithm].query_stats
        
        if was_skipped:
            query_stats.skipped_queries += 1
        else:
            query_stats.add_query(duration, is_batch, batch_size)
    
    def add_rule(
        self, 
        support: float, 
        confidence: float, 
        length: int,
        is_valid: bool = True
    ) -> None:
        """
        Ajoute les statistiques d'une règle découverte.
        
        :param support: Support de la règle
        :param confidence: Confiance de la règle
        :param length: Longueur/complexité de la règle
        :param is_valid: Si la règle est valide selon les critères de qualité
        """
        if not self.current_algorithm or self.current_algorithm not in self.algorithms_stats:
            return
            
        algorithm_stats = self.algorithms_stats[self.current_algorithm]
        discovery_time = time.time() - algorithm_stats.start_time
        
        algorithm_stats.rule_stats.add_rule(
            support=support,
            confidence=confidence,
            length=length,
            discovery_time=discovery_time,
            is_valid=is_valid
        )
    
    def update_cache_stats(
        self, 
        entries_count: int, 
        memory_usage_mb: float, 
        evictions: int = 0,
        computation_time_saved: float = 0.0
    ) -> None:
        """
        Met à jour les statistiques détaillées du cache.
        
        :param entries_count: Nombre d'entrées dans le cache
        :param memory_usage_mb: Utilisation mémoire du cache en Mo
        :param evictions: Nombre d'évictions du cache
        :param computation_time_saved: Estimation du temps de calcul économisé
        """
        if not self.current_algorithm or self.current_algorithm not in self.algorithms_stats:
            return
            
        cache_stats = self.algorithms_stats[self.current_algorithm].cache_stats
        cache_stats.entries_count = entries_count
        cache_stats.memory_usage_mb = memory_usage_mb
        cache_stats.evictions = evictions
        cache_stats.computation_time_saved = computation_time_saved
        
        # Mettre à jour les statistiques de mémoire
        memory_stats = self.algorithms_stats[self.current_algorithm].memory_stats
        current_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_stats.update(current_memory, self.algorithms_stats[self.current_algorithm].rule_stats.total_discovered, memory_usage_mb)
    
    def set_parallelism_stats(
        self, 
        worker_count: int, 
        sequential_time: float, 
        parallel_time: float,
        thread_times: Dict[int, float] = None,
        batch_processing_time: float = 0.0
    ) -> None:
        """
        Configure les statistiques de parallélisation.
        
        :param worker_count: Nombre de workers/threads utilisés
        :param sequential_time: Temps estimé pour exécution séquentielle
        :param parallel_time: Temps réel avec parallélisation
        :param thread_times: Temps de calcul par thread/worker
        :param batch_processing_time: Temps de traitement par lots
        """
        if not self.current_algorithm or self.current_algorithm not in self.algorithms_stats:
            return
            
        parallelism_stats = self.algorithms_stats[self.current_algorithm].parallelism_stats
        parallelism_stats.set_speedup(sequential_time, parallel_time, worker_count)
        
        if thread_times:
            parallelism_stats.thread_time = thread_times
            
        parallelism_stats.batch_processing_time = batch_processing_time
    
    def end_algorithm(self) -> Dict[str, Any]:
        """
        Finalise le suivi de l'algorithme actuel et retourne ses statistiques.
        
        :return: Dictionnaire des statistiques de l'algorithme
        """
        if not self.current_algorithm or self.current_algorithm not in self.algorithms_stats:
            return {}
        
        # Arrêter le suivi de la mémoire
        if self.enable_memory_tracking and self._tracking_active:
            self._stop_memory_tracking()
        
        # Finaliser les statistiques de l'algorithme
        algorithm_stats = self.algorithms_stats[self.current_algorithm]
        algorithm_stats.complete()
        
        # Réinitialiser l'algorithme actuel
        current_name = self.current_algorithm
        self.current_algorithm = None
        
        return algorithm_stats.to_dict()
    
    def _start_memory_tracking(self) -> None:
        """Démarre un thread pour surveiller l'utilisation de la mémoire."""
        self._tracking_active = True
        self._memory_tracker_thread = threading.Thread(target=self._memory_monitor, daemon=True)
        self._memory_tracker_thread.start()
    
    def _stop_memory_tracking(self) -> None:
        """Arrête le thread de surveillance de la mémoire."""
        self._tracking_active = False
        if self._memory_tracker_thread:
            self._memory_tracker_thread.join(timeout=1.0)
    
    def _memory_monitor(self) -> None:
        """Fonction exécutée par le thread de surveillance pour mesurer la mémoire périodiquement."""
        while self._tracking_active and self.current_algorithm:
            try:
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                if self.current_algorithm in self.algorithms_stats:
                    self.algorithms_stats[self.current_algorithm].memory_stats.memory_samples.append(memory_mb)
            except:
                pass  # Ignorer les erreurs lors du monitoring
            
            time.sleep(self._monitor_interval)
    
    def compare_algorithms(self, algorithm_names: List[str] = None) -> Dict[str, Any]:
        """
        Compare les performances entre plusieurs algorithmes.
        
        :param algorithm_names: Liste des noms d'algorithmes à comparer, ou None pour tous
        :return: Dictionnaire avec les métriques comparatives
        """
        if algorithm_names is None:
            algorithm_names = list(self.algorithms_stats.keys())
        
        selected_stats = {}
        for name in algorithm_names:
            if name in self.algorithms_stats:
                selected_stats[name] = self.algorithms_stats[name]
        
        if len(selected_stats) <= 1:
            return {"error": "Need at least 2 algorithms to compare"}
        
        # Calculer les statistiques comparatives
        comparison = {
            "execution_time": {name: stats.total_duration for name, stats in selected_stats.items()},
            "rules_discovered": {name: stats.total_rules_discovered for name, stats in selected_stats.items()},
            "time_per_rule": {
                name: stats.total_duration / stats.total_rules_discovered if stats.total_rules_discovered > 0 else 0.0 
                for name, stats in selected_stats.items()
            },
            "first_rule_time": {name: stats.first_rule_time for name, stats in selected_stats.items()},
            "cache_efficiency": {
                name: stats.cache_stats.hit_rate for name, stats in selected_stats.items()
            },
            "memory_usage": {
                name: stats.memory_stats.peak_memory_mb for name, stats in selected_stats.items()
            },
            "query_counts": {
                name: stats.query_stats.total_queries for name, stats in selected_stats.items()
            }
        }
        
        return comparison
    
    def plot_comparison(self, algorithm_names: List[str] = None, save_path: Optional[str] = None) -> None:
        """
        Génère des graphiques comparatifs entre les algorithmes.
        
        :param algorithm_names: Liste des noms d'algorithmes à comparer, ou None pour tous
        :param save_path: Chemin où sauvegarder les graphiques, ou None pour afficher
        """
        comparison = self.compare_algorithms(algorithm_names)
        if "error" in comparison:
            logging.error(comparison["error"])
            return
        
        # Configuration matplotlib pour des graphiques de qualité
        plt.style.use('ggplot')
        plt.rcParams['figure.figsize'] = (12, 8)
        
        # Créer une figure avec 2x2 sous-plots
        fig, axs = plt.subplots(2, 2)
        
        # 1. Temps d'exécution
        algs = list(comparison["execution_time"].keys())
        times = list(comparison["execution_time"].values())
        axs[0, 0].bar(algs, times, color='skyblue')
        axs[0, 0].set_title('Temps d\'exécution total (s)')
        axs[0, 0].set_ylabel('Secondes')
        
        # 2. Nombre de règles découvertes
        rules = list(comparison["rules_discovered"].values())
        axs[0, 1].bar(algs, rules, color='lightgreen')
        axs[0, 1].set_title('Règles découvertes')
        axs[0, 1].set_ylabel('Nombre de règles')
        
        # 3. Temps par règle
        time_per_rule = list(comparison["time_per_rule"].values())
        axs[1, 0].bar(algs, time_per_rule, color='salmon')
        axs[1, 0].set_title('Temps par règle (s)')
        axs[1, 0].set_ylabel('Secondes / règle')
        
        # 4. Utilisation mémoire
        memory = list(comparison["memory_usage"].values())
        axs[1, 1].bar(algs, memory, color='lightcoral')
        axs[1, 1].set_title('Utilisation mémoire (MB)')
        axs[1, 1].set_ylabel('MB')
        
        # Ajuster la mise en page
        plt.tight_layout()
        
        # Sauvegarder ou afficher
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logging.info(f"Comparison plot saved to {save_path}")
        else:
            plt.show()
    
    def generate_full_report(self, output_dir: str, algorithm_names: List[str] = None) -> None:
        """
        Génère un rapport complet avec graphiques et métriques détaillées.
        
        :param output_dir: Répertoire où sauvegarder le rapport
        :param algorithm_names: Liste des algorithmes à inclure, None pour tous
        """
        if algorithm_names is None:
            algorithm_names = list(self.algorithms_stats.keys())
        
        # Créer le répertoire de sortie s'il n'existe pas
        os.makedirs(output_dir, exist_ok=True)
        
        # Rapport comparatif
        if len(algorithm_names) >= 2:
            # Sauvegarder les comparaisons sous forme JSON
            comparison = self.compare_algorithms(algorithm_names)
            with open(os.path.join(output_dir, "comparison.json"), "w") as f:
                json.dump(comparison, f, indent=2)
                
            # Générer les graphiques comparatifs
            self.plot_comparison(
                algorithm_names=algorithm_names,
                save_path=os.path.join(output_dir, "comparison_metrics.png")
            )
            
            # Graphiques supplémentaires de comparaison
            self._plot_queries_comparison(
                algorithm_names,
                save_path=os.path.join(output_dir, "query_comparison.png")
            )
            
            self._plot_cache_comparison(
                algorithm_names,
                save_path=os.path.join(output_dir, "cache_comparison.png")
            )
        
        # Rapports individuels par algorithme
        for name in algorithm_names:
            if name in self.algorithms_stats:
                algo_dir = os.path.join(output_dir, name)
                os.makedirs(algo_dir, exist_ok=True)
                
                # Sauvegarder les statistiques JSON
                self.algorithms_stats[name].save_to_file(
                    os.path.join(algo_dir, "stats.json")
                )
                
                # Générer les graphiques spécifiques à l'algorithme
                self._plot_algorithm_performance(
                    name,
                    save_path=os.path.join(algo_dir, "performance.png")
                )
                
                self._plot_rule_discovery_timeline(
                    name,
                    save_path=os.path.join(algo_dir, "discovery_timeline.png")
                )
                
                self._plot_memory_usage(
                    name,
                    save_path=os.path.join(algo_dir, "memory_usage.png")
                )
                
                self._plot_rule_quality_distribution(
                    name,
                    save_path=os.path.join(algo_dir, "rule_quality.png")
                )
        
        # Générer un rapport HTML résumant les résultats
        self._generate_html_report(output_dir, algorithm_names)
    
    def _plot_queries_comparison(self, algorithm_names: List[str], save_path: Optional[str] = None) -> None:
        """
        Génère un graphique comparant l'utilisation des requêtes entre algorithmes.
        
        :param algorithm_names: Liste des algorithmes à comparer
        :param save_path: Chemin où sauvegarder le graphique
        """
        selected_stats = {
            name: self.algorithms_stats[name] 
            for name in algorithm_names 
            if name in self.algorithms_stats
        }
        
        if not selected_stats:
            return
            
        plt.figure(figsize=(12, 8))
        
        # Préparer les données pour un graphique empilé
        ind = np.arange(len(selected_stats))
        width = 0.6
        
        individual_queries = [stats.query_stats.individual_queries for stats in selected_stats.values()]
        batch_queries = [stats.query_stats.batch_queries for stats in selected_stats.values()]
        skipped_queries = [stats.query_stats.skipped_queries for stats in selected_stats.values()]
        
        p1 = plt.bar(ind, individual_queries, width, color='cornflowerblue')
        p2 = plt.bar(ind, batch_queries, width, bottom=individual_queries, color='lightgreen')
        p3 = plt.bar(ind, skipped_queries, width, 
                     bottom=np.array(individual_queries) + np.array(batch_queries),
                     color='lightcoral')
        
        plt.title('Comparaison des requêtes par algorithme')
        plt.ylabel('Nombre de requêtes')
        plt.xticks(ind, list(selected_stats.keys()))
        plt.legend((p1[0], p2[0], p3[0]), ('Requêtes individuelles', 'Requêtes par lot', 'Requêtes évitées'))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
    
    def _plot_cache_comparison(self, algorithm_names: List[str], save_path: Optional[str] = None) -> None:
        """
        Génère un graphique comparant l'efficacité du cache entre algorithmes.
        
        :param algorithm_names: Liste des algorithmes à comparer
        :param save_path: Chemin où sauvegarder le graphique
        """
        selected_stats = {
            name: self.algorithms_stats[name] 
            for name in algorithm_names 
            if name in self.algorithms_stats
        }
        
        if not selected_stats:
            return
            
        plt.figure(figsize=(12, 8))
        
        # Préparer les données
        names = list(selected_stats.keys())
        hit_rates = [stats.cache_stats.hit_rate * 100 for stats in selected_stats.values()]
        hits = [stats.cache_stats.hits for stats in selected_stats.values()]
        misses = [stats.cache_stats.misses for stats in selected_stats.values()]
        
        # Créer un graphique à double axe Y
        fig, ax1 = plt.subplots(figsize=(12, 8))
        
        color = 'tab:blue'
        ax1.set_xlabel('Algorithme')
        ax1.set_ylabel('Taux de succès du cache (%)', color=color)
        ax1.bar(names, hit_rates, color='skyblue', alpha=0.7)
        ax1.tick_params(axis='y', labelcolor=color)
        
        ax2 = ax1.twinx()  # Deuxième axe Y
        
        color = 'tab:red'
        ax2.set_ylabel('Nombre d\'accès au cache', color=color)
        ax2.plot(names, hits, 'o-', color='green', label='Succès')
        ax2.plot(names, misses, 'o-', color='red', label='Échecs')
        ax2.tick_params(axis='y', labelcolor=color)
        
        plt.title('Efficacité du cache par algorithme')
        ax2.legend()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
    
    def _plot_algorithm_performance(self, algorithm_name: str, save_path: Optional[str] = None) -> None:
        """
        Génère un graphique de performance détaillé pour un algorithme spécifique.
        
        :param algorithm_name: Nom de l'algorithme
        :param save_path: Chemin où sauvegarder le graphique
        """
        if algorithm_name not in self.algorithms_stats:
            return
            
        stats = self.algorithms_stats[algorithm_name]
        
        if not stats.iterations:
            return
        
        # Préparer les données d'itération
        iteration_nums = [it.iteration_number for it in stats.iterations]
        durations = [it.duration for it in stats.iterations]
        rules_discovered = [it.rules_discovered for it in stats.iterations]
        candidates_expanded = [it.candidates_expanded for it in stats.iterations]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        
        # Graphique supérieur: durée et règles
        ax1.bar(iteration_nums, durations, color='skyblue', alpha=0.7, label='Durée (s)')
        ax1.set_ylabel('Durée (s)')
        ax1.set_title(f'Performance de l\'algorithme {algorithm_name}')
        
        ax1_twin = ax1.twinx()
        ax1_twin.plot(iteration_nums, rules_discovered, 'ro-', label='Règles découvertes')
        ax1_twin.set_ylabel('Règles découvertes', color='r')
        ax1_twin.tick_params(axis='y', labelcolor='r')
        
        # Graphique inférieur: candidates explorés
        ax2.bar(iteration_nums, candidates_expanded, color='lightgreen', label='Candidats explorés')
        ax2.set_xlabel('Itération')
        ax2.set_ylabel('Candidats explorés')
        
        # Légendes
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
    
    def _plot_rule_discovery_timeline(self, algorithm_name: str, save_path: Optional[str] = None) -> None:
        """
        Génère un graphique de la chronologie de découverte des règles.
        
        :param algorithm_name: Nom de l'algorithme
        :param save_path: Chemin où sauvegarder le graphique
        """
        if algorithm_name not in self.algorithms_stats:
            return
            
        stats = self.algorithms_stats[algorithm_name]
        rule_stats = stats.rule_stats
        
        if not rule_stats.discovery_times:
            return
            
        plt.figure(figsize=(10, 6))
        
        # Trier les temps de découverte
        discovery_times = sorted(rule_stats.discovery_times)
        rule_count = range(1, len(discovery_times) + 1)
        
        plt.plot(discovery_times, rule_count, 'b-', linewidth=2)
        plt.xlabel('Temps écoulé (secondes)')
        plt.ylabel('Nombre de règles découvertes')
        plt.title(f'Chronologie de découverte des règles - {algorithm_name}')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Ajouter une annotation pour la première règle
        if discovery_times:
            plt.axvline(x=discovery_times[0], color='r', linestyle='--', alpha=0.5)
            plt.annotate(f'Première règle: {discovery_times[0]:.2f}s', 
                        xy=(discovery_times[0], 1),
                        xytext=(discovery_times[0] + 0.2, 2),
                        arrowprops=dict(facecolor='red', shrink=0.05))
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
    
    def _plot_memory_usage(self, algorithm_name: str, save_path: Optional[str] = None) -> None:
        """
        Génère un graphique de l'utilisation de la mémoire au fil du temps.
        
        :param algorithm_name: Nom de l'algorithme
        :param save_path: Chemin où sauvegarder le graphique
        """
        if algorithm_name not in self.algorithms_stats or not self.enable_memory_tracking:
            return
            
        stats = self.algorithms_stats[algorithm_name]
        memory_stats = stats.memory_stats
        
        if not memory_stats.memory_samples:
            return
            
        plt.figure(figsize=(10, 6))
        
        # L'axe X représente un échantillon de temps approximatif
        x_vals = np.linspace(0, stats.total_duration, len(memory_stats.memory_samples))
        
        plt.plot(x_vals, memory_stats.memory_samples, 'g-', linewidth=2)
        plt.xlabel('Temps approximatif (secondes)')
        plt.ylabel('Mémoire utilisée (MB)')
        plt.title(f'Utilisation mémoire - {algorithm_name}')
        
        # Ajouter une ligne horizontale pour le pic de mémoire
        plt.axhline(y=memory_stats.peak_memory_mb, color='r', linestyle='--', alpha=0.5)
        plt.annotate(f'Pic: {memory_stats.peak_memory_mb:.2f} MB', 
                     xy=(x_vals[-1]/2, memory_stats.peak_memory_mb),
                     xytext=(x_vals[-1]/2, memory_stats.peak_memory_mb + 20),
                     arrowprops=dict(facecolor='red', shrink=0.05))
        
        plt.grid(True, linestyle='--', alpha=0.7)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
    
    def _plot_rule_quality_distribution(self, algorithm_name: str, save_path: Optional[str] = None) -> None:
        """
        Génère un graphique de la distribution de qualité des règles.
        
        :param algorithm_name: Nom de l'algorithme
        :param save_path: Chemin où sauvegarder le graphique
        """
        if algorithm_name not in self.algorithms_stats:
            return
            
        stats = self.algorithms_stats[algorithm_name]
        rule_stats = stats.rule_stats
        
        if not rule_stats.rule_qualities:
            return
        
        plt.figure(figsize=(12, 10))
        
        # Support et confiance
        supports = [rule["support"] for rule in rule_stats.rule_qualities]
        confidences = [rule["confidence"] for rule in rule_stats.rule_qualities]
        
        # Préparer un graphique à 2x2 panneaux
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        
        # 1. Histogramme du support
        ax1.hist(supports, bins=20, color='skyblue', alpha=0.7)
        ax1.set_xlabel('Support')
        ax1.set_ylabel('Nombre de règles')
        ax1.set_title('Distribution du support')
        
        # 2. Histogramme de la confiance
        ax2.hist(confidences, bins=20, color='lightgreen', alpha=0.7)
        ax2.set_xlabel('Confiance')
        ax2.set_ylabel('Nombre de règles')
        ax2.set_title('Distribution de la confiance')
        
        # 3. Nuage de points support vs. confiance
        ax3.scatter(supports, confidences, alpha=0.7)
        ax3.set_xlabel('Support')
        ax3.set_ylabel('Confiance')
        ax3.set_title('Support vs. Confiance')
        
        # 4. Distribution de la longueur des règles
        lengths = [rule["length"] for rule in rule_stats.rule_qualities]
        ax4.hist(lengths, bins=range(1, max(lengths) + 2), color='salmon', alpha=0.7, rwidth=0.8)
        ax4.set_xlabel('Longueur de la règle')
        ax4.set_ylabel('Nombre de règles')
        ax4.set_title('Distribution de la complexité des règles')
        
        plt.tight_layout()
        plt.suptitle(f'Qualité des règles - {algorithm_name}', fontsize=16, y=1.05)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
    
    def _generate_html_report(self, output_dir: str, algorithm_names: List[str]) -> None:
        """
        Génère un rapport HTML récapitulatif.
        
        :param output_dir: Répertoire de sortie
        :param algorithm_names: Liste des algorithmes à inclure
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rapport de performance des algorithmes de découverte de règles</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333366; }}
                h2 {{ color: #666699; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                img {{ max-width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <h1>Rapport de performance des algorithmes de découverte de règles</h1>
            <p>Généré le {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <h2>Résumé comparatif</h2>
            
            <table>
                <tr>
                    <th>Algorithme</th>
                    <th>Temps d'exécution (s)</th>
                    <th>Règles découvertes</th>
                    <th>Temps par règle (s)</th>
                    <th>Requêtes exécutées</th>
                    <th>Mémoire max (MB)</th>
                    <th>Cache hit rate (%)</th>
                </tr>
        """
        
        # Ajouter une ligne pour chaque algorithme
        for name in algorithm_names:
            if name in self.algorithms_stats:
                stats = self.algorithms_stats[name]
                html_content += f"""
                <tr>
                    <td>{name}</td>
                    <td>{stats.total_duration:.2f}</td>
                    <td>{stats.total_rules_discovered}</td>
                    <td>{stats.total_duration / stats.total_rules_discovered if stats.total_rules_discovered > 0 else 0:.4f}</td>
                    <td>{stats.query_stats.total_queries}</td>
                    <td>{stats.memory_stats.peak_memory_mb:.2f}</td>
                    <td>{stats.cache_stats.hit_rate * 100:.2f}%</td>
                </tr>
                """
        
        html_content += """
            </table>
            
            <h2>Graphiques comparatifs</h2>
            
            <div>
                <h3>Comparaison des métriques principales</h3>
                <img src="comparison_metrics.png" alt="Comparaison des métriques principales">
            </div>
            
            <div>
                <h3>Comparaison des requêtes</h3>
                <img src="query_comparison.png" alt="Comparaison des requêtes">
            </div>
            
            <div>
                <h3>Efficacité du cache</h3>
                <img src="cache_comparison.png" alt="Efficacité du cache">
            </div>
            
            <h2>Rapports détaillés par algorithme</h2>
        """
        
        # Ajouter des liens vers les rapports détaillés
        for name in algorithm_names:
            if name in self.algorithms_stats:
                html_content += f"""
                <div>
                    <h3>{name}</h3>
                    <p><a href="{name}/stats.json">Statistiques détaillées (JSON)</a></p>
                    <p>Performance: <img src="{name}/performance.png" alt="Performance {name}"></p>
                    <p>Chronologie de découverte: <img src="{name}/discovery_timeline.png" alt="Chronologie {name}"></p>
                    <p>Qualité des règles: <img src="{name}/rule_quality.png" alt="Qualité des règles {name}"></p>
                </div>
                """
        
        html_content += """
        </body>
        </html>
        """
        
        # Écrire le fichier HTML
        with open(os.path.join(output_dir, "report.html"), "w") as f:
            f.write(html_content)