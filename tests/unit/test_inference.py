import pytest

from bvsim_cli.templates import get_basic_template
from bvsim_core.team import Team
from bvsim_stats.analysis import _calculate_win_rate, full_skill_analysis
from bvsim_stats.inference import (
    aggregate_effect_statistics,
    holm_adjust,
    mean_confidence_interval,
    paired_difference_statistics,
    student_t_critical,
    wilson_interval,
)


def test_student_t_critical_matches_known_values():
    assert student_t_critical(0.95, 4) == pytest.approx(2.776445, rel=1e-6)
    assert student_t_critical(0.99, 4) == pytest.approx(4.604095, rel=1e-6)


def test_confidence_level_changes_interval_width():
    values = [1, 2, 3, 4, 5]
    _, lower_80, upper_80 = mean_confidence_interval(values, 0.80)
    _, lower_99, upper_99 = mean_confidence_interval(values, 0.99)

    assert lower_99 < lower_80
    assert upper_99 > upper_80


def test_single_value_has_no_across_run_interval():
    mean, lower, upper = mean_confidence_interval([7.0])

    assert mean == 7.0
    assert lower is None
    assert upper is None


def test_paired_difference_statistics_detect_constant_effect():
    mean, lower, upper, p_value = paired_difference_statistics(
        [50.0, 51.0, 49.0],
        [52.0, 53.0, 51.0],
    )

    assert mean == 2.0
    assert lower == 2.0
    assert upper == 2.0
    assert p_value == 0.0


def test_wilson_interval_stays_in_probability_bounds():
    proportion, lower, upper = wilson_interval(0, 10)

    assert proportion == 0.0
    assert 0.0 <= lower <= upper <= 1.0
    assert upper > 0.0


def test_holm_adjustment_is_monotone_in_sorted_order():
    adjusted = holm_adjust([0.01, 0.04, 0.03])

    assert adjusted == pytest.approx([0.03, 0.06, 0.06])


def test_seeded_win_rate_is_reproducible():
    team_a = Team.from_dict(get_basic_template("A"))
    team_b = Team.from_dict(get_basic_template("B"))

    first = _calculate_win_rate(team_a, team_b, 200, "A", seed=123)
    second = _calculate_win_rate(team_a, team_b, 200, "A", seed=123)

    assert first == second


def test_zero_change_has_exactly_zero_paired_effect():
    team_a = Team.from_dict(get_basic_template("A"))
    team_b = Team.from_dict(get_basic_template("B"))

    results = full_skill_analysis(
        team_a,
        team_b,
        change_value=0.0,
        points_per_test=100,
        parallel=False,
        seed=123,
    )

    assert results["seed"] == 123
    assert all(
        result["improvement"] == 0.0
        for result in results["parameter_improvements"].values()
    )


def test_aggregate_effects_with_one_run_does_not_claim_inference():
    rows = aggregate_effect_statistics(
        [{
            "effects": {
                "serve": {
                    "improvement": 1.0,
                    "match_improvement": 2.0,
                }
            }
        }],
        "effects",
    )

    assert rows[0]["point_lower"] is None
    assert rows[0]["match_upper"] is None
    assert rows[0]["raw_p_value"] is None
    assert rows[0]["adjusted_p_value"] is None
    assert rows[0]["holm_significant"] is False


def test_full_skill_analysis_can_run_independent_holdout_subset():
    team_a = Team.from_dict(get_basic_template("A"))
    team_b = Team.from_dict(get_basic_template("B"))
    parameter = "serve_probabilities.ace"

    results = full_skill_analysis(
        team_a,
        team_b,
        change_value=0.01,
        points_per_test=50,
        parallel=False,
        seed=456,
        parameters=[parameter],
    )

    assert list(results["parameter_improvements"]) == [parameter]
    assert results["total_parameters"] == 1
