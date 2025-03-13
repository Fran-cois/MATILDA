from typing import Generator, Optional, Any, Dict, List, Set, Tuple
from queue import PriorityQueue
from dataclasses import dataclass
import concurrent.futures
import pickle
import time
import logging
import os
import json
from pathlib import Path

from algorithms.base_algorithm import BaseAlgorithm
from algorithms.MATILDA.rule_discovery_core import RuleDiscoveryCore
from utils.rules import Rule, TGDRuleFactory, TGDRule, EGDRule,FunctionalDependency
from algorithms.MATILDA.rule_types import tgd_discovery, egd_discovery
from algorithms.MATILDA.compatibility_checker import CompatibilityChecker


class MATILDA(BaseAlgorithm):
    """
    MATILDA algorithm for discovering tuple-generating dependencies (TGDs) and
    equality-generating dependencies (EGDs) in a database.
    """

    def __init__(self, database: object, settings: Optional[dict] = None):
        """
        Initialize the MATILDA algorithm with a database inspector and optional settings.

        :param database: The database inspector object.
        :param settings: Optional settings for the algorithm.
        """
        self.db_inspector = database
        self.settings = settings or {}
        
        # Configure logging
        log_level = self.settings.get('log_level', 'INFO')
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {log_level}')
        
        log_file = self.settings.get('log_file', 'matilda.log')
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('MATILDA')
        
        # Initialize rule discovery core
        enable_stats = self.settings.get('enable_stats', True)
        track_memory = self.settings.get('track_memory', True)
        
        search_algorithm = self.settings.get('search_algorithm', 'dfs')
        core_settings = self.settings.copy()
        core_settings.update({
            'enable_detailed_stats': enable_stats,
            'track_memory': track_memory,
            'db_engine_accessor': self.get_db_engine  # Passer une référence à notre méthode d'accès
        })
        
        self.discovery_core = RuleDiscoveryCore(database, core_settings)
        self.rule_cache = {}  # Cache discovered rules to avoid duplicate computation
        
        # Initialize statistics tracking
        self.stats = {
            "tgd_discovery_time": 0,
            "egd_discovery_time": 0,
            "fd_discovery_time": 0,  # Nouveau pour FD
            "tgds_discovered": 0,
            "egds_discovered": 0,
            "fds_discovered": 0,     # Nouveau pour FD
            "tgd_avg_support": 0,
            "tgd_avg_confidence": 0,
            "egd_avg_support": 0,
            "egd_avg_confidence": 0,
            "fd_avg_support": 0,     # Nouveau pour FD
            "fd_avg_confidence": 0    # Nouveau pour FD
        }

        # Initialiser des listes pour stocker les règles découvertes
        self.discovered_tgds = []
        self.discovered_egds = []
        self.discovered_fds = []  # Nouvelle liste pour stocker les FDs découvertes

        # Liste des modes de compatibilité disponibles
        self.compatibility_modes = {
            # Modes standards
            "fk": CompatibilityChecker.MODE_FK,
            "full": CompatibilityChecker.MODE_FULL,
            "hybrid": CompatibilityChecker.MODE_HYBRID,
            "overlap": CompatibilityChecker.MODE_OVERLAP,
            # Modes spécifiques
            "semantic": CompatibilityChecker.MODE_SEMANTIC,
            "pattern": CompatibilityChecker.MODE_PATTERN,
            "distribution": CompatibilityChecker.MODE_DISTRIBUTION,
            "subset": CompatibilityChecker.MODE_SUBSET,
            "temporal": CompatibilityChecker.MODE_TEMPORAL,
            # Modes optimisés pour la détection des EGDs
            "eq_sample": CompatibilityChecker.MODE_EQ_SAMPLE,
            "cardinality": CompatibilityChecker.MODE_CARD_RATIO,
            "uniqueness": CompatibilityChecker.MODE_UNIQUE_RATIO,
            "key": CompatibilityChecker.MODE_KEY_CANDIDATE,
            "egd": CompatibilityChecker.MODE_EGD,
            # Mode optimisé pour la détection des FDs
            "fd": CompatibilityChecker.MODE_FD,
        }
        
        # Mode de compatibilité par défaut
        self.default_compatibility_mode = "fk"

    def discover_rules(self, **kwargs) -> Generator[Rule, None, None]:
        """
        Discover rules based on the provided database and settings.
        Supports mining TGDs, EGDs, FDs, or combinations.

        :param kwargs: Optional parameters to override default settings.
            - dependency_type (str): Type of dependency to mine ('tgd', 'egd', 'fd', or 'all').
            - nb_occurrence (int): Minimum number of occurrences for a rule to be considered.
            - max_table (int): Maximum number of tables involved in a rule.
            - max_vars (int): Maximum number of variables in a rule.
            - min_support (float): Minimum support threshold (0.0-1.0)
            - min_confidence (float): Minimum confidence threshold (0.0-1.0)
            - parallel (bool): Whether to run discovery in parallel
            - max_workers (int): Maximum number of parallel workers
            - compatibility_mode (str): Mode de compatibilité à utiliser ('fk', 'semantic', 'egd', 'fd', etc.)
            - search_algorithm (str): The search algorithm to use (dfs, bfs, a_star, etc.)
            - algorithm_params (dict): Specific parameters for the chosen algorithm
            - resume_checkpoint (str): Path to a checkpoint file to resume search
            - checkpoint_interval (int): Save checkpoint after discovering this many rules
            - enable_checkpoint (bool): Whether to save checkpoints during discovery (default: True)
            - stats_output_dir (str): Directory for storing detailed performance stats
            - filter_redundant (bool): Whether to filter redundant rules
        :return: A generator yielding discovered Rules (TGDRules, EGDRules and/or FunctionalDependencies).
        """
        # Extract parameters
        dependency_type = kwargs.get("dependency_type", self.settings.get("dependency_type", "egd"))
        nb_occurrence = kwargs.get("nb_occurrence", self.settings.get("nb_occurrence", 2))
        max_table = kwargs.get("max_table", self.settings.get("max_table", 3))
        max_vars = kwargs.get("max_vars", self.settings.get("max_vars", 6))
        results_path = kwargs.get("results_dir", self.settings.get("results_dir", "results"))
        min_support = kwargs.get("min_support", self.settings.get("min_support", 0.0))
        min_confidence = kwargs.get("min_confidence", self.settings.get("min_confidence", 0.0))
        parallel = kwargs.get("parallel", self.settings.get("parallel", False))
        filter_redundant = kwargs.get("filter_redundant", self.settings.get("filter_redundant", True))
        checkpoint_interval = kwargs.get("checkpoint_interval", self.settings.get("checkpoint_interval", 100))
        enable_checkpoint = kwargs.get("enable_checkpoint", self.settings.get("enable_checkpoint", False))
        
        # Récupérer le mode de compatibilité
        compatibility_mode = kwargs.get("compatibility_mode", self.settings.get("compatibility_mode", self.default_compatibility_mode))
        
        # Convertir la chaîne compatibility_mode en mode de compatibilité réel
        #if isinstance(compatibility_mode, str):
        #    compatibility_mode = self.compatibility_modes.get(compatibility_mode.lower(),
        #                                                     self.compatibility_modes[self.default_compatibility_mode])
        #else:
        #    # Si ce n'est pas une chaîne, supposer que c'est déjà un mode de compatibilité valide
        #    compatibility_mode = compatibility_mode
        
        self.logger.info(f"Using compatibility type: {compatibility_mode} (Mode: {compatibility_mode})")
        
        # Create results folder if it does not exist
        if results_path:
            os.makedirs(results_path, exist_ok=True)
        
        self.logger.info(f"Starting rule discovery with dependency type: {dependency_type}")
        self.logger.info(f"Parameters: max_table={max_table}, max_vars={max_vars}, min_support={min_support}, min_confidence={min_confidence}")
        
        # Initialize lists to store discovered rules for filtering
        discovered_rules = set()
        rule_count = 0

        # Réinitialiser les listes de règles découvertes
        self.discovered_tgds = []
        self.discovered_egds = []
        self.discovered_fds = []  # Réinitialiser aussi les FDs
        
        # Mine based on dependency type
        if dependency_type.lower() in ['tgd', 'all']:
            self.logger.info("=== Beginning TGD Discovery Phase ===")
            tgd_gen = self._discover_tgds(
                nb_occurrence=nb_occurrence,
                max_table=max_table,
                max_vars=max_vars,
                results_path=results_path,
                min_support=min_support,
                min_confidence=min_confidence,
                parallel=parallel,
                compatibility_mode=compatibility_mode,
                **kwargs
            )
            
            tgd_processed = 0
            for rule in tgd_gen:
                tgd_processed += 1
                rule_count += 1
                rule_hash = self._get_rule_hash(rule)
                if rule_hash not in discovered_rules or not filter_redundant:
                    discovered_rules.add(rule_hash)
                    self.stats["tgds_discovered"] += 1
                    
                    if enable_checkpoint and rule_count % checkpoint_interval == 0:
                        self._save_checkpoint(discovered_rules, results_path, rule_count, dependency_type)
                        
                    # Stocker la règle TGD découverte
                    self.discovered_tgds.append(rule)
                    yield rule
                    
                    # Update statistics
                    self.stats["tgd_avg_support"] = ((self.stats["tgd_avg_support"] * (self.stats["tgds_discovered"] - 1)) + 
                                                     rule.accuracy) / self.stats["tgds_discovered"]
                    self.stats["tgd_avg_confidence"] = ((self.stats["tgd_avg_confidence"] * (self.stats["tgds_discovered"] - 1)) + 
                                                        rule.confidence) / self.stats["tgds_discovered"]
            self.logger.info(f"=== TGD Discovery Phase Complete: Processed {tgd_processed} TGDs ===")
        
        if dependency_type.lower() in ['egd', 'all']:
            self.logger.info("=== Beginning EGD Discovery Phase ===")
            egd_gen = self._discover_egds(
                nb_occurrence=nb_occurrence,
                max_table=max_table,
                max_vars=max_vars,
                results_path=results_path,
                min_support=min_support,
                min_confidence=min_confidence,
                parallel=parallel,
                compatibility_mode=compatibility_mode,
                **kwargs
            )
            
            egd_processed = 0
            for rule in egd_gen:
                egd_processed += 1
                rule_count += 1
                rule_hash = self._get_rule_hash(rule)
                if rule_hash not in discovered_rules or not filter_redundant:
                    discovered_rules.add(rule_hash)
                    self.stats["egds_discovered"] += 1
                    
                    if enable_checkpoint and rule_count % checkpoint_interval == 0:
                        self._save_checkpoint(discovered_rules, results_path, rule_count, dependency_type)
                    
                    # Stocker la règle EGD découverte
                    self.discovered_egds.append(rule)
                    yield rule
                    
                    # Update statistics
                    self.stats["egd_avg_support"] = ((self.stats["egd_avg_support"] * (self.stats["egds_discovered"] - 1)) + 
                                                     rule.accuracy) / self.stats["egds_discovered"]
                    self.stats["egd_avg_confidence"] = ((self.stats["egd_avg_confidence"] * (self.stats["egds_discovered"] - 1)) + 
                                                        rule.confidence) / self.stats["egds_discovered"]
            self.logger.info(f"=== EGD Discovery Phase Complete: Processed {egd_processed} EGDs ===")
        
        # Ajout du traitement des FDs
        if dependency_type.lower() in ['fd', 'all']:
            self.logger.info("=== Beginning FD Discovery Phase ===")
            fd_gen = self._discover_fds(
                nb_occurrence=nb_occurrence,
                max_table=max_table,
                max_vars=max_vars,
                results_path=results_path,
                min_support=min_support,
                min_confidence=min_confidence,
                parallel=parallel,
                compatibility_mode=compatibility_mode,
                **kwargs
            )
            
            fd_processed = 0
            for rule in fd_gen:
                fd_processed += 1
                rule_count += 1
                rule_hash = self._get_rule_hash(rule)
                if rule_hash not in discovered_rules or not filter_redundant:
                    discovered_rules.add(rule_hash)
                    self.stats["fds_discovered"] += 1
                    
                    if enable_checkpoint and rule_count % checkpoint_interval == 0:
                        self._save_checkpoint(discovered_rules, results_path, rule_count, dependency_type)
                        
                    # Stocker la règle FD découverte
                    self.discovered_fds.append(rule)
                    yield rule
                    
                    # Update statistics
                    self.stats["fd_avg_support"] = ((self.stats["fd_avg_support"] * (self.stats["fds_discovered"] - 1)) + 
                                                   rule.support) / self.stats["fds_discovered"]
                    self.stats["fd_avg_confidence"] = ((self.stats["fd_avg_confidence"] * (self.stats["fds_discovered"] - 1)) + 
                                                      rule.confidence) / self.stats["fds_discovered"]
            self.logger.info(f"=== FD Discovery Phase Complete: Processed {fd_processed} FDs ===")
        
        # Generate final statistics report
        stats_output_dir = kwargs.get("stats_output_dir", self.settings.get("stats_output_dir", results_path))
        if stats_output_dir:
            os.makedirs(stats_output_dir, exist_ok=True)
            self._save_statistics(stats_output_dir)

    def _discover_tgds(self, **kwargs) -> Generator[TGDRule, None, None]:
        """
        Discover TGDs (Tuple-Generating Dependencies) with optimized processing.
        
        :param kwargs: Parameters forwarded from discover_rules.
        :return: A generator yielding discovered TGDRules.
        """
        # Ajouter plus de détails au log pour diagnostic
        log_params = {k: v for k, v in kwargs.items() if k in ['nb_occurrence', 'max_table', 'max_vars', 'min_support', 'min_confidence', 'compatibility_mode']}
        self.logger.info(f"Starting TGD discovery with parameters: {log_params}")
        start_time = time.time()
        
        min_support = kwargs.get('min_support', 0.0)
        min_confidence = kwargs.get('min_confidence', 0.0)
        parallel = kwargs.get('parallel', False)
        max_workers = kwargs.get('max_workers', os.cpu_count())
        compatibility_mode = kwargs.get('compatibility_mode', self.compatibility_modes[self.default_compatibility_mode])
        
        # Configurer le mode de compatibilité pour le discovery core
        if hasattr(self.discovery_core, 'set_compatibility_mode'):
            self.discovery_core.set_compatibility_mode(compatibility_mode)
            self.logger.debug(f"Set compatibility mode for discovery core: {compatibility_mode}")
        
        # Initialize discovery core if needed
        if not self.discovery_core.initialized:
            try:
                success = self.discovery_core.initialize(
                    min_occurrences=kwargs.get('nb_occurrence', 3),
                    results_path=kwargs.get('results_path', None)
                )
                if not success:
                    self.logger.error("Failed to initialize discovery core for TGDs")
                    return
            except AttributeError as e:
                if "'AlchemyUtility' object has no attribute 'get_engine'" in str(e):
                    self.logger.warning("Erreur lors de l'accès au moteur via get_engine(), "
                                        "utilisation de notre méthode d'adaptation à la place.")
                    # Initialisation manuelle - implémenter si nécessaire
                else:
                    raise e
        
        # Use parallel processing if requested
        if parallel:
            self.logger.info(f"Using parallel TGD discovery with {max_workers} workers")
            yield from self._parallel_discover_tgds(max_workers=max_workers, **kwargs)
        else:
            # Sequential processing
            for rule in self.discovery_core.discover_rules(
                start_node=None,
                max_table=kwargs.get('max_table', 3),
                max_vars=kwargs.get('max_vars', 6),
                algorithm_params=kwargs.get('algorithm_params', {}),
                resume_checkpoint=kwargs.get('resume_checkpoint', None),
            ):
                # Apply quality filters
                if rule.accuracy >= min_support and rule.confidence >= min_confidence:
                    yield rule
        
        elapsed_time = time.time() - start_time
        self.stats["tgd_discovery_time"] = elapsed_time
        self.logger.info(f"Completed TGD discovery in {elapsed_time:.2f} seconds")

    def _parallel_discover_tgds(self, max_workers=None, **kwargs) -> Generator[TGDRule, None, None]:
        """
        Discover TGDs using parallel processing.
        
        :param max_workers: Maximum number of parallel workers.
        :param kwargs: Other discovery parameters.
        :return: Generator yielding TGD rules.
        """
        # Implementation depends on the specifics of how to parallelize the TGD discovery
        # This is a simplified approach - actual implementation would need to be tailored to your system
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Partition the search space (this is a placeholder - the actual implementation
            # would depend on how you can divide the search space effectively)
            tasks = self._create_tgd_discovery_tasks(**kwargs)
            futures = [executor.submit(self._discover_tgds_batch, task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                try:
                    for rule in future.result():
                        yield rule
                except Exception as e:
                    self.logger.error(f"Error in parallel TGD discovery: {e}")

    def _create_tgd_discovery_tasks(self, **kwargs):
        """
        Create tasks for parallel TGD discovery.
        
        :param kwargs: Discovery parameters.
        :return: List of task configurations.
        """
        # This is a placeholder - the actual implementation would depend on your system
        # For example, you might divide by starting nodes, parameter ranges, etc.
        return [kwargs]  # Placeholder

    def _discover_tgds_batch(self, task_config):
        """
        Process a batch of TGD discovery (for parallel execution).
        
        :param task_config: Configuration for this batch.
        :return: List of discovered TGDRules.
        """
        # This is a placeholder - the actual implementation would depend on your system
        return []  # Placeholder

    def _discover_egds(self, **kwargs) -> Generator[EGDRule, None, None]:
        """
        Discover EGDs (Equality-Generating Dependencies) using the rule discovery core.
        
        :param kwargs: Parameters forwarded from discover_rules.
        :return: A generator yielding discovered EGDRules.
        """

        # Ajouter plus de détails au log pour diagnostic
        log_params = {k: v for k, v in kwargs.items() if k in ['nb_occurrence', 'max_table', 'max_vars', 'min_support', 'min_confidence', 'compatibility_mode']}
        self.logger.info(f"Starting EGD discovery with parameters: {log_params}")
        start_time = time.time()
        
        min_support = kwargs.get('min_support', 0.0)
        min_confidence = kwargs.get('min_confidence', 0.0)
        parallel = kwargs.get('parallel', False)
        max_workers = kwargs.get('max_workers', os.cpu_count())
        compatibility_mode = kwargs.get('compatibility_mode', self.compatibility_modes[self.default_compatibility_mode])
        
        # Configurer le mode de compatibilité pour le discovery core
        if hasattr(self.discovery_core, 'set_compatibility_mode'):
            self.discovery_core.set_compatibility_mode(compatibility_mode)
            self.logger.debug(f"Set compatibility mode for discovery core: {compatibility_mode}")
        
        # Configurer le core pour la découverte des EGDs
        if hasattr(self.discovery_core, 'set_dependency_type'):
            self.discovery_core.set_dependency_type('egd')
            self.logger.debug("Set discovery core to discover EGDs")
        
        # Initialize discovery core if needed
        if not self.discovery_core.initialized:
            try:
                success = self.discovery_core.initialize(
                    min_occurrences=kwargs.get('nb_occurrence', 3),
                    results_path=kwargs.get('results_path', None)
                )
                if not success:
                    self.logger.error("Failed to initialize discovery core for EGDs")
                    self.logger.info("Falling back to direct EGD discovery method")
            except AttributeError as e:
                if "'AlchemyUtility' object has no attribute 'get_engine'" in str(e):
                    self.logger.warning("Erreur lors de l'accès au moteur via get_engine(), "
                                        "utilisation de la méthode de découverte EGD alternative.")
                    # Fallback vers l'implémentation directe d'egd_discovery
                else:
                    raise e
        
        # Compteur pour suivre si des règles sont générées
        rules_count = 0
        filtered_count = 0
        timeout_seconds = kwargs.get('timeout', 300)  # 5 minutes par défaut

        self.logger.info("Starting sequential EGD discovery using core")
        # Définir un temps maximum d'exécution avant le fallback
        start_discovery_time = time.time()

        try:
            # Sequential processing using the discovery core
            for rule in self.discovery_core.discover_rules(
                start_node=None,
                max_table=kwargs.get('max_table', 3),
                max_vars=kwargs.get('max_vars', 6),
                algorithm_params=kwargs.get('algorithm_params', {}),
                resume_checkpoint=kwargs.get('resume_checkpoint', None),
                rule_type="egd"
            ):
                # Log pour déboguer le type de règle
                self.logger.debug(f"Found rule: {type(rule).__name__} - {rule}")

                # Verify if this is an EGD rule
                if not isinstance(rule, EGDRule):
                    self.logger.warning(f"Non-EGD rule encountered: {type(rule).__name__}")
                    # Try to convert if it's a string or dict representation
                    if isinstance(rule, dict) and 'body' in rule and 'head_variables' in rule:
                        try:
                            # Attempt to convert dict to EGDRule
                            rule = EGDRule(body=rule['body'], head_variables=rule['head_variables'],
                                          accuracy=rule.get('accuracy', 0.0),
                                          confidence=rule.get('confidence', 0.0))
                        except Exception as e:
                            self.logger.error(f"Failed to convert dict to EGDRule: {e}")
                            continue
                    elif isinstance(rule, str):
                        try:
                            # Attempt to parse string as EGD rule
                            rule = EGDRule.str_to_egd(rule)
                        except Exception as e:
                            self.logger.error(f"Failed to parse string as EGDRule: {e}")
                            continue
                    else:
                        self.logger.warning(f"Skipping non-convertible rule: {rule}")
                        continue
                rules_count += 1

                # Apply quality filters with more lenient defaults for initial testing
                if hasattr(rule, 'accuracy') and hasattr(rule, 'confidence'):
                    if rule.accuracy >= min_support and rule.confidence >= min_confidence:
                        self.logger.debug(f"Yielding EGD rule with acc={rule.accuracy:.2f}, conf={rule.confidence:.2f}")
                        yield rule
                    else:
                        filtered_count += 1
                        self.logger.debug(f"Filtered EGD rule: acc={rule.accuracy:.2f}, conf={rule.confidence:.2f}")
                else:
                    # Si la règle n'a pas de métriques de qualité, on l'accepte quand même
                    self.logger.debug("Rule without quality metrics, yielding anyway")
                    yield rule

                # Check timeout
                if time.time() - start_discovery_time > timeout_seconds:
                    self.logger.warning(f"Core EGD discovery timeout after {timeout_seconds}s. Found {rules_count} rules.")
                    break

        except Exception as e:
            self.logger.error(f"Error during core EGD discovery: {e}")
            self.logger.info("Falling back to direct EGD discovery method")
        
        # Si aucune règle n'est trouvée avec le core, utiliser la méthode de repli
        if rules_count == 0:
            self.logger.warning("No EGD rules found with core method, trying fallback method")
        else:
            self.logger.info(f"Core EGD discovery found {rules_count} rules, yielded {rules_count - filtered_count} after filtering")
        
        elapsed_time = time.time() - start_time
        self.stats["egd_discovery_time"] = elapsed_time
        self.logger.info(f"Completed EGD discovery in {elapsed_time:.2f} seconds")

    def _parallel_discover_egds(self, cg, mapper, max_workers=None, **kwargs) -> Generator[EGDRule, None, None]:
        """
        Discover EGDs using parallel processing.
        
        :param cg: Constraint graph.
        :param mapper: Attribute mapper.
        :param max_workers: Maximum number of parallel workers.
        :param kwargs: Other discovery parameters.
        :return: Generator yielding EGD rules.
        """
        # Implementation depends on the specifics of how to parallelize the EGD discovery
        # This is a simplified approach - actual implementation would need to be tailored to your system
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Partition the search space (this is a placeholder - the actual implementation
            # would depend on how you can divide the search space effectively)
            tasks = self._create_egd_discovery_tasks(cg, mapper, **kwargs)
            futures = [executor.submit(self._discover_egds_batch, task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                try:
                    for rule in future.result():
                        yield rule
                except Exception as e:
                    self.logger.error(f"Error in parallel EGD discovery: {e}")

    def _create_egd_discovery_tasks(self, cg, mapper, **kwargs):
        """
        Create tasks for parallel EGD discovery.
        
        :param cg: Constraint graph.
        :param mapper: Attribute mapper.
        :param kwargs: Discovery parameters.
        :return: List of task configurations.
        """
        # This is a placeholder - the actual implementation would depend on your system
        return [{"cg": cg, "mapper": mapper, **kwargs}]  # Placeholder

    def _discover_egds_batch(self, task_config):
        """
        Process a batch of EGD discovery (for parallel execution).
        
        :param task_config: Configuration for this batch.
        :return: List of discovered EGDRules.
        """
        # This is a placeholder - the actual implementation would depend on your system
        return []  # Placeholder

    def _discover_fds(self, **kwargs) -> Generator[FunctionalDependency, None, None]:
        """
        Discover FDs (Functional Dependencies) using the rule discovery core.
        
        :param kwargs: Parameters forwarded from discover_rules.
        :return: A generator yielding discovered FunctionalDependencies.
        """
        # Ajouter plus de détails au log pour diagnostic
        log_params = {k: v for k, v in kwargs.items() if k in ['nb_occurrence', 'max_table', 'max_vars', 'min_support', 'min_confidence', 'compatibility_mode']}
        self.logger.info(f"Starting FD discovery with parameters: {log_params}")
        start_time = time.time()
        
        min_support = kwargs.get('min_support', 0.0)
        min_confidence = kwargs.get('min_confidence', 0.0)
        parallel = kwargs.get('parallel', False)
        max_workers = kwargs.get('max_workers', os.cpu_count())

        # Configurer le core pour la découverte des FDs
        if hasattr(self.discovery_core, 'set_dependency_type'):
            self.discovery_core.set_dependency_type('fd')
            self.logger.debug("Set discovery core to discover FDs")
        
        # Initialize discovery core if needed
        if not self.discovery_core.initialized:
            try:
                success = self.discovery_core.initialize(
                    min_occurrences=kwargs.get('nb_occurrence', 3),
                    results_path=kwargs.get('results_path', None),
                    rule_type='fd'  # Spécifier qu'on cherche des FDs
                )
                if not success:
                    self.logger.error("Failed to initialize discovery core for FDs")
                    return
            except AttributeError as e:
                if "'AlchemyUtility' object has no attribute 'get_engine'" in str(e):
                    self.logger.warning("Erreur lors de l'accès au moteur via get_engine(), "
                                        "utilisation de la méthode de découverte FD alternative.")
                    # Fallback vers l'implémentation directe de fd_discovery
                    return e
                else:
                    raise e
        
        # Compteur pour suivre si des règles sont générées
        rules_count = 0
        filtered_count = 0
        timeout_seconds = kwargs.get('timeout', 300)  # 5 minutes par défaut

        self.logger.info("Starting sequential FD discovery using core")
        # Définir un temps maximum d'exécution avant le fallback
        start_discovery_time = time.time()

        try:
            # Sequential processing using the discovery core
            for rule in self.discovery_core.discover_rules(
                start_node=None,
                max_table=kwargs.get('max_table', 3),
                max_vars=kwargs.get('max_vars', 6),
                algorithm_params=kwargs.get('algorithm_params', {}),
                resume_checkpoint=kwargs.get('resume_checkpoint', None),
                rule_type="fd"  # Spécifier qu'on cherche des FDs
            ):
                # Log pour déboguer le type de règle
                self.logger.debug(f"Found rule: {type(rule).__name__} - {rule}")

                # Verify if this is a FD rule

                    
                rules_count += 1

                # Apply quality filters
                if hasattr(rule, 'support') and hasattr(rule, 'confidence'):
                    if rule.support >= min_support and rule.confidence >= min_confidence:
                        self.logger.debug(f"Yielding FD rule with support={rule.support:.2f}, conf={rule.confidence:.2f}")
                        yield rule
                    else:
                        filtered_count += 1
                        self.logger.debug(f"Filtered FD rule: support={rule.support:.2f}, conf={rule.confidence:.2f}")
                else:
                    # Si la règle n'a pas de métriques de qualité, on l'accepte quand même
                    self.logger.debug("Rule without quality metrics, yielding anyway")
                    yield rule

                # Check timeout
                if time.time() - start_discovery_time > timeout_seconds:
                    self.logger.warning(f"Core FD discovery timeout after {timeout_seconds}s. Found {rules_count} rules.")
                    break

        except Exception as e:
            self.logger.error(f"Error during core FD discovery: {e}")
            self.logger.info("Falling back to direct FD discovery method")
            return

        
        # Si aucune règle n'est trouvée avec le core, utiliser la méthode de repli

        self.logger.info(f"Core FD discovery found {rules_count} rules, yielded {rules_count - filtered_count} after filtering")
        
        elapsed_time = time.time() - start_time
        self.stats["fd_discovery_time"] = elapsed_time
        self.logger.info(f"Completed FD discovery in {elapsed_time:.2f} seconds")

    
    def _get_rule_hash(self, rule: Rule) -> str:
        """
        Create a unique hash for a rule to identify duplicates.
        
        :param rule: The rule to hash.
        :return: A string hash representing the rule.
        """
        if isinstance(rule, TGDRule):
            # For TGD rules, hash the body and head predicates
            body_str = "".join(sorted(str(p) for p in rule.body))
            head_str = "".join(sorted(str(p) for p in rule.head))
            return f"TGD_{hash(body_str + head_str)}"
        elif isinstance(rule, EGDRule):
            # Pour les EGDs, utiliser le corps et les variables d'égalité
            body_str = "".join(sorted(str(p) for p in rule.body))
            head_vars_str = "".join(sorted(f"{a}={b}" for a, b in rule.head_variables))
            return f"EGD_{hash(body_str + head_vars_str)}"
        else:
            # For other rule types
            return str(hash(str(rule)))

    def _save_checkpoint(self, discovered_rules: Set[str], results_path: str, rule_count: int, dependency_type: str) -> None:
        """
        Save discovery checkpoint for possible resumption.
        
        :param discovered_rules: Set of discovered rule hashes.
        :param results_path: Path to save the checkpoint.
        :param rule_count: Current count of rules discovered.
        :param dependency_type: Type of dependency being mined.
        """
        checkpoint_path = os.path.join(results_path, f"checkpoint_{dependency_type}_{rule_count}.pkl")
        try:
            with open(checkpoint_path, 'wb') as f:
                pickle.dump({
                    'discovered_rules': discovered_rules,
                    'rule_count': rule_count,
                    'stats': self.stats,
                    'timestamp': time.time()
                }, f)
            self.logger.info(f"Saved checkpoint to {checkpoint_path} after {rule_count} rules")
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")

    def _save_statistics(self, output_dir: str) -> None:
        """
        Save detailed discovery statistics to JSON and generate HTML report.
        
        :param output_dir: Directory to save statistics.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Save raw statistics as JSON
        stats_path = os.path.join(output_dir, "matilda_stats.json")
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        # Generate HTML report using the dedicated generator
        from utils.html_report_generator import HtmlReportGenerator
        html_report_path = os.path.join(output_dir, "matilda_report.html")
        report_generator = HtmlReportGenerator(logger=self.logger)
        report_generator.generate_report(
            output_path=html_report_path,
            stats=self.stats,
            tgd_rules=self.discovered_tgds,
            egd_rules=self.discovered_egds,
            fd_rules=self.discovered_fds  # Ajout des règles FD au rapport
        )
        
        # Exporter les règles au format JSON pour une utilisation ultérieure
        rules_json_path = os.path.join(output_dir, "matilda_rules.json")
        from utils.html_report_generator import export_rules_to_json
        
        # Modification: Adapter l'appel à export_rules_to_json sans le paramètre fd_rules
        try:
            # Tenter d'utiliser la nouvelle signature avec fd_rules
            export_rules_to_json(
                tgd_rules=self.discovered_tgds,
                egd_rules=self.discovered_egds,
                fd_rules=self.discovered_fds,
                output_path=rules_json_path
            )
        except TypeError:
            # Fallback: utiliser la signature existante
            self.logger.warning("La fonction export_rules_to_json ne prend pas en charge le paramètre fd_rules. "
                               "Les règles FD ne seront pas exportées dans le fichier JSON.")
            export_rules_to_json(
                tgd_rules=self.discovered_tgds,
                egd_rules=self.discovered_egds,
                output_path=rules_json_path
            )
        
        self.logger.info(f"Saved discovery statistics to {stats_path}")
        self.logger.info(f"Generated HTML report at {html_report_path}")
        self.logger.info(f"Exported rules to {rules_json_path}")

    def export_rules(self, rules: List[Rule], output_path: str, format: str = "json") -> None:
        """
        Export discovered rules to a file in the specified format.
        
        :param rules: List of rules to export
        :param output_path: Path to save the exported rules
        :param format: Export format ("json", "csv", "sql", "html")
        """
        # Séparer les règles en TGDs et EGDs
        tgd_rules = [rule for rule in rules if isinstance(rule, TGDRule)]
        egd_rules = [rule for rule in rules if isinstance(rule, EGDRule)]
        
        if format.lower() == "json":
            from utils.html_report_generator import export_rules_to_json
            success = export_rules_to_json(tgd_rules, egd_rules, output_path)
            if success:
                self.logger.info(f"Exported {len(rules)} rules to {output_path} in JSON format")
            else:
                self.logger.error(f"Failed to export rules to {output_path} in JSON format")
        elif format.lower() == "csv":
            from utils.html_report_generator import export_rules_to_csv
            success = export_rules_to_csv(tgd_rules, egd_rules, output_path)
            if success:
                self.logger.info(f"Exported {len(rules)} rules to {output_path} in CSV format")
            else:
                self.logger.error(f"Failed to export rules to {output_path} in CSV format")
        elif format.lower() == "html":
            from utils.html_report_generator import HtmlReportGenerator
            report_generator = HtmlReportGenerator(logger=self.logger)
            success = report_generator.generate_report(
                output_path=output_path,
                stats=self.stats,
                tgd_rules=tgd_rules,
                egd_rules=egd_rules
            )
            if success:
                self.logger.info(f"Exported {len(rules)} rules to {output_path} in HTML format")
            else:
                self.logger.error(f"Failed to export rules to {output_path} in HTML format")
        elif format.lower() == "sql":
            self._export_rules_to_sql(rules, output_path)
        else:
            self.logger.error(f"Unsupported export format: {format}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the last rule discovery process.
        
        :return: Dictionary with discovery statistics
        """
        # Combine core stats with our high-level stats
        core_stats = self.discovery_core.get_stats()
        return {**self.stats, **core_stats}

    def load_checkpoint(self, checkpoint_path: str) -> Dict[str, Any]:
        """
        Load a discovery checkpoint to resume processing.
        
        :param checkpoint_path: Path to the checkpoint file
        :return: Checkpoint data
        """
        try:
            with open(checkpoint_path, 'rb') as f:
                checkpoint_data = pickle.load(f)
                self.logger.info(f"Loaded checkpoint from {checkpoint_path} with {checkpoint_data['rule_count']} rules")
                # Restore statistics
                self.stats.update(checkpoint_data.get('stats', {}))
                return checkpoint_data
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return {}

    def _export_rules_to_csv(self, rules: List[Rule], output_path: str) -> None:
        """
        Export rules to CSV format.
        
        :param rules: List of rules to export
        :param output_path: Path to save the exported rules
        """
        import csv
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(["Type", "Display", "Support", "Confidence"])
            
            # Write rules
            for rule in rules:
                rule_type = type(rule).__name__
                support = getattr(rule, 'accuracy', 'N/A')
                confidence = getattr(rule, 'confidence', 'N/A')
                writer.writerow([rule_type, rule.display, support, confidence])
        self.logger.info(f"Exported {len(rules)} rules to {output_path} in CSV format")

    def _export_rules_to_sql(self, rules: List[Rule], output_path: str) -> None:
        """
        Export rules as SQL constraints.
        
        :param rules: List of rules to export
        :param output_path: Path to save the SQL script
        """
        # This is a placeholder - actual implementation would depend on your database
        # and how you want to represent the rules as SQL constraints
        self.logger.warning("SQL export is not fully implemented")
        
        with open(output_path, 'w') as f:
            f.write("-- Generated SQL constraints from MATILDA\n")
            f.write(f"-- Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for rule in rules:
                f.write(f"-- {rule.display}\n")
                # Here you would generate actual SQL based on the rule type
                f.write("-- SQL constraint would go here\n\n")
        self.logger.info(f"Exported {len(rules)} rules to {output_path} in SQL format")

    def get_available_algorithms(self) -> List[str]:
        """
        Get the list of available search algorithms for rule discovery.
        
        :return: List of algorithm names
        """
        # Delegate to the discovery core if available, otherwise provide defaults
        if hasattr(self.discovery_core, 'get_available_algorithms'):
            return self.discovery_core.get_available_algorithms()
        else:
            return [
                'dfs', 'bfs', 'a_star', 'beam_search', 'pattern_growth_search',
                'genetic_search', 'mcts_search', 'random_walk_search'
            ]

    def configure_algorithm(self, algorithm_name: str, **params) -> None:
        """
        Configure a specific search algorithm with parameters.
        
        :param algorithm_name: Name of the algorithm to configure
        :param params: Algorithm-specific parameters
        """
        if algorithm_name not in self.get_available_algorithms():
            self.logger.warning(f"Unknown algorithm: {algorithm_name}. Using default.")
            algorithm_name = 'dfs'
            
        # Update algorithm in settings
        self.settings['search_algorithm'] = algorithm_name
        self.settings['algorithm_params'] = params
        self.logger.info(f"Configured algorithm: {algorithm_name} with parameters: {params}")

    def validate_database(self) -> Dict[str, Any]:
        """
        Validate the database structure and connection for rule discovery.
        
        :return: Dictionary with validation results
        """
        validation_results = {
            "success": False,
            "errors": [],
            "warnings": [],
            "tables": 0,
            "attributes": 0
        }
        
        try:
            # Check if the database connection works
            tables = self.db_inspector.get_table_names()
            validation_results["tables"] = len(tables)
            
            # Count attributes across all tables
            total_attributes = 0
            for table in tables:
                attributes = self.db_inspector.get_attribute_names(table)
                total_attributes += len(attributes)
            validation_results["attributes"] = total_attributes
            
            # Mark as successful if we have tables and attributes
            if validation_results["tables"] > 0 and validation_results["attributes"] > 0:
                validation_results["success"] = True
            else:
                validation_results["warnings"].append("Database has no tables or attributes")
                
        except Exception as e:
            validation_results["errors"].append(f"Database validation error: {str(e)}")
            return validation_results
        return validation_results

    def estimate_discovery_time(self, dependency_type: str = "tgd", **kwargs) -> Dict[str, Any]:
        """
        Estimate the time it will take to complete the rule discovery process.
        
        :param dependency_type: Type of dependency to mine ('tgd', 'egd', or 'all')
        :param kwargs: Additional parameters (same as discover_rules)
        :return: Dictionary with time estimation details
        """
        # Extract relevant parameters
        max_table = kwargs.get("max_table", self.settings.get("max_table", 3))
        max_vars = kwargs.get("max_vars", self.settings.get("max_vars", 6))
        nb_occurrence = kwargs.get("nb_occurrence", self.settings.get("nb_occurrence", 3))
        
        # Create a base estimate using a simple formula (this should be calibrated based on real measurements)
        base_estimate = 0
        tables_factor = 2.5 ** max_table  # Exponential growth with table count
        vars_factor = 1.7 ** max_vars    # Exponential growth with variable count
        occurrence_factor = nb_occurrence ** 1.5  # Superlinear growth with occurrence count
        
        if dependency_type.lower() in ["tgd", "all"]:
            base_estimate += tables_factor * vars_factor * occurrence_factor * 0.5  # seconds
            
        if dependency_type.lower() in ["egd", "all"]:
            base_estimate += tables_factor * vars_factor * occurrence_factor * 0.8  # EGDs are typically more expensive
        
        # Adjust based on database size
        try:
            table_count = len(self.db_inspector.get_table_names())
            # Sample a few tables to estimate average row count
            sampled_tables = self.db_inspector.get_table_names()[:5]
            avg_rows = 1000  # Default estimate
            if sampled_tables:
                row_counts = [self.db_inspector.get_row_count(table) for table in sampled_tables]
                if row_counts:
                    avg_rows = sum(row_counts) / len(row_counts)
            
            # Adjust estimate based on database size
            db_size_factor = (table_count * avg_rows) / 10000  # Normalize to 10K rows
            base_estimate *= max(1.0, db_size_factor)
        except Exception as e:
            self.logger.warning(f"Could not adjust time estimate based on database size: {e}")
            
        # Convert to human-readable format
        hours = int(base_estimate // 3600)
        minutes = int((base_estimate % 3600) // 60)
        seconds = int(base_estimate % 60)
        
        return {
            "seconds": base_estimate,
            "formatted": f"{hours}h {minutes}m {seconds}s",
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "factors": {
                "tables": max_table,
                "variables": max_vars,
                "occurrences": nb_occurrence,
                "dependency_type": dependency_type
            }
        }

    def optimize_parameters(self, target_time_seconds: float = 3600) -> Dict[str, Any]:
        """
        Suggest optimal parameters to complete rule discovery within a target time.
        
        :param target_time_seconds: Target time in seconds (default: 1 hour)
        :return: Dictionary with suggested parameters
        """
        # Start with defaults
        suggested_params = {
            "max_table": self.settings.get("max_table", 3),
            "max_vars": self.settings.get("max_vars", 6),
            "nb_occurrence": self.settings.get("nb_occurrence", 3),
        }
        
        # Simple binary search to find parameters that fit within the target time
        for _ in range(10):  # Maximum iterations
            estimate = self.estimate_discovery_time(**suggested_params)
            if abs(estimate["seconds"] - target_time_seconds) / target_time_seconds < 0.2:
                # Within 20% of target, good enough
                break
            if estimate["seconds"] > target_time_seconds * 1.5:
                # Too slow, reduce parameters
                if suggested_params["max_table"] > 2:
                    suggested_params["max_table"] -= 1
                elif suggested_params["max_vars"] > 4:
                    suggested_params["max_vars"] -= 1
                elif suggested_params["nb_occurrence"] > 2:
                    suggested_params["nb_occurrence"] -= 1
            elif estimate["seconds"] < target_time_seconds * 0.5:
                # Too fast, increase parameters
                if suggested_params["max_table"] < 5:
                    suggested_params["max_table"] += 1
                elif suggested_params["max_vars"] < 8:
                    suggested_params["max_vars"] += 1
                elif suggested_params["nb_occurrence"] < 4:
                    suggested_params["nb_occurrence"] += 1
            else:
                # Close enough
                break
                
        # Final estimate with suggested parameters
        estimate = self.estimate_discovery_time(**suggested_params)
        suggested_params["estimated_time"] = estimate["formatted"]
        suggested_params["estimated_seconds"] = estimate["seconds"]
        return suggested_params

    def set_pruning_thresholds(self, support_threshold: float = 0.0, confidence_threshold: float = 0.0) -> None:
        """
        Set minimum support and confidence thresholds for rule pruning.
        
        :param support_threshold: Minimum support value (0.0-1.0)
        :param confidence_threshold: Minimum confidence value (0.0-1.0)
        """
        # Validate inputs
        if not (0.0 <= support_threshold <= 1.0):
            raise ValueError("Support threshold must be between 0.0 and 1.0")
        if not (0.0 <= confidence_threshold <= 1.0):
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
            
        # Update settings
        self.settings['min_support'] = support_threshold
        self.settings['min_confidence'] = confidence_threshold
        
        # Update the global variable in modules if applicable
        if hasattr(tgd_discovery, 'SPLIT_PRUNING_MEAN_THRESHOLD'):
            tgd_discovery.SPLIT_PRUNING_MEAN_THRESHOLD = (support_threshold + confidence_threshold) / 2
        if hasattr(egd_discovery, 'SPLIT_PRUNING_MEAN_THRESHOLD'):
            egd_discovery.SPLIT_PRUNING_MEAN_THRESHOLD = (support_threshold + confidence_threshold) / 2
        
        self.logger.info(f"Set pruning thresholds - support: {support_threshold}, confidence: {confidence_threshold}")

    def filter_rules(self, rules: List[Rule], min_support: float = 0.0, min_confidence: float = 0.0) -> List[Rule]:
        """
        Filter a list of rules based on support and confidence thresholds.
        
        :param rules: List of rules to filter
        :param min_support: Minimum support threshold
        :param min_confidence: Minimum confidence threshold
        :return: Filtered list of rules
        """
        filtered_rules = []
        for rule in rules:
            if not hasattr(rule, 'accuracy') or not hasattr(rule, 'confidence'):
                # Skip rules without support/confidence
                continue
            if rule.accuracy >= min_support and rule.confidence >= min_confidence:
                filtered_rules.append(rule)
        self.logger.info(f"Filtered {len(rules)} rules down to {len(filtered_rules)} rules")
        return filtered_rules

    def set_compatibility_mode(self, mode_name: str) -> bool:
        """
        Configure le mode de compatibilité à utiliser pour la découverte de règles.
        
        :param mode_name: Nom du mode de compatibilité à utiliser
        :return: True si le mode existe et a été configuré, False sinon
        """
        if mode_name in self.compatibility_modes:
            self.settings['compatibility_mode'] = mode_name
            self.logger.info(f"Mode de compatibilité configuré: {mode_name}")
            return True
        else:
            valid_modes = ", ".join(self.compatibility_modes.keys())
            self.logger.warning(f"Mode de compatibilité inconnu: {mode_name}. "
                                f"Modes valides: {valid_modes}")
            return False

    def get_available_compatibility_modes(self) -> List[str]:
        """
        Retourne la liste des modes de compatibilité disponibles.
        
        :return: Liste des noms des modes de compatibilité
        """
        return list(self.compatibility_modes.keys())

    def get_recommended_compatibility_mode(self, dependency_type: str) -> str:
        """
        Suggère un mode de compatibilité recommandé pour un type de dépendance donné.
        
        :param dependency_type: Type de dépendance ('tgd', 'egd', 'fd', ou 'all')
        :return: Nom du mode de compatibilité recommandé
        """
        if dependency_type.lower() == 'tgd':
            return "fk"     # Mode recommandé pour les TGDs
        elif dependency_type.lower() == 'egd':
            return "egd"    # Mode optimisé pour les EGDs
        elif dependency_type.lower() == 'fd':
            return "fd"     # Mode optimisé pour les FDs
        else:
            return "fk" # Mode par défaut pour les combinaisons

    # Ajouter cette nouvelle méthode
    def get_db_engine(self):
        """
        Méthode adaptateur pour obtenir le moteur de base de données à partir de l'inspecteur.
        Cette méthode est utilisée par le RuleDiscoveryCore pour accéder au moteur sans appeler directement get_engine().
        
        :return: Le moteur de base de données ou un objet équivalent selon l'implémentation de l'inspecteur.
        """
        self.logger.debug("Tentative d'accès au moteur de base de données")
        
        # Vérifier les différentes méthodes possibles pour obtenir le moteur
        if hasattr(self.db_inspector, 'get_engine'):
            return self.db_inspector.get_engine()
        elif hasattr(self.db_inspector, 'engine'):
            return self.db_inspector.engine
        elif hasattr(self.db_inspector, 'get_connection'):
            # Certains inspecteurs fournissent une connexion plutôt qu'un moteur
            return self.db_inspector.get_connection()
        elif hasattr(self.db_inspector, 'connection'):
            return self.db_inspector.connection
        else:
            # Retourner l'inspecteur lui-même s'il n'y a pas de méthode spécifique ou une connexion à la base de données.
            self.logger.warning("Impossible de trouver un moteur ou une connexion à la base de données. "
                                "Retour de l'inspecteur complet.")
            return self.db_inspector

