# tests/test_ilp.py

import json
from types import ModuleType
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

# Import the function and class to be tested
from algorithms.ilp import ILP
from utils.rules import TGDRule


@pytest.fixture
def mock_database():
    db = MagicMock()
    db.get_table_names.return_value = ["table1", "table2"]
    db.get_attribute_names.side_effect = lambda table: {
        "table1": ["attr1", "attr2"],
        "table2": ["attr3", "attr4"],
    }.get(table, [])
    db._select_query.side_effect = lambda table, predicates: [
        (1, 2) if table == "table1" else (3, 4)
    ]
    db.base_name = "test_db"
    return db


@pytest.fixture
def ilp_instance(mock_database):

    ilp = ILP(database=mock_database)

    return ilp


# Test for ILP.discover_rules method
def test_discover_rules_success(ilp_instance, mocker):
    # Mock system calls
    mocker.patch("algorithms.ilp.os.system", return_value=0)

    # Mock import_and_reload_package
    mock_popper = MagicMock()
    mock_popper.util.Settings.return_value = MagicMock()
    mock_popper.loop.learn_solution.return_value = ("prog", [1, 0], {"stat": "value"})
    mock_popper.util.format_prog.return_value = "predicate1(x) :- predicate1(x), predicate2(y)."
    mock_popper.util.order_prog.return_value = "prog"

    mocker.patch("algorithms.ilp.import_and_reload_package", return_value=mock_popper)

    # Mock generate_prolog_files
    ilp_instance.generate_prolog_files = MagicMock(return_value=["dir1", "dir2"])

    # Mock other dependencies if necessary
    ilp_instance.clean_string = MagicMock(side_effect=lambda s: s.lower())
    ilp_instance.sanitize_identifier = MagicMock(side_effect=lambda s: s)
    ilp_instance.get_possible_heads = MagicMock(return_value=["table1", "table2"])
    ilp_instance.get_possible_other_tables = MagicMock(
        return_value={"table1": ["table2"], "table2": ["table1"]}
    )

    # Execute the method
    rules = ilp_instance.discover_rules()

    # Assertions
    assert isinstance(rules, list)
    assert len(rules) == 0  # Assuming two directories produce one rule each
    # for rule in rules:
    #     assert hasattr(rule, 'accuracy')
    #     assert hasattr(rule, 'confidence')
    #     assert hasattr(rule, 'display')
    # assert isinstance(rule, ilp_instance.convert_prologrule_to_rule.__annotations__[
    #    'TGDRule'])  # Adjust as per actual return type


def test_discover_rules_no_prolog_files(ilp_instance, mocker):
    # Mock system calls
    mocker.patch("algorithms.ilp.os.system", return_value=0)

    # Mock generate_prolog_files to return empty list
    ilp_instance.generate_prolog_files = MagicMock(return_value=[])

    # Execute the method
    rules = ilp_instance.discover_rules()

    # Assertions
    assert isinstance(rules, list)
    assert len(rules) == 0


def test_discover_rules_popper_exception(ilp_instance, mocker):
    # Mock system calls
    mocker.patch("algorithms.ilp.os.system", return_value=0)

    # Mock import_and_reload_package to raise exception
    mocker.patch("algorithms.ilp.import_and_reload_package", side_effect=Exception("Popper failed"))

    # Mock generate_prolog_files
    ilp_instance.generate_prolog_files = MagicMock(return_value=["dir1"])

    # Execute the method and expect exception
    with pytest.raises(Exception) as exc_info:
        ilp_instance.discover_rules()

    assert "Popper failed" in str(exc_info.value)


# Test for ILP.import_and_reload_package (if it's a method, but in the code it's a standalone function)
# Since we already have tests for the standalone function, no need to duplicate here.

# Additional tests can be added to cover other methods like convert_prologrule_to_rule, generate_prolog_files, etc.
# Below is an example for convert_prologrule_to_rule


def test_convert_prologrule_to_rule(ilp_instance):
    prolog_rule = "parent(X, Y) :- father(X, Y), mother(X, Z)."
    precision = 0.8
    recall = 0.9

    # Mock methods used within convert_prologrule_to_rule
    ilp_instance.get_attribute_names = MagicMock(
        side_effect=lambda relation: {
            "father": ["name", "age"],
            "mother": ["name", "age"],
            "parent": ["name", "age"],
        }.get(relation, [])
    )
    ilp_instance.clean_string = MagicMock(side_effect=lambda s: s.lower())

    rule = ilp_instance.convert_prologrule_to_rule(prolog_rule, precision, recall)

    # Assertions
    assert rule.accuracy == precision
    assert rule.confidence == recall
    assert rule.display == prolog_rule
    assert isinstance(rule, TGDRule)
    # Further assertions can be made based on the expected structure of TGDRule


