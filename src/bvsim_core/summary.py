"""Allocation-light summary simulation with optional CPU/GPU acceleration."""

import secrets
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from .team import Team
from .validation import validate_team_configuration

try:
    import numpy as np
    from numba import njit, prange
    from numba.extending import register_jitable
except ImportError:
    np = None
    njit = None
    prange = range

    def register_jitable(function=None, *args, **kwargs):
        del args, kwargs
        if function is not None:
            return function

        def decorator(function):
            return function

        return decorator


_MASK_32 = 0xFFFFFFFF
_MASK_64 = 0xFFFFFFFFFFFFFFFF
_TEAM_STRIDE = 43
_SERVE_OFFSET = 0
_RECEIVE_OFFSET = 3
_SET_OFFSET = 7
_ATTACK_OFFSET = 19
_BLOCK_OFFSET = 31
_DIG_DEFLECTION_OFFSET = 35
_DIG_NO_TOUCH_OFFSET = 39
_NUMBA_MIN_POINTS = 50_000
_CUDA_MIN_POINTS = 1_000_000
_CUDA_THREADS_PER_BLOCK = 256
_CUDA_MAX_BLOCKS = 65_535

_cupy_module = None
_cuda_kernel = None
_cuda_unavailable_reason = None

POINT_TYPES = (
    "ace",
    "serve_error",
    "receive_error",
    "set_error",
    "kill",
    "attack_error",
    "stuff",
    "dig_error",
    "rally",
)
_ACE = 0
_SERVE_ERROR = 1
_RECEIVE_ERROR = 2
_SET_ERROR = 3
_KILL = 4
_ATTACK_ERROR = 5
_STUFF = 6
_DIG_ERROR = 7
_RALLY = 8


