"""Shared statistical inference helpers for BVSim."""

import math
import statistics
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


def _validate_confidence(confidence: float) -> None:
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    max_iterations = 200
    epsilon = 3e-14
    floor = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < floor:
        d = floor
    d = 1.0 / d
    result = d

    for iteration in range(1, max_iterations + 1):
        m2 = 2 * iteration
        numerator = iteration * (b - iteration) * x / (
            (qam + m2) * (a + m2)
        )
        d = 1.0 + numerator * d
        if abs(d) < floor:
            d = floor
        c = 1.0 + numerator / c
        if abs(c) < floor:
            c = floor
        d = 1.0 / d
        result *= d * c

        numerator = -(a + iteration) * (qab + iteration) * x / (
            (a + m2) * (qap + m2)
        )
        d = 1.0 + numerator * d
        if abs(d) < floor:
            d = floor
        c = 1.0 + numerator / c
        if abs(c) < floor:
            c = floor
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < epsilon:
            return result

    raise RuntimeError("incomplete beta calculation did not converge")


def _regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    scale = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return scale * _beta_continued_fraction(a, b, x) / a
    return 1.0 - scale * _beta_continued_fraction(b, a, 1.0 - x) / b


def student_t_cdf(value: float, degrees_of_freedom: int) -> float:
    if degrees_of_freedom < 1:
        raise ValueError("degrees_of_freedom must be at least 1")
    if value == 0.0:
        return 0.5

    x = degrees_of_freedom / (degrees_of_freedom + value * value)
    tail = 0.5 * _regularized_incomplete_beta(
        x, degrees_of_freedom / 2.0, 0.5
    )
    return 1.0 - tail if value > 0 else tail


def student_t_critical(confidence: float, degrees_of_freedom: int) -> float:
    _validate_confidence(confidence)
    if degrees_of_freedom < 1:
        raise ValueError("degrees_of_freedom must be at least 1")

    target = 0.5 + confidence / 2.0
    lower = 0.0
    upper = 1.0
    while student_t_cdf(upper, degrees_of_freedom) < target:
        upper *= 2.0

    for _ in range(100):
        midpoint = (lower + upper) / 2.0
        if student_t_cdf(midpoint, degrees_of_freedom) < target:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


def mean_confidence_interval(
    values: Iterable[float], confidence: float = 0.95
) -> Tuple[float, Optional[float], Optional[float]]:
    _validate_confidence(confidence)
    samples = list(values)
    if not samples:
        raise ValueError("at least one value is required")

    mean = statistics.mean(samples)
    if len(samples) < 2:
        return mean, None, None

    standard_error = statistics.stdev(samples) / math.sqrt(len(samples))
    critical = student_t_critical(confidence, len(samples) - 1)
    margin = critical * standard_error
    return mean, mean - margin, mean + margin


def paired_difference_statistics(
    baseline: Sequence[float],
    variant: Sequence[float],
    confidence: float = 0.95,
) -> Tuple[float, Optional[float], Optional[float], Optional[float]]:
    if len(baseline) != len(variant):
        raise ValueError("paired samples must have the same length")
    differences = [new - base for base, new in zip(baseline, variant)]
    mean, lower, upper = mean_confidence_interval(differences, confidence)
    if len(differences) < 2:
        return mean, lower, upper, None

    standard_error = statistics.stdev(differences) / math.sqrt(len(differences))
    if standard_error == 0.0:
        p_value = 0.0 if mean != 0.0 else 1.0
    else:
        statistic = abs(mean / standard_error)
        p_value = 2.0 * (
            1.0 - student_t_cdf(statistic, len(differences) - 1)
        )
    return mean, lower, upper, min(max(p_value, 0.0), 1.0)


def wilson_interval(
    successes: int, total: int, confidence: float = 0.95
) -> Tuple[float, float, float]:
    _validate_confidence(confidence)
    if total <= 0:
        raise ValueError("total must be positive")
    if not 0 <= successes <= total:
        raise ValueError("successes must be between 0 and total")

    proportion = successes / total
    z = statistics.NormalDist().inv_cdf(0.5 + confidence / 2.0)
    z_squared = z * z
    denominator = 1.0 + z_squared / total
    center = (proportion + z_squared / (2.0 * total)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z_squared / (4.0 * total * total)
        )
        / denominator
    )
    return proportion, max(0.0, center - margin), min(1.0, center + margin)


def holm_adjust(p_values: Sequence[float]) -> List[float]:
    if any(not 0.0 <= value <= 1.0 for value in p_values):
        raise ValueError("p-values must be between 0 and 1")

    count = len(p_values)
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * count
    running_max = 0.0
    for rank, (original_index, p_value) in enumerate(ordered):
        candidate = min(1.0, (count - rank) * p_value)
        running_max = max(running_max, candidate)
        adjusted[original_index] = running_max
    return adjusted


def aggregate_effect_statistics(
    all_results: Sequence[Mapping[str, Any]],
    container_key: str,
    confidence: float = 0.95,
) -> List[Dict[str, Any]]:
    """Aggregate run-level model effects and apply Holm correction."""
    if not all_results:
        return []
    first_container = all_results[0].get(container_key, {})
    aggregated: List[Dict[str, Any]] = []
    for name in first_container:
        point_effects = []
        match_effects = []
        for result in all_results:
            effect = result.get(container_key, {}).get(name)
            if effect is not None:
                point_effects.append(effect.get("improvement", 0.0))
                match_effects.append(effect.get("match_improvement", 0.0))
        if not point_effects:
            continue
        point_mean, point_lower, point_upper = mean_confidence_interval(
            point_effects, confidence
        )
        match_mean, match_lower, match_upper = mean_confidence_interval(
            match_effects, confidence
        )
        _, _, _, raw_p_value = paired_difference_statistics(
            [0.0] * len(point_effects), point_effects, confidence
        )
        aggregated.append({
            "name": name,
            "point_mean": point_mean,
            "point_lower": point_lower,
            "point_upper": point_upper,
            "match_mean": match_mean,
            "match_lower": match_lower,
            "match_upper": match_upper,
            "raw_p_value": raw_p_value,
            "adjusted_p_value": None,
            "holm_significant": False,
            "num_runs": len(point_effects),
        })

    comparable = [
        effect for effect in aggregated if effect["raw_p_value"] is not None
    ]
    adjusted_values = holm_adjust(
        [effect["raw_p_value"] for effect in comparable]
    )
    alpha = 1.0 - confidence
    for effect, adjusted in zip(comparable, adjusted_values):
        effect["adjusted_p_value"] = adjusted
        effect["holm_significant"] = adjusted < alpha
    return aggregated
