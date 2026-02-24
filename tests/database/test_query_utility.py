import logging
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
)

from database.query_utility import ColorFormatter, QueryUtility


@pytest.fixture
def mock_logger():
    logger_query_time = MagicMock()
    logger_query_results = MagicMock()
    return logger_query_time, logger_query_results


@pytest.fixture
def in_memory_metadata():
    """Create an in-memory metadata with tables for testing."""
    metadata = MetaData()
    # Example tables
    Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
        Column("age", Integer),
    )

    Table(
        "posts",
        metadata,
        Column("post_id", Integer, primary_key=True),
        Column("user_id", Integer),
        Column("content", String),
    )
    return metadata


@pytest.fixture
def mock_engine():
    # Mock an SQLAlchemy engine
    engine = MagicMock()
    conn = MagicMock()
    # Mock the engine.connect() to return a mock connection
    engine.connect.return_value.__enter__.return_value = conn

    # Mock a simple scalar result
    # By default, scalar() returns None; you can set return values in tests if needed.
    conn.execute.return_value.scalar.return_value = None
    return engine, conn


@pytest.fixture
def query_utility(mock_engine, in_memory_metadata, mock_logger):
    engine, _ = mock_engine
    logger_query_time, logger_query_results = mock_logger
    return QueryUtility(engine, in_memory_metadata, logger_query_time, logger_query_results)


def test_check_threshold_no_query(query_utility, mock_engine):
    # If _construct_threshold_query returns None, should return 0
    # We can simulate this by passing empty join_conditions that produce no query
    result = query_utility.check_threshold(join_conditions=[])
    assert result == 0


def test_get_join_row_count_no_query(query_utility, mock_engine):
    # Similarly, if no query is constructed, result should be 0
    result = query_utility.get_join_row_count(join_conditions=[])
    assert result == 0


def test_check_threshold(query_utility, mock_engine):
    engine, conn = mock_engine

    # Mock a scenario where a query is constructed. We provide join_conditions that should be valid.
    # Let's join users.id = posts.user_id
    join_conditions = [("users", 1, "id", "posts", 1, "user_id")]

    # Mock the database result
    # The query checks threshold by counting rows > threshold
    # Let's say the result is True (meaning threshold exceeded)
    conn.execute.return_value.scalar.return_value = True

    result = query_utility.check_threshold(join_conditions=join_conditions, threshold=1)
    assert result == 1  # True converted to int is 1

    # Check that a query was executed
    assert conn.execute.called


def test_get_join_row_count(query_utility, mock_engine):
    engine, conn = mock_engine

    # Setup a simple join condition
    join_conditions = [("users", 1, "id", "posts", 1, "user_id")]
    conn.execute.return_value.scalar.return_value = 5  # Suppose 5 rows match

    result = query_utility.get_join_row_count(join_conditions=join_conditions)
    assert result == 5

    assert conn.execute.called


def test_organize_join_conditions(query_utility):
    join_conditions = [
        ("users", 1, "id", "posts", 1, "user_id"),
        ("users", 1, "name", "users", 1, "name"),  # same table, same occurrence
    ]
    # Access the internal method for testing (generally not recommended, but okay for unit tests)
    organized = query_utility._organize_join_conditions(join_conditions)
    # Expect keys for each unique set of (table, occurrence)
    # For ("users",1) <-> ("posts",1) and ("users",1) alone
    assert len(organized) == 2


def test_get_or_create_alias_existing_table(query_utility, in_memory_metadata):
    aliases = {}
    alias_obj = query_utility._get_or_create_alias(aliases, "users", 1)
    assert "users_1" in aliases
    # Recalling _get_or_create_alias should return the same alias object
    alias_obj2 = query_utility._get_or_create_alias(aliases, "users", 1)
    assert alias_obj is alias_obj2


def test_get_or_create_alias_non_existing_table(query_utility):
    aliases = {}
    with pytest.raises(ValueError) as exc:
        query_utility._get_or_create_alias(aliases, "non_existent", 1)
    assert "does not exist" in str(exc.value)