_CUDA_SOURCE = r"""
extern "C" {

__device__ __forceinline__ double random_value(
    const unsigned long long seed,
    const unsigned long long point_index,
    const unsigned int draw_index
) {
    unsigned int seed_low = (unsigned int)seed;
    unsigned int seed_high = (unsigned int)(seed >> 32);
    unsigned int left = (unsigned int)point_index ^ seed_low;
    unsigned int right = (unsigned int)(point_index >> 32)
        ^ seed_high ^ (draw_index * 2654435769U);
    unsigned int round_key = seed_low
        ^ ((seed_high << 16) | (seed_high >> 16))
        ^ (draw_index * 2246822519U);
    for (unsigned int round = 0; round < 10; ++round) {
        left = ((left >> 8) | (left << 24)) + right;
        left ^= round_key + round * 2654435769U;
        right = ((right << 3) | (right >> 29)) ^ left;
    }
    return ((double)left + ((double)right + 0.5) / 4294967296.0)
        / 4294967296.0;
}

__device__ __forceinline__ int sample(
    const double* parameters,
    const int offset,
    const int outcome_count,
    const double value
) {
    for (int outcome = 0; outcome < outcome_count; ++outcome) {
        if (value <= parameters[offset + outcome]) {
            return outcome;
        }
    }
    return outcome_count - 1;
}

__device__ __forceinline__ unsigned short pack_result(
    const int winner, const int point_type, const int duration
) {
    return (unsigned short)(winner | (point_type << 1) | (duration << 5));
}

__device__ __forceinline__ unsigned short simulate_one(
    const double* parameters,
    const unsigned long long seed,
    const unsigned long long point_index,
    const int serving_team
) {
    const int team_stride = 43;
    const int serve_offset = 0;
    const int receive_offset = 3;
    const int set_offset = 7;
    const int attack_offset = 19;
    const int block_offset = 31;
    const int dig_deflection_offset = 35;
    const int dig_no_touch_offset = 39;

    unsigned int draw_index = 0;
    int current_team = serving_team;
    int receiving_team = 1 - serving_team;
    int current_offset = current_team * team_stride;
    int receiving_offset = receiving_team * team_stride;

    double value = random_value(seed, point_index, draw_index++);
    int serve = sample(parameters, current_offset + serve_offset, 3, value);
    if (serve == 0) return pack_result(current_team, 0, 1);
    if (serve == 2) return pack_result(receiving_team, 1, 1);

    value = random_value(seed, point_index, draw_index++);
    int receive = sample(
        parameters, receiving_offset + receive_offset, 4, value
    );
    if (receive == 3) return pack_result(current_team, 2, 2);

    value = random_value(seed, point_index, draw_index++);
    int set_quality = sample(
        parameters, receiving_offset + set_offset + receive * 4, 4, value
    );
    if (set_quality == 3) return pack_result(current_team, 3, 3);

    value = random_value(seed, point_index, draw_index++);
    int attack = sample(
        parameters, receiving_offset + attack_offset + set_quality * 3, 3, value
    );
    if (attack == 0) return pack_result(receiving_team, 4, 4);
    if (attack == 1) return pack_result(current_team, 5, 4);

    value = random_value(seed, point_index, draw_index++);
    int block = sample(parameters, current_offset + block_offset, 4, value);
    if (block == 0) return pack_result(current_team, 6, 5);

    int action_count = 5;
    int attacking_team;
    int defending_team;
    int dig_quality;
    if (block == 1) {
        value = random_value(seed, point_index, draw_index++);
        dig_quality = sample(
            parameters, receiving_offset + dig_deflection_offset, 4, value
        );
        if (dig_quality == 3) return pack_result(current_team, 7, 6);
        attacking_team = receiving_team;
        defending_team = current_team;
        action_count = 6;
    } else if (block == 2) {
        value = random_value(seed, point_index, draw_index++);
        set_quality = sample(
            parameters, current_offset + set_offset, 4, value
        );
        ++action_count;

        value = random_value(seed, point_index, draw_index++);
        attack = sample(
            parameters, current_offset + attack_offset + set_quality * 3, 3,
            value
        );
        ++action_count;
        if (attack == 0) return pack_result(current_team, 4, action_count);
        if (attack == 1) return pack_result(receiving_team, 5, action_count);
        attacking_team = receiving_team;
        defending_team = current_team;
        dig_quality = 0;
    } else {
        value = random_value(seed, point_index, draw_index++);
        if (value >= 0.80) return pack_result(receiving_team, 4, action_count);
        value = random_value(seed, point_index, draw_index++);
        dig_quality = sample(
            parameters, current_offset + dig_no_touch_offset, 4, value
        );
        if (dig_quality == 3) return pack_result(receiving_team, 7, 6);
        attacking_team = current_team;
        defending_team = receiving_team;
        action_count = 6;
    }

    while (action_count < 100) {
        int attacking_offset = attacking_team * team_stride;
        int defending_offset = defending_team * team_stride;

        value = random_value(seed, point_index, draw_index++);
        set_quality = sample(
            parameters, attacking_offset + set_offset + dig_quality * 4, 4,
            value
        );
        ++action_count;
        if (set_quality == 3) {
            return pack_result(defending_team, 3, action_count);
        }
        if (action_count >= 100) break;

        value = random_value(seed, point_index, draw_index++);
        attack = sample(
            parameters, attacking_offset + attack_offset + set_quality * 3, 3,
            value
        );
        ++action_count;
        if (attack == 0) return pack_result(attacking_team, 4, action_count);
        if (attack == 1) return pack_result(defending_team, 5, action_count);
        if (action_count >= 100) break;

        value = random_value(seed, point_index, draw_index++);
        block = sample(parameters, defending_offset + block_offset, 4, value);
        ++action_count;
        if (block == 0) return pack_result(defending_team, 6, action_count);
        if (block == 1) {
            if (action_count >= 100) break;
            value = random_value(seed, point_index, draw_index++);
            dig_quality = sample(
                parameters, attacking_offset + dig_deflection_offset, 4, value
            );
            ++action_count;
            if (dig_quality == 3) {
                return pack_result(defending_team, 7, action_count);
            }
            continue;
        }
        if (block == 2) {
            if (action_count >= 100) break;
            value = random_value(seed, point_index, draw_index++);
            int counter_set = sample(
                parameters, defending_offset + set_offset, 4, value
            );
            ++action_count;
            if (counter_set == 3) {
                return pack_result(attacking_team, 3, action_count);
            }
            if (action_count >= 100) break;
            value = random_value(seed, point_index, draw_index++);
            int counter_attack = sample(
                parameters,
                defending_offset + attack_offset + counter_set * 3,
                3,
                value
            );
            ++action_count;
            if (counter_attack == 0) {
                return pack_result(defending_team, 4, action_count);
            }
            if (counter_attack == 1) {
                return pack_result(attacking_team, 5, action_count);
            }
            dig_quality = 0;
            continue;
        }

        value = random_value(seed, point_index, draw_index++);
        if (value >= 0.80) {
            return pack_result(attacking_team, 4, action_count);
        }
        if (action_count >= 100) break;
        value = random_value(seed, point_index, draw_index++);
        dig_quality = sample(
            parameters, defending_offset + dig_no_touch_offset, 4, value
        );
        ++action_count;
        if (dig_quality == 3) {
            return pack_result(attacking_team, 7, action_count);
        }
        int swap = attacking_team;
        attacking_team = defending_team;
        defending_team = swap;
    }

    value = random_value(seed, point_index, draw_index);
    int winner = value < 0.5 ? attacking_team : defending_team;
    return pack_result(winner, 8, action_count);
}

__global__ void simulate_summary(
    const double* parameters,
    const unsigned long long seed,
    const unsigned long long num_points,
    const int base_serving,
    unsigned long long* summary
) {
    unsigned long long index =
        (unsigned long long)blockIdx.x * blockDim.x + threadIdx.x;
    const unsigned long long stride =
        (unsigned long long)blockDim.x * gridDim.x;
    while (index < num_points) {
        int serving_team = (index & 1ULL)
            ? 1 - base_serving
            : base_serving;
        unsigned short packed = simulate_one(
            parameters, seed, index, serving_team
        );
        unsigned int winner = packed & 1U;
        unsigned int point_type = (packed >> 1) & 15U;
        unsigned long long duration = packed >> 5;
        if (winner == 0) {
            atomicAdd(&summary[0], 1ULL);
            atomicAdd(&summary[serving_team == 0 ? 1 : 2], 1ULL);
            atomicAdd(&summary[12 + point_type], 1ULL);
        } else {
            atomicAdd(&summary[21 + point_type], 1ULL);
        }
        atomicAdd(&summary[3 + point_type], 1ULL);
        atomicAdd(&summary[30 + point_type], duration);
        atomicMin(&summary[39 + point_type], duration);
        atomicMax(&summary[48 + point_type], duration);
        atomicAdd(&summary[57], duration);
        index += stride;
    }
}

}
"""

