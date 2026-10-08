"""Evaluation statistics from GENERALIZATION_PLAN.md section 5."""
from __future__ import annotations

from math import sqrt

import numpy as np


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Two-sided Wilson score interval; (0, 1) when there are no trials."""
    if trials <= 0:
        return 0.0, 1.0
    if not 0 <= successes <= trials:
        raise ValueError("successes must lie in [0, trials]")
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    half = z * sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def surveyed_length_m(positions: list[list[float]], max_step_m: float = 1.0) -> float:
    """Path length over consecutive inspection frames, ignoring jumps between sections."""
    if len(positions) < 2:
        return 0.0
    steps = np.linalg.norm(np.diff(np.asarray(positions, float), axis=0), axis=1)
    return float(steps[steps <= max_step_m].sum())


def rate_per_100m(count: int, length_m: float) -> float | None:
    return None if length_m <= 0 else 100.0 * count / length_m


def fraction(successes: int, trials: int) -> dict:
    low, high = wilson_interval(successes, trials)
    return {"count": successes, "total": trials,
            "rate": successes / trials if trials else None, "wilson95": [low, high]}
