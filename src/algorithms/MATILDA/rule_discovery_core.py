"""
Module central pour la découverte de règles dans MATILDA.
Gère différents algorithmes de recherche et leur configuration.
"""

import time
import logging
import os
import gc
from typing import List, Dict, Any, Callable, Set, Optional, Generator, Tuple
import tracemalloc
import copy

from database.alchemy_utility import AlchemyUtility
from utils.rules import Rule, TGDRule, EGDRule
from algorithms.MATILDA.constraint_graph import (
    Attribute, AttributeMapper, IndexedAttribute, JoinableIndexedAttributes, ConstraintGraph
)

# Import des différents algorithmes de recherche
from algorithms.MATILDA.discovery_algorithms.dfs_search import dfs
from algorithms.MATILDA.discovery_algorithms.common import (
    CandidateRule, TableOccurrence, extract_table_occurrences
)

# Import conditionnel des autres algorithmes disponibles
try:
    from algorithms.MATILDA.discovery_algorithms.astar_search import a_star_search
except ImportError:
    a_star_search = None

try:
    from algorithms.MATILDA.discovery_algorithms.beam_dfs_search import beam_dfs_search
except ImportError:
    beam_dfs_search = None

# Import des fonctions utilitaires pour la découverte de TGDs
from algorithms.MATILDA.rule_types.tgd_discovery import (
    path_pruning as tgd_path_pruning,
    instantiate_tgd, split_candidate_rule as tgd_split_candidate_rule,
    split_pruning as tgd_split_pruning,
    init as tgd_init
)

# Import conditionnel de la fonction d'instanciation d'objet pour les TGDs
try:
    from algorithms.MATILDA.rule_types.tgd_discovery import instantiate_tgd_object
except ImportError:
    instantiate_tgd_object = None

# Import conditionnel des fonctions utilitaires pour la découverte d'EGDs
try:
    from algorithms.MATILDA.rule_types.egd_discovery import (
        path_pruning as egd_path_pruning,
        instantiate_egd, split_candidate_rule as egd_split_candidate_rule,
        split_pruning as egd_split_pruning,
        init as egd_init
    )
    from algorithms.MATILDA.rule_types.egd_discovery import instantiate_egd_object
except ImportError:
    egd_path_pruning = instantiate_egd = egd_split_candidate_rule = egd_split_pruning = egd_init = instantiate_egd_object = None

# Import conditionnel des fonctions utilitaires pour la découverte de règles de Horn
try:
    from utils.rules import HornRule
    from algorithms.MATILDA.rule_types.horn_discovery import (
        path_pruning as horn_path_pruning,
        instantiate_horn as instantiate_horn, split_candidate_rule as horn_split_candidate_rule,
        split_pruning as horn_split_pruning,
        init as horn_init
    )
    from algorithms.MATILDA.rule_types.horn_discovery import instantiate_horn_object
except ImportError:
    HornRule = None
    horn_path_pruning = instantiate_horn = horn_split_candidate_rule = horn_split_pruning = horn_init = instantiate_horn_object = None

# Import conditionnel des fonctions utilitaires pour la découverte de dépendances fonctionnelles
try:
    from utils.rules import FunctionalDependency
    from algorithms.MATILDA.rule_types.fd_discovery import (
        path_pruning as fd_path_pruning,
        instantiate_fd as instantiate_fd, split_candidate_rule as fd_split_candidate_rule,
        split_pruning as fd_split_pruning,
        init as fd_init
    )
    from algorithms.MATILDA.rule_types.fd_discovery import instantiate_fd_object
except ImportError:
    FunctionalDependency = None
    fd_path_pruning = instantiate_fd = fd_split_candidate_rule = fd_split_pruning = fd_init = instantiate_fd_object = None

from algorithms.MATILDA.compatibility_checker import CompatibilityChecker

# Configurez le logger
logger = logging.getLogger(__name__)