_SERVE_FALLBACK = {"ace": 0.10, "in_play": 0.85, "error": 0.05}
_RECEIVE_FALLBACK = {
    "excellent": 0.40,
    "good": 0.40,
    "poor": 0.15,
    "error": 0.05,
}
_SET_FALLBACK = {
    "excellent": 0.28,
    "good": 0.48,
    "poor": 0.22,
    "error": 0.02,
}
_ATTACK_FALLBACK = {"kill": 0.50, "error": 0.20, "defended": 0.30}
_BLOCK_FALLBACK = {
    "stuff": 0.20,
    "deflection_to_attack": 0.15,
    "deflection_to_defense": 0.15,
    "no_touch": 0.50,
}
_DIG_DEFLECTION_FALLBACK = {
    "excellent": 0.30,
    "good": 0.40,
    "poor": 0.25,
    "error": 0.05,
}
_DIG_NO_TOUCH_FALLBACK = {
    "excellent": 0.25,
    "good": 0.35,
    "poor": 0.30,
    "error": 0.10,
}


@dataclass(frozen=True)
class SummaryResult:
    """Aggregate point outcomes without per-point rally histories."""

    total_points: int
    team_a_wins: int
    a_serves_wins: int
    a_serves_total: int
    b_serves_wins: int
    b_serves_total: int
    seed: int
    backend: str
    point_type_counts: tuple[int, ...]
    team_a_point_type_counts: tuple[int, ...]
    team_b_point_type_counts: tuple[int, ...]
    duration_sums: tuple[int, ...]
    duration_mins: tuple[int, ...]
    duration_maxs: tuple[int, ...]
    total_duration: int

    def point_rates(self) -> Dict[str, object]:
        overall = self.team_a_wins / self.total_points
        return {
            "overall_win_rate": overall * 100.0,
            "a_serves_win_probability": (
                self.a_serves_wins / self.a_serves_total
                if self.a_serves_total
                else overall
            ),
            "b_serves_win_probability": (
                self.b_serves_wins / self.b_serves_total
                if self.b_serves_total
                else overall
            ),
            "backend": self.backend,
        }

    @property
    def average_duration(self) -> float:
        return self.total_duration / self.total_points

    def aggregate_breakdown(self) -> Dict[str, object]:
        point_counts = {
            name: self.point_type_counts[index]
            for index, name in enumerate(POINT_TYPES)
            if self.point_type_counts[index]
        }
        return {
            "point_type_breakdown": point_counts,
            "point_type_percentages": {
                name: count / self.total_points * 100.0
                for name, count in point_counts.items()
            },
            "team_a_point_types": {
                name: self.team_a_point_type_counts[index]
                for index, name in enumerate(POINT_TYPES)
                if self.team_a_point_type_counts[index]
            },
            "team_b_point_types": {
                name: self.team_b_point_type_counts[index]
                for index, name in enumerate(POINT_TYPES)
                if self.team_b_point_type_counts[index]
            },
            "duration_by_type": {
                name: {
                    "count": self.point_type_counts[index],
                    "average": (
                        self.duration_sums[index]
                        / self.point_type_counts[index]
                    ),
                    "min": self.duration_mins[index],
                    "max": self.duration_maxs[index],
                }
                for index, name in enumerate(POINT_TYPES)
                if self.point_type_counts[index]
            },
            "serving_advantage": {
                "team_a_serve_win_rate": (
                    self.a_serves_wins / self.a_serves_total * 100.0
                    if self.a_serves_total
                    else 0.0
                ),
                "team_b_serve_win_rate": (
                    (self.b_serves_total - self.b_serves_wins)
                    / self.b_serves_total
                    * 100.0
                    if self.b_serves_total
                    else 0.0
                ),
                "team_a_serves": self.a_serves_total,
                "team_b_serves": self.b_serves_total,
            },
        }


