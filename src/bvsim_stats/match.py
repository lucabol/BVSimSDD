"""Deterministic service-aware beach-volleyball match probabilities."""

from functools import lru_cache
from typing import Dict, Tuple


def _validate_probability(value: float, name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")


def _solve_linear_system(
    matrix: list[list[float]], vector: list[float]
) -> list[float]:
    size = len(vector)
    augmented = [
        [*matrix[row], vector[row]]
        for row in range(size)
    ]

    for column in range(size):
        pivot = max(
            range(column, size),
            key=lambda row: abs(augmented[row][column]),
        )
        if abs(augmented[pivot][column]) < 1e-14:
            raise ValueError("match probability system is singular")
        augmented[column], augmented[pivot] = (
            augmented[pivot],
            augmented[column],
        )

        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(
                    augmented[row], augmented[column]
                )
            ]
    return [augmented[row][-1] for row in range(size)]


def _deuce_probabilities(
    a_wins_when_a_serves: float,
    a_wins_when_b_serves: float,
) -> Dict[Tuple[int, str], float]:
    states = [
        (-1, "A"), (-1, "B"),
        (0, "A"), (0, "B"),
        (1, "A"), (1, "B"),
    ]
    indices = {state: index for index, state in enumerate(states)}
    matrix = [[0.0] * len(states) for _ in states]
    vector = [0.0] * len(states)

    for state, row in indices.items():
        difference, server = state
        probability_a = (
            a_wins_when_a_serves
            if server == "A"
            else a_wins_when_b_serves
        )
        matrix[row][row] = 1.0

        if difference == 1:
            vector[row] += probability_a
            next_state = (0, "B")
            matrix[row][indices[next_state]] -= 1.0 - probability_a
        elif difference == -1:
            next_state = (0, "A")
            matrix[row][indices[next_state]] -= probability_a
        else:
            matrix[row][indices[(1, "A")]] -= probability_a
            matrix[row][indices[(-1, "B")]] -= 1.0 - probability_a

    solution = _solve_linear_system(matrix, vector)
    return {
        state: solution[index]
        for state, index in indices.items()
    }


def set_win_probability(
    a_wins_when_a_serves: float,
    a_wins_when_b_serves: float,
    points_to_win: int,
    initial_server: str,
) -> float:
    """Return Team A's set-win probability under winner-serves-next."""
    _validate_probability(a_wins_when_a_serves, "a_wins_when_a_serves")
    _validate_probability(a_wins_when_b_serves, "a_wins_when_b_serves")
    if points_to_win < 2:
        raise ValueError("points_to_win must be at least 2")
    if initial_server not in {"A", "B"}:
        raise ValueError("initial_server must be A or B")

    deuce = _deuce_probabilities(
        a_wins_when_a_serves, a_wins_when_b_serves
    )

    @lru_cache(maxsize=None)
    def probability(a_points: int, b_points: int, server: str) -> float:
        if a_points >= points_to_win and a_points - b_points >= 2:
            return 1.0
        if b_points >= points_to_win and b_points - a_points >= 2:
            return 0.0
        if a_points >= points_to_win - 1 and b_points >= points_to_win - 1:
            return deuce[(a_points - b_points, server)]

        probability_a = (
            a_wins_when_a_serves
            if server == "A"
            else a_wins_when_b_serves
        )
        return (
            probability_a * probability(a_points + 1, b_points, "A")
            + (1.0 - probability_a)
            * probability(a_points, b_points + 1, "B")
        )

    return probability(0, 0, initial_server)


def match_win_probability(
    a_wins_when_a_serves: float,
    a_wins_when_b_serves: float,
) -> float:
    """Return Team A's best-of-three match-win probability.

    The first server of each set is treated as an even pre-set choice, so each
    set probability averages the A-start and B-start cases.
    """
    standard_set = 0.5 * (
        set_win_probability(
            a_wins_when_a_serves, a_wins_when_b_serves, 21, "A"
        )
        + set_win_probability(
            a_wins_when_a_serves, a_wins_when_b_serves, 21, "B"
        )
    )
    deciding_set = 0.5 * (
        set_win_probability(
            a_wins_when_a_serves, a_wins_when_b_serves, 15, "A"
        )
        + set_win_probability(
            a_wins_when_a_serves, a_wins_when_b_serves, 15, "B"
        )
    )
    return (
        standard_set * standard_set
        + 2.0
        * standard_set
        * (1.0 - standard_set)
        * deciding_set
    )


def match_impact(
    baseline_a_serves: float,
    baseline_b_serves: float,
    improved_a_serves: float,
    improved_b_serves: float,
) -> float:
    """Return the match-win probability change in percentage points."""
    baseline = match_win_probability(
        baseline_a_serves, baseline_b_serves
    )
    improved = match_win_probability(
        improved_a_serves, improved_b_serves
    )
    return (improved - baseline) * 100.0
