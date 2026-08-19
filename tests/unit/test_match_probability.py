import pytest

from bvsim_stats.match import (
    match_impact,
    match_win_probability,
    set_win_probability,
)


def test_symmetric_service_model_has_even_match_probability():
    assert match_win_probability(0.4, 0.6) == pytest.approx(0.5, abs=1e-12)


def test_even_points_have_even_match_probability():
    assert match_win_probability(0.5, 0.5) == pytest.approx(0.5, abs=1e-12)


def test_extreme_point_models_are_absorbing():
    assert match_win_probability(1.0, 1.0) == 1.0
    assert match_win_probability(0.0, 0.0) == 0.0


def test_zero_model_change_has_zero_match_impact():
    assert match_impact(0.45, 0.55, 0.45, 0.55) == 0.0


def test_better_point_model_improves_match_probability():
    assert match_impact(0.45, 0.55, 0.46, 0.56) > 0.0


def test_set_probability_validates_server():
    with pytest.raises(ValueError, match="initial_server"):
        set_win_probability(0.5, 0.5, 21, "C")