def _append_cumulative(
    target: list[float],
    probabilities: Dict[str, float],
    outcomes: Sequence[str],
    fallback: Dict[str, float],
) -> None:
    distribution = probabilities or fallback
    cumulative = 0.0
    for outcome in outcomes:
        cumulative += distribution.get(outcome, 0.0)
        target.append(cumulative)
    target[-1] = 1.0


def _append_block_cumulative(
    target: list[float], probabilities: Dict[str, float]
) -> None:
    distribution = probabilities or _BLOCK_FALLBACK
    known = {"stuff", "deflection_to_attack", "deflection_to_defense"}
    normalized = {
        "stuff": distribution.get("stuff", 0.0),
        "deflection_to_attack": distribution.get(
            "deflection_to_attack", 0.0
        ),
        "deflection_to_defense": distribution.get(
            "deflection_to_defense", 0.0
        ),
        "no_touch": sum(
            value for name, value in distribution.items() if name not in known
        ),
    }
    _append_cumulative(
        target,
        normalized,
        ("stuff", "deflection_to_attack", "deflection_to_defense", "no_touch"),
        _BLOCK_FALLBACK,
    )


def _compile_team(team: Team) -> list[float]:
    compiled: list[float] = []
    _append_cumulative(
        compiled,
        team.serve_probabilities,
        ("ace", "in_play", "error"),
        _SERVE_FALLBACK,
    )
    _append_cumulative(
        compiled,
        team.receive_probabilities.get("in_play_serve", {}),
        ("excellent", "good", "poor", "error"),
        _RECEIVE_FALLBACK,
    )
    for quality in ("excellent", "good", "poor"):
        _append_cumulative(
            compiled,
            team.set_probabilities.get(f"{quality}_reception", {}),
            ("excellent", "good", "poor", "error"),
            _SET_FALLBACK,
        )
    for quality in ("excellent", "good", "poor"):
        _append_cumulative(
            compiled,
            team.attack_probabilities.get(f"{quality}_set", {}),
            ("kill", "error", "defended"),
            _ATTACK_FALLBACK,
        )
    _append_cumulative(
        compiled,
        team.attack_probabilities.get("error_set", {}),
        ("kill", "error", "defended"),
        _ATTACK_FALLBACK,
    )
    _append_block_cumulative(
        compiled, team.block_probabilities.get("power_attack", {})
    )
    dig_probabilities = team.dig_probabilities.get("deflected_attack", {})
    _append_cumulative(
        compiled,
        dig_probabilities,
        ("excellent", "good", "poor", "error"),
        _DIG_DEFLECTION_FALLBACK,
    )
    _append_cumulative(
        compiled,
        dig_probabilities,
        ("excellent", "good", "poor", "error"),
        _DIG_NO_TOUCH_FALLBACK,
    )
    return compiled


@register_jitable
def _random_value(
    seed: tuple[int, int], point_index: int, draw_index: int
) -> float:
    seed_low, seed_high = seed
    left = ((point_index & _MASK_32) ^ seed_low) & _MASK_32
    right = (
        ((point_index >> 32) & _MASK_32)
        ^ seed_high
        ^ ((draw_index * 2_654_435_769) & _MASK_32)
    )
    round_key = (
        seed_low
        ^ (((seed_high << 16) & _MASK_32) | (seed_high >> 16))
        ^ ((draw_index * 2_246_822_519) & _MASK_32)
    ) & _MASK_32
    for round_index in range(10):
        left = (
            ((left >> 8) | ((left << 24) & _MASK_32)) + right
        ) & _MASK_32
        left ^= (
            round_key + round_index * 2_654_435_769
        ) & _MASK_32
        right = (
            ((right << 3) & _MASK_32) | (right >> 29)
        ) ^ left
    return (
        left + (right + 0.5) / 4_294_967_296.0
    ) / 4_294_967_296.0


def _kernel_seed(seed: int) -> tuple[int, int]:
    """Bijectively mix a public seed into two kernel seed words."""
    value = (seed + 0x9E3779B97F4A7C15) & _MASK_64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK_64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK_64
    value ^= value >> 31
    return value & _MASK_32, (value >> 32) & _MASK_32


@register_jitable(inline="always")
def _sample(
    parameters: Sequence[float],
    offset: int,
    outcome_count: int,
    random_value: float,
) -> int:
    for outcome in range(outcome_count):
        if random_value <= parameters[offset + outcome]:
            return outcome
    return outcome_count - 1


