"""Randomized run conditions: reproducible, safe routes, and held-out values outside train."""
from __future__ import annotations

import argparse
import importlib.util
from math import hypot
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from inspection_route import ROUTE  # noqa: E402
from robustness.conditions import (  # noqa: E402
    NOMINAL, PROFILES, CaptureSchedule, conditioned_route, current_at, sample_conditions)

SEEDS = range(60)


def inside(value: float, intervals: list[tuple[float, float]]) -> bool:
    return any(low - 1e-9 <= value <= high + 1e-9 for low, high in intervals)


def factor_values(conditions) -> dict[str, float]:
    return {
        "pipe_offset_m": conditions.pipe_offset_m,
        "pier_radius_m": conditions.pier_radius_m,
        "depth_jitter_m": conditions.depth_jitter_m,
        "yaw_jitter_deg": conditions.yaw_jitter_deg,
        "current_speed_mps": hypot(*conditions.current_mps[:2]),
        "current_variation_mps": conditions.current_variation_mps,
        "light_scale": conditions.light_intensity / NOMINAL.light_intensity,
        "light_pitch_deg": conditions.light_pitch_deg,
    }


class ConditionTests(unittest.TestCase):
    def test_nominal_conditions_reproduce_the_validated_runtime(self) -> None:
        self.assertEqual(NOMINAL.light_intensity, 2500.0)
        self.assertEqual(NOMINAL.light_pitch_deg, 0.0)
        self.assertEqual(NOMINAL.capture_interval_ticks, (10, 10))
        self.assertEqual(conditioned_route(NOMINAL), ROUTE)

    def test_sampling_is_reproducible_per_profile_and_seed(self) -> None:
        self.assertEqual(sample_conditions("train", 4), sample_conditions("train", 4))
        self.assertNotEqual(sample_conditions("train", 4), sample_conditions("train", 5))
        self.assertNotEqual(sample_conditions("train", 4), sample_conditions("heldout", 4))
        with self.assertRaises(ValueError):
            sample_conditions("extreme", 1)

    def test_train_samples_stay_inside_train_ranges(self) -> None:
        for seed in SEEDS:
            for factor, value in factor_values(sample_conditions("train", seed)).items():
                self.assertTrue(inside(value, PROFILES["train"][factor]), (seed, factor, value))

    def test_heldout_samples_never_fall_inside_train_ranges(self) -> None:
        for seed in SEEDS:
            for factor, value in factor_values(sample_conditions("heldout", seed)).items():
                self.assertTrue(inside(value, PROFILES["heldout"][factor]), (seed, factor, value))
                self.assertFalse(inside(value, PROFILES["train"][factor]), (seed, factor, value))

    def test_randomized_routes_keep_segment_order_and_structure_clearance(self) -> None:
        def segments(route) -> list[str]:
            # Interpolated waypoint counts change with standoff; segment order must not.
            names = [name.rsplit("_", 1)[0] for name, _ in route]
            return [name for index, name in enumerate(names) if index == 0 or names[index - 1] != name]

        nominal = segments(ROUTE)
        for profile in PROFILES:
            for seed in SEEDS:
                route = conditioned_route(sample_conditions(profile, seed))  # raises on violation
                self.assertEqual(segments(route), nominal, (profile, seed))
                # Radii above ~3.07 m split each 15 degree arc into two waypoints.
                steps = {name.rsplit("_", 1)[0] for name, _ in route
                         if name.startswith("pier_1_level_2_orbit_")}
                self.assertEqual(len(steps), 24, (profile, seed))

    def test_fixed_capture_grid_matches_previous_modulo_rule(self) -> None:
        schedule = CaptureSchedule((10, 10), seed=0)
        self.assertEqual([tick for tick in range(100) if schedule.due(tick)], list(range(0, 100, 10)))

    def test_random_capture_gaps_respect_bounds_and_seed(self) -> None:
        def ticks(seed: int) -> list[int]:
            schedule = CaptureSchedule((3, 17), seed=seed)
            return [tick for tick in range(30, 3000) if schedule.due(tick)]

        captured = ticks(1)
        gaps = [later - earlier for earlier, later in zip(captured, captured[1:])]
        self.assertTrue(all(3 <= gap <= 17 for gap in gaps), gaps)
        self.assertGreater(len(set(gaps)), 5)
        self.assertEqual(captured, ticks(1))
        self.assertNotEqual(captured, ticks(2))

    def test_current_varies_slowly_around_its_mean(self) -> None:
        conditions = sample_conditions("heldout", 3)
        samples = [current_at(conditions, tick, 30) for tick in range(0, 3600, 30)]
        for x, y, _ in samples:
            deviation = hypot(x - conditions.current_mps[0], y - conditions.current_mps[1])
            self.assertLessEqual(deviation, conditions.current_variation_mps + 1e-9)
        self.assertEqual(current_at(NOMINAL, 900, 30), [0.0, 0.0, 0.0])

    @unittest.skipUnless(importlib.util.find_spec("win32api"), "run_inspection needs pywin32 (mainenv)")
    def test_runtime_rejects_randomized_manual_runs_before_launching_unreal(self) -> None:
        import run_inspection
        args = argparse.Namespace(mode="manual", randomize="train", seed=1, preview_source=None)
        with self.assertRaises(ValueError):
            run_inspection.run(args)


if __name__ == "__main__":
    unittest.main()