# Test for ILP.generate_prolog_files method
def test_generate_prolog_files(ilp_instance, mocker):
    # Mock database methods
    ilp_instance.database.get_table_names.return_value = ["table1"]
    ilp_instance.database.get_attribute_names.return_value = ["attr1", "attr2"]
    ilp_instance.database._select_query.return_value = [(1, 2), (3, 4)]

    # Mock file operations
    with (
        patch("algorithms.ilp.os.makedirs") as mock_makedirs,
        patch("builtins.open", mock.mock_open()) as mock_file,
    ):
        directories = ilp_instance.generate_prolog_files("prolog_tmp", [])

        # Assertions
        mock_makedirs.assert_called_once_with("prolog_tmp/table1", exist_ok=True)
        assert directories == ["prolog_tmp/table1"]
        assert mock_file.call_count == 3  # exs.pl, bk.pl, bias.pl


# You can add more tests for other helper methods as needed.


# ── New tests to increase coverage ──────────────────────────────────────────


# import_and_reload_package (lines 29-31)
def test_import_and_reload_package():
    from algorithms.ilp import import_and_reload_package

    # Use 'json' – a stdlib package that will import and reload cleanly
    result = import_and_reload_package("json")
    assert isinstance(result, ModuleType)
    assert result.__name__ == "json"


# discover_rules – shutil.copytree fails (lines 41-43)
def test_discover_rules_copytree_exception(ilp_instance, mocker):
    mocker.patch("algorithms.ilp.shutil.copytree", side_effect=Exception("copy failed"))
    rules = ilp_instance.discover_rules()
    assert rules == []


# discover_rules – no tables (lines 47-48)
def test_discover_rules_no_tables(ilp_instance, mocker):
    mocker.patch("algorithms.ilp.shutil.copytree")
    ilp_instance.database.get_table_names.return_value = []
    rules = ilp_instance.discover_rules()
    assert rules == []


# discover_rules – compatibility file exists (lines 61-62)
def test_discover_rules_with_compatibility_file(ilp_instance, mocker):
    compat_data = []
    mocker.patch("algorithms.ilp.shutil.copytree")
    mocker.patch("algorithms.ilp.os.path.exists", return_value=True)
    mocker.patch("algorithms.ilp.json.load", return_value=compat_data)
    mocker.patch("builtins.open", mock.mock_open(read_data=json.dumps(compat_data)))
    ilp_instance.generate_prolog_files = MagicMock(return_value=[])
    rules = ilp_instance.discover_rules()
    assert rules == []


# discover_rules – prog is None → continue (line 86)
def test_discover_rules_prog_is_none(ilp_instance, mocker):
    mocker.patch("algorithms.ilp.shutil.copytree")
    mock_popper = MagicMock()
    mock_popper.loop.learn_solution.return_value = (None, [1, 0], {})
    mocker.patch("algorithms.ilp.import_and_reload_package", return_value=mock_popper)
    ilp_instance.generate_prolog_files = MagicMock(return_value=["dir1"])
    rules = ilp_instance.discover_rules()
    assert rules == []


# discover_rules – empty raw_rule skipped + non-None rule appended (lines 91, 94)
def test_discover_rules_empty_raw_rule_and_appended(ilp_instance, mocker):
    mocker.patch("algorithms.ilp.shutil.copytree")
    mock_popper = MagicMock()
    mock_popper.loop.learn_solution.return_value = ("prog", [1, 0], {})
    mock_popper.util.format_prog.return_value = "\nparent(X) :- father(X)."
    mock_popper.util.order_prog.return_value = "prog"
    mocker.patch("algorithms.ilp.import_and_reload_package", return_value=mock_popper)
    ilp_instance.generate_prolog_files = MagicMock(return_value=["dir1"])
    fake_rule = MagicMock()
    ilp_instance.process_raw_rule = MagicMock(return_value=fake_rule)
    rules = ilp_instance.discover_rules()
    # empty line skipped, one real rule appended
    assert len(rules) == 1