@register_jitable(inline="always")
def _pack_result(winner: int, point_type: int, duration: int) -> int:
    return winner | (point_type << 1) | (duration << 5)


def _simulate_one(
    parameters: Sequence[float],
    seed: tuple[int, int],
    point_index: int,
    serving_team: int,
) -> int:
    draw_index = 0
    current_team = serving_team
    receiving_team = 1 - serving_team
    current_offset = current_team * _TEAM_STRIDE
    receiving_offset = receiving_team * _TEAM_STRIDE

    random_value = _random_value(seed, point_index, draw_index)
    draw_index += 1
    serve = _sample(
        parameters, current_offset + _SERVE_OFFSET, 3, random_value
    )
    if serve == 0:
        return _pack_result(current_team, _ACE, 1)
    if serve == 2:
        return _pack_result(receiving_team, _SERVE_ERROR, 1)

    random_value = _random_value(seed, point_index, draw_index)
    draw_index += 1
    receive = _sample(
        parameters, receiving_offset + _RECEIVE_OFFSET, 4, random_value
    )
    if receive == 3:
        return _pack_result(current_team, _RECEIVE_ERROR, 2)

    random_value = _random_value(seed, point_index, draw_index)
    draw_index += 1
    set_quality = _sample(
        parameters,
        receiving_offset + _SET_OFFSET + receive * 4,
        4,
        random_value,
    )
    if set_quality == 3:
        return _pack_result(current_team, _SET_ERROR, 3)

    random_value = _random_value(seed, point_index, draw_index)
    draw_index += 1
    attack = _sample(
        parameters,
        receiving_offset + _ATTACK_OFFSET + set_quality * 3,
        3,
        random_value,
    )
    if attack == 0:
        return _pack_result(receiving_team, _KILL, 4)
    if attack == 1:
        return _pack_result(current_team, _ATTACK_ERROR, 4)

    random_value = _random_value(seed, point_index, draw_index)
    draw_index += 1
    block = _sample(
        parameters, current_offset + _BLOCK_OFFSET, 4, random_value
    )
    if block == 0:
        return _pack_result(current_team, _STUFF, 5)

    action_count = 5
    if block == 1:
        random_value = _random_value(seed, point_index, draw_index)
        draw_index += 1
        dig_quality = _sample(
            parameters,
            receiving_offset + _DIG_DEFLECTION_OFFSET,
            4,
            random_value,
        )
        if dig_quality == 3:
            return _pack_result(current_team, _DIG_ERROR, 6)
        attacking_team = receiving_team
        defending_team = current_team
        action_count = 6
    elif block == 2:
        random_value = _random_value(seed, point_index, draw_index)
        draw_index += 1
        set_quality = _sample(
            parameters,
            current_offset + _SET_OFFSET,
            4,
            random_value,
        )
        action_count += 1

        random_value = _random_value(seed, point_index, draw_index)
        draw_index += 1
        attack = _sample(
            parameters,
            current_offset + _ATTACK_OFFSET + set_quality * 3,
            3,
            random_value,
        )
        action_count += 1
        if attack == 0:
            return _pack_result(current_team, _KILL, action_count)
        if attack == 1:
            return _pack_result(receiving_team, _ATTACK_ERROR, action_count)
        attacking_team = receiving_team
        defending_team = current_team
        dig_quality = 0
    else:
        random_value = _random_value(seed, point_index, draw_index)
        draw_index += 1
        if random_value >= 0.80:
            return _pack_result(receiving_team, _KILL, action_count)
        random_value = _random_value(seed, point_index, draw_index)
        draw_index += 1
        dig_quality = _sample(
            parameters,
            current_offset + _DIG_NO_TOUCH_OFFSET,
            4,
            random_value,
        )
        if dig_quality == 3:
            return _pack_result(receiving_team, _DIG_ERROR, 6)
        attacking_team = current_team
        defending_team = receiving_team
        action_count = 6

    while action_count < 100:
        attacking_offset = attacking_team * _TEAM_STRIDE
        defending_offset = defending_team * _TEAM_STRIDE

        random_value = _random_value(seed, point_index, draw_index)
        draw_index += 1
        set_quality = _sample(
            parameters,
            attacking_offset + _SET_OFFSET + dig_quality * 4,
            4,
            random_value,
        )
        action_count += 1
        if set_quality == 3:
            return _pack_result(defending_team, _SET_ERROR, action_count)
        if action_count >= 100:
            break

        random_value = _random_value(seed, point_index, draw_index)
        draw_index += 1
        attack = _sample(
            parameters,
            attacking_offset + _ATTACK_OFFSET + set_quality * 3,
            3,
            random_value,
        )
        action_count += 1
        if attack == 0:
            return _pack_result(attacking_team, _KILL, action_count)
        if attack == 1:
            return _pack_result(defending_team, _ATTACK_ERROR, action_count)
        if action_count >= 100:
            break

        random_value = _random_value(seed, point_index, draw_index)
        draw_index += 1
        block = _sample(
            parameters, defending_offset + _BLOCK_OFFSET, 4, random_value
        )
        action_count += 1
        if block == 0:
            return _pack_result(defending_team, _STUFF, action_count)
        if block == 1:
            if action_count >= 100:
                break
            random_value = _random_value(seed, point_index, draw_index)
            draw_index += 1
            dig_quality = _sample(
                parameters,
                attacking_offset + _DIG_DEFLECTION_OFFSET,
                4,
                random_value,
            )
            action_count += 1
            if dig_quality == 3:
                return _pack_result(defending_team, _DIG_ERROR, action_count)
            continue
        if block == 2:
            if action_count >= 100:
                break
            random_value = _random_value(seed, point_index, draw_index)
            draw_index += 1
            counter_set = _sample(
                parameters,
                defending_offset + _SET_OFFSET,
                4,
                random_value,
            )
            action_count += 1
            if counter_set == 3:
                return _pack_result(attacking_team, _SET_ERROR, action_count)
            if action_count >= 100:
                break
            random_value = _random_value(seed, point_index, draw_index)
            draw_index += 1
            counter_attack = _sample(
                parameters,
                defending_offset + _ATTACK_OFFSET + counter_set * 3,
                3,
                random_value,
            )
            action_count += 1
            if counter_attack == 0:
                return _pack_result(defending_team, _KILL, action_count)
            if counter_attack == 1:
                return _pack_result(
                    attacking_team, _ATTACK_ERROR, action_count
                )
            dig_quality = 0
            continue

        random_value = _random_value(seed, point_index, draw_index)
        draw_index += 1
        if random_value >= 0.80:
            return _pack_result(attacking_team, _KILL, action_count)
        if action_count >= 100:
            break
        random_value = _random_value(seed, point_index, draw_index)
        draw_index += 1
        dig_quality = _sample(
            parameters,
            defending_offset + _DIG_NO_TOUCH_OFFSET,
            4,
            random_value,
        )
        action_count += 1
        if dig_quality == 3:
            return _pack_result(attacking_team, _DIG_ERROR, action_count)
        attacking_team, defending_team = defending_team, attacking_team

    random_value = _random_value(seed, point_index, draw_index)
    winner = attacking_team if random_value < 0.5 else defending_team
    return _pack_result(winner, _RALLY, action_count)


