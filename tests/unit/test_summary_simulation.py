import random
from dataclasses import replace

import pytest

import bvsim_core.summary as summary_module
from bvsim_cli.templates import get_basic_template
from bvsim_core.state_machine import simulate_point
from bvsim_core.summary import (
    _kernel_seed,
    _random_value,
    cuda_backend_available,
    cuda_backend_unavailability_reason,
    simulate_summary,
)
from bvsim_core.team import Team


def _basic_teams():
    return (
        Team.from_dict(get_basic_template("Team A")),
        Team.from_dict(get_basic_template("Team B")),
    )


def test_summary_is_reproducible_and_has_consistent_counts():
    team_a, team_b = _basic_teams()

    first = simulate_summary(
        team_a, team_b, 2_001, seed=12345, backend="python"
    )
    second = simulate_summary(
        team_a, team_b, 2_001, seed=12345, backend="python"
    )

    assert first == second
    assert first.team_a_wins <= first.total_points
    assert first.a_serves_total + first.b_serves_total == first.total_points
    assert first.a_serves_total == 1_001
    assert first.b_serves_total == 1_000


def test_high_seed_bits_do_not_collapse_to_the_same_kernel_stream():
    seed_pairs = (
        (123, 123 ^ 0x1_0000_0001),
        (12_158, 16_372),
    )

    for first_seed, second_seed in seed_pairs:
        first_kernel_seed = _kernel_seed(first_seed)
        second_kernel_seed = _kernel_seed(second_seed)
        assert first_kernel_seed != second_kernel_seed
        assert any(
            _random_value(first_kernel_seed, 7, draw_index)
            != _random_value(second_kernel_seed, 7, draw_index)
            for draw_index in range(20)
        )


def test_high_point_index_bits_do_not_repeat_the_random_stream():
    seed = _kernel_seed(123)
    index_pairs = (
        (7, 7 + 2**32),
        (2**32, 3_660_452_897),
    )
    for first_index, second_index in index_pairs:
        assert any(
            _random_value(seed, first_index, draw_index)
            != _random_value(seed, second_index, draw_index)
            for draw_index in range(20)
        )


def test_summary_respects_server_for_deterministic_aces():
    ace_team = Team.from_dict({
        "name": "Ace Team",
        "serve_probabilities": {"ace": 1.0, "in_play": 0.0, "error": 0.0},
    })

    result = simulate_summary(
        ace_team, ace_team, 101, seed=7, backend="python"
    )

    assert result.team_a_wins == 51
    assert result.a_serves_wins == 51
    assert result.b_serves_wins == 0
    assert result.aggregate_breakdown()["point_type_breakdown"] == {
        "ace": 101
    }
    assert result.aggregate_breakdown()["duration_by_type"]["ace"] == {
        "count": 101,
        "average": 1.0,
        "min": 1,
        "max": 1,
    }


def test_summary_tracks_point_types_and_winners_independently():
    ace_team = Team.from_dict({
        "name": "Ace Team",
        "serve_probabilities": {"ace": 1.0, "in_play": 0.0, "error": 0.0},
    })
    error_team = Team.from_dict({
        "name": "Error Team",
        "serve_probabilities": {"ace": 0.0, "in_play": 0.0, "error": 1.0},
    })

    result = simulate_summary(
        ace_team, error_team, 100, seed=9, backend="python"
    )
    breakdown = result.aggregate_breakdown()

    assert result.team_a_wins == 100
    assert breakdown["point_type_breakdown"] == {
        "ace": 50,
        "serve_error": 50,
    }
    assert breakdown["team_a_point_types"] == {
        "ace": 50,
        "serve_error": 50,
    }
    assert breakdown["team_b_point_types"] == {}
    assert breakdown["duration_by_type"]["serve_error"]["average"] == 1.0


def test_summary_is_statistically_consistent_with_detailed_simulation():
    team_a, team_b = _basic_teams()
    num_points = 20_000
    seed = 12_345
    seed_stream = random.Random(seed)
    detailed_wins = 0
    for point_index in range(num_points):
        serving_team = "A" if point_index % 2 == 0 else "B"
        point = simulate_point(
            team_a,
            team_b,
            serving_team=serving_team,
            seed=seed_stream.getrandbits(64),
        )
        detailed_wins += point.winner == "A"

    summary = simulate_summary(
        team_a, team_b, num_points, seed=seed, backend="python"
    )

    assert summary.team_a_wins / num_points == pytest.approx(
        detailed_wins / num_points, abs=0.02
    )


@pytest.mark.parametrize("seed", [98_765, 2**63 + 12_345, 2**64 - 1])
def test_numba_and_python_backends_are_identical(seed):
    team_a, team_b = _basic_teams()
    try:
        accelerated = simulate_summary(
            team_a, team_b, 2_000, seed=seed, backend="numba"
        )
    except RuntimeError:
        pytest.skip("Numba is not installed")

    reference = simulate_summary(
        team_a, team_b, 2_000, seed=seed, backend="python"
    )

    assert accelerated.team_a_wins == reference.team_a_wins
    assert accelerated.a_serves_wins == reference.a_serves_wins
    assert accelerated.b_serves_wins == reference.b_serves_wins
    assert accelerated.point_type_counts == reference.point_type_counts
    assert accelerated.duration_sums == reference.duration_sums
    assert accelerated.duration_mins == reference.duration_mins
    assert accelerated.duration_maxs == reference.duration_maxs