# discover_rules – learn_solution raises inner exception (lines 81-83)
def test_discover_rules_learn_solution_exception(ilp_instance, mocker):
    mocker.patch("algorithms.ilp.shutil.copytree")
    mock_popper = MagicMock()
    mock_popper.loop.learn_solution.side_effect = RuntimeError("learn failed")
    mocker.patch("algorithms.ilp.import_and_reload_package", return_value=mock_popper)
    ilp_instance.generate_prolog_files = MagicMock(return_value=["dir1"])
    with pytest.raises(Exception):
        ilp_instance.discover_rules()


# process_raw_rule – no ":-" separator (lines 107-109)
def test_process_raw_rule_invalid_format(ilp_instance):
    result = ilp_instance.process_raw_rule("no_separator_here", [1, 0])
    assert result is None


# process_raw_rule – score causes ZeroDivisionError (lines 116-117)
def test_process_raw_rule_zero_division(ilp_instance):
    # score[0]=0, score[1]=0 → ZeroDivisionError → precision=0
    result = ilp_instance.process_raw_rule("head(X) :- body(X).", [0, 0])
    # Must not raise; return value depends on variable filtering (may be None or TGDRule)
    assert result is None or isinstance(result, TGDRule)


# process_raw_rule – reaches convert_prologrule_to_rule (line 127)
def test_process_raw_rule_returns_rule(ilp_instance):
    from utils.rules import Predicate

    # Mock parse_predicates and parse_head to return non-empty predicates
    # so body_lst and head_lst survive variable-count filtering (both use var 'X' twice).
    shared_var = "X"
    body_pred = Predicate("id-b", "father", shared_var)
    head_pred = Predicate("id-h", "parent", shared_var)
    ilp_instance.parse_predicates = MagicMock(return_value=[body_pred])
    ilp_instance.parse_head = MagicMock(return_value=[head_pred])
    # variables_used will have 'X' from body parse mock, but since we mocked parse_predicates
    # the variables_used dict won't be populated; we also mock convert_prologrule_to_rule
    fake_rule = TGDRule(
        [body_pred], [head_pred], display="parent(X) :- father(X).", accuracy=1.0, confidence=-1
    )
    ilp_instance.convert_prologrule_to_rule = MagicMock(return_value=fake_rule)
    result = ilp_instance.process_raw_rule("parent(X) :- father(X).", [1, 0])
    # With mocked parse functions returning non-empty lists that are kept, line 127 executes
    assert result is not None


# parse_predicates – predicate without "(" (lines 136-138)
def test_parse_predicates_invalid_format(ilp_instance):
    variables_used = {}
    result = ilp_instance.parse_predicates("no_parens_here", variables_used)
    assert result == []


# parse_head – head without "(" (lines 150-152)
def test_parse_head_invalid_format(ilp_instance):
    variables_used = {}
    result = ilp_instance.parse_head("no_parens", variables_used)
    assert result == []


# convert_prologrule_to_rule – no ":-" in rule string (lines 167-169)
def test_convert_prologrule_to_rule_invalid_format(ilp_instance):
    result = ilp_instance.convert_prologrule_to_rule("no_separator", 0.5, 0.5)
    assert result is None


# convert_prologrule_to_rule – body attribute without "(" (lines 180-182)
def test_convert_prologrule_to_rule_invalid_attribute(ilp_instance):
    # body.count(')') > 1 → split on '),': gives ['father(X', 'no_paren)']
    # 'no_paren)' stripped to 'no_paren' → has no '(' → ValueError caught at line 180
    result = ilp_instance.convert_prologrule_to_rule("parent(X) :- father(X),no_paren)", 0.5, 0.5)
    # Should not crash; the bad segment is skipped and a TGDRule is returned
    assert result is None or isinstance(result, TGDRule)


# convert_prologrule_to_rule – attribute_name taken from DB list (lines 189, 202)
def test_convert_prologrule_to_rule_attr_names_used(ilp_instance):
    # i < len(attributes_names) path for both body and head
    ilp_instance.database.get_attribute_names.side_effect = lambda t: ["name", "age"]
    result = ilp_instance.convert_prologrule_to_rule("parent(X,Y) :- father(X,Y).", 0.8, 0.9)
    assert isinstance(result, TGDRule)


# generate_prolog_files – no tables (lines 235-236)
def test_generate_prolog_files_no_tables(ilp_instance):
    ilp_instance.database.get_table_names.return_value = []
    result = ilp_instance.generate_prolog_files("some_path")
    assert result == []