class RuleDiscoveryCore:
    """
    Cœur de la découverte de règles qui gère la coordination des différents algorithmes
    et le suivi des performances.
    """
    # Dictionnaire des algorithmes de recherche disponibles
    SEARCH_ALGORITHMS = {
        'dfs': dfs, # OK
        'a_star': a_star_search,
        'beam_dfs': beam_dfs_search
    }
    
    # Dictionnaire de configuration pour les types de règles
    RULE_CONFIGS = {
        'tgd': {
            'path_pruning': tgd_path_pruning,
            'split_candidate_rule': tgd_split_candidate_rule,
            'split_pruning': tgd_split_pruning,
            'instantiate': instantiate_tgd,
            'rule_class': TGDRule,
            'rule_parser': lambda s, sup, conf: TGDRule.str_to_tgd(s, sup, conf),
            'init': tgd_init,
            'instantiate_object': instantiate_tgd_object
        },
        'egd': {
            'path_pruning': egd_path_pruning,
            'split_candidate_rule': egd_split_candidate_rule,
            'split_pruning': egd_split_pruning,
            'instantiate': instantiate_egd,
            'rule_class': EGDRule,
            'rule_parser': lambda s, sup, conf: EGDRule.str_to_egd(s, sup, conf),
            'init': egd_init,
            'instantiate_object': instantiate_egd_object
        },
        'horn': {
            'path_pruning': horn_path_pruning,
            'split_candidate_rule': horn_split_candidate_rule,
            'split_pruning': horn_split_pruning,
            'instantiate': instantiate_horn,
            'rule_class': HornRule,
            'rule_parser': lambda s, sup, conf: HornRule.str_to_horn(s, sup, conf) if HornRule else None,
            'init': horn_init,
            'instantiate_object': instantiate_horn_object
        },
        'fd': {
            'path_pruning': fd_path_pruning,
            'split_candidate_rule': fd_split_candidate_rule,
            'split_pruning': fd_split_pruning,
            'instantiate': instantiate_fd,
            'rule_class': FunctionalDependency,
            'rule_parser': lambda s, sup, conf: FunctionalDependency.str_to_fd(s, sup, conf) if FunctionalDependency else None,
            'init': fd_init,
            'instantiate_object': instantiate_fd_object
        }
    }
    
    def __init__(self, db_inspector: AlchemyUtility, settings: Dict[str, Any] = None):
        """
        Initialise le cœur de découverte de règles.
        
        :param db_inspector: Inspecteur de base de données pour accéder aux données
        :param settings: Paramètres de configuration
        """
        self.db_inspector = db_inspector
        self.settings = settings or {}
        
        # Initialisation des attributs
        self.constraint_graph = None
        self.mapper = None
        self.jia_list = None
        self.initialized = False
        
        # Configuration des métriques et statistiques
        self.enable_detailed_stats = self.settings.get('enable_detailed_stats', True)
        self.track_memory = self.settings.get('track_memory', True)
        self.stats = {
            'initialization_time': 0,
            'rule_discovery_time': 0,
            'rules_discovered': 0,
            'memory_usage': []
        }
        
        # Configuration des seuils de qualité
        self.min_support = self.settings.get('min_support', 0.0)
        self.min_confidence = self.settings.get('min_confidence', 0.0)
        
        # Initialisation du suivi mémoire si activé
        if self.track_memory:
            tracemalloc.start()
        
        # Mode de compatibilité par défaut
        self._compatibility_mode = CompatibilityChecker.MODE_HYBRID
        self._compatibility_checker = None
        
    def initialize(self, min_occurrences: int = 3, results_path: str = None, rule_type: str = 'tgd') -> bool:
        """
        Initialise le graphe de contrainte et le mappage des attributs.
        Cette étape est nécessaire avant de pouvoir découvrir des règles.
        
        :param min_occurrences: Nombre minimum d'occurrences pour chaque table
        :param results_path: Chemin pour enregistrer les résultats intermédiaires
        :param rule_type: Type de règle à découvrir ('tgd' ou 'egd')
        :return: True si l'initialisation réussit, False sinon
        """
        logger.info(f"Initializing RuleDiscoveryCore for {rule_type} rules...")
        start_time = time.time()
        
        try:
            # Obtenir la fonction d'initialisation appropriée selon le type de règle
            rule_config = self._get_rule_config(rule_type)
            if not rule_config or not rule_config['init']:
                logger.error(f"Initialization function not available for rule type: {rule_type}")
                return False
                
            init_function = rule_config['init']
            
            # Initialiser le graphe de contrainte et le mappage
            self.constraint_graph, self.mapper, self.jia_list = init_function(
                self.db_inspector,
                max_nb_occurrence=min_occurrences,
                results_path=results_path
            )
            
            if not self.constraint_graph or not self.mapper:
                logger.error("Failed to initialize constraint graph or mapper")
                return False
            
            # Initialiser le vérificateur de compatibilité avec le mode configuré
            engine = self.db_inspector.get_engine()
            metadata = self.db_inspector.get_metadata()
            self._compatibility_checker = CompatibilityChecker(engine, metadata, logger=logger)
            
            self.initialized = True
            
            # Enregistrer le temps d'initialisation
            self.stats['initialization_time'] = time.time() - start_time
            logger.info(f"Initialization completed in {self.stats['initialization_time']:.2f} seconds")
            
            # Capturer l'utilisation de la mémoire après initialisation
            if self.track_memory:
                current, peak = tracemalloc.get_traced_memory()
                self.stats['memory_usage'].append({
                    'timestamp': time.time(),
                    'phase': 'initialization',
                    'current_bytes': current,
                    'peak_bytes': peak
                })
                
            return True
            
        except Exception as e:
            logger.exception(f"Error during initialization: {e}")
            return False
    
    def _get_rule_config(self, rule_type: str) -> Dict[str, Any]:
        """
        Récupère la configuration pour un type de règle spécifique.
        
        :param rule_type: Type de règle ('tgd', 'egd', 'horn', 'fd')
        :return: Dictionnaire de configuration pour le type de règle
        """
        rule_type = rule_type.lower()
        if rule_type not in self.RULE_CONFIGS:
            logger.error(f"Unsupported rule type: {rule_type}")
            return {}
        
        config = self.RULE_CONFIGS[rule_type]
        # Vérifier si les fonctions nécessaires sont disponibles
        if any(config[key] is None for key in ['path_pruning', 'split_candidate_rule', 'split_pruning', 'instantiate']):
            logger.error(f"Required functions are not available for rule type: {rule_type}")
            return {}
            
        return config
    
    def get_supported_rule_types(self) -> List[str]:
        """
        Renvoie la liste des types de règles pris en charge et disponibles.
        
        :return: Liste des types de règles disponibles
        """
        return [
            rule_type for rule_type, config in self.RULE_CONFIGS.items() 
            if not any(config[key] is None for key in ['path_pruning', 'split_candidate_rule', 'split_pruning', 'instantiate'])
        ]
    
    def set_compatibility_mode(self, mode):
        """
        Configure le mode de compatibilité à utiliser pour la découverte de règles.
        
        :param mode: Mode de compatibilité (voir CompatibilityChecker.MODE_*)
        """
        self._compatibility_mode = mode
        logger.info(f"Mode de compatibilité configuré dans le core: {mode}")
        
        # Si le checker est déjà initialisé, informer l'utilisateur qu'il faut réinitialiser
        if self._compatibility_checker is not None:
            logger.info("Le vérificateur de compatibilité est déjà initialisé. "
                        "Le nouveau mode sera utilisé pour les prochaines vérifications.")
    
    def discover_rules(self, 
                       start_node=None, 
                       max_table: int = 3, 
                       max_vars: int = 6,
                       search_algorithm: str = 'dfs',
                       algorithm_params: Dict[str, Any] = None,
                       rule_type: str = 'tgd',
                       resume_checkpoint: Dict[str, Any] = None) -> Generator[Rule, None, None]:
        """
        Découvre des règles en utilisant l'algorithme de recherche spécifié.
        
        :param start_node: Nœud de départ pour la recherche (optionnel)
        :param max_table: Nombre maximum de tables par règle
        :param max_vars: Nombre maximum de variables par règle
        :param search_algorithm: Algorithme de recherche à utiliser ('dfs', 'a_star', etc.)
        :param algorithm_params: Paramètres spécifiques à l'algorithme
        :param rule_type: Type de règle à découvrir ('tgd' ou 'egd')
        :param resume_checkpoint: Point de reprise pour continuer une recherche précédente
        :return: Générateur produisant des règles découvertes
        """
        if not self.initialized:
            logger.error("RuleDiscoveryCore not initialized. Call initialize() first.")
            return
        
        # Sélectionner l'algorithme de recherche
        algorithm = self.SEARCH_ALGORITHMS.get(search_algorithm.lower(), dfs)
        if algorithm is None:
            logger.warning(f"Search algorithm '{search_algorithm}' not available, using DFS")
            algorithm = dfs
        
        algorithm_params = algorithm_params or {}
        
        # Obtenir la configuration pour le type de règle spécifié
        rule_config = self._get_rule_config(rule_type)
        if not rule_config:
            logger.error(f"No configuration available for rule type: {rule_type}")
            return
            
        # Extraire les fonctions nécessaires de la configuration
        pruning_fn = rule_config['path_pruning']
        split_candidate_rule_fn = rule_config['split_candidate_rule']
        split_pruning_fn = rule_config['split_pruning']
        instantiate_fn = rule_config['instantiate']
        rule_parser = rule_config['rule_parser']
        instantiate_object_fn = rule_config.get('instantiate_object')
            
        # Démarrer le suivi du temps
        discovery_start_time = time.time()
        
        # Initialiser compteurs
        rules_discovered = 0
        rules_processed = 0
        memory_snapshot_interval = self.settings.get('memory_snapshot_interval', 100)
        
        # Capturer l'utilisation de la mémoire avant la découverte
        if self.track_memory:
            current, peak = tracemalloc.get_traced_memory()
            self.stats['memory_usage'].append({
                'timestamp': time.time(),
                'phase': 'discovery_start',
                'current_bytes': current,
                'peak_bytes': peak
            })
        
        # Stocker les informations de compatibilité pour les fonctions de traitement
        compatibility_mode = algorithm_params.pop('compatibility_mode', self._compatibility_mode)
        compatibility_checker = algorithm_params.pop('compatibility_checker', self._compatibility_checker)
        
        # Adapter la fonction d'élagage pour utiliser les informations de compatibilité
        if pruning_fn and hasattr(pruning_fn, '__closure__') and pruning_fn.__closure__:
            # Si la fonction de pruning est une closure ou accepte des contextes supplémentaires
            original_pruning_fn = pruning_fn
            def wrapped_pruning_fn(candidate_rule, db_inspector, mapper, **kwargs):
                return original_pruning_fn(
                    candidate_rule, 
                    db_inspector, 
                    mapper,
                    compatibility_mode=compatibility_mode,
                    compatibility_checker=compatibility_checker,
                    **kwargs
                )
            pruning_fn = wrapped_pruning_fn
        
        # Lancer la découverte avec l'algorithme choisi
        try:
            # Découvrir les règles candidates
            for candidate_rule in algorithm(
                graph=self.constraint_graph,
                start_node=start_node,
                pruning_prediction=pruning_fn,
                db_inspector=self.db_inspector,
                mapper=self.mapper,
                max_table=max_table,
                max_vars=max_vars,
                **algorithm_params
            ):
                rules_processed += 1
                
                # Prise de mesures mémoire périodiques
                if self.track_memory and rules_processed % memory_snapshot_interval == 0:
                    current, peak = tracemalloc.get_traced_memory()
                    self.stats['memory_usage'].append({
                        'timestamp': time.time(),
                        'phase': f'processing_rule_{rules_processed}',
                        'current_bytes': current,
                        'peak_bytes': peak,
                        'rules_processed': rules_processed
                    })
                
                # Pour chaque candidat, trouver les différentes façons de le diviser en corps/tête
                splits = split_candidate_rule_fn(candidate_rule)
                for split in splits:
                    body, head = split
                    
                    # Évaluer si la division satisfait nos critères de qualité
                    valid, support, confidence = split_pruning_fn(
                        candidate_rule, body, head, self.db_inspector, self.mapper
                    )
                    
                    # Si la division est valide et satisfait nos seuils
                    if True:  # valid :# and support >= self.min_support and confidence >= self.min_confidence:
                        # Si la fonction d'instanciation d'objet est disponible, l'utiliser
                        if instantiate_object_fn:
                            try:

                                rule = instantiate_object_fn(candidate_rule, split, self.mapper, support, confidence)

                                if rule:
                                    rules_discovered += 1
                                    yield rule
                            except Exception as e:
                                logger.error(f"Error instantiating rule object: {e}")
                                continue
                        """else:
                            # Sinon, utiliser l'approche traditionnelle avec chaînes de caractères
                            rule_string = instantiate_fn(candidate_rule, split, self.mapper)
                            
                            if rule_string:
                                try:
                                    rule = rule_parser(rule_string, support, confidence)
                                    rules_discovered += 1
                                    yield rule
                                except Exception as e:
                                    logger.error(f"Error converting rule string to object: {e}")
                                    logger.debug(f"Problematic rule string: {rule_string}")
                                    continue"""
                
                # Libération de mémoire périodique
                if rules_processed % 1000 == 0:
                    gc.collect()
        
        except Exception as e:
            logger.exception(f"Error during rule discovery: {e}")
        
        finally:
            # Mettre à jour les statistiques
            discovery_time = time.time() - discovery_start_time
            self.stats['rule_discovery_time'] += discovery_time
            self.stats['rules_discovered'] += rules_discovered
            
            logger.info(f"Discovery completed in {discovery_time:.2f} seconds")
            logger.info(f"Processed {rules_processed} candidate rules")
            logger.info(f"Discovered {rules_discovered} valid rules")
            
            # Dernière capture de l'utilisation de la mémoire
            if self.track_memory:
                current, peak = tracemalloc.get_traced_memory()
                self.stats['memory_usage'].append({
                    'timestamp': time.time(),
                    'phase': 'discovery_end',
                    'current_bytes': current,
                    'peak_bytes': peak,
                    'rules_processed': rules_processed,
                    'rules_discovered': rules_discovered
                })
    
    # Nous conservons cette méthode comme méthode de secours si les fonctions spécifiques ne sont pas disponibles
    def instantiate_rule_object(self, rule_type, candidate_rule, split, mapper, support, confidence):
        """
        Crée directement un objet Rule à partir d'un candidat et d'un split, sans passer par la représentation en chaîne.
        Cette méthode est utilisée comme secours si les fonctions d'instanciation spécifiques ne sont pas disponibles.
        
        :param rule_type: Type de règle ('tgd', 'egd', 'horn', 'fd')
        :param candidate_rule: Le candidat de règle
        :param split: La division du candidat en corps/tête
        :param mapper: Le mappeur d'attributs
        :param support: Le support de la règle
        :param confidence: La confiance de la règle
        :return: Un objet Rule ou None si l'instanciation échoue
        """
        try:
            rule_config = self._get_rule_config(rule_type)
            if not rule_config:
                logger.error(f"No configuration available for rule type: {rule_type}")
                return None
                
            rule_class = rule_config['rule_class']
            if not rule_class:
                logger.error(f"Rule class not available for rule type: {rule_type}")
                return None
                
            body, head = split
            
            # Obtenir les attributs du corps et de la tête avec leurs tables
            body_attributes = []
            for attr_idx in body:
                indexed_attr = candidate_rule.indexed_attributes[attr_idx]
                attr = mapper.get_attr_from_index(indexed_attr)
                if attr:
                    body_attributes.append((attr.table, attr.column, indexed_attr.variable))
            
            head_attributes = []
            for attr_idx in head:
                indexed_attr = candidate_rule.indexed_attributes[attr_idx]
                attr = mapper.get_attr_from_index(indexed_attr)
                if attr:
                    head_attributes.append((attr.table, attr.column, indexed_attr.variable))
            
            # Création de l'objet de règle selon son type
            if rule_type == 'tgd':
                return TGDRule(body_attributes, head_attributes, support, confidence)
            elif rule_type == 'egd':
                return EGDRule(body_attributes, head_attributes, support, confidence)
            elif rule_type == 'horn' and HornRule:
                return HornRule(body_attributes, head_attributes, support, confidence)
            elif rule_type == 'fd' and FunctionalDependency:
                return FunctionalDependency(body_attributes, head_attributes, support, confidence)
            else:
                logger.error(f"Unsupported rule type for direct object instantiation: {rule_type}")
                return None
                
        except Exception as e:
            logger.exception(f"Error instantiating rule object: {e}")
            return None
    
    def check_compatibility(self, table1, column1, table2, column2, sample_size=100):
        """
        Vérifie la compatibilité entre deux colonnes en utilisant le mode configuré.
        
        :param table1: Première table
        :param column1: Colonne de la première table
        :param table2: Deuxième table
        :param column2: Colonne de la deuxième table
        :param sample_size: Taille de l'échantillon pour les vérifications
        :return: True si compatible, False sinon
        """
        if self._compatibility_checker is None:
            logger.error("Le vérificateur de compatibilité n'est pas initialisé")
            return False
            
        return self._compatibility_checker.is_compatible(
            table1, column1, table2, column2,
            mode=self._compatibility_mode,
            sample_size=sample_size
        )
    
    def get_compatibility_stats(self):
        """
        Récupère les statistiques d'utilisation du cache de compatibilité.
        
        :return: Dictionnaire de statistiques ou None si non initialisé
        """
        if self._compatibility_checker is None:
            return None
            
        return self._compatibility_checker.get_cache_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtient les statistiques de découverte de règles.
        
        :return: Dictionnaire contenant les statistiques
        """
        return self.stats
    
    def get_available_algorithms(self) -> List[str]:
        """
        Obtient la liste des algorithmes de recherche disponibles.
        
        :return: Liste des noms d'algorithmes
        """
        return list(alg for alg, func in self.SEARCH_ALGORITHMS.items() if func is not None)
    
    def cleanup(self):
        """
        Nettoie les ressources utilisées par le module de découverte.
        """
        if self.track_memory:
            tracemalloc.stop()
        
        # Libérer les ressources de mémoire
        self.constraint_graph = None
        self.mapper = None
        self.jia_list = None
        gc.collect()
        
        logger.info("RuleDiscoveryCore resources cleaned up")