def test_attribute_helpers(query_utility):
    # Check attribute helpers on known tables
    tables = query_utility._get_table_names()
    assert "users" in tables
    assert "posts" in tables

    user_columns = query_utility._get_attribute_names("users")
    assert set(user_columns) == {"id", "name", "age"}

    # Check domain
    domain = query_utility._get_attribute_domain("users", "id")
    # Domain will be the SQLAlchemy type name, something like INTEGER
    assert "INTEGER" in domain.upper()

    # Check primary key
    assert query_utility._get_attribute_is_key("users", "id") is True
    assert query_utility._get_attribute_is_key("users", "name") is False


def test_disjoint_semantics_primary_key_conditions(query_utility, in_memory_metadata):
    # Test the creation of primary key conditions under disjoint semantics
    # For simplicity, we will just call _construct_query_base with disjoint_semantics=True
    join_conditions = [("users", 1, "id", "posts", 1, "user_id")]

    query, primary_key_conditions, join_base = query_utility._construct_query_base(
        join_conditions=join_conditions,
        disjoint_semantics=True,
        distinct=False,
        count_over=None,
    )

    # We expect query not to be None
    assert query is not None
    # primary_key_conditions might include conditions for ensuring distinct primary keys if multiple occurrences
    # but in this simple case, there's just one occurrence of each table.
    # So no PK inequality conditions expected between multiple occurrences of the same table.
    # We still should have some conditions related to the join.
    # Check that primary_key_conditions is at least not None
    assert primary_key_conditions is not None


def test_count_over_clause(query_utility, mock_engine):
    engine, conn = mock_engine
    # count_over scenario: we specify attributes over which we want a distinct count
    join_conditions = [("users", 1, "id", "posts", 1, "user_id")]
    count_over = [[("users", 1, "id")]]

    conn.execute.return_value.scalar.return_value = 10

    result = query_utility.get_join_row_count(
        join_conditions=join_conditions,
        disjoint_semantics=False,
        distinct=False,
        count_over=count_over,
    )
    assert result == 10
    assert conn.execute.called


# ---------------------------------------------------------------------------
# New tests for uncovered lines
# ---------------------------------------------------------------------------


def test_color_formatter_format():
    """Lines 34-36: ColorFormatter.format() applies color to record.msg."""
    formatter = ColorFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "hello" in formatted


def test_check_threshold_query_execution_error(query_utility, mock_engine):
    """Lines 90-92: engine.connect raises during check_threshold."""
    engine, conn = mock_engine
    conn.execute.side_effect = Exception("DB error")
    join_conditions = [("users", 1, "id", "posts", 1, "user_id")]
    result = query_utility.check_threshold(join_conditions=join_conditions)
    assert result == 0
    query_utility.logger_query_time.error.assert_called()


def test_get_join_row_count_query_execution_error(query_utility, mock_engine):
    """Lines 123-125: engine.connect raises during get_join_row_count."""
    engine, conn = mock_engine
    conn.execute.side_effect = Exception("DB error")
    join_conditions = [("users", 1, "id", "posts", 1, "user_id")]
    result = query_utility.get_join_row_count(join_conditions=join_conditions)
    assert result == 0
    query_utility.logger_query_time.error.assert_called()


def test_construct_threshold_query_with_pk_conditions(query_utility, in_memory_metadata):
    """Line 156: primary_key_conditions applied to threshold query (two occurrences of users)."""
    # users appears as occurrence 1 and 2 -> disjoint_semantics generates PK conditions
    join_conditions = [
        ("users", 1, "id", "posts", 1, "user_id"),
        ("users", 2, "id", "posts", 1, "user_id"),
        ("users", 1, "id", "users", 2, "id"),
    ]
    query, pk_conds, join_base = query_utility._construct_threshold_query(
        join_conditions, disjoint_semantics=True, distinct=False, count_over=None, threshold=1
    )
    # The pk_conds should be non-empty because users appears twice
    assert query is not None
    assert len(pk_conds) > 0


def test_construct_query_base_process_exception(query_utility, mock_engine):
    """Lines 184-186: _process_join_conditions raises, returns None triple."""
    with patch.object(query_utility, "_process_join_conditions", side_effect=RuntimeError("fail")):
        result_query, pk, jb = query_utility._construct_query_base(
            [("users", 1, "id", "posts", 1, "user_id")],
            disjoint_semantics=False,
            distinct=False,
            count_over=None,
        )
    assert result_query is None
    assert pk is None
    assert jb is None