if njit is not None:
    _simulate_one_jit = njit(cache=True, inline="always")(_simulate_one)

    @njit(cache=True, parallel=True)
    def _simulate_outcomes_numba(
        parameters, seed, num_points: int, base_serving: int
    ):
        outcomes = np.empty(num_points, dtype=np.uint16)
        for point_index in prange(num_points):
            serving_team = (
                base_serving if point_index % 2 == 0 else 1 - base_serving
            )
            outcomes[point_index] = _simulate_one_jit(
                parameters, seed, point_index, serving_team
            )
        return outcomes
else:
    _simulate_outcomes_numba = None


def _load_cuda_backend():
    """Load CuPy and construct the CUDA kernel only when CUDA is requested."""
    global _cupy_module, _cuda_kernel, _cuda_unavailable_reason
    if _cuda_unavailable_reason is not None:
        raise RuntimeError(_cuda_unavailable_reason)
    if _cupy_module is None:
        try:
            cupy = __import__("cupy")
            device_count = cupy.cuda.runtime.getDeviceCount()
            if device_count < 1:
                raise RuntimeError("no CUDA-capable devices were found")
        except Exception as error:
            _cuda_unavailable_reason = str(error)
            raise RuntimeError(_cuda_unavailable_reason) from error
        _cupy_module = cupy
    if _cuda_kernel is None:
        try:
            kernel = _cupy_module.RawKernel(
                _CUDA_SOURCE,
                "simulate_summary",
                options=("--std=c++11",),
            )
            kernel.compile()
            _cuda_kernel = kernel
        except Exception as error:
            _cuda_unavailable_reason = str(error)
            raise RuntimeError(_cuda_unavailable_reason) from error
    return _cupy_module, _cuda_kernel


def cuda_backend_unavailability_reason() -> Optional[str]:
    """Return why CUDA cannot be used, or ``None`` when it is available."""
    try:
        _load_cuda_backend()
    except RuntimeError as error:
        return str(error)
    return None


def cuda_backend_available() -> bool:
    """Return whether the optional CuPy CUDA summary backend is available."""
    return cuda_backend_unavailability_reason() is None


