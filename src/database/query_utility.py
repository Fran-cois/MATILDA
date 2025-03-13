import csv
import hashlib
import logging
import os
import time
from typing import Any, Dict, List, Tuple

import psutil
from sqlalchemy import (
    MetaData,
    alias,
    and_,
    create_engine,
    func,
    select,
    text
)

#from utils.log_setup import setup_loggers
import colorama   # Ajout de colorama
colorama.init(autoreset=True)
from colorama import Fore, Style

import pandas as pd  # Ajout pour pd.DataFrame
from typing import Optional  # Ajout pour le type Optional

class ColorFormatter(logging.Formatter):
    COLOR_MAP = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
    }

    def format(self, record):
        color = self.COLOR_MAP.get(record.levelno, Fore.WHITE)
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)



class QueryUtility:
    """
    Handles complex queries, including threshold checks and join row counts.
    """

    def __init__(self, engine, metadata: MetaData, logger_query_time, logger_query_results):
        self.engine = engine
        self.metadata = metadata
        self.logger_query_time = logger_query_time
        self.logger_query_results = logger_query_results

        self._setup_logging_handlers()  # Setup logging handlers
    def _setup_logging_handlers(self):
        formatter = ColorFormatter('%(asctime)s - %(levelname)s - %(message)s')

        # Formatter for logger_query_time
        handler_time = logging.StreamHandler()
        handler_time.setFormatter(formatter)
        self.logger_query_time.addHandler(handler_time)
        self.logger_query_time.setLevel(logging.DEBUG)

        # Formatter for logger_query_results
        handler_results = logging.StreamHandler()
        handler_results.setFormatter(formatter)
        self.logger_query_results.addHandler(handler_results)
        self.logger_query_results.setLevel(logging.DEBUG)
    def check_threshold(
        self,
        join_conditions: List[Tuple[str, int, str, str, int, str]],
        disjoint_semantics: bool = False,
        distinct: bool = False,
        count_over: List[List[Tuple[str, int, str]]] = None,
        threshold: int = 1,
        flag:str="threshold"
    ) -> int:
        """
        Check if the count of resulting rows from the given join exceeds a threshold.
        """
        query, primary_key_conditions, join_base = self._construct_threshold_query(
            join_conditions, disjoint_semantics, distinct, count_over, threshold
        )

        if query is None :
            return 0

        start = time.time()
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query).scalar()
                result = bool(result)
        except Exception as e:
            self.logger_query_time.error(f"Error executing threshold query: {e}")
            return 0
        end = time.time()

        execution_time = end - start
        # self.logger_query_time.info(
        #     f"Execution Time: {execution_time:.4f} seconds for Threshold Query: {str(query)}"
        # )
        # self.logger_query_results.info(
        #     f"Threshold Query: {str(query)}; Result: {result}; Execution Time: {execution_time:.4f}"
        # )

        return int(result) if result is not None else 0

    def get_join_row_count(
        self,
        join_conditions: List[Tuple[str, int, str, str, int, str]],
        disjoint_semantics: bool = False,
        distinct: bool = False,
        count_over: List[List[Tuple[str, int, str]]] = None,
    ) -> int:
        query, primary_key_conditions, join_base = self._construct_count_query(
            join_conditions, disjoint_semantics, distinct, count_over
        )

        if query is None:
            return 0

        start = time.time()
        try:
            with self.engine.connect() as conn:
                result_sqlite = conn.execute(query).scalar()
        except Exception as e:
            self.logger_query_time.error(f"Error executing query: {e}")
            return 0
        end = time.time()

        execution_time_sqlite = end - start
        # self.logger_query_time.info(
        #     f"Execution Time: {execution_time_sqlite:.4f} seconds for Query: {str(query)}"
        # )
        # self.logger_query_results.info(
        #     f"Query: {str(query)}; Result: {result_sqlite}"
        # )

        return result_sqlite if result_sqlite is not None else 0

    # Below methods are similar to the original code but reorganized for clarity.

    def _construct_threshold_query(
        self,
        join_conditions,
        disjoint_semantics,
        distinct,
        count_over,
        threshold
    ):
        # Construct the query and return it along with conditions
        query, primary_key_conditions, join_base = self._construct_query_base(
            join_conditions, disjoint_semantics, distinct, count_over
        )
        if join_base is None :
            return None, None, None
        query = select((func.count() > threshold).label("count_exceeds_threshold")).select_from(join_base)
        if primary_key_conditions:
            query = query.where(and_(*primary_key_conditions))
        return query, primary_key_conditions, join_base

    def _construct_count_query(
        self,
        join_conditions,
        disjoint_semantics,
        distinct,
        count_over
    ):
        # Construct the query and return it along with conditions
        query, primary_key_conditions, join_base = self._construct_query_base(
            join_conditions, disjoint_semantics, distinct, count_over
        )
        return query, primary_key_conditions, join_base

    def _construct_query_base(
        self,
        join_conditions,
        disjoint_semantics,
        distinct,
        count_over
    ):
        condition_groups = self._organize_join_conditions(join_conditions)
        try:
            join_bases, aliases, used_aliases, table_occurrences = (
                self._process_join_conditions(condition_groups, disjoint_semantics)
            )
        except Exception as e:
            self.logger_query_time.error(f"Error processing join conditions: {e}")
            return None, None, None

        if not join_bases:
            return None, None, None

        join_base, where_constraints = self._construct_join(join_bases, aliases, used_aliases)
        if disjoint_semantics:
            primary_key_conditions = self._construct_primary_key_conditions(table_occurrences, aliases, used_aliases)
            primary_key_conditions += where_constraints
        else:
            primary_key_conditions = where_constraints

        query = self._construct_select_query(join_base, distinct, primary_key_conditions, count_over, aliases)
        return query, primary_key_conditions, join_base

    def _organize_join_conditions(self, join_conditions: List[Tuple[str, int, str, str, int, str]]):
        condition_groups = {}
        for condition in join_conditions:
            table_name1, occurrence1, attribute_name1, table_name2, occurrence2, attribute_name2 = condition
            key = frozenset({(table_name1, occurrence1), (table_name2, occurrence2)})
            if key not in condition_groups:
                condition_groups[key] = []
            condition_groups[key].append(condition)
        return condition_groups

    def _process_join_conditions(
        self,
        condition_groups: Dict[frozenset, List[Tuple[str, int, str, str, int, str]]],
        disjoint_semantics: bool,
    ):
        used_aliases = set()
        aliases = {}
        join_bases = []
        table_occurrences = {}

        for key, group in condition_groups.items():
            sorted_key = sorted(list(key))
            if len(sorted_key) == 2:
                table_name1, occurrence1 = sorted_key[0]
                table_name2, occurrence2 = sorted_key[1]

                if table_name1 not in self.metadata.tables:
                    #self.logger_query_time.debug(f"Table '{table_name1}' does not exist; skipping join condition.")
                    continue
                if table_name2 not in self.metadata.tables:
                    #self.logger_query_time.debug(f"Table '{table_name2}' does not exist; skipping join condition.")
                    continue

                if disjoint_semantics:
                    table_occurrences.setdefault(table_name1, set()).add(occurrence1)
                    table_occurrences.setdefault(table_name2, set()).add(occurrence2)

                alias1 = self._get_or_create_alias(aliases, table_name1, occurrence1)
                alias2 = self._get_or_create_alias(aliases, table_name2, occurrence2)

                partial_join_conditions = []
                for (tn1, o1, attr1, tn2, o2, attr2) in group:
                    columns_alias1 = [str(el).split(".")[1] for el in alias1.columns._all_columns]
                    columns_alias2 = [str(el).split(".")[1] for el in alias2.columns._all_columns]

                    if attr1 in columns_alias1 and attr2 in columns_alias2:
                        partial_join_conditions.append(alias1.columns[attr1] == alias2.columns[attr2])
                    elif attr2 in columns_alias1 and attr1 in columns_alias2:
                        partial_join_conditions.append(alias1.columns[attr2] == alias2.columns[attr1])

                if partial_join_conditions:
                    join_condition = and_(*partial_join_conditions)
                    join_bases.append(
                        (f"{table_name1}_{occurrence1}", f"{table_name2}_{occurrence2}", join_condition)
                    )
                    used_aliases.add(f"{table_name1}_{occurrence1}")
                    used_aliases.add(f"{table_name2}_{occurrence2}")

            elif len(sorted_key) == 1:
                (table_name1, occurrence1) = sorted_key[0]
                if table_name1 not in self.metadata.tables:
                    self.logger_query_time.error(f"Table '{table_name1}' does not exist; skipping condition.")
                    continue
                alias1 = self._get_or_create_alias(aliases, table_name1, occurrence1)
                partial_join_conditions = []
                for (tn1, o1, attr1, tn2, o2, attr2) in group:
                    columns_alias1 = [str(el).split(".")[1] for el in alias1.columns._all_columns]
                    if attr1 in columns_alias1 and attr2 in columns_alias1:
                        partial_join_conditions.append(alias1.columns[attr1] == alias1.columns[attr2])
                if partial_join_conditions:
                    join_condition = and_(*partial_join_conditions)
                    join_bases.append((f"{table_name1}_{occurrence1}", None, join_condition))
                    used_aliases.add(f"{table_name1}_{occurrence1}")

        return join_bases, aliases, used_aliases, table_occurrences

    def _get_or_create_alias(self, aliases: Dict[str, Any], table_name: str, occurrence: int):
        alias_key = f"{table_name}_{occurrence}"
        if table_name not in self.metadata.tables:
            raise ValueError(f"Table {table_name} does not exist in the database")
        if alias_key not in aliases:
            aliases[alias_key] = alias(self.metadata.tables[table_name], name=alias_key)
        return aliases[alias_key]

    def _construct_join(self, join_bases, aliases: Dict[str, Any], used_aliases: set):
        where_constraints = []
        used_aliases_in_join = set()

        if not join_bases:
            return None, where_constraints

        first_base_key = join_bases[0][0]
        used_aliases_in_join.add(first_base_key)
        join_base = aliases[first_base_key].selectable
        for alias_key1, alias_key2, join_condition in join_bases:
            if alias_key2 is None:
                where_constraints.append(join_condition)
            elif alias_key1 in used_aliases_in_join and alias_key2 not in used_aliases_in_join:
                used_aliases_in_join.add(alias_key2)
                join_base = join_base.join(aliases[alias_key2], join_condition)
            elif alias_key2 in used_aliases_in_join and alias_key1 not in used_aliases_in_join:
                used_aliases_in_join.add(alias_key1)
                join_base = join_base.join(aliases[alias_key1], join_condition)
            elif alias_key1 in used_aliases_in_join and alias_key2 in used_aliases_in_join:
                where_constraints.append(join_condition)

        return join_base, where_constraints

    def _construct_primary_key_conditions(self, table_occurrences: Dict[str, set], aliases: Dict[str, Any], used_aliases: set):
        primary_key_conditions = []
        for table_name, occurrences in table_occurrences.items():
            if len(occurrences) <= 1:
                continue
            table_pk = self.metadata.tables[table_name].primary_key
            pks = [col.name for col in table_pk.columns] if table_pk else []
            for occurrence1 in occurrences:
                for occurrence2 in occurrences:
                    if occurrence1 >= occurrence2:
                        continue
                    alias_key1 = f"{table_name}_{occurrence1}"
                    alias_key2 = f"{table_name}_{occurrence2}"
                    if alias_key1 not in used_aliases or alias_key2 not in used_aliases:
                        continue
                    alias1 = aliases[alias_key1]
                    alias2 = aliases[alias_key2]
                    for pk in pks:
                        pk_condition = alias1.columns[pk] != alias2.columns[pk]
                        primary_key_conditions.append(pk_condition)
        return primary_key_conditions

    def _construct_select_query(
        self,
        join_base,
        distinct: bool,
        primary_key_conditions: List[Any] = None,
        count_over: List[List[Tuple[str, int, str]]] = None,
        aliases: Dict[str, Any] = None,
    ):
        if count_over and not aliases:
            raise ValueError("Aliases must be provided when count_over is specified.")

        if count_over and len(count_over) > 0:
            count_over_clause = []
            for x_class in count_over:
                for attribute in x_class:
                    table_name, occurrence, attribute_name = attribute
                    alias_key = f"{table_name}_{occurrence}"
                    if alias_key not in aliases:
                        raise ValueError(f"Alias {alias_key} not found in aliases")
                    count_over_clause.append(aliases[alias_key].columns[attribute_name])
                    break

            inner_query = select(*count_over_clause).distinct().select_from(join_base)
            if primary_key_conditions:
                inner_query = inner_query.where(and_(*primary_key_conditions))
            #query = select(func.count()).select_from(inner_query)
            query = select(func.count()).select_from(inner_query.subquery()) # for future version of sqlalchemy

        else:
            query = select(func.count()).distinct().select_from(join_base)
            if primary_key_conditions:
                query = query.where(and_(*primary_key_conditions))

        return query


    def _get_table_names(self) -> List[str]:
        return sorted(self.metadata.tables.keys())
    def _get_attribute_names(self, table_name: str) -> List[str]:
        return [col.name for col in self.metadata.tables[table_name].columns]
    def _get_attribute_domain(self, table_name: str, attribute_name: str) -> str:
        """
        Return the domain (data type) of a given attribute in a table.

        :param table_name: Name of the table.
        :param attribute_name: Name of the attribute (column).
        :return: The data type of the attribute as a string, or None if not found.
        """
        table = self.metadata.tables.get(table_name)
        if table is not None and hasattr(table, "columns"):
            column = table.columns.get(attribute_name)
            if column is not None:
                return str(column.type)
        return None
    def _get_attribute_is_key(self, table_name: str, attribute_name: str) -> bool:
        """
        Check if a given attribute (column) is part of the primary key in a table.

        :param table_name: Name of the table.
        :param attribute_name: Name of the attribute (column).
        :return: True if the attribute is part of the primary key, False otherwise.
        """
        table = self.metadata.tables.get(table_name)
        if table is not None and hasattr(table, "columns"):
            column = table.columns.get(attribute_name)
            if column is not None:
                return column.primary_key
        return False
    def _get_foreign_keys(self) -> Dict[str, Dict[str, Tuple[str, str]]]:
        """
        Retrieve all foreign key relationships in the database.
        Returns a dictionary where keys are table names and values are dicts with the key being an attribute
        and the values tuples containing (referenced_table, referenced_column).
        """
        foreign_keys_info = {}
        for table_name, table in self.metadata.tables.items():
            for fk in table.foreign_keys:
                ref_table = fk.column.table.name
                local_column = fk.parent.name
                reference_column = fk.column.name
                
                # Check if the referenced table exists
                if ref_table not in self.metadata.tables:
                    self.logger_query_time.error(f"Referenced table '{ref_table}' does not exist for foreign key '{local_column}' in table '{table_name}'.")
                    continue
                
                # Check if the referenced column exists
                if reference_column not in self.metadata.tables[ref_table].columns:
                    self.logger_query_time.error(f"Referenced column '{reference_column}' does not exist in table '{ref_table}' for foreign key '{local_column}' in table '{table_name}'.")
                    continue
                
                if table_name not in foreign_keys_info:
                    foreign_keys_info[table_name] = {}
                foreign_keys_info[table_name][local_column] = (ref_table, reference_column)
        return foreign_keys_info

    def get_row_count(self, table_name: str) -> int:
        """
        Obtient le nombre de lignes dans une table.
        
        :param table_name: Nom de la table
        :return: Nombre de lignes
        """
        try:
            # Construire la requête COUNT
            query = f"SELECT COUNT(*) FROM {table_name}"
            
            # Exécuter la requête
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                count = result.scalar()
                
            return count
        except Exception as e:
            self.logger_query_time.warning(f"Couldn't get row count for {table_name}: {e}")
            # Approche alternative: charger la table et compter les lignes
            try:
                table = self.metadata.tables.get(table_name)
                if table is not None:
                    df = pd.read_sql_table(table_name, self.engine)
                    return len(df)
                else:
                    self.logger_query_time.error(f"Table {table_name} not found in metadata")
                    return 0
            except Exception as e2:
                self.logger_query_time.error(f"Failed to get row count for {table_name}: {e2}")
                return 0

    def get_join_content_custom(self, join_conditions: List[Dict[str, Any]], 
                               where_clause: Optional[str] = None, 
                               limit: Optional[int] = None,
                               flag: str = "") -> pd.DataFrame:
        """
        Exécute une requête JOIN personnalisée et retourne les résultats.
        
        :param join_conditions: Liste de dictionnaires ou de tuples décrivant les conditions de jointure
          Format dict: {'table1': str, 'column1': str, 'table2': str, 'column2': str, 'type': str}
          Format tuple: (table_name1, occurrence1, attribute_name1, table_name2, occurrence2, attribute_name2)
        :param where_clause: Condition WHERE optionnelle (chaîne SQL ou liste de tuples)
        :param limit: Nombre maximum de lignes à retourner
        :param flag: Indicateur optionnel pour le traitement spécifique
        :return: DataFrame pandas avec les résultats de la jointure
        """
        try:
            # Construire la requête JOIN dynamiquement
            if not join_conditions:
                return pd.DataFrame()
            
            # Détecter le format des conditions de jointure (dict ou tuple)
            first_element = join_conditions[0]
            is_tuple_format = isinstance(first_element, tuple)
            
            # Log pour debug
            #self.logger_query_time.debug(f"Join conditions format: {'tuple' if is_tuple_format else 'dict'}")
            
            if is_tuple_format:
                # Format tuple: (table_name1, occurrence1, attribute_name1, table_name2, occurrence2, attribute_name2)
                # Extraire le nom de base de la table (sans occurrence)
                first_condition = join_conditions[0]
                base_table = first_condition[0]  # table_name1 (ex: "mcv")
                
                # Construire la chaîne SQL de base avec la première table
                query = f"SELECT * FROM {base_table}"
                
                # Pour les tables avec occurrence, on extrait la liste des tables uniques
                table_aliases = set()
                for condition in join_conditions:
                    table1 = condition[0]
                    table2 = condition[3]
                    table_aliases.add(f"{table1}_{condition[1]}")  # ex: "mcv_0"
                    table_aliases.add(f"{table2}_{condition[4]}")  # ex: "mcv_1"
                
                # Construire la clause WHERE pour les conditions de jointure
                join_where_clauses = []
                for condition in join_conditions:
                    table1 = condition[0]
                    attribute1 = condition[2]
                    table2 = condition[3]
                    attribute2 = condition[5]
                    join_where_clauses.append(f"{base_table}.{attribute1} = {base_table}.{attribute2}")
                
                # Ajouter WHERE pour les conditions de jointure
                if join_where_clauses:
                    query += " WHERE " + " AND ".join(join_where_clauses)
                
                # Gérer la clause WHERE supplémentaire
                if where_clause:
                    if isinstance(where_clause, (list, tuple)):
                        where_conditions = []
                        for col_name, val in where_clause:
                            # Extraire la partie colonne des chaînes comme "mcv_0.arg1"
                            if '.' in col_name:
                                base_col = col_name.split('.')[1]  # Obtenir "arg1" de "mcv_0.arg1"
                            else:
                                base_col = col_name
                                
                            # Formater avec la table de base
                            if isinstance(val, str):
                                where_conditions.append(f"{base_table}.{base_col} = '{val}'")
                            else:
                                where_conditions.append(f"{base_table}.{base_col} = {val}")
                        
                        where_str = " AND ".join(where_conditions)
                        if "WHERE" in query:
                            query += f" AND {where_str}"
                        else:
                            query += f" WHERE {where_str}"
                    else:
                        # Remplacer les alias de table par le nom de base dans where_clause
                        modified_where = where_clause
                        for alias in table_aliases:
                            # Remplace "mcv_0." par "mcv."
                            modified_where = modified_where.replace(f"{alias}.", f"{base_table}.")
                            
                        if "WHERE" in query:
                            query += f" AND {modified_where}"
                        else:
                            query += f" WHERE {modified_where}"
            else:
                # ...existing code for dict format...
                first_condition = join_conditions[0]
                first_table = first_condition['table1']
                
                # Construire la chaîne SQL de base avec la première table
                query = f"SELECT * FROM {first_table}"
                
                # Ajouter les JOINs
                tables_used = set([first_table])
                for condition in join_conditions:
                    table1 = condition['table1']
                    column1 = condition['column1']
                    table2 = condition['table2']
                    column2 = condition['column2']
                    join_type = condition.get('type', 'inner').upper()
                    
                    # Vérifier si table2 est déjà dans la requête
                    if table2 not in tables_used:
                        query += f" {join_type} JOIN {table2} ON {table1}.{column1} = {table2}.{column2}"
                        tables_used.add(table2)
                    else:
                        # Si la table est déjà présente, ajouter simplement la condition
                        query += f" AND {table1}.{column1} = {table2}.{column2}"
            
                # Ajouter WHERE si spécifié
                if where_clause:
                    # Si where_clause est une liste ou un tuple, on la formate
                    if isinstance(where_clause, (list, tuple)):
                        where_conditions = []
                        for col, val in where_clause:
                            # Gérer les valeurs numériques et les chaînes
                            if isinstance(val, str):
                                where_conditions.append(f"{col} = '{val}'")
                            else:
                                where_conditions.append(f"{col} = {val}")
                        
                        where_str = " AND ".join(where_conditions)
                        if "WHERE" in query:
                            query += f" AND {where_str}"
                        else:
                            query += f" WHERE {where_str}"
                    else:
                        # where_clause est une chaîne
                        if "WHERE" in query:
                            query += f" AND {where_clause}"
                        else:
                            query += f" WHERE {where_clause}"
            
            # Ajouter LIMIT si spécifié
            if limit:
                query += f" LIMIT {limit}"
            
            # Exécuter la requête
            #self.logger_query_time.debug(f"Executing custom join query: {query}")
            df = pd.read_sql_query(query, self.engine)
            return df
            
        except Exception as e:
            self.logger_query_time.error(f"Error executing custom join: {e}")
            return pd.DataFrame()

    def count_distinct_values(self, table_name: str, column_name: str) -> int:
        """
        Compte le nombre de valeurs distinctes dans une colonne.
        
        :param table_name: Nom de la table
        :param column_name: Nom de la colonne
        :return: Nombre de valeurs distinctes
        """
        try:
            query = f"SELECT COUNT(DISTINCT {column_name}) FROM {table_name}"
            
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                count = result.scalar()
                
            return count
        except Exception as e:
            self.logger_query_time.error(f"Error counting distinct values: {e}")
            return 0
    
    def get_correlation_matrix(self, table_name: str) -> pd.DataFrame:
        """
        Calcule la matrice de corrélation entre les colonnes numériques d'une table.
        
        :param table_name: Nom de la table
        :return: DataFrame pandas contenant la matrice de corrélation
        """
        try:
            # Charger la table en tant que DataFrame
            df = pd.read_sql_table(table_name, self.engine)
            
            # Sélectionner uniquement les colonnes numériques
            numeric_columns = df.select_dtypes(include=['number']).columns
            if len(numeric_columns) > 1:
                # Calculer la matrice de corrélation
                correlation_matrix = df[numeric_columns].corr()
                return correlation_matrix
            else:
                self.logger_query_time.warning(f"Table {table_name} has less than 2 numeric columns")
                return pd.DataFrame()
        except Exception as e:
            self.logger_query_time.error(f"Error computing correlation matrix: {e}")
            return pd.DataFrame()