"""Tests for src/database/triple_converter.py"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)

from database.triple_converter import TripleConverter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_logger():
    return MagicMock()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_engine_and_metadata():
    """Real in-memory SQLite engine with users + posts (FK relationship)."""
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    users = Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
        Column("email", String),
    )
    posts = Table(
        "posts",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("users.id")),
        Column("title", String),
    )

    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(
            users.insert(),
            [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
            ],
        )
        conn.execute(
            posts.insert(),
            [
                {"id": 1, "user_id": 1, "title": "Post 1"},
                {"id": 2, "user_id": 2, "title": "Post 2"},
            ],
        )

    return engine, metadata


# ---------------------------------------------------------------------------
# 1. Basic integration test
# ---------------------------------------------------------------------------


def test_convert_to_triples_basic(basic_engine_and_metadata):
    engine, metadata = basic_engine_and_metadata
    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    triples = converter.convert_to_triples()

    # Literal triples from users table (non-PK attributes)
    assert ("users_1", "users.name", '"Alice"') in triples
    assert ("users_1", "users.email", '"alice@example.com"') in triples
    assert ("users_2", "users.name", '"Bob"') in triples
    assert ("users_2", "users.email", '"bob@example.com"') in triples

    # FK triples from posts table
    assert ("posts_1", "posts.user_id", "users_1") in triples
    assert ("posts_2", "posts.user_id", "users_2") in triples

    # Literal triples from posts table
    assert ("posts_1", "posts.title", '"Post 1"') in triples
    assert ("posts_2", "posts.title", '"Post 2"') in triples

    # PK columns should NOT produce literal triples
    assert not any(t[1] == "users.id" for t in triples)
    assert not any(t[1] == "posts.id" for t in triples)


# ---------------------------------------------------------------------------
# 2. Table with no primary key → skipped with warning
# ---------------------------------------------------------------------------


def test_convert_to_triples_table_no_pk():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    # SQLAlchemy requires at least one PK to enforce FK, so we create the table
    # without declaring a primary_key constraint.
    Table(
        "no_pk_table",
        metadata,
        Column("col_a", String),
        Column("col_b", String),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO no_pk_table VALUES ('x', 'y')"))

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)
    triples = converter.convert_to_triples()

    assert triples == []
    logger.warning.assert_called()
    warning_msg = logger.warning.call_args[0][0]
    assert "no_pk_table" in warning_msg


# ---------------------------------------------------------------------------
# 3. Table with only 1 column → skipped with warning
# ---------------------------------------------------------------------------


def test_convert_to_triples_table_single_column():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    Table(
        "single_col",
        metadata,
        Column("id", Integer, primary_key=True),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO single_col VALUES (1)"))

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)
    triples = converter.convert_to_triples()

    assert triples == []
    logger.warning.assert_called()
    warning_msg = logger.warning.call_args[0][0]
    assert "single_col" in warning_msg


# ---------------------------------------------------------------------------
# 4. Row where PK value is None → error logged, row skipped
# ---------------------------------------------------------------------------


def test_convert_to_triples_null_pk_value():
    """
    A row where the PK column value is None must be skipped and an error logged.

    SQLite's INTEGER PRIMARY KEY auto-assigns a rowid when NULL is inserted, so
    we cannot use a real INSERT to plant a NULL PK.  Instead we patch
    _select_query to return a synthetic row where id=None.
    """
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    Table(
        "items",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
    )
    metadata.create_all(engine)

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    # Inject a row where the PK column 'id' is None
    with patch.object(converter, "_select_query", return_value=[(None, "nokey")]):
        triples = converter.convert_to_triples()

    # The None-pk row must be skipped
    assert triples == []
    logger.error.assert_called()
    error_msg = logger.error.call_args[0][0]
    assert "items" in error_msg


# ---------------------------------------------------------------------------
# 5. Row where a non-PK attribute is None → that attribute skipped
# ---------------------------------------------------------------------------


def test_convert_to_triples_null_attribute_value():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    Table(
        "products",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
        Column("description", String),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO products (id, name, description) VALUES (1, 'Widget', NULL)")
        )

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)
    triples = converter.convert_to_triples()

    subjects = [t[0] for t in triples]
    assert "products_1" in subjects

    # description is NULL → no triple for it
    assert not any(t[1] == "products.description" for t in triples)

    # name is present → triple exists
    assert ("products_1", "products.name", '"Widget"') in triples


# ---------------------------------------------------------------------------
# 6. FK column exists but ref_column value is None in the row → FK triple skipped
# ---------------------------------------------------------------------------


def test_convert_to_triples_fk_missing_ref_column():
    """
    Line 76: `ref_column not in row_dict` fires when the referenced table's PK
    column name does not appear among the current table's columns.

    Setup: orders.user_id is a "FK" pointing to a target whose PK is named
    "user_key" — a name that does not exist as a column in orders.  So when
    iterating over an orders row, `ref_column ("user_key") not in row_dict` is
    True and the FK triple is skipped (line 76 `continue`).
    """
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    # target table: PK column named "user_key" (unusual name, not present in orders)
    Table(
        "users",
        metadata,
        Column("user_key", Integer, primary_key=True),
        Column("name", String),
    )
    orders_table = Table(
        "orders",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer),  # no real FK constraint — we inject it via patch
        Column("product", String),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (user_key, name) VALUES (1, 'Alice')"))
        conn.execute(
            orders_table.insert(),
            [{"id": 1, "user_id": 1, "product": "Widget"}],
        )

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    # Inject a FK: orders.user_id → users.user_key
    # row_dict for orders will have keys: id, user_id, product
    # ref_column = "user_key" is NOT in row_dict → line 76 fires
    with patch.object(
        converter,
        "_get_foreign_keys",
        return_value={"orders": {"user_id": ("users", "user_key")}},
    ):
        triples = converter.convert_to_triples()

    # FK triple must be skipped
    assert not any(t[0] == "orders_1" and t[2].startswith("users_") for t in triples)
    # Literal triple for product must still appear
    assert ("orders_1", "orders.product", '"Widget"') in triples


# ---------------------------------------------------------------------------
# 7. FK references a table with no PK → warning logged, FK triple skipped
# ---------------------------------------------------------------------------


def test_convert_to_triples_fk_no_ref_pk():
    """
    Inject a fake fk_columns entry pointing to a table that has no PK
    in the primary_keys dict.  This exercises the `if not ref_pk_columns` branch.
    """
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    items_table = Table(
        "items",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("ref_id", Integer),
        Column("label", String),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(
            items_table.insert(),
            [{"id": 1, "ref_id": 99, "label": "foo"}],
        )

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    # Patch _get_foreign_keys to pretend ref_id is a FK to "ghost_table"
    # and patch _get_primary_keys to return [] for ghost_table
    original_get_fk = converter._get_foreign_keys
    original_get_pk = converter._get_primary_keys

    def fake_get_foreign_keys():
        fks = original_get_fk()
        fks["items"] = {"ref_id": ("ghost_table", "ref_id")}
        return fks

    def fake_get_primary_keys(table_name):
        if table_name == "ghost_table":
            return []
        return original_get_pk(table_name)

    with (
        patch.object(converter, "_get_foreign_keys", side_effect=fake_get_foreign_keys),
        patch.object(converter, "_get_primary_keys", side_effect=fake_get_primary_keys),
    ):
        # Also need primary_keys dict computed inside convert_to_triples to know ghost_table has no pk.
        # We need to patch the call inside convert_to_triples; the easiest approach is to
        # let the method run naturally — but convert_to_triples builds primary_keys via
        # `_get_table_names()` which only returns tables in metadata (ghost_table absent).
        # So primary_keys.get("ghost_table", []) == [] automatically. Good.
        triples = converter.convert_to_triples()

    # FK triple must not appear
    assert not any(t[1] == "items.ref_id" and not t[2].startswith('"') for t in triples)
    logger.warning.assert_called()
    warning_calls = [str(c) for c in logger.warning.call_args_list]
    assert any("ghost_table" in msg for msg in warning_calls)


# ---------------------------------------------------------------------------
# 8. FK processing raises an exception → error logged, continues
# ---------------------------------------------------------------------------


def test_convert_to_triples_fk_exception():
    """
    Patch _generate_rdf_id to raise when called with ref_table name,
    which causes the except branch in the FK handling block to fire.
    """
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    users_table = Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
    )
    orders_table = Table(
        "orders",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("users.id")),
        Column("product", String),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(users_table.insert(), [{"id": 1, "name": "Alice"}])
        conn.execute(orders_table.insert(), [{"id": 1, "user_id": 1, "product": "Widget"}])

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    original_generate = converter._generate_rdf_id

    def raising_generate(table, primary_keys, row_dict):
        # FK ref calls use a single-entry dict: {ref_column: value}.
        # Normal subject calls include all row columns (>1 key here).
        # Raise only for the FK ref resolution targeting the users table.
        if table == "users" and len(row_dict) == 1:
            raise RuntimeError("forced error on FK ref generation")
        return original_generate(table, primary_keys, row_dict)

    with patch.object(converter, "_generate_rdf_id", side_effect=raising_generate):
        triples = converter.convert_to_triples()

    # No FK triple for orders; literal triples may still appear
    assert not any(t[0].startswith("orders") and t[2].startswith("users") for t in triples)
    logger.error.assert_called()
    error_calls = [str(c) for c in logger.error.call_args_list]
    assert any("orders" in msg for msg in error_calls)


# ---------------------------------------------------------------------------
# 9. _get_foreign_keys returns correct mapping
# ---------------------------------------------------------------------------


def test_get_foreign_keys():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    Table(
        "authors",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
    )
    Table(
        "books",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("author_id", Integer, ForeignKey("authors.id")),
        Column("title", String),
    )

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    fks = converter._get_foreign_keys()

    assert "books" in fks
    assert "author_id" in fks["books"]
    assert fks["books"]["author_id"] == ("authors", "id")
    # authors table has no FKs
    assert "authors" not in fks


# ---------------------------------------------------------------------------
# 10. _get_primary_keys returns correct columns
# ---------------------------------------------------------------------------


def test_get_primary_keys():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    Table(
        "things",
        metadata,
        Column("pk1", Integer, primary_key=True),
        Column("pk2", String, primary_key=True),
        Column("val", String),
    )

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    pks = converter._get_primary_keys("things")
    assert set(pks) == {"pk1", "pk2"}

    # Non-existent table returns []
    assert converter._get_primary_keys("nonexistent") == []


# ---------------------------------------------------------------------------
# 11. _get_attribute_names returns all columns
# ---------------------------------------------------------------------------


def test_get_attribute_names():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    Table(
        "widgets",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("color", String),
        Column("weight", Integer),
    )

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    attrs = converter._get_attribute_names("widgets")
    assert set(attrs) == {"id", "color", "weight"}

    # Non-existent table returns []
    assert converter._get_attribute_names("nonexistent") == []


# ---------------------------------------------------------------------------
# 12. _select_query on non-existent table returns []
# ---------------------------------------------------------------------------


def test_select_query_no_table():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    result = converter._select_query("does_not_exist", ["col"])
    assert result == []


# ---------------------------------------------------------------------------
# 13. _select_query when no attributes match returns []
# ---------------------------------------------------------------------------


def test_select_query_no_columns():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    Table(
        "stuff",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("val", String),
    )
    metadata.create_all(engine)

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    # Pass attributes that don't exist in the table
    result = converter._select_query("stuff", ["nonexistent_col"])
    assert result == []


# ---------------------------------------------------------------------------
# 14. _select_query when engine.connect raises → logs error, returns []
# ---------------------------------------------------------------------------


def test_select_query_exception():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    Table(
        "data",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("value", String),
    )
    # Do NOT call create_all so the actual table doesn't exist in the DB

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    # Mock engine.connect to raise an exception
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("connection refused")
    converter.engine = mock_engine

    result = converter._select_query("data", ["id", "value"])
    assert result == []
    logger.error.assert_called()
    error_msg = logger.error.call_args[0][0]
    assert "data" in error_msg


# ---------------------------------------------------------------------------
# 15. _generate_rdf_id with missing PK key → logs error, returns "unknown_id"
# ---------------------------------------------------------------------------


def test_generate_rdf_id_missing_key():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)

    # primary_keys references "missing_pk" but row_dict doesn't have it
    result = converter._generate_rdf_id(
        table="mytable",
        primary_keys=["missing_pk"],
        row_dict={"other_col": 42},
    )

    assert result == "unknown_id"
    logger.error.assert_called()
    error_msg = logger.error.call_args[0][0]
    assert "mytable" in error_msg


# ---------------------------------------------------------------------------
# 16. _sanitize_identifier converts non-alnum to _
# ---------------------------------------------------------------------------


def test_sanitize_identifier():
    assert TripleConverter._sanitize_identifier("hello world") == "hello_world"
    assert TripleConverter._sanitize_identifier("abc123") == "abc123"
    assert TripleConverter._sanitize_identifier("foo-bar.baz") == "foo_bar_baz"
    assert TripleConverter._sanitize_identifier("") == ""
    assert TripleConverter._sanitize_identifier("a@b#c$d") == "a_b_c_d"
    assert TripleConverter._sanitize_identifier("   ") == "___"


# ---------------------------------------------------------------------------
# Extra: value with embedded quote is escaped
# ---------------------------------------------------------------------------


def test_convert_to_triples_value_with_quote():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    t = Table(
        "quotes_test",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("label", String),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(t.insert(), [{"id": 1, "label": 'say "hello"'}])

    logger = make_logger()
    converter = TripleConverter(engine, metadata, logger)
    triples = converter.convert_to_triples()

    # The embedded double-quote in the value must be backslash-escaped.
    # The source value 'say "hello"' → safe_value = 'say \\"hello\\"'
    # so the triple object value is: '"say \\"hello\\""'
    # We verify by checking the full expected triple is present.
    expected_value = '"say \\"hello\\""'
    assert any(
        triple == ("quotes_test_1", "quotes_test.label", expected_value) for triple in triples
    )
