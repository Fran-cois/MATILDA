import logging
from typing import List, Dict, Tuple, Optional, Set, Union, Any, Callable
import time
from functools import lru_cache
import pandas as pd
import numpy as np
from sqlalchemy import MetaData, Table, select, func, create_engine, text
from difflib import SequenceMatcher
from collections import Counter, defaultdict

# Imports pour les transformers
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from colorama import Fore, Style

class CompatibilityChecker:
    """
    Vérifie la compatibilité entre différentes tables/colonnes avec plusieurs modes.
    
    Cette classe fournit diverses méthodes pour vérifier la compatibilité entre colonnes
    de différentes tables, ce qui est utile pour la détection de jointures potentielles,
    la découverte de relations et l'analyse de dépendances génératrices d'égalité.
    """
    
    # Modes de compatibilité existants
    MODE_FULL = "full"
    MODE_FK = "fk"
    MODE_HYBRID = "hybrid"
    MODE_OVERLAP = "overlap"
    MODE_ONE_TABLE = "only_one_table"
    MODE_ALL_COMPATIBLE="all_compatible"
    # Nouveaux modes de compatibilité
    MODE_SEMANTIC = "semantic"         # Compatibilité basée sur la similarité sémantique des noms
    MODE_PATTERN = "pattern"           # Compatibilité basée sur les motifs de données
    MODE_DISTRIBUTION = "distribution" # Compatibilité basée sur les distributions statistiques
    MODE_SUBSET = "subset"             # Vérification si une colonne est sous-ensemble d'une autre
    MODE_TEMPORAL = "temporal"         # Compatibilité spécifique aux données temporelles
    
    # Nouveaux modes simples pour la détection de dépendances génératrices d'égalité
    MODE_EQ_SAMPLE = "equality_sample"       # Vérifie l'égalité sur un échantillon de valeurs
    MODE_CARD_RATIO = "cardinality_ratio"    # Compare le ratio des cardinalités entre colonnes
    MODE_UNIQUE_RATIO = "unique_ratio"       # Évalue le ratio de valeurs uniques
    MODE_KEY_CANDIDATE = "key_candidate"     # Vérifie si une colonne est un candidat clé
    
    # Mode combiné pour l'analyse des dépendances génératrices d'égalité
    MODE_EGD = "egd_detection"       # Combinaison de modes efficaces pour détecter les dépendances d'égalité
    MODE_FD = "fd"

    def __init__(self, engine, metadata: MetaData, logger=None, cache_size: int = 128):
        self.engine = engine
        self.metadata = metadata
        self.logger = logger or logging.getLogger(__name__)
        self._semantic_model = None
        self._cache = {}  # Cache simple pour stocker les résultats précédents
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0
        self._column_types = {}  # Cache pour les types de colonnes
    
    # Décorateur pour mettre en cache les résultats des fonctions fréquemment appelées
    def _cache_result(func):
        def wrapper(self, *args, **kwargs):
            # Créer une clé de cache basée sur la fonction et ses arguments
            cache_key = (func.__name__, args, frozenset(kwargs.items()))
            
            # Vérifier si le résultat est déjà dans le cache
            if cache_key in self._cache:
                self._cache_hits += 1
                return self._cache[cache_key]
            
            # Calculer le résultat
            self._cache_misses += 1
            result = func(self, *args, **kwargs)
            
            # Stocker dans le cache
            if len(self._cache) >= self._cache_size:
                # Simple stratégie d'éviction: supprimer une entrée aléatoire
                self._cache.pop(next(iter(self._cache)))
            self._cache[cache_key] = result
            
            return result
        return wrapper
        
    def is_compatible(self, 
                     table1: str, column1: str, 
                     table2: str, column2: str, 
                     mode: str = MODE_HYBRID,
                     sample_size: int = 1000,
                     confidence_threshold: float = 0.8) -> Union[bool, Dict[str, float]]:
        """
        Vérifie la compatibilité entre deux colonnes selon le mode spécifié.
        
        Args:
            table1: Nom de la première table
            column1: Nom de la colonne dans la première table
            table2: Nom de la deuxième table
            column2: Nom de la colonne dans la deuxième table
            mode: Mode de compatibilité à utiliser
            sample_size: Taille de l'échantillon pour les modes utilisant l'échantillonnage
            confidence_threshold: Seuil de confiance pour les modes retournant un score
            
        Returns:
            bool ou dict: Résultat de la compatibilité (True/False) ou dictionnaire avec scores
                          de confiance lorsque le mode est MODE_EGD
        """
        # Vérifier le cache avant de calculer
        # cache_key = (table1, column1, table2, column2, mode, sample_size)
        # if cache_key in self._cache:
        #     return self._cache[cache_key]
        
        start_time = time.time()
        mode= self.MODE_OVERLAP
        if mode== self.MODE_ALL_COMPATIBLE:
            return True
        # Mode combiné pour l'analyse EGD
        # if mode == self.MODE_EGD:
        #     result = self._check_egd_compatibility(table1, column1, table2, column2, sample_size)
            
        #     # Mise en cache du résultat
        #     if len(self._cache) >= self._cache_size:
        #         # Stratégie LRU simple
        #         oldest_key = next(iter(self._cache))
        #         self._cache.pop(oldest_key)
        #     self._cache[cache_key] = result
            
        #     execution_time = time.time() - start_time
        #     if execution_time > 1.0:  # Log seulement si l'exécution prend plus d'une seconde
        #         self.logger.info(f"Vérification de compatibilité ({mode}) entre {table1}.{column1} et {table2}.{column2} "
        #                       f"effectuée en {execution_time:.2f}s")
            
        #     return result
        
        # Modes existants
        if mode == self.MODE_ONE_TABLE:
            return table1 == table2
        if mode == self.MODE_FD:
            return table1 == table2 and column1 != column2
        if mode == self.MODE_FK:
            return self._check_fk_compatibility(table1, column1, table2, column2)
            
        if mode == self.MODE_FULL:
            return (self._check_fk_compatibility(table1, column1, table2, column2) and
                   self._check_schema_compatibility(table1, column1, table2, column2) and
                   self._check_value_compatibility(table1, column1, table2, column2))
                   
        if mode == self.MODE_HYBRID:
            return (self._check_fk_compatibility(table1, column1, table2, column2) or
                   self._check_sample_compatibility(table1, column1, table2, column2, sample_size))
                   
        if mode == self.MODE_OVERLAP:
            return self._check_overlap_compatibility(table1, column1, table2, column2, sample_size)
        
        # Nouveaux modes
        if mode == self.MODE_SEMANTIC:
            return self._check_semantic_compatibility(table1, column1, table2, column2)
            
        if mode == self.MODE_PATTERN:
            return self._check_pattern_compatibility(table1, column1, table2, column2, sample_size)
            
        if mode == self.MODE_DISTRIBUTION:
            return self._check_distribution_compatibility(table1, column1, table2, column2)
            
        if mode == self.MODE_SUBSET:
            return self._check_subset_compatibility(table1, column1, table2, column2)
            
        if mode == self.MODE_TEMPORAL:
            return self._check_temporal_compatibility(table1, column1, table2, column2)
        
        # Nouveaux modes simples pour EGD
        if mode == self.MODE_EQ_SAMPLE:
            return self._check_equality_sample(table1, column1, table2, column2, sample_size)
            
        if mode == self.MODE_CARD_RATIO:
            return self._check_cardinality_ratio(table1, column1, table2, column2)
            
        if mode == self.MODE_UNIQUE_RATIO:
            return self._check_unique_ratio(table1, column1, table2, column2)
            
        if mode == self.MODE_KEY_CANDIDATE:
            return self._check_key_candidate(table1, column1)
            
        self.logger.warning(f"Mode de compatibilité inconnu: {mode}, utilisation du mode 'hybrid' par défaut")
        return self.is_compatible(table1, column1, table2, column2, mode=self.MODE_HYBRID)
    
    def _check_fk_compatibility(self, table1: str, column1: str, table2: str, column2: str) -> bool:
        """Vérifie si une relation de clé étrangère existe entre les colonnes."""
        try:
            # Vérifier si table1.column1 référence table2.column2
            for fk in self.metadata.tables[table1].foreign_keys:
                if fk.parent.name == column1:
                    ref_column = fk.column
                    if ref_column.table.name == table2 and ref_column.name == column2:
                        return True
                        
            # Vérifier si table2.column2 référence table1.column1
            for fk in self.metadata.tables[table2].foreign_keys:
                if fk.parent.name == column2:
                    ref_column = fk.column
                    if ref_column.table.name == table1 and ref_column.name == column1:
                        return True
                        
            return False
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification des clés étrangères: {e}")
            return False
    
    def _check_schema_compatibility(self, table1: str, column1: str, table2: str, column2: str) -> bool:
        """Vérifie si les schémas des colonnes sont compatibles."""
        try:
            t1 = self.metadata.tables[table1]
            t2 = self.metadata.tables[table2]
            
            c1_type = str(t1.columns[column1].type)
            c2_type = str(t2.columns[column2].type)
            
            # Types identiques = compatible
            if c1_type == c2_type:
                return True
                
            # Vérification de compatibilité de types numériques
            numeric_types = ['INTEGER', 'INT', 'SMALLINT', 'BIGINT', 'DECIMAL', 'NUMERIC', 'FLOAT', 'REAL']
            if any(t in c1_type.upper() for t in numeric_types) and any(t in c2_type.upper() for t in numeric_types):
                return True
                
            # Vérification de compatibilité de types texte
            text_types = ['VARCHAR', 'CHAR', 'TEXT', 'STRING']
            if any(t in c1_type.upper() for t in text_types) and any(t in c2_type.upper() for t in text_types):
                return True
                
            return False
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification du schéma: {e}")
            return False
            
    def _check_value_compatibility(self, table1: str, column1: str, table2: str, column2: str) -> bool:
        """Vérifie la compatibilité complète des valeurs."""
        try:
            query = f"""
                SELECT COUNT(*) 
                FROM {table1} t1 
                LEFT JOIN {table2} t2 ON t1.{column1} = t2.{column2} 
                WHERE t1.{column1} IS NOT NULL AND t2.{column2} IS NULL
            """
            
            with self.engine.connect() as connection:
                result1 = connection.execute(text(query)).scalar() or 0
                
            query = f"""
                SELECT COUNT(*) 
                FROM {table2} t2 
                LEFT JOIN {table1} t1 ON t2.{column2} = t1.{column1} 
                WHERE t2.{column2} IS NOT NULL AND t1.{column1} IS NULL
            """
            
            with self.engine.connect() as connection:
                result2 = connection.execute(text(query)).scalar() or 0
                
            # Si aucune valeur n'est orpheline, les ensembles sont compatibles
            return result1 == 0 and result2 == 0
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification des valeurs: {e}")
            return False
            
    def _check_sample_compatibility(self, table1: str, column1: str, table2: str, column2: str, sample_size: int) -> bool:
        """Vérifie la compatibilité sur un échantillon de valeurs."""
        try:
            # Obtenir un échantillon de valeurs de la première table
            query = f"""
                SELECT DISTINCT {column1} 
                FROM {table1} 
                WHERE {column1} IS NOT NULL 
                ORDER BY RANDOM() 
                LIMIT {sample_size}
            """
            
            with self.engine.connect() as connection:
                sample_df = pd.read_sql(query, connection)
                
            if sample_df.empty:
                return False
                
            # Vérifier combien de ces valeurs existent dans la deuxième table
            values_list = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) 
                                  for v in sample_df[column1].tolist())
            
            query = f"""
                SELECT COUNT(DISTINCT {column2}) 
                FROM {table2} 
                WHERE {column2} IN ({values_list})
            """
            
            with self.engine.connect() as connection:
                match_count = connection.execute(text(query)).scalar() or 0
                
            # Si au moins 80% des valeurs correspondent, considérer comme compatible
            compatibility_ratio = match_count / len(sample_df)
            return compatibility_ratio >= 0.8
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de l'échantillon: {e}")
            return False
            
    def _check_overlap_compatibility(self, table1: str, column1: str, table2: str, column2: str, sample_size: int) -> bool:
        """Vérifie s'il y a un chevauchement significatif entre les valeurs."""
        try:
            # Compter les valeurs distinctes dans les deux tables
            query1 = f"SELECT COUNT(DISTINCT {column1}) FROM {table1} WHERE {column1} IS NOT NULL"
            query2 = f"SELECT COUNT(DISTINCT {column2}) FROM {table2} WHERE {column2} IS NOT NULL"
            
            with self.engine.connect() as connection:
                count1 = connection.execute(text(query1)).scalar() or 0
                count2 = connection.execute(text(query2)).scalar() or 0
                
            # Compter les valeurs qui se chevauchent
            query_overlap = f"""
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT {column1} FROM {table1} WHERE {column1} IN (
                        SELECT DISTINCT {column2} FROM {table2} WHERE {column2} IS NOT NULL
                    )
                ) t
            """
            
            with self.engine.connect() as connection:
                overlap_count = connection.execute(text(query_overlap)).scalar() or 0
                
            # Calculer le ratio de chevauchement par rapport à la plus petite table
            min_count = min(count1, count2)
            if min_count == 0:
                return False
                
            overlap_ratio = overlap_count / min_count
            return overlap_ratio >= 0.5  # Au moins 50% de chevauchement
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification du chevauchement: {e}")
            return False
    
    def check_common_elements_above_threshold(self, table1: str, column1: str, table2: str, column2: str, threshold: int) -> bool:
        """
        Vérifie si le nombre d'éléments communs entre deux colonnes est supérieur à un seuil.
        
        :param table1: Nom de la première table
        :param column1: Nom de la colonne dans la première table
        :param table2: Nom de la deuxième table
        :param column2: Nom de la colonne dans la deuxième table
        :param threshold: Seuil minimal du nombre d'éléments communs
        :return: True si le nombre d'éléments communs est supérieur au seuil, False sinon
        """
        try:
            # Récupérer les valeurs distinctes des deux colonnes
            query1 = f"SELECT DISTINCT {column1} FROM {table1} WHERE {column1} IS NOT NULL"
            query2 = f"SELECT DISTINCT {column2} FROM {table2} WHERE {column2} IS NOT NULL"
            
            with self.engine.connect() as connection:
                df1_values = [str(row[0]) for row in connection.execute(text(query1)).fetchall()]
                df2_values = [str(row[0]) for row in connection.execute(text(query2)).fetchall()]
            
            # Convertir en ensembles et trouver l'intersection
            set1 = set(filter(None, df1_values))
            set2 = set(filter(None, df2_values))
            common_values = set1.intersection(set2)
            
            # Vérifier si le nombre d'éléments communs est supérieur au seuil
            return len(common_values) > threshold
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification des éléments communs: {e}")
            return False
    
    def check_jaccard_similarity_above_threshold(self, table1: str, column1: str, table2: str, column2: str, threshold: float) -> bool:
        """
        Vérifie si le coefficient de Jaccard entre deux colonnes est supérieur à un seuil.
        
        :param table1: Nom de la première table
        :param column1: Nom de la colonne dans la première table
        :param table2: Nom de la deuxième table
        :param column2: Nom de la colonne dans la deuxième table
        :param threshold: Seuil minimal du coefficient de Jaccard (0-1)
        :return: True si le coefficient est supérieur au seuil, False sinon
        """
        try:
            # Récupérer les valeurs distinctes des deux colonnes
            query1 = f"SELECT DISTINCT {column1} FROM {table1} WHERE {column1} IS NOT NULL"
            query2 = f"SELECT DISTINCT {column2} FROM {table2} WHERE {column2} IS NOT NULL"
            
            with self.engine.connect() as connection:
                df1_values = [str(row[0]) for row in connection.execute(text(query1)).fetchall()]
                df2_values = [str(row[0]) for row in connection.execute(text(query2)).fetchall()]
            
            # Convertir en ensembles
            set1 = set(filter(None, df1_values))
            set2 = set(filter(None, df2_values))
            
            # Calculer l'intersection et l'union
            common_values = set1.intersection(set2)
            union_values = set1.union(set2)
            
            # Éviter la division par zéro
            if not union_values:
                return False
            
            # Calculer le coefficient de Jaccard et comparer au seuil
            jaccard = len(common_values) / len(union_values)
            return jaccard > threshold
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de similarité de Jaccard: {e}")
            return False
    
    def _check_semantic_compatibility(self, table1: str, column1: str, table2: str, column2: str) -> bool:
        """
        Vérifie la compatibilité sémantique en analysant la similarité des noms de colonnes
        à l'aide d'un modèle de language Transformer.
        
        Exemples: customer_id et client_id, first_name et fname, birth_date et dob
        """
        try:
            # Normaliser les noms de colonnes (supprimer table_, id_, etc.)
            normalized1 = self._normalize_column_name(column1)
            normalized2 = self._normalize_column_name(column2)
            
            # Essayer d'utiliser le modèle Transformer si disponible
            if TRANSFORMERS_AVAILABLE:
                similarity = self._get_transformer_similarity(normalized1, normalized2)
                if similarity is not None:
                    self.logger.info(f"Similarité par transformer entre {normalized1} et {normalized2}: {similarity}")
                    return similarity > 0.75  # Seuil pour la similarité par transformers
            
            # Fallback à la méthode basée sur SequenceMatcher si les transformers ne sont pas disponibles
            similarity = SequenceMatcher(None, normalized1, normalized2).ratio()
            
            # Dictionnaire de synonymes courants (comme avant)
            synonyms = {
                "customer": ["client", "user", "buyer"],
                "product": ["item", "article", "merchandise"],
                "price": ["cost", "amount", "value"],
                "date": ["dt", "day", "timestamp"],
                "name": ["label", "title", "designation"],
                "firstname": ["fname", "givenname"],
                "lastname": ["lname", "surname", "familyname"],
                "address": ["addr", "location"],
                "telephone": ["phone", "tel", "mobile"],
                "employee": ["staff", "personnel"],
                "company": ["organization", "firm", "enterprise"]
            }
            
            # Vérifier si les colonnes appartiennent à des synonymes
            for word, synonyms_list in synonyms.items():
                if (normalized1 == word and normalized2 in synonyms_list) or \
                   (normalized2 == word and normalized1 in synonyms_list):
                    return True
            
            # Retourner vrai si la similarité est supérieure à 0.8 (méthode SequenceMatcher)
            return similarity > 0.8
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de compatibilité sémantique: {e}")
            return False
    
    def _normalize_column_name(self, column_name: str) -> str:
        """Normalise un nom de colonne pour comparaison sémantique."""
        # Convertir en minuscules
        name = column_name.lower()
        
        # Supprimer les préfixes/suffixes courants
        prefixes = ["id_", "fk_", "pk_", "tbl_"]
        suffixes = ["_id", "_fk", "_pk", "_key", "_code", "_num"]
        
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                
        # Remplacer les underscores et tirets par des espaces
        name = name.replace("_", " ").replace("-", " ")
        
        return name.strip()
    
    def _get_transformer_similarity(self, text1: str, text2: str) -> Optional[float]:
        """
        Calcule la similarité sémantique entre deux textes en utilisant un modèle Transformer.
        
        :param text1: Premier texte à comparer
        :param text2: Second texte à comparer
        :return: Score de similarité cosinus entre 0 et 1, ou None en cas d'erreur
        """
        try:
            # Initialiser le modèle si nécessaire
            if self._semantic_model is None:
                self._initialize_semantic_model()
                
                # Vérifier si l'initialisation a échoué
                if self._semantic_model is None:
                    return None
            
            # Encoder les textes
            embeddings = self._semantic_model.encode([text1, text2])
            
            # Calculer la similarité cosinus
            embedding1 = embeddings[0]
            embedding2 = embeddings[1]
            
            # Normaliser les vecteurs
            embedding1 = embedding1 / np.linalg.norm(embedding1)
            embedding2 = embedding2 / np.linalg.norm(embedding2)
            
            # Calculer le produit scalaire (similarité cosinus)
            similarity = np.dot(embedding1, embedding2)
            
            return float(similarity)
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de similarité par transformer: {e}")
            return None
    
    def _initialize_semantic_model(self) -> None:
        """
        Initialise le modèle de transformers pour l'analyse sémantique.
        Utilise un modèle léger adapté aux similarités de textes courts.
        """
        try:
            if not TRANSFORMERS_AVAILABLE:
                self.logger.warning("Sentence-transformers n'est pas disponible. "
                                   "Installez-le avec 'pip install sentence-transformers'")
                return
            
            # Utiliser un modèle léger optimisé pour la similarité de textes courts
            model_name = 'paraphrase-MiniLM-L6-v2'
            
            # Charger le modèle
            self.logger.info(f"Chargement du modèle {model_name}...")
            self._semantic_model = SentenceTransformer(model_name)
            self.logger.info(f"Modèle {model_name} chargé avec succès")
        except Exception as e:
            self.logger.error(f"Impossible de charger le modèle de transformer: {e}")
            self._semantic_model = None
    
    def _check_pattern_compatibility(self, table1: str, column1: str, table2: str, column2: str, sample_size: int = 100) -> bool:
        """
        Vérifie si deux colonnes contiennent des données avec des motifs similaires.
        
        Exemples: formats de téléphone, codes postaux, emails, etc.
        """
        try:
            # Extraire un échantillon de données
            query1 = f"""
                SELECT {column1} 
                FROM {table1}
                WHERE {column1} IS NOT NULL
                LIMIT {sample_size}
            """
            query2 = f"""
                SELECT {column2} 
                FROM {table2}
                WHERE {column2} IS NOT NULL
                LIMIT {sample_size}
            """
            
            with self.engine.connect() as connection:
                sample1 = [str(row[0]) for row in connection.execute(text(query1)).fetchall()]
                sample2 = [str(row[0]) for row in connection.execute(text(query2)).fetchall()]
            
            if not sample1 or not sample2:
                return False
            
            # Extraire les motifs (longueur, présence de caractères spéciaux, format général)
            pattern_stats1 = self._extract_pattern_stats(sample1)
            pattern_stats2 = self._extract_pattern_stats(sample2)
            
            # Calculer la similarité entre les statistiques de motifs
            similarity_score = self._calculate_pattern_similarity(pattern_stats1, pattern_stats2)
            
            return similarity_score > 0.7  # Seuil de similarité de motif
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de compatibilité par motif: {e}")
            return False
    
    def _extract_pattern_stats(self, samples: List[str]) -> Dict:
        """Extrait des statistiques sur les motifs des données."""
        length_counts = Counter([len(s) for s in samples])
        has_letters = sum(1 for s in samples if any(c.isalpha() for c in s))
        has_digits = sum(1 for s in samples if any(c.isdigit() for c in s))
        has_special = sum(1 for s in samples if any(not c.isalnum() for c in s))
        
        # Calculer les formats courants (ex: XXX-XXX-XXXX pour téléphones)
        formats = []
        for sample in samples:
            fmt = ''.join('X' if c.isalpha() else '9' if c.isdigit() else c for c in sample)
            formats.append(fmt)
        
        common_formats = Counter(formats).most_common(3)
        
        return {
            'avg_length': sum(length_counts.elements()) / len(samples),
            'length_variance': np.var(list(length_counts.elements())),
            'pct_has_letters': has_letters / len(samples),
            'pct_has_digits': has_digits / len(samples),
            'pct_has_special': has_special / len(samples),
            'common_formats': common_formats
        }
    
    def _calculate_pattern_similarity(self, stats1: Dict, stats2: Dict) -> float:
        """Calcule la similarité entre deux ensembles de statistiques de motifs."""
        # Différence de longueur moyenne pondérée
        length_diff = abs(stats1['avg_length'] - stats2['avg_length']) / max(stats1['avg_length'], stats2['avg_length'])
        
        # Différences de pourcentages de types de caractères
        letter_diff = abs(stats1['pct_has_letters'] - stats2['pct_has_letters'])
        digit_diff = abs(stats1['pct_has_digits'] - stats2['pct_has_digits'])
        special_diff = abs(stats1['pct_has_special'] - stats2['pct_has_special'])
        
        # Similarité des formats courants
        format_similarity = 0
        formats1 = dict(stats1['common_formats'])
        formats2 = dict(stats2['common_formats'])
        
        common_formats = set(formats1.keys()).intersection(set(formats2.keys()))
        if common_formats:
            format_similarity = len(common_formats) / min(len(formats1), len(formats2))
        
        # Score global (pondéré)
        score = (
            (1 - length_diff) * 0.3 + 
            (1 - (letter_diff + digit_diff + special_diff) / 3) * 0.4 + 
            format_similarity * 0.3
        )
        
        return score
    
    def _check_distribution_compatibility(self, table1: str, column1: str, table2: str, column2: str) -> bool:
        """
        Vérifie si les distributions statistiques de deux colonnes numériques sont similaires.
        """
        try:
            # Vérifier si les colonnes sont numériques
            if not self._is_numeric_column(table1, column1) or not self._is_numeric_column(table2, column2):
                return False
            
            # Calculer les statistiques de base
            stats1 = self._get_numeric_stats(table1, column1)
            stats2 = self._get_numeric_stats(table2, column2)
            
            if not stats1 or not stats2:
                return False
            
            # Comparer les distributions (normalisation pour gérer les échelles différentes)
            # On vérifie si les formes des distributions sont similaires
            # en utilisant les statistiques standardisées
            
            # Vérifier si les coefficients de variation sont similaires
            cv1 = stats1['std'] / stats1['mean'] if stats1['mean'] != 0 else 0
            cv2 = stats2['std'] / stats2['mean'] if stats2['mean'] != 0 else 0
            
            cv_similarity = 1 - min(abs(cv1 - cv2) / max(abs(cv1), abs(cv2), 1), 1)
            
            # Vérifier si les skewness sont similaires
            skew_similarity = 1 - min(abs(stats1['skew'] - stats2['skew']) / 2, 1)
            
            # Score combiné
            distribution_score = 0.6 * cv_similarity + 0.4 * skew_similarity
            
            return distribution_score > 0.7
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de compatibilité par distribution: {e}")
            return False
    
    def _is_numeric_column(self, table: str, column: str) -> bool:
        """Vérifie si une colonne est de type numérique."""
        try:
            t = self.metadata.tables[table]
            c_type = str(t.columns[column].type).upper()
            numeric_types = ['INTEGER', 'INT', 'SMALLINT', 'BIGINT', 'DECIMAL', 'NUMERIC', 'FLOAT', 'REAL', 'DOUBLE']
            return any(t in c_type for t in numeric_types)
        except Exception:
            return False
    
    def _get_numeric_stats(self, table: str, column: str) -> Dict:
        """Calcule les statistiques numériques d'une colonne."""
        try:
            query = f"""
                SELECT 
                    AVG({column}) as mean,
                    MIN({column}) as min,
                    MAX({column}) as max,
                    STDDEV({column}) as std
                FROM {table}
                WHERE {column} IS NOT NULL
            """
            
            # Requête pour calculer l'asymétrie (skewness)
            skew_query = f"""
                SELECT 
                    (SUM(POWER({column} - avg_val, 3)) / COUNT({column})) / 
                    POWER(SUM(POWER({column} - avg_val, 2)) / COUNT({column}), 1.5) as skewness
                FROM {table}, 
                    (SELECT AVG({column}) as avg_val FROM {table} WHERE {column} IS NOT NULL) as stats
                WHERE {column} IS NOT NULL
            """
            
            with self.engine.connect() as connection:
                stats = dict(connection.execute(text(query)).fetchone())
                skew_result = connection.execute(text(skew_query)).scalar() or 0
                stats['skew'] = skew_result
                return stats
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul des statistiques: {e}")
            return {}
    
    def _check_subset_compatibility(self, table1: str, column1: str, table2: str, column2: str) -> bool:
        """
        Vérifie si une colonne est un sous-ensemble d'une autre colonne.
        Utile pour les relations parent-enfant non explicites.
        """
        try:
            # Vérifier si toutes les valeurs de la table1 existent dans la table2
            query = f"""
                SELECT COUNT(*) 
                FROM (
                    SELECT DISTINCT {column1} as val 
                    FROM {table1} 
                    WHERE {column1} IS NOT NULL 
                    EXCEPT 
                    SELECT DISTINCT {column2} 
                    FROM {table2} 
                    WHERE {column2} IS NOT NULL
                ) as missing_values
            """
            
            with self.engine.connect() as connection:
                missing_count = connection.execute(text(query)).scalar() or 0
            
            # Nombre total de valeurs distinctes dans table1
            query = f"SELECT COUNT(DISTINCT {column1}) FROM {table1} WHERE {column1} IS NOT NULL"
            with self.engine.connect() as connection:
                total_count = connection.execute(text(query)).scalar() or 0
            
            if total_count == 0:
                return False
                
            # Si moins de 5% des valeurs manquent, considérer comme sous-ensemble
            return missing_count / total_count < 0.05
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de sous-ensemble: {e}")
            return False
    
    def _check_temporal_compatibility(self, table1: str, column1: str, table2: str, column2: str) -> bool:
        """
        Vérifie la compatibilité des colonnes temporelles (dates/heures).
        """
        try:
            # Vérifier si les deux colonnes sont de type date/heure
            if not self._is_temporal_column(table1, column1) or not self._is_temporal_column(table2, column2):
                return False
            
            # Obtenir les plages temporelles des deux colonnes
            range1 = self._get_temporal_range(table1, column1)
            range2 = self._get_temporal_range(table2, column2)
            
            if not range1 or not range2:
                return False
            
            # Vérifier le chevauchement des plages temporelles
            has_overlap = max(range1['min'], range2['min']) <= min(range1['max'], range2['max'])
            
            # Calculer le pourcentage de chevauchement par rapport à la plus petite plage
            if has_overlap:
                overlap_start = max(range1['min'], range2['min'])
                overlap_end = min(range1['max'], range2['max'])
                
                range1_size = (range1['max'] - range1['min']).total_seconds()
                range2_size = (range2['max'] - range2['min']).total_seconds()
                overlap_size = (overlap_end - overlap_start).total_seconds()
                
                overlap_ratio = overlap_size / min(range1_size, range2_size)
                return overlap_ratio > 0.3  # Au moins 30% de chevauchement
            
            return False
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de compatibilité temporelle: {e}")
            return False
    
    def _is_temporal_column(self, table: str, column: str) -> bool:
        """Vérifie si une colonne est de type temporel."""
        try:
            t = self.metadata.tables[table]
            c_type = str(t.columns[column].type).upper()
            temporal_types = ['DATE', 'TIME', 'DATETIME', 'TIMESTAMP']
            return any(t in c_type for t in temporal_types)
        except Exception:
            return False
    
    def _get_temporal_range(self, table: str, column: str) -> Dict:
        """Obtient la plage temporelle d'une colonne."""
        try:
            query = f"""
                SELECT 
                    MIN({column}) as min_date,
                    MAX({column}) as max_date
                FROM {table}
                WHERE {column} IS NOT NULL
            """
            
            with self.engine.connect() as connection:
                result = connection.execute(text(query)).fetchone()
                
            if result:
                return {
                    'min': result[0],
                    'max': result[1]
                }
            return None
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction de la plage temporelle: {e}")
            return None
    
    def _check_equality_sample(self, table1: str, column1: str, table2: str, column2: str, sample_size: int = 100) -> bool:
        """
        Vérifie si deux colonnes ont des valeurs égales sur un échantillon aléatoire.
        Version améliorée avec échantillonnage stratifié.
        """
        try:
            # Utiliser un échantillonnage stratifié pour les grandes tables
            if self._get_table_size(table1) > 10000:
                query = f"""
                    SELECT COUNT(*) as match_count
                    FROM (
                        SELECT t1.{column1} as val
                        FROM (
                            SELECT {column1}, ntile({sample_size}) OVER (ORDER BY {column1}) as bucket
                            FROM {table1}
                            WHERE {column1} IS NOT NULL
                        ) t1
                        WHERE t1.bucket = 1
                    ) as sample
                    INNER JOIN {table2} t2 ON sample.val = t2.{column2}
                """
            else:
                # Version simple pour les petites tables
                query = f"""
                    SELECT COUNT(*) as match_count
                    FROM (
                        SELECT t1.{column1} as val
                        FROM {table1} t1
                        WHERE t1.{column1} IS NOT NULL
                        ORDER BY RANDOM()
                        LIMIT {sample_size}
                    ) as sample
                    INNER JOIN {table2} t2 ON sample.val = t2.{column2}
                """
            
            with self.engine.connect() as connection:
                match_count = connection.execute(text(query)).scalar() or 0
                
            # Récupérer la taille réelle de l'échantillon
            query_sample_size = f"""
                SELECT COUNT(*) FROM (
                    SELECT {column1}
                    FROM {table1}
                    WHERE {column1} IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT {sample_size}
                ) s
            """
            with self.engine.connect() as connection:
                actual_sample_size = connection.execute(text(query_sample_size)).scalar() or 1
                
            # On considère des colonnes compatibles si au moins 90% des valeurs correspondent
            return match_count >= 0.9 * actual_sample_size
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification d'égalité sur échantillon: {e}")
            return False
    
    def _check_cardinality_ratio(self, table1: str, column1: str, table2: str, column2: str) -> bool:
        """
        Compare simplement le ratio des cardinalités entre deux colonnes.
        Utile pour identifier rapidement des colonnes qui pourraient être liées.
        """
        try:
            # Récupérer le nombre de valeurs distinctes dans chaque colonne
            query1 = f"SELECT COUNT(DISTINCT {column1}) FROM {table1} WHERE {column1} IS NOT NULL"
            query2 = f"SELECT COUNT(DISTINCT {column2}) FROM {table2} WHERE {column2} IS NOT NULL"
            
            with self.engine.connect() as connection:
                distinct1 = connection.execute(text(query1)).scalar() or 0
                distinct2 = connection.execute(text(query2)).scalar() or 0
                
            # Éviter la division par zéro
            if distinct1 == 0 or distinct2 == 0:
                return False
                
            # Calculer le ratio entre le plus petit et le plus grand
            ratio = min(distinct1, distinct2) / max(distinct1, distinct2)
            
            # Considérer comme compatible si le ratio est supérieur à 0.8
            return ratio >= 0.8
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la comparaison des cardinalités: {e}")
            return False
    
    def _check_unique_ratio(self, table1: str, column1: str, table2: str, column2: str) -> bool:
        """
        Évalue le ratio de valeurs uniques dans chaque colonne.
        Deux colonnes avec des ratios similaires ont plus de chances d'être liées.
        """
        try:
            # Calculer le ratio de valeurs uniques pour chaque colonne
            query1 = f"""
                SELECT 
                    COUNT(DISTINCT {column1}) as distinct_count,
                    COUNT(*) as total_count
                FROM {table1}
                WHERE {column1} IS NOT NULL
            """
            
            query2 = f"""
                SELECT 
                    COUNT(DISTINCT {column2}) as distinct_count,
                    COUNT(*) as total_count
                FROM {table2}
                WHERE {column2} IS NOT NULL
            """
            
            with self.engine.connect() as connection:
                result1 = dict(connection.execute(text(query1)).fetchone())
                result2 = dict(connection.execute(text(query2)).fetchone())
                
            # Calculer les ratios
            ratio1 = result1['distinct_count'] / result1['total_count'] if result1['total_count'] > 0 else 0
            ratio2 = result2['distinct_count'] / result2['total_count'] if result2['total_count'] > 0 else 0
            
            # Calculer la différence entre les ratios
            ratio_diff = abs(ratio1 - ratio2)
            
            # Les colonnes sont compatibles si leurs ratios sont similaires
            return ratio_diff <= 0.1  # Différence de 10% ou moins
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul des ratios de valeurs uniques: {e}")
            return False
    
    def _check_key_candidate(self, table: str, column: str) -> bool:
        """
        Vérifie si une colonne est un candidat clé (unique ou presque unique).
        Important pour identifier les colonnes pouvant participer à des dépendances.
        """
        try:
            query = f"""
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT {column}) as distinct_values
                FROM {table}
                WHERE {column} IS NOT NULL
            """
            
            with self.engine.connect() as connection:
                result = dict(connection.execute(text(query)).fetchone())
                
            if result['total_rows'] == 0:
                return False
                
            # Calculer le ratio de valeurs distinctes
            uniqueness_ratio = result['distinct_values'] / result['total_rows']
            
            # Une colonne est un candidat clé si au moins 95% des valeurs sont uniques
            return uniqueness_ratio >= 0.95
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de candidat clé: {e}")
            return False
    
    def _check_egd_compatibility(self, table1: str, column1: str, table2: str, column2: str, sample_size: int = 100) -> Dict[str, float]:
        """
        Analyse complète pour détecter les dépendances génératrices d'égalité potentielles.
        Combine plusieurs modes simples et retourne un dictionnaire avec des scores de confiance.
        
        Returns:
            dict: Dictionnaire contenant des scores pour différentes métriques et un score global
        """
        results = {}
        
        # Vérifier la compatibilité d'égalité sur un échantillon
        try:
            eq_sample = self._check_equality_sample(table1, column1, table2, column2, sample_size)
            results['equality_sample'] = 1.0 if eq_sample else 0.0
        except Exception as e:
            self.logger.debug(f"Erreur lors de la vérification d'égalité sur échantillon: {e}")
            results['equality_sample'] = 0.0
        
        # Vérifier le ratio de cardinalité
        try:
            card_score = self._get_cardinality_ratio_score(table1, column1, table2, column2)
            results['cardinality_ratio'] = card_score
        except Exception as e:
            self.logger.debug(f"Erreur lors de la vérification du ratio de cardinalité: {e}")
            results['cardinality_ratio'] = 0.0
        
        # Vérifier le ratio de valeurs uniques
        try:
            unique_score = self._get_unique_ratio_score(table1, column1, table2, column2)
            results['unique_ratio'] = unique_score
        except Exception as e:
            self.logger.debug(f"Erreur lors de la vérification du ratio de valeurs uniques: {e}")
            results['unique_ratio'] = 0.0
        
        # Vérifier si l'une des colonnes est un candidat clé
        try:
            key1 = self._check_key_candidate(table1, column1)
            key2 = self._check_key_candidate(table2, column2)
            results['key_candidate'] = 1.0 if (key1 or key2) else 0.0
        except Exception as e:
            self.logger.debug(f"Erreur lors de la vérification de candidat clé: {e}")
            results['key_candidate'] = 0.0
        
        # Vérifier la compatibilité sémantique des noms
        try:
            semantic_score = self._get_semantic_score(table1, column1, table2, column2)
            results['semantic'] = semantic_score
        except Exception as e:
            self.logger.debug(f"Erreur lors de la vérification de compatibilité sémantique: {e}")
            results['semantic'] = 0.0
        
        # Calculer un score global pondéré
        weights = {
            'equality_sample': 0.4,
            'cardinality_ratio': 0.25,
            'unique_ratio': 0.15,
            'key_candidate': 0.1,
            'semantic': 0.1
        }
        
        overall_score = sum(results[k] * weights[k] for k in weights)
        results['overall'] = overall_score
        results['is_compatible'] = overall_score >= 0.7  # Seuil de décision
        
        return results
    
    def _get_cardinality_ratio_score(self, table1: str, column1: str, table2: str, column2: str) -> float:
        """Version améliorée qui retourne un score plutôt qu'un booléen."""
        try:
            query1 = f"SELECT COUNT(DISTINCT {column1}) FROM {table1} WHERE {column1} IS NOT NULL"
            query2 = f"SELECT COUNT(DISTINCT {column2}) FROM {table2} WHERE {column2} IS NOT NULL"
            
            with self.engine.connect() as connection:
                distinct1 = connection.execute(text(query1)).scalar() or 0
                distinct2 = connection.execute(text(query2)).scalar() or 0
                
            # Éviter la division par zéro
            if distinct1 == 0 or distinct2 == 0:
                return 0.0
                
            # Calculer le ratio entre le plus petit et le plus grand
            ratio = min(distinct1, distinct2) / max(distinct1, distinct2)
            return ratio
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la comparaison des cardinalités: {e}")
            return 0.0
    
    def _get_unique_ratio_score(self, table1: str, column1: str, table2: str, column2: str) -> float:
        """Version améliorée qui retourne un score plutôt qu'un booléen."""
        try:
            query1 = f"""
                SELECT 
                    COUNT(DISTINCT {column1}) as distinct_count,
                    COUNT(*) as total_count
                FROM {table1}
                WHERE {column1} IS NOT NULL
            """
            
            query2 = f"""
                SELECT 
                    COUNT(DISTINCT {column2}) as distinct_count,
                    COUNT(*) as total_count
                FROM {table2}
                WHERE {column2} IS NOT NULL
            """
            
            with self.engine.connect() as connection:
                result1 = dict(connection.execute(text(query1)).fetchone())
                result2 = dict(connection.execute(text(query2)).fetchone())
                
            # Calculer les ratios
            ratio1 = result1['distinct_count'] / result1['total_count'] if result1['total_count'] > 0 else 0
            ratio2 = result2['distinct_count'] / result2['total_count'] if result2['total_count'] > 0 else 0
            
            # Calculer la similarité entre les ratios (1 - différence normalisée)
            ratio_diff = abs(ratio1 - ratio2)
            return max(0, 1 - ratio_diff)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul des ratios de valeurs uniques: {e}")
            return 0.0
    
    def _get_semantic_score(self, table1: str, column1: str, table2: str, column2: str) -> float:
        """Version améliorée qui retourne un score de similarité sémantique."""
        try:
            # Normaliser les noms de colonnes
            normalized1 = self._normalize_column_name(column1)
            normalized2 = self._normalize_column_name(column2)
            
            # Essayer d'utiliser le modèle Transformer si disponible
            if TRANSFORMERS_AVAILABLE:
                similarity = self._get_transformer_similarity(normalized1, normalized2)
                if similarity is not None:
                    return float(similarity)
            
            # Fallback à la méthode SequenceMatcher
            similarity = SequenceMatcher(None, normalized1, normalized2).ratio()
            
            # Vérifier les synonymes
            synonyms = {
                "customer": ["client", "user", "buyer"],
                "product": ["item", "article", "merchandise"],
                "price": ["cost", "amount", "value"],
                "date": ["dt", "day", "timestamp"],
                "name": ["label", "title", "designation"],
                "firstname": ["fname", "givenname"],
                "lastname": ["lname", "surname", "familyname"],
                "address": ["addr", "location"],
                "telephone": ["phone", "tel", "mobile"],
                "employee": ["staff", "personnel"],
                "company": ["organization", "firm", "enterprise"]
            }
            
            # Bonus pour les synonymes connus
            for word, synonyms_list in synonyms.items():
                if (normalized1 == word and normalized2 in synonyms_list) or \
                   (normalized2 == word and normalized1 in synonyms_list):
                    similarity = max(similarity, 0.9)  # Forte similarité pour les synonymes connus
            
            return similarity
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de similarité sémantique: {e}")
            return 0.0
        
    @_cache_result
    def batch_check_compatibility(self, column_pairs: List[Tuple[str, str, str, str]], 
                               mode: str = MODE_HYBRID, 
                               sample_size: int = 1000,
                               parallel: bool = False,
                               max_workers: int = 4) -> Dict[Tuple[str, str, str, str], Union[bool, Dict]]:
        """
        Vérifie la compatibilité pour plusieurs paires de colonnes en une seule opération.
        
        Args:
            column_pairs: Liste de tuples (table1, column1, table2, column2)
            mode: Mode de compatibilité à utiliser
            sample_size: Taille de l'échantillon pour les modes utilisant l'échantillonnage
            parallel: Si True, exécute les vérifications en parallèle
            max_workers: Nombre maximum de threads pour le traitement parallèle
            
        Returns:
            dict: Dictionnaire avec les paires de colonnes comme clés et les résultats comme valeurs
        """
        results = {}
        
        if parallel and len(column_pairs) > 1:
            # Exécution parallèle
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_pair = {
                    executor.submit(self.is_compatible, t1, c1, t2, c2, mode, sample_size): (t1, c1, t2, c2)
                    for t1, c1, t2, c2 in column_pairs
                }
                
                for future in concurrent.futures.as_completed(future_to_pair):
                    pair = future_to_pair[future]
                    try:
                        results[pair] = future.result()
                    except Exception as e:
                        self.logger.error(f"Erreur lors de la vérification de {pair}: {e}")
                        results[pair] = False
        else:
            # Exécution séquentielle
            for t1, c1, t2, c2 in column_pairs:
                try:
                    results[(t1, c1, t2, c2)] = self.is_compatible(t1, c1, t2, c2, mode, sample_size)
                except Exception as e:
                    self.logger.error(f"Erreur lors de la vérification de {(t1, c1, t2, c2)}: {e}")
                    results[(t1, c1, t2, c2)] = False
        
        return results
    
    def get_candidate_columns_for_egd(self, table1: str, table2: str = None, min_score: float = 0.7,
                                   sample_size: int = 100) -> List[Dict[str, Any]]:
        """
        Identifie les paires de colonnes susceptibles de participer à des dépendances génératrices d'égalité.
        
        Args:
            table1: Première table à analyser
            table2: Deuxième table à analyser (si None, compare avec toutes les tables)
            min_score: Score minimum pour considérer une paire comme candidate
            sample_size: Taille de l'échantillon pour les vérifications
            
        Returns:
            list: Liste de dictionnaires décrivant les paires de colonnes candidates
        """
        candidates = []
        
        # Si table2 n'est pas spécifiée, utiliser toutes les tables
        tables_to_check = [table2] if table2 else [t.name for t in self.metadata.sorted_tables 
                                                 if t.name != table1]
        
        for t2 in tables_to_check:
            # Obtenir les colonnes des tables
            t1_columns = [c.name for c in self.metadata.tables[table1].columns]
            t2_columns = [c.name for c in self.metadata.tables[t2].columns]
            
            # Générer toutes les paires de colonnes possibles
            column_pairs = [(table1, c1, t2, c2) for c1 in t1_columns for c2 in t2_columns]
            
            # Vérifier les compatibilités par lots
            batch_size = 10  # Ajuster selon la complexité des vérifications
            for i in range(0, len(column_pairs), batch_size):
                batch = column_pairs[i:i+batch_size]
                results = self.batch_check_compatibility(batch, mode=self.MODE_EGD, sample_size=sample_size)
                
                for pair, result in results.items():
                    if result['overall'] >= min_score:
                        t1, c1, t2, c2 = pair
                        candidates.append({
                            'table1': t1,
                            'column1': c1,
                            'table2': t2,
                            'column2': c2,
                            'score': result['overall'],
                            'metrics': result
                        })
        
        # Trier par score décroissant
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Retourne des statistiques sur l'utilisation du cache."""
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'size': len(self._cache),
            'max_size': self._cache_size
        }
        
    def clear_cache(self) -> None:
        """Vide le cache."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