def test_process_join_conditions_unknown_table1(query_utility):
    """Line 229: table_name1 not in metadata.tables -> continue."""
    join_conditions = [("ghost_table", 1, "id", "posts", 1, "user_id")]
    condition_groups = query_utility._organize_join_conditions(join_conditions)
    join_bases, aliases, used_aliases, table_occurrences = query_utility._process_join_conditions(
        condition_groups, disjoint_semantics=False
    )
    assert join_bases == []


def test_process_join_conditions_unknown_table2(query_utility):
    """Line 232: table_name2 not in metadata.tables -> continue.

    Sorted key: [("posts", 1), ("zzz_unknown", 1)] -> table_name1="posts" (valid),
    table_name2="zzz_unknown" (missing) -> hits line 232.
    """
    join_conditions = [("posts", 1, "post_id", "zzz_unknown", 1, "user_id")]
    condition_groups = query_utility._organize_join_conditions(join_conditions)
    join_bases, aliases, used_aliases, table_occurrences = query_utility._process_join_conditions(
        condition_groups, disjoint_semantics=False
    )
    assert join_bases == []


def test_process_join_conditions_forward_attr_match(query_utility, in_memory_metadata):
    """Line 247: attr1 in alias1 columns AND attr2 in alias2 columns (forward branch).

    sorted_key: [("posts", 1), ("users", 1)]  (p < u alphabetically)
    alias1 = posts  (columns: post_id, user_id, content)
    alias2 = users  (columns: id, name, age)
    We need attr1 in posts AND attr2 in users -> e.g. attr1="post_id", attr2="name"
    """
    join_conditions = [("posts", 1, "post_id", "users", 1, "name")]
    condition_groups = query_utility._organize_join_conditions(join_conditions)
    join_bases, aliases, used_aliases, _ = query_utility._process_join_conditions(
        condition_groups, disjoint_semantics=False
    )
    assert len(join_bases) == 1


def test_process_join_conditions_self_join(query_utility, in_memory_metadata):
    """Lines 259-273: frozenset key has length 1 (same table+occurrence join)."""
    # Both sides of join condition are same (table, occurrence) -> frozenset has len=1
    join_conditions = [("users", 1, "id", "users", 1, "id")]
    condition_groups = query_utility._organize_join_conditions(join_conditions)
    join_bases, aliases, used_aliases, _ = query_utility._process_join_conditions(
        condition_groups, disjoint_semantics=False
    )
    # self-join appended with alias_key2=None
    assert len(join_bases) == 1
    assert join_bases[0][1] is None


def test_process_join_conditions_self_join_unknown_table(query_utility):
    """Lines 261-263: self-join with unknown table -> error logged, continue."""
    join_conditions = [("unknown_table", 1, "col", "unknown_table", 1, "col")]
    condition_groups = query_utility._organize_join_conditions(join_conditions)
    join_bases, aliases, used_aliases, _ = query_utility._process_join_conditions(
        condition_groups, disjoint_semantics=False
    )
    assert join_bases == []
    query_utility.logger_query_time.error.assert_called()


def test_construct_join_empty_join_bases(query_utility):
    """Line 290: _construct_join returns None when join_bases is empty."""
    result, where = query_utility._construct_join([], {}, set())
    assert result is None
    assert where == []


def test_construct_join_with_self_join_condition(query_utility, in_memory_metadata):
    """Line 297: where_constraints when alias_key2 is None (self-join)."""
    join_conditions = [("users", 1, "id", "users", 1, "id")]
    condition_groups = query_utility._organize_join_conditions(join_conditions)
    join_bases, aliases, used_aliases, _ = query_utility._process_join_conditions(
        condition_groups, disjoint_semantics=False
    )
    join_base, where_constraints = query_utility._construct_join(join_bases, aliases, used_aliases)
    assert len(where_constraints) > 0


