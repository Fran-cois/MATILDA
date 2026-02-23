from unittest.mock import MagicMock, patch

import pytest

from algorithms.matilda import MATILDA


@pytest.fixture
def mock_database():
    """Fixture to create a mock database inspector."""
    return MagicMock(name="DatabaseInspector")


@pytest.fixture
def matilda_instance(mock_database):
    """Fixture to create an instance of MATILDA with a mock database."""
    return MATILDA(database=mock_database)


@patch("algorithms.matilda.instantiate_tgd")
@patch("algorithms.matilda.TGDRuleFactory.str_to_tgd")
@patch("algorithms.matilda.split_pruning")
@patch("algorithms.matilda.split_candidate_rule")
@patch("algorithms.matilda.dfs")
@patch("algorithms.matilda.init")
def test_discover_rules_no_jia_list(
    mock_init,
    mock_dfs,
    mock_split_candidate_rule,
    mock_split_pruning,
    mock_str_to_tgd,
    mock_instantiate_tgd,
    matilda_instance,
):
    """Test discover_rules when jia_list is empty — generator yields nothing."""
    mock_init.return_value = (MagicMock(), MagicMock(), [])
    results = list(matilda_instance.discover_rules())
    assert len(results) == 0
    mock_init.assert_called_once_with(
        matilda_instance.db_inspector,
        max_nb_occurrence=3,
        results_path=None,
    )
    mock_dfs.assert_not_called()


def test_init_method(matilda_instance, mock_database):
    """Test the initialization of MATILDA class."""
    assert matilda_instance.db_inspector == mock_database
    assert matilda_instance.settings == {}
    settings = {"nb_occurrence": 5}
    matilda_with_settings = MATILDA(database=mock_database, settings=settings)
    assert matilda_with_settings.settings == settings


@patch("algorithms.matilda.instantiate_tgd")
@patch("algorithms.matilda.TGDRuleFactory.str_to_tgd")
@patch("algorithms.matilda.split_pruning")
@patch("algorithms.matilda.split_candidate_rule")
@patch("algorithms.matilda.dfs")
@patch("algorithms.matilda.init")
def test_discover_rules_split_pruning_false(
    mock_init,
    mock_dfs,
    mock_split_candidate_rule,
    mock_split_pruning,
    mock_str_to_tgd,
    mock_instantiate_tgd,
    matilda_instance,
):
    """Test discover_rules when split_pruning returns res=False — rules skipped."""
    mock_cg = MagicMock(name="cg")
    mock_mapper = MagicMock(name="mapper")
    mock_init.return_value = (mock_cg, mock_mapper, ["jia1"])
    candidate_rule = MagicMock(name="CandidateRule")
    mock_dfs.return_value = [candidate_rule]
    mock_split_candidate_rule.return_value = [("body", "head")]
    mock_split_pruning.return_value = (False, 10, 0.8)
    results = list(matilda_instance.discover_rules())
    assert len(results) == 0
    mock_str_to_tgd.assert_not_called()


@patch("algorithms.matilda.instantiate_tgd")
@patch("algorithms.matilda.TGDRuleFactory.str_to_tgd")
@patch("algorithms.matilda.split_pruning")
@patch("algorithms.matilda.split_candidate_rule")
@patch("algorithms.matilda.dfs")
@patch("algorithms.matilda.init")
def test_discover_rules_invalid_splits(
    mock_init,
    mock_dfs,
    mock_split_candidate_rule,
    mock_split_pruning,
    mock_str_to_tgd,
    mock_instantiate_tgd,
    matilda_instance,
):
    """Test discover_rules with invalid splits — all skipped."""
    mock_init.return_value = (MagicMock(name="cg"), MagicMock(name="mapper"), ["jia1"])
    mock_dfs.return_value = [MagicMock(name="CandidateRule")]
    mock_split_candidate_rule.return_value = [
        ([], "head1"),
        (["body1"], []),
        (["body2"], ["head2a", "head2b"]),
    ]
    results = list(matilda_instance.discover_rules())
    assert len(results) == 0
    mock_split_pruning.assert_not_called()
    mock_str_to_tgd.assert_not_called()


# ---------------------------------------------------------------------------
# Additional tests to cover lines 60-61 and 83-103
# ---------------------------------------------------------------------------