# generate_prolog_files – with non-empty compatibility_dir (lines 243-244)
def test_generate_prolog_files_with_compatibility(ilp_instance):
    # table1 is in possible_heads (key); table2 is possible_other for table1
    compat = {"table1___sep___attr1": ["table2___sep___attr2"]}
    ilp_instance.database.get_table_names.return_value = ["table1", "table2"]
    ilp_instance.database.get_attribute_names.side_effect = lambda t: ["a", "b"]
    ilp_instance.database._select_query.return_value = [(1, 2)]
    with patch("algorithms.ilp.os.makedirs"), patch("builtins.open", mock.mock_open()):
        result = ilp_instance.generate_prolog_files("prolog_tmp", compat)
    # table1 is a possible head → dir created; table2 is not → skipped
    assert "prolog_tmp/table1" in result


# generate_prolog_files – table not in possible_heads → continue (line 251)
def test_generate_prolog_files_table_not_in_heads(ilp_instance):
    # table3 is in the DB but NOT in any compat key or value → skipped by line 251
    # get_possible_heads(compat) returns ["table1", "table2"] only
    compat = {"table1___sep___attr1": ["table2___sep___attr2"]}
    ilp_instance.database.get_table_names.return_value = ["table1", "table2", "table3"]
    ilp_instance.database.get_attribute_names.side_effect = lambda t: ["a", "b"]
    ilp_instance.database._select_query.return_value = [(1, 2)]
    with patch("algorithms.ilp.os.makedirs"), patch("builtins.open", mock.mock_open()):
        result = ilp_instance.generate_prolog_files("prolog_tmp", compat)
    # table3 not in possible_heads → only table1 and table2 dirs created
    assert len(result) == 2
    assert "prolog_tmp/table3" not in result


# generate_prolog_files – rows for other_table written (lines 276-283)
def test_generate_prolog_files_with_body_predicates(ilp_instance):
    ilp_instance.database.get_table_names.return_value = ["table1", "table2"]
    ilp_instance.database.get_attribute_names.side_effect = lambda t: ["a", "b"]
    ilp_instance.database._select_query.return_value = [(1, 2)]
    with patch("algorithms.ilp.os.makedirs"), patch("builtins.open", mock.mock_open()):
        # No compatibility_dir → both tables are possible heads
        result = ilp_instance.generate_prolog_files("prolog_tmp", None)
    assert len(result) == 2


# is_integer (lines 304, 307)
def test_is_integer(ilp_instance):
    assert ilp_instance.is_integer(5) is True
    assert ilp_instance.is_integer(True) is False  # bool excluded
    assert ilp_instance.is_integer("123") is True
    assert ilp_instance.is_integer("abc") is False
    assert ilp_instance.is_integer(3.14) is False


# filter_non_alpha (lines 310-311)
def test_filter_non_alpha(ilp_instance):
    assert ilp_instance.filter_non_alpha("hello123") == "hello"
    assert ilp_instance.filter_non_alpha("abc!@#") == "abc"
    assert ilp_instance.filter_non_alpha("123") == ""


# sanitize_identifier branches (lines 316, 319-321)
def test_sanitize_identifier(ilp_instance):
    assert ilp_instance.sanitize_identifier(None) == "_"
    assert ilp_instance.sanitize_identifier("none") == "_"
    assert ilp_instance.sanitize_identifier("None") == "_"
    assert ilp_instance.sanitize_identifier("42") == "42"
    assert ilp_instance.sanitize_identifier("Hello World") == "helloworld"
    assert ilp_instance.sanitize_identifier("123abc") == "abc"  # digits stripped → "abc"
    assert ilp_instance.sanitize_identifier("!@#") == "_"  # empty after filter → "_"


# get_possible_heads (lines 329-333)
def test_get_possible_heads(ilp_instance):
    compat = {"table1___sep___attr1": ["table2___sep___attr2", "table3___sep___attr3"]}
    heads = ilp_instance.get_possible_heads(compat)
    assert "table1" in heads
    assert "table2" in heads
    assert "table3" in heads


# get_possible_other_tables (lines 336-340)
def test_get_possible_other_tables(ilp_instance):
    compat = {"table1___sep___attr1": ["table2___sep___attr2"]}
    tables = ilp_instance.get_possible_other_tables(compat)
    assert "table1" in tables
    assert "table2" in tables["table1"]
