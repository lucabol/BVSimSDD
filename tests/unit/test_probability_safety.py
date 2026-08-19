import pytest

from bvsim_cli.templates import get_basic_template
from bvsim_stats.analysis import _adjust_probability_distribution


def test_templates_do_not_share_nested_probability_data():
    first = get_basic_template("First")
    second = get_basic_template("Second")

    first["serve_probabilities"]["ace"] = 1.0

    assert second["serve_probabilities"]["ace"] == 0.10


def test_probability_adjustment_rejects_out_of_range_target():
    team_data = {"serve_probabilities": {"ace": 0.8, "in_play": 0.2}}

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        _adjust_probability_distribution(
            team_data, "serve_probabilities.ace", 1.1
        )


def test_probability_adjustment_rejects_missing_redistribution_mass():
    team_data = {"serve_probabilities": {"ace": 0.0, "in_play": 0.0}}

    with pytest.raises(ValueError, match="zero mass"):
        _adjust_probability_distribution(
            team_data, "serve_probabilities.ace", 0.5
        )


def test_probability_adjustment_preserves_distribution():
    team_data = {
        "serve_probabilities": {"ace": 0.1, "in_play": 0.85, "error": 0.05}
    }

    adjusted = _adjust_probability_distribution(
        team_data, "serve_probabilities.ace", 0.2
    )

    probabilities = adjusted["serve_probabilities"]
    assert probabilities["ace"] == 0.2
    assert all(value >= 0 for value in probabilities.values())
    assert sum(probabilities.values()) == pytest.approx(1.0)