_INIT_PATH = "algorithms.matilda.init"
_TG_PATH = "algorithms.matilda.traverse_graph"
_SPLIT_CR = "algorithms.matilda.split_candidate_rule"
_SPLIT_PR = "algorithms.matilda.split_pruning"
_INST_TGD = "algorithms.matilda.instantiate_tgd"
_STR_TGD = "algorithms.matilda.TGDRuleFactory.str_to_tgd"


@patch(_INST_TGD)
@patch(_STR_TGD)
@patch(_SPLIT_PR)
@patch(_SPLIT_CR)
@patch(_TG_PATH)
@patch(_INIT_PATH)
def test_results_path_creates_directory(
    mock_init, mock_tg, mock_scr, mock_sp, mock_str_tgd, mock_inst, tmp_path
):
    """results_dir kwarg triggers os.makedirs (lines 59-61)."""
    mock_init.return_value = (MagicMock(), MagicMock(), [])
    results = list(MATILDA(database=MagicMock()).discover_rules(results_dir=str(tmp_path / "out")))
    assert results == []
    assert (tmp_path / "out").is_dir()


@patch(_INST_TGD)
@patch(_STR_TGD)
@patch(_SPLIT_PR)
@patch(_SPLIT_CR)
@patch(_TG_PATH)
@patch(_INIT_PATH)
def test_empty_candidate_rule_is_skipped(
    mock_init, mock_tg, mock_scr, mock_sp, mock_str_tgd, mock_inst
):
    """traverse_graph yielding an empty list is skipped (lines 83-84)."""
    mock_init.return_value = (MagicMock(), MagicMock(), ["jia1"])
    mock_tg.return_value = iter([[]])
    results = list(MATILDA(database=MagicMock()).discover_rules())
    assert results == []
    mock_scr.assert_not_called()


@patch(_INST_TGD)
@patch(_STR_TGD)
@patch(_SPLIT_PR)
@patch(_SPLIT_CR)
@patch(_TG_PATH)
@patch(_INIT_PATH)
def test_discover_rules_yields_tgd_on_success(
    mock_init, mock_tg, mock_scr, mock_sp, mock_str_tgd, mock_inst
):
    """Full happy path: split_pruning passes → TGD yielded (lines 86-103)."""
    mock_init.return_value = (MagicMock(), MagicMock(), ["jia1"])
    mock_tg.return_value = iter([["jia1", "jia2"]])
    mock_scr.return_value = [(["jia1"], ["jia2"])]
    mock_sp.return_value = (True, 10, 0.9)
    mock_inst.return_value = "tgd_string"
    fake_rule = MagicMock()
    mock_str_tgd.return_value = fake_rule

    results = list(MATILDA(database=MagicMock()).discover_rules())

    assert results == [fake_rule]
    mock_inst.assert_called_once()
    mock_str_tgd.assert_called_once_with("tgd_string", 10, 0.9)


@patch(_INST_TGD)
@patch(_STR_TGD)
@patch(_SPLIT_PR)
@patch(_SPLIT_CR)
@patch(_TG_PATH)
@patch(_INIT_PATH)
def test_invalid_splits_via_traverse_graph(
    mock_init, mock_tg, mock_scr, mock_sp, mock_str_tgd, mock_inst
):
    """Invalid splits (empty body/head, multi-head) are skipped via line 89."""
    mock_init.return_value = (MagicMock(), MagicMock(), ["jia1"])
    mock_tg.return_value = iter([["jia1", "jia2"]])
    mock_scr.return_value = [
        ([], ["head"]),
        (["body"], []),
        (["body"], ["h1", "h2"]),
    ]
    results = list(MATILDA(database=MagicMock()).discover_rules())
    assert results == []
    mock_sp.assert_not_called()


@patch(_INST_TGD)
@patch(_STR_TGD)
@patch(_SPLIT_PR)
@patch(_SPLIT_CR)
@patch(_TG_PATH)
@patch(_INIT_PATH)
def test_discover_rules_split_pruning_false_calls_instantiate(
    mock_init, mock_tg, mock_scr, mock_sp, mock_str_tgd, mock_inst
):
    """split_pruning False triggers debug instantiate_tgd call (lines 95-100)."""
    mock_init.return_value = (MagicMock(), MagicMock(), ["jia1"])
    mock_tg.return_value = iter([["jia1", "jia2"]])
    mock_scr.return_value = [(["jia1"], ["jia2"])]
    mock_sp.return_value = (False, 0, 0.0)
    mock_inst.return_value = "tgd_string"

    results = list(MATILDA(database=MagicMock()).discover_rules())

    assert results == []
    mock_inst.assert_called_once()
    mock_str_tgd.assert_not_called()