def test_auto_selects_numba_for_large_simulations():
    team_a, team_b = _basic_teams()
    try:
        accelerated = simulate_summary(
            team_a, team_b, 50_000, seed=2**63 + 1, backend="auto"
        )
    except RuntimeError:
        pytest.skip("Numba is not installed")
    if accelerated.backend != "numba":
        pytest.skip("Numba is not installed")

    reference = simulate_summary(
        team_a, team_b, 50_000, seed=2**63 + 1, backend="python"
    )

    assert accelerated.team_a_wins == reference.team_a_wins
    assert accelerated.a_serves_wins == reference.a_serves_wins
    assert accelerated.b_serves_wins == reference.b_serves_wins


def test_auto_selects_cuda_above_threshold_when_available(monkeypatch):
    monkeypatch.setattr(summary_module, "_CUDA_MIN_POINTS", 10)
    monkeypatch.setattr(
        summary_module, "cuda_backend_available", lambda: True
    )

    assert summary_module._select_backend("auto", 10) == "cuda"
    assert summary_module._select_backend("cpu", 10) == "python"


def test_auto_falls_back_to_cpu_after_cuda_runtime_failure(monkeypatch):
    team_a, team_b = _basic_teams()

    def fail_cuda(*args):
        raise RuntimeError("GPU failed")

    monkeypatch.setattr(summary_module, "_CUDA_MIN_POINTS", 10)
    monkeypatch.setattr(
        summary_module, "cuda_backend_available", lambda: True
    )
    monkeypatch.setattr(
        summary_module,
        "_simulate_summary_cuda",
        fail_cuda,
    )

    result = simulate_summary(
        team_a, team_b, 10, seed=123, backend="auto"
    )

    assert result.backend == "python"


def test_explicit_cuda_fails_clearly_and_auto_falls_back_when_unavailable(
    monkeypatch,
):
    team_a, team_b = _basic_teams()
    monkeypatch.setattr(
        summary_module, "_cuda_unavailable_reason", "test GPU unavailable"
    )
    monkeypatch.setattr(summary_module, "_cupy_module", None)
    monkeypatch.setattr(summary_module, "_cuda_kernel", None)

    assert not cuda_backend_available()
    assert cuda_backend_unavailability_reason() == "test GPU unavailable"
    with pytest.raises(
        RuntimeError,
        match="CUDA summary backend is unavailable: test GPU unavailable",
    ):
        simulate_summary(team_a, team_b, 10, seed=1, backend="cuda")
    assert (
        simulate_summary(team_a, team_b, 10, seed=1, backend="auto").backend
        == "python"
    )


@pytest.mark.parametrize(
    ("seed", "base_serving"),
    [
        (98_765, "A"),
        (2**63 + 12_345, "B"),
        (2**64 - 1, "A"),
    ],
)
def test_cuda_and_python_backends_are_identical_when_available(
    seed, base_serving
):
    team_a, team_b = _basic_teams()
    try:
        accelerated = simulate_summary(
            team_a,
            team_b,
            20_001,
            base_serving=base_serving,
            seed=seed,
            backend="cuda",
        )
    except RuntimeError as error:
        pytest.skip(f"CUDA is unavailable: {error}")
    reference = simulate_summary(
        team_a,
        team_b,
        20_001,
        base_serving=base_serving,
        seed=seed,
        backend="python",
    )

    assert replace(accelerated, backend="python") == reference


def test_cuda_tracks_point_types_and_durations_when_available():
    ace_team = Team.from_dict({
        "name": "Ace Team",
        "serve_probabilities": {"ace": 1.0, "in_play": 0.0, "error": 0.0},
    })
    error_team = Team.from_dict({
        "name": "Error Team",
        "serve_probabilities": {"ace": 0.0, "in_play": 0.0, "error": 1.0},
    })
    try:
        result = simulate_summary(
            ace_team, error_team, 101, seed=2**64 - 1, backend="cuda"
        )
    except RuntimeError as error:
        pytest.skip(f"CUDA is unavailable: {error}")

    assert result.team_a_wins == 101
    assert result.point_type_counts[:2] == (51, 50)
    assert result.team_a_point_type_counts[:2] == (51, 50)
    assert result.team_b_point_type_counts[:2] == (0, 0)
    assert result.duration_sums[:2] == (51, 50)
    assert result.duration_mins[:2] == (1, 1)
    assert result.duration_maxs[:2] == (1, 1)
    assert result.total_duration == 101


@pytest.mark.parametrize("backend", ["unknown", "gpu"])
def test_summary_rejects_unknown_backend(backend):
    team_a, team_b = _basic_teams()

    with pytest.raises(ValueError, match="backend must be"):
        simulate_summary(team_a, team_b, 10, seed=1, backend=backend)
