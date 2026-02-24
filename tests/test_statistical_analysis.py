"""
Tests for utils/statistical_analysis.py.
All functions operate on in-memory data or temporary files — no database needed.
"""

import json
from pathlib import Path

import pytest

from utils.statistical_analysis import (
    SignificanceTest,
    analyze_rules_performance,
    analyze_time_metrics,
    compare_algorithms,
    compare_time_metrics,
    compute_statistics,
    format_significance_test_markdown,
    format_statistics_markdown,
    generate_statistical_report,
    perform_mannwhitneyu_test,
    perform_t_test,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data) -> Path:
    path.write_text(json.dumps(data))
    return path


# ---------------------------------------------------------------------------
# compute_statistics
# ---------------------------------------------------------------------------


class TestComputeStatistics:
    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="empty"):
            compute_statistics([])

    def test_single_value(self):
        s = compute_statistics([5.0], "score")
        assert s.mean == pytest.approx(5.0)
        assert s.std == 0.0
        assert s.count == 1
        # CI degenerates to (mean, mean)
        assert s.confidence_interval_95 == (5.0, 5.0)

    def test_multiple_values(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        s = compute_statistics(values, "metric")
        assert s.mean == pytest.approx(3.0)
        assert s.median == pytest.approx(3.0)
        assert s.min == pytest.approx(1.0)
        assert s.max == pytest.approx(5.0)
        assert s.count == 5
        assert s.confidence_interval_95[0] < s.mean < s.confidence_interval_95[1]

    def test_to_dict_keys(self):
        s = compute_statistics([1.0, 2.0])
        d = s.to_dict()
        assert "mean" in d and "std" in d and "median" in d
        assert "ci_95_lower" in d and "ci_95_upper" in d


# ---------------------------------------------------------------------------
# perform_t_test
# ---------------------------------------------------------------------------


class TestPerformTTest:
    def test_too_few_samples_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            perform_t_test([1.0], [2.0, 3.0], "m")

    def test_basic_t_test(self):
        g1 = [1.0, 1.1, 0.9, 1.05]
        g2 = [5.0, 5.1, 4.9, 5.05]
        result = perform_t_test(g1, g2, "score", "A", "B")
        assert isinstance(result, SignificanceTest)
        assert result.is_significant
        assert result.effect_size > 0
        assert result.test_name == "Independent t-test"

    def test_to_dict_keys(self):
        result = perform_t_test([1, 2, 3], [4, 5, 6], "m")
        d = result.to_dict()
        assert "p_value" in d and "statistic" in d and "is_significant" in d

    def test_identical_groups_zero_effect(self):
        g = [1.0, 2.0, 3.0]
        result = perform_t_test(g, g, "m")
        assert result.effect_size == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# perform_mannwhitneyu_test
# ---------------------------------------------------------------------------


class TestPerformMannWhitneyU:
    def test_empty_group_raises(self):
        with pytest.raises(ValueError, match="at least 1"):
            perform_mannwhitneyu_test([], [1.0, 2.0], "m")

    def test_basic_mannwhitney(self):
        # Need n>=4 per group for Mann-Whitney to reach p<0.05 (min p with n=3 is 0.1)
        g1 = [1.0, 1.5, 2.0, 1.8]
        g2 = [10.0, 11.0, 12.0, 10.5]
        result = perform_mannwhitneyu_test(g1, g2, "score", "A", "B")
        assert isinstance(result, SignificanceTest)
        assert result.test_name == "Mann-Whitney U test"
        assert result.is_significant

    def test_effect_size_is_non_negative(self):
        result = perform_mannwhitneyu_test([1, 2, 3], [4, 5, 6], "m")
        assert result.effect_size >= 0


# ---------------------------------------------------------------------------
# analyze_rules_performance
# ---------------------------------------------------------------------------


class TestAnalyzeRulesPerformance:
    def _make_rules_file(self, tmp_path, rules):
        return _write_json(tmp_path / "rules.json", rules)

    def test_basic_analysis(self, tmp_path):
        rules = [
            {"accuracy": 0.8, "confidence": 0.9},
            {"accuracy": 0.6, "confidence": 0.7},
        ]
        f = self._make_rules_file(tmp_path, rules)
        stats = analyze_rules_performance(f)
        assert "accuracy" in stats
        assert "confidence" in stats
        assert stats["accuracy"].count == 2

    def test_missing_metric_skipped(self, tmp_path):
        rules = [{"accuracy": 0.8}, {"confidence": 0.7}]
        f = self._make_rules_file(tmp_path, rules)
        stats = analyze_rules_performance(f, metrics=["accuracy"])
        assert "accuracy" in stats
        assert stats["accuracy"].count == 1

    def test_custom_metrics(self, tmp_path):
        rules = [{"precision": 0.5}, {"precision": 0.7}]
        f = self._make_rules_file(tmp_path, rules)
        stats = analyze_rules_performance(f, metrics=["precision"])
        assert "precision" in stats

    def test_none_values_skipped(self, tmp_path):
        rules = [{"accuracy": 0.8}, {"accuracy": None}]
        f = self._make_rules_file(tmp_path, rules)
        stats = analyze_rules_performance(f, metrics=["accuracy"])
        assert stats["accuracy"].count == 1

    def test_all_none_returns_empty_for_metric(self, tmp_path):
        rules = [{"accuracy": None}]
        f = self._make_rules_file(tmp_path, rules)
        stats = analyze_rules_performance(f, metrics=["accuracy"])
        assert "accuracy" not in stats


# ---------------------------------------------------------------------------
# analyze_time_metrics
# ---------------------------------------------------------------------------


class TestAnalyzeTimeMetrics:
    def test_missing_file_returns_empty(self, tmp_path):
        result = analyze_time_metrics(tmp_path / "nonexistent.json")
        assert result == {}

    def test_basic_time_metrics(self, tmp_path):
        data = {"time_compute_compatible": 1.5, "time_building_cg": 0.3}
        f = _write_json(tmp_path / "time.json", data)
        result = analyze_time_metrics(f)
        assert "time_compute_compatible" in result
        assert result["time_compute_compatible"].mean == pytest.approx(1.5)

    def test_custom_metrics_filter(self, tmp_path):
        data = {"a": 1.0, "b": 2.0}
        f = _write_json(tmp_path / "time.json", data)
        result = analyze_time_metrics(f, metrics=["a"])
        assert "a" in result
        assert "b" not in result


# ---------------------------------------------------------------------------
# compare_algorithms
# ---------------------------------------------------------------------------


class TestCompareAlgorithms:
    def _make_file(self, tmp_path, name, rules):
        return _write_json(tmp_path / name, rules)

    def test_parametric_comparison(self, tmp_path):
        r1 = [{"accuracy": v} for v in [0.8, 0.85, 0.9, 0.82]]
        r2 = [{"accuracy": v} for v in [0.5, 0.55, 0.6, 0.52]]
        f1 = self._make_file(tmp_path, "a1.json", r1)
        f2 = self._make_file(tmp_path, "a2.json", r2)
        results = compare_algorithms(f1, f2, "A1", "A2", metrics=["accuracy"])
        assert "accuracy" in results
        assert results["accuracy"].is_significant

    def test_non_parametric_comparison(self, tmp_path):
        r1 = [{"accuracy": v} for v in [0.8, 0.85]]
        r2 = [{"accuracy": v} for v in [0.5, 0.55]]
        f1 = self._make_file(tmp_path, "a1.json", r1)
        f2 = self._make_file(tmp_path, "a2.json", r2)
        results = compare_algorithms(f1, f2, "A1", "A2", metrics=["accuracy"], use_parametric=False)
        assert "accuracy" in results

    def test_missing_metric_skipped(self, tmp_path):
        r1 = [{"accuracy": 0.8}]
        r2 = [{"confidence": 0.7}]
        f1 = self._make_file(tmp_path, "a1.json", r1)
        f2 = self._make_file(tmp_path, "a2.json", r2)
        results = compare_algorithms(f1, f2, "A1", "A2", metrics=["accuracy"])
        assert results == {}

    def test_inner_exception_handler(self, tmp_path):
        """Exception inside perform_t_test is caught per-metric (lines 313-314)."""
        from unittest.mock import patch

        r1 = [{"accuracy": v} for v in [0.8, 0.82, 0.79]]
        r2 = [{"accuracy": v} for v in [0.6, 0.62, 0.59]]
        f1 = self._make_file(tmp_path, "a1.json", r1)
        f2 = self._make_file(tmp_path, "a2.json", r2)
        with patch(
            "utils.statistical_analysis.perform_t_test",
            side_effect=RuntimeError("forced"),
        ):
            results = compare_algorithms(f1, f2, "A1", "A2", metrics=["accuracy"])
        # Exception caught → metric is skipped
        assert "accuracy" not in results

    def test_single_sample_falls_back_to_mannwhitney(self, tmp_path):
        """When one group has only 1 sample, parametric test falls back to non-parametric."""
        r1 = [{"accuracy": 0.9}]
        r2 = [{"accuracy": 0.5}]
        f1 = self._make_file(tmp_path, "a1.json", r1)
        f2 = self._make_file(tmp_path, "a2.json", r2)
        results = compare_algorithms(f1, f2, "A1", "A2", metrics=["accuracy"], use_parametric=True)
        assert "accuracy" in results


# ---------------------------------------------------------------------------
# compare_time_metrics
# ---------------------------------------------------------------------------


class TestCompareTimeMetrics:
    def test_missing_file_returns_empty(self, tmp_path):
        result = compare_time_metrics(tmp_path / "no1.json", tmp_path / "no2.json", "A1", "A2")
        assert result == {}

    def test_basic_comparison(self, tmp_path):
        t1 = {"build_time": 2.0, "search_time": 1.0}
        t2 = {"build_time": 3.0, "search_time": 0.5}
        f1 = _write_json(tmp_path / "t1.json", t1)
        f2 = _write_json(tmp_path / "t2.json", t2)
        result = compare_time_metrics(f1, f2, "A1", "A2")
        assert "build_time" in result
        assert result["build_time"]["A1_time"] == pytest.approx(2.0)
        assert result["build_time"]["faster_algorithm"] == "A1"

    def test_custom_metrics_filter(self, tmp_path):
        t1 = {"a": 1.0, "b": 2.0}
        t2 = {"a": 2.0, "b": 1.0}
        f1 = _write_json(tmp_path / "t1.json", t1)
        f2 = _write_json(tmp_path / "t2.json", t2)
        result = compare_time_metrics(f1, f2, "A1", "A2", metrics=["a"])
        assert "a" in result
        assert "b" not in result

    def test_zero_divisor_gives_inf(self, tmp_path):
        t1 = {"m": 1.0}
        t2 = {"m": 0.0}
        f1 = _write_json(tmp_path / "t1.json", t1)
        f2 = _write_json(tmp_path / "t2.json", t2)
        result = compare_time_metrics(f1, f2, "A1", "A2")
        assert result["m"]["percent_difference"] == float("inf")


# ---------------------------------------------------------------------------
# generate_statistical_report
# ---------------------------------------------------------------------------


class TestGenerateStatisticalReport:
    def _populate_dir(self, results_dir: Path):
        """Create mock result files for two algorithms on one dataset."""
        rules_a = [{"accuracy": v, "confidence": v + 0.05} for v in [0.8, 0.82, 0.79]]
        rules_b = [{"accuracy": v, "confidence": v + 0.05} for v in [0.6, 0.62, 0.59]]
        _write_json(results_dir / "MATILDA_ds1_results.json", rules_a)
        _write_json(results_dir / "SPIDER_ds1_results.json", rules_b)
        _write_json(results_dir / "init_time_metrics_ds1.json", {"build_time": 1.0})

    def test_basic_report(self, tmp_path):
        self._populate_dir(tmp_path)
        report = generate_statistical_report(tmp_path, algorithms=["MATILDA", "SPIDER"])
        assert "statistics" in report
        assert "comparisons" in report
        assert "summary" in report

    def test_report_saved_to_file(self, tmp_path):
        self._populate_dir(tmp_path)
        output = tmp_path / "report.json"
        generate_statistical_report(tmp_path, output_file=output, algorithms=["MATILDA", "SPIDER"])
        assert output.exists()
        data = json.loads(output.read_text())
        assert "summary" in data

    def test_empty_dir_returns_empty_report(self, tmp_path):
        report = generate_statistical_report(tmp_path, algorithms=["MATILDA"])
        assert report["summary"]["total_datasets"] == 0

    def test_include_time_metrics_false(self, tmp_path):
        self._populate_dir(tmp_path)
        report = generate_statistical_report(
            tmp_path, algorithms=["MATILDA"], include_time_metrics=False
        )
        assert report["time_metrics"] == {}

    def test_default_algorithms_parameter(self, tmp_path):
        """Calling without algorithms uses the built-in default list (line 389)."""
        # Empty dir → no files → summary has 0 datasets but no crash
        report = generate_statistical_report(tmp_path)
        assert "summary" in report

    def test_corrupted_rules_file_is_skipped(self, tmp_path):
        """analyze_rules_performance failure is caught (lines 429-430)."""
        # Write a non-list JSON so the for-rule loop fails
        (tmp_path / "MATILDA_ds1_results.json").write_text('{"bad": "data"}')
        report = generate_statistical_report(tmp_path, algorithms=["MATILDA"])
        # Should not raise; just produce empty/partial stats
        assert "statistics" in report

    def test_corrupted_time_file_is_skipped(self, tmp_path):
        """analyze_time_metrics failure is caught (lines 443-444)."""
        rules = [{"accuracy": 0.8}]
        _write_json(tmp_path / "MATILDA_ds1_results.json", rules)
        (tmp_path / "init_time_metrics_ds1.json").write_text("not-json")
        report = generate_statistical_report(tmp_path, algorithms=["MATILDA"])
        assert "time_metrics" in report

    def test_invalid_json_rules_file_is_skipped(self, tmp_path):
        """JSON parse error in analyze_rules_performance is caught (lines 429-430)."""
        (tmp_path / "MATILDA_ds1_results.json").write_text("!!! not json !!!")
        report = generate_statistical_report(tmp_path, algorithms=["MATILDA"])
        assert "MATILDA" in report["statistics"]
        assert "ds1" not in report["statistics"].get("MATILDA", {})

    def test_compare_algorithms_exception_handler(self, tmp_path):
        """Exception from compare_algorithms is caught (lines 465-466)."""
        from unittest.mock import patch

        rules_a = [{"accuracy": v} for v in [0.8, 0.82, 0.79]]
        rules_b = [{"accuracy": v} for v in [0.6, 0.62, 0.59]]
        _write_json(tmp_path / "MATILDA_ds1_results.json", rules_a)
        _write_json(tmp_path / "SPIDER_ds1_results.json", rules_b)

        with patch(
            "utils.statistical_analysis.compare_algorithms",
            side_effect=RuntimeError("forced comparison error"),
        ):
            report = generate_statistical_report(tmp_path, algorithms=["MATILDA", "SPIDER"])
        assert "comparisons" in report

    def test_compare_time_metrics_exception_handler(self, tmp_path):
        """Exception from compare_time_metrics is caught (lines 479-480)."""
        from unittest.mock import patch

        rules_a = [{"accuracy": 0.8}]
        rules_b = [{"accuracy": 0.6}]
        _write_json(tmp_path / "MATILDA_ds1_results.json", rules_a)
        _write_json(tmp_path / "SPIDER_ds1_results.json", rules_b)
        _write_json(tmp_path / "init_time_metrics_ds1.json", {"build_time": 1.0})

        with patch(
            "utils.statistical_analysis.compare_time_metrics",
            side_effect=RuntimeError("forced time error"),
        ):
            report = generate_statistical_report(tmp_path, algorithms=["MATILDA", "SPIDER"])
        assert "time_comparisons" in report


# ---------------------------------------------------------------------------
# format helpers
# ---------------------------------------------------------------------------


class TestFormatHelpers:
    def test_format_statistics_markdown(self):
        s = compute_statistics([0.8, 0.9, 0.85], "accuracy")
        md = format_statistics_markdown(s)
        assert "accuracy" in md
        assert "|" in md

    def test_format_significance_test_markdown_significant(self):
        result = perform_t_test([1, 2, 3, 4], [10, 11, 12, 13], "m", "A", "B")
        md = format_significance_test_markdown(result)
        assert "A vs B" in md
        assert "✓" in md

    def test_format_significance_test_markdown_not_significant(self):
        result = perform_t_test([1, 2, 3, 4], [1.1, 2.1, 3.1, 4.1], "m", "A", "B")
        # p-value likely > 0.05
        md = format_significance_test_markdown(result)
        assert "|" in md

    def test_significance_test_to_dict_effect_none(self):
        t = SignificanceTest("t", "m", "A", "B", 1.0, 0.5, False, effect_size=None)
        d = t.to_dict()
        assert d["effect_size"] is None