def _simulate_summary_cuda(
    parameters: Sequence[float],
    seed: tuple[int, int],
    num_points: int,
    base_serving: int,
):
    try:
        cupy, kernel = _load_cuda_backend()
        device_parameters = cupy.asarray(parameters, dtype=cupy.float64)
        device_summary = cupy.zeros(58, dtype=cupy.uint64)
        device_summary[39:48] = 101
        block_count = min(
            (num_points + _CUDA_THREADS_PER_BLOCK - 1)
            // _CUDA_THREADS_PER_BLOCK,
            _CUDA_MAX_BLOCKS,
        )
        kernel(
            (block_count,),
            (_CUDA_THREADS_PER_BLOCK,),
            (
                device_parameters,
                cupy.uint64(seed[0] | (seed[1] << 32)),
                cupy.uint64(num_points),
                cupy.int32(base_serving),
                device_summary,
            ),
        )
        values = cupy.asnumpy(device_summary)
        point_type_counts = tuple(int(value) for value in values[3:12])
        duration_mins = tuple(
            int(value) if point_type_counts[index] else 0
            for index, value in enumerate(values[39:48])
        )
        a_serves_total = (
            (num_points + 1) // 2
            if base_serving == 0
            else num_points // 2
        )
        return {
            "team_a_wins": int(values[0]),
            "a_serves_wins": int(values[1]),
            "a_serves_total": a_serves_total,
            "b_serves_wins": int(values[2]),
            "b_serves_total": num_points - a_serves_total,
            "point_type_counts": point_type_counts,
            "team_a_point_type_counts": tuple(
                int(value) for value in values[12:21]
            ),
            "team_b_point_type_counts": tuple(
                int(value) for value in values[21:30]
            ),
            "duration_sums": tuple(int(value) for value in values[30:39]),
            "duration_mins": duration_mins,
            "duration_maxs": tuple(int(value) for value in values[48:57]),
            "total_duration": int(values[57]),
        }
    except Exception as error:
        global _cuda_unavailable_reason
        _cuda_unavailable_reason = str(error)
        raise RuntimeError(
            f"CUDA summary backend failed: {_cuda_unavailable_reason}"
        ) from error


def _summarize_outcomes(outcomes, base_serving: int) -> Dict[str, object]:
    a_parity = 0 if base_serving == 0 else 1
    b_parity = 1 - a_parity
    point_type_counts = [0] * len(POINT_TYPES)
    team_a_point_type_counts = [0] * len(POINT_TYPES)
    team_b_point_type_counts = [0] * len(POINT_TYPES)
    duration_sums = [0] * len(POINT_TYPES)
    duration_mins = [101] * len(POINT_TYPES)
    duration_maxs = [0] * len(POINT_TYPES)

    if np is not None and isinstance(outcomes, np.ndarray):
        winners = outcomes & 1
        point_types = (outcomes >> 1) & 15
        durations = outcomes >> 5
        team_a_wins = int(np.count_nonzero(winners == 0))
        a_serves_wins = int(
            np.count_nonzero(winners[a_parity::2] == 0)
        )
        b_serves_wins = int(
            np.count_nonzero(winners[b_parity::2] == 0)
        )
        for point_type in range(len(POINT_TYPES)):
            mask = point_types == point_type
            count = int(np.count_nonzero(mask))
            point_type_counts[point_type] = count
            if not count:
                continue
            point_durations = durations[mask]
            team_a_point_type_counts[point_type] = int(
                np.count_nonzero(mask & (winners == 0))
            )
            team_b_point_type_counts[point_type] = (
                count - team_a_point_type_counts[point_type]
            )
            duration_sums[point_type] = int(np.sum(point_durations))
            duration_mins[point_type] = int(np.min(point_durations))
            duration_maxs[point_type] = int(np.max(point_durations))
        total_duration = int(np.sum(durations))
    else:
        team_a_wins = 0
        a_serves_wins = 0
        b_serves_wins = 0
        total_duration = 0
        for index, packed in enumerate(outcomes):
            winner = packed & 1
            point_type = (packed >> 1) & 15
            duration = packed >> 5
            if winner == 0:
                team_a_wins += 1
                if index % 2 == a_parity:
                    a_serves_wins += 1
                else:
                    b_serves_wins += 1
                team_a_point_type_counts[point_type] += 1
            else:
                team_b_point_type_counts[point_type] += 1
            point_type_counts[point_type] += 1
            duration_sums[point_type] += duration
            duration_mins[point_type] = min(
                duration_mins[point_type], duration
            )
            duration_maxs[point_type] = max(
                duration_maxs[point_type], duration
            )
            total_duration += duration

    for point_type, count in enumerate(point_type_counts):
        if not count:
            duration_mins[point_type] = 0
    a_serves_total = len(range(a_parity, len(outcomes), 2))
    return {
        "team_a_wins": team_a_wins,
        "a_serves_wins": a_serves_wins,
        "a_serves_total": a_serves_total,
        "b_serves_wins": b_serves_wins,
        "b_serves_total": len(outcomes) - a_serves_total,
        "point_type_counts": tuple(point_type_counts),
        "team_a_point_type_counts": tuple(team_a_point_type_counts),
        "team_b_point_type_counts": tuple(team_b_point_type_counts),
        "duration_sums": tuple(duration_sums),
        "duration_mins": tuple(duration_mins),
        "duration_maxs": tuple(duration_maxs),
        "total_duration": total_duration,
    }