def test_construct_join_reverse_and_both_in_branches(query_utility, in_memory_metadata):
    """Lines 301-305: alias_key2 already in join (301-303) and both already in join (304-305)."""
    aliases = {}
    alias_u1 = query_utility._get_or_create_alias(aliases, "users", 1)
    alias_u2 = query_utility._get_or_create_alias(aliases, "users", 2)
    alias_p1 = query_utility._get_or_create_alias(aliases, "posts", 1)

    cond1 = alias_u1.columns["id"] == alias_p1.columns["user_id"]
    cond2 = alias_u2.columns["id"] == alias_p1.columns["user_id"]
    cond3 = alias_u1.columns["id"] == alias_u2.columns["id"]

    # Step 1: (users_1, posts_1, cond1)
    #   first_base_key = "users_1" -> used_aliases_in_join = {"users_1"}
    #   iter 1: alias_key1="users_1" IN set, alias_key2="posts_1" NOT -> line 298-300: add "posts_1"
    #   used_aliases_in_join = {"users_1", "posts_1"}
    # Step 2: (users_2, posts_1, cond2)
    #   alias_key1="users_2" NOT in set, alias_key2="posts_1" IN set -> line 301-303: add "users_2"
    # Step 3: (users_1, users_2, cond3)
    #   both in set -> line 304-305: append to where_constraints
    join_bases = [
        ("users_1", "posts_1", cond1),
        ("users_2", "posts_1", cond2),
        ("users_1", "users_2", cond3),
    ]
    used_aliases = {"users_1", "posts_1", "users_2"}
    join_base, where = query_utility._construct_join(join_bases, aliases, used_aliases)
    assert join_base is not None
    # The last condition (cond3) should have been added to where_constraints (line 305)
    assert len(where) >= 1


def test_construct_primary_key_conditions_multiple_occurrences(query_utility, in_memory_metadata):
    """Lines 314-328: generates pk conditions when same table has multiple occurrences."""
    aliases = {}
    query_utility._get_or_create_alias(aliases, "users", 1)
    query_utility._get_or_create_alias(aliases, "users", 2)

    table_occurrences = {"users": {1, 2}}
    used_aliases = {"users_1", "users_2"}

    pk_conds = query_utility._construct_primary_key_conditions(
        table_occurrences, aliases, used_aliases
    )
    assert len(pk_conds) > 0


def test_construct_primary_key_conditions_aliases_not_in_used(query_utility, in_memory_metadata):
    """Line 323: alias keys not in used_aliases -> continue (no pk conditions generated)."""
    aliases = {}
    query_utility._get_or_create_alias(aliases, "users", 1)
    query_utility._get_or_create_alias(aliases, "users", 2)

    table_occurrences = {"users": {1, 2}}
    # Intentionally leave used_aliases empty so alias_key1/alias_key2 are not in it
    used_aliases = set()

    pk_conds = query_utility._construct_primary_key_conditions(
        table_occurrences, aliases, used_aliases
    )
    assert pk_conds == []


def test_construct_select_query_count_over_no_aliases(query_utility, in_memory_metadata):
    """Line 340: raises ValueError when count_over is specified but aliases is None."""
    aliases = {}
    alias_u = query_utility._get_or_create_alias(aliases, "users", 1)
    join_base = alias_u.selectable

    with pytest.raises(ValueError, match="Aliases must be provided"):
        query_utility._construct_select_query(
            join_base, False, count_over=[[("users", 1, "id")]], aliases=None
        )


def test_construct_select_query_count_over_missing_alias(query_utility, in_memory_metadata):
    """Line 349: raises ValueError when alias key not found in aliases."""
    aliases = {}
    alias_u = query_utility._get_or_create_alias(aliases, "users", 1)
    join_base = alias_u.selectable

    # count_over references users_2 which doesn't exist in aliases
    with pytest.raises(ValueError, match="not found in aliases"):
        query_utility._construct_select_query(
            join_base, False, count_over=[[("users", 2, "id")]], aliases=aliases
        )


def test_construct_select_query_count_over_with_pk_conditions(query_utility, in_memory_metadata):
    """Line 355: inner_query.where called when count_over + primary_key_conditions."""
    aliases = {}
    alias_u = query_utility._get_or_create_alias(aliases, "users", 1)
    join_base = alias_u.selectable

    # A dummy primary key condition (always-false, but structurally valid)
    pk_cond = [alias_u.columns["id"] != alias_u.columns["id"]]

    result_query = query_utility._construct_select_query(
        join_base,
        False,
        primary_key_conditions=pk_cond,
        count_over=[[("users", 1, "id")]],
        aliases=aliases,
    )
    assert result_query is not None