def _select_backend(backend: str, num_points: int) -> str:
    if backend not in {"auto", "cpu", "python", "numba", "cuda"}:
        raise ValueError(
            "backend must be one of: auto, cpu, python, numba, cuda"
        )
    if backend == "cuda":
        reason = cuda_backend_unavailability_reason()
        if reason is not None:
            raise RuntimeError(
                f"CUDA summary backend is unavailable: {reason}"
            )
        return "cuda"
    if backend == "numba":
        if _simulate_outcomes_numba is None:
            raise RuntimeError(
                "Numba summary backend is unavailable; install bvsim[acceleration]"
            )
        return "numba"
    if (
        backend == "auto"
        and num_points >= _CUDA_MIN_POINTS
        and cuda_backend_available()
    ):
        return "cuda"
    if (
        backend in {"auto", "cpu"}
        and _simulate_outcomes_numba is not None
        and num_points >= _NUMBA_MIN_POINTS
    ):
        return "numba"
    return "python"


def uses_accelerated_backend(num_points: int) -> bool:
    """Return whether an automatic summary run will use native parallelism."""
    return _select_backend("auto", num_points) in {"numba", "cuda"}


def simulate_summary(
    team_a: Team,
    team_b: Team,
    num_points: int,
    base_serving: str = "A",
    seed: Optional[int] = None,
    backend: str = "auto",
) -> SummaryResult:
    """Simulate aggregate point wins without allocating rally histories."""
    if num_points <= 0:
        raise ValueError("num_points must be positive")
    if base_serving not in {"A", "B"}:
        raise ValueError("base_serving must be A or B")
    for team in (team_a, team_b):
        errors = validate_team_configuration(team)
        if errors:
            raise ValueError(
                f"Invalid team configuration '{team.name}': "
                + "; ".join(errors)
            )

    effective_seed = seed if seed is not None else secrets.randbits(64)
    kernel_seed = _kernel_seed(effective_seed)
    selected_backend = _select_backend(backend, num_points)
    parameters = _compile_team(team_a) + _compile_team(team_b)
    base_serving_index = 0 if base_serving == "A" else 1

    if selected_backend == "numba":
        outcomes = _simulate_outcomes_numba(
            np.asarray(parameters, dtype=np.float64),
            kernel_seed,
            num_points,
            base_serving_index,
        )
    elif selected_backend == "cuda":
        try:
            summary = _simulate_summary_cuda(
                parameters,
                kernel_seed,
                num_points,
                base_serving_index,
            )
        except RuntimeError:
            if backend != "auto":
                raise
            selected_backend = _select_backend("cpu", num_points)
            if selected_backend == "numba":
                outcomes = _simulate_outcomes_numba(
                    np.asarray(parameters, dtype=np.float64),
                    kernel_seed,
                    num_points,
                    base_serving_index,
                )
            else:
                outcomes = [
                    _simulate_one(
                        parameters,
                        kernel_seed,
                        point_index,
                        (
                            base_serving_index
                            if point_index % 2 == 0
                            else 1 - base_serving_index
                        ),
                    )
                    for point_index in range(num_points)
                ]
    else:
        outcomes = [
            _simulate_one(
                parameters,
                kernel_seed,
                point_index,
                (
                    base_serving_index
                    if point_index % 2 == 0
                    else 1 - base_serving_index
                ),
            )
            for point_index in range(num_points)
        ]

    if selected_backend != "cuda":
        summary = _summarize_outcomes(outcomes, base_serving_index)
    return SummaryResult(
        total_points=num_points,
        team_a_wins=summary["team_a_wins"],
        a_serves_wins=summary["a_serves_wins"],
        a_serves_total=summary["a_serves_total"],
        b_serves_wins=summary["b_serves_wins"],
        b_serves_total=summary["b_serves_total"],
        seed=effective_seed,
        backend=selected_backend,
        point_type_counts=summary["point_type_counts"],
        team_a_point_type_counts=summary["team_a_point_type_counts"],
        team_b_point_type_counts=summary["team_b_point_type_counts"],
        duration_sums=summary["duration_sums"],
        duration_mins=summary["duration_mins"],
        duration_maxs=summary["duration_maxs"],
        total_duration=summary["total_duration"],
    )