def test_construct_select_query_with_pk_conditions_no_count_over(query_utility, in_memory_metadata):
    """Line 362: query.where called when primary_key_conditions and no count_over."""
    aliases = {}
    alias_u = query_utility._get_or_create_alias(aliases, "users", 1)
    join_base = alias_u.selectable

    pk_cond = [alias_u.columns["id"] != alias_u.columns["id"]]

    result_query = query_utility._construct_select_query(
        join_base, False, primary_key_conditions=pk_cond, aliases=aliases
    )
    assert result_query is not None


def test_get_attribute_domain_unknown_column(query_utility):
    """Line 384: returns None when column not found in table."""
    result = query_utility._get_attribute_domain("users", "nonexistent_column")
    assert result is None


def test_get_attribute_is_key_unknown_column(query_utility):
    """Line 398: returns False when column not found."""
    result = query_utility._get_attribute_is_key("users", "nonexistent_column")
    assert result is False


def test_get_foreign_keys_with_real_fk(mock_engine, mock_logger):
    """Lines 405-425: _get_foreign_keys with actual FK relationships."""
    engine, _ = mock_engine
    logger_query_time, logger_query_results = mock_logger

    metadata = MetaData()
    Table(
        "departments",
        metadata,
        Column("dept_id", Integer, primary_key=True),
        Column("name", String),
    )
    Table(
        "employees",
        metadata,
        Column("emp_id", Integer, primary_key=True),
        Column("dept_id", Integer, ForeignKey("departments.dept_id")),
        Column("name", String),
    )

    qu = QueryUtility(engine, metadata, logger_query_time, logger_query_results)
    fk_info = qu._get_foreign_keys()

    assert "employees" in fk_info
    assert "dept_id" in fk_info["employees"]
    assert fk_info["employees"]["dept_id"] == ("departments", "dept_id")


def test_get_foreign_keys_missing_referenced_table(mock_engine, mock_logger):
    """Lines 413-415: referenced table doesn't exist in metadata -> error logged."""
    engine, _ = mock_engine
    logger_query_time, logger_query_results = mock_logger

    metadata = MetaData()
    Table(
        "employees",
        metadata,
        Column("emp_id", Integer, primary_key=True),
        Column("dept_id", Integer),
    )

    # Build a mock FK that points to a table not in metadata
    mock_fk = MagicMock()
    mock_fk.column.table.name = "nonexistent_table"
    mock_fk.parent.name = "dept_id"
    mock_fk.column.name = "dept_id"

    qu = QueryUtility(engine, metadata, logger_query_time, logger_query_results)

    class FakeTableWithFK:
        def __init__(self, name, fks):
            self.name = name
            self.foreign_keys = fks

    fake_table = FakeTableWithFK("employees", [mock_fk])
    fake_metadata_tables = {"employees": fake_table}

    with patch.object(metadata, "tables", fake_metadata_tables):
        qu._get_foreign_keys()

    logger_query_time.error.assert_called()


def test_get_foreign_keys_missing_referenced_column(mock_engine, mock_logger):
    """Lines 418-420: referenced column doesn't exist in referenced table -> error logged."""
    engine, _ = mock_engine
    logger_query_time, logger_query_results = mock_logger

    # departments table exists but does NOT have column "nonexistent_col"
    metadata = MetaData()
    Table(
        "departments",
        metadata,
        Column("dept_id", Integer, primary_key=True),
        Column("name", String),
    )
    Table(
        "employees",
        metadata,
        Column("emp_id", Integer, primary_key=True),
        Column("dept_id", Integer),
    )

    # Mock FK: references departments.nonexistent_col (which is not in departments)
    mock_fk = MagicMock()
    mock_fk.column.table.name = "departments"
    mock_fk.parent.name = "dept_id"
    mock_fk.column.name = "nonexistent_col"

    qu = QueryUtility(engine, metadata, logger_query_time, logger_query_results)

    class FakeTableWithFK:
        def __init__(self, name, fks):
            self.name = name
            self.foreign_keys = fks

    fake_metadata_tables = {
        "employees": FakeTableWithFK("employees", [mock_fk]),
        "departments": metadata.tables["departments"],
    }

    with patch.object(metadata, "tables", fake_metadata_tables):
        qu._get_foreign_keys()

    logger_query_time.error.assert_called()
