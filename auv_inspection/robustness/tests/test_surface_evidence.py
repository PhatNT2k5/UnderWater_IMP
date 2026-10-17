"""P5: surface coordinates, the k-of-n surface rule and its conformal calibration."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from inspection_route import PIER_CENTERS_X, PIER_Y  # noqa: E402
from robustness.calibrate_surface import conformal_threshold, kth_highest  # noqa: E402
from robustness.geometry import load_params  # noqa: E402
from robustness.surface import render_uv, surface_point, surface_uv  # noqa: E402
from robustness.surface_evidence import (  # noqa: E402
    CELL_M, MERGE_RADIUS_M, MIN_MOVE_M, POOL_PX, VIEWS_REQUIRED, SurfaceCalibration,
    SurfaceEvidence, element_of, load_calibration, pooled)

PARAMS = load_params()
PIXEL = {"pipe_front": 60.0, "pipe_back": 60.0, "pier_0": 60.0, "pier_1": 60.0}
HIT = (70.0, 2.0)          # (score, score / frame median): above both thresholds


def evidence(threshold: float = 1.5) -> SurfaceEvidence:
    names = [f"{c}/{e}" for c in ("pipe_front", "pipe_back") for e in ("pipe_body", "pipe_joint")]
    names += ["pier_0/pier_face", "pier_1/pier_face"]
    return SurfaceEvidence(SurfaceCalibration({name: threshold for name in names}), PIXEL)


def moved(step: int) -> np.ndarray:
    return np.array([step * (MIN_MOVE_M + 0.05), 2.0, -10.2])


class SurfaceCoordinateTests(unittest.TestCase):
    def test_pipe_arc_length_from_the_facing_side(self) -> None:
        r, axis = PARAMS.pipe_radius_m, PARAMS.pipe_axis_z
        front = surface_uv(np.array([[1.0, r, axis], [1.0, 0.0, axis + r]]), "pipe_front", PARAMS)
        np.testing.assert_allclose(front, [[1.0, 0.0], [1.0, r * np.pi / 2]], atol=1e-9)
        back = surface_uv(np.array([[2.0, -r, axis]]), "pipe_back", PARAMS)
        np.testing.assert_allclose(back, [[2.0, 0.0]], atol=1e-9)

    def test_pier_perimeter_is_continuous_around_the_section(self) -> None:
        h, cx = PARAMS.pier_half_width_m, PIER_CENTERS_X[0]
        centres = np.array([[cx, PIER_Y + h, -8.0], [cx - h, PIER_Y, -8.0],
                            [cx, PIER_Y - h, -8.0], [cx + h, PIER_Y, -8.0]])
        np.testing.assert_allclose(surface_uv(centres, "pier_0", PARAMS)[:, 1], [h, 3 * h, 5 * h, 7 * h])
        corner = np.array([[cx - h, PIER_Y + h, -8.0]])
        self.assertAlmostEqual(float(surface_uv(corner, "pier_0", PARAMS)[0, 1]), 2 * h)

    def test_surface_point_inverts_surface_uv(self) -> None:
        r, axis, h = PARAMS.pipe_radius_m, PARAMS.pipe_axis_z, PARAMS.pier_half_width_m
        pipe = np.array([[2.0, r * np.cos(0.3), axis + r * np.sin(0.3)]])
        np.testing.assert_allclose(surface_point(surface_uv(pipe, "pipe_front", PARAMS), "pipe_front", PARAMS),
                                   pipe, atol=1e-9)
        cx = PIER_CENTERS_X[1]
        pier = np.array([[cx + 0.3, PIER_Y + h, -7.0], [cx - h, PIER_Y - 0.2, -5.0],
                         [cx - 0.4, PIER_Y - h, -3.0], [cx + h, PIER_Y + 0.5, -2.0]])
        np.testing.assert_allclose(surface_point(surface_uv(pier, "pier_1", PARAMS), "pier_1", PARAMS),
                                   pier, atol=1e-9)

    def test_render_uv_follows_the_camera_along_the_pipe(self) -> None:
        uv = render_uv(np.array([3.0, 2.1, -10.3]), -90.0, "pipe_front", PARAMS, POOL_PX)
        self.assertEqual(uv.shape, (480 // POOL_PX, 640 // POOL_PX, 2))
        self.assertTrue(np.isnan(uv[0, 0, 0]))                  # water above the pipe
        self.assertAlmostEqual(float(np.nanmedian(uv[..., 0])), 3.0 - PARAMS.camera_lateral_m, delta=0.4)


class SurfaceRuleTests(unittest.TestCase):
    def test_joint_and_body_elements(self) -> None:
        self.assertEqual(element_of("pipe_front", 3.1), "pipe_joint")
        self.assertEqual(element_of("pipe_back", 1.5), "pipe_body")
        self.assertEqual(element_of("pipe_back", -18.0), "pipe_joint")
        self.assertEqual(element_of("pier_1", -8.0), "pier_face")

    def test_pooled_keeps_block_maximum_and_unscored_blocks(self) -> None:
        scores = np.full((8, 8), np.nan, np.float32)
        scores[0, 1], scores[2, 3] = 1.0, 5.0
        grid = pooled(scores)
        self.assertEqual(grid.shape, (2, 2))
        self.assertEqual(grid[0, 0], 5.0)
        self.assertTrue(np.isnan(grid[1, 1]))

    def test_strict_threshold_makes_a_high_absolute_score_a_hit_alone(self) -> None:
        state = evidence()
        state.strict_thresholds = {group: 90.0 for group in PIXEL}
        cell = ("pipe_front", 5, 0)
        for step in range(VIEWS_REQUIRED - 1):
            self.assertEqual(state.observe(moved(step), {cell: (95.0, 1.0)})[0], [])  # relative too low, strict hit
        self.assertEqual(state.observe(moved(VIEWS_REQUIRED - 1), {cell: (85.0, 1.0)})[0], [])  # below strict
        self.assertEqual(len(state.observe(moved(VIEWS_REQUIRED), {cell: (90.0, 1.0)})[0]), 1)
        self.assertEqual(evidence().strict_thresholds, None)

    def test_alert_needs_k_separated_views_above_threshold(self) -> None:
        state = evidence()
        cell = ("pipe_front", 5, 0)
        for step in range(VIEWS_REQUIRED - 1):
            self.assertEqual(state.observe(moved(step), {cell: HIT})[0], [])
        same_place = moved(VIEWS_REQUIRED - 2) + 0.05
        self.assertEqual(state.observe(same_place, {cell: HIT})[0], [])   # not a new view
        self.assertEqual(state.observe(moved(VIEWS_REQUIRED), {cell: (70.0, 1.0)})[0], [])  # relative too low
        self.assertEqual(state.observe(moved(VIEWS_REQUIRED + 1), {cell: (50.0, 2.0)})[0], [])  # absolute too low
        alerts, _ = state.observe(moved(VIEWS_REQUIRED + 2), {cell: HIT})
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].cells, (cell,))
        self.assertEqual(state.observe(moved(VIEWS_REQUIRED + 3), {cell: HIT})[0], [])  # alerts once

    def test_nearby_cells_join_an_alert_and_far_cells_raise_a_new_one(self) -> None:
        state = evidence()
        near = int(MERGE_RADIUS_M / CELL_M) - 1
        cells = {("pier_0", 10, 10): HIT, ("pier_0", 10, 10 + near): HIT, ("pier_0", 40, 10): HIT,
                 ("pier_1", 10, 10): HIT}
        alerts = []
        for step in range(VIEWS_REQUIRED):
            alerts += state.observe(moved(step), cells)[0]
        self.assertEqual(sorted((a.category, a.cells[0][1]) for a in alerts),
                         [("pier_0", 10), ("pier_0", 40), ("pier_1", 10)])
        self.assertEqual(state.coverage(), {"pier_0": 3, "pier_1": 1})

    def test_lowest_threshold_per_group(self) -> None:
        calibration = SurfaceCalibration({"pipe_front/pipe_body": 1.2, "pipe_front/pipe_joint": 1.4,
                                          "pier_0/pier_face": 1.3})
        self.assertEqual(calibration.lowest_threshold("pipe_front"), 1.2)
        with self.assertRaises(KeyError):
            calibration.lowest_threshold("pier_1")

    def test_ambiguous_regions_group_unresolved_cells(self) -> None:
        state = evidence()
        two_hits = {("pipe_front", 10, 0): HIT, ("pipe_front", 11, 0): HIT}   # neighbours, 2 hits each
        alerting = {("pipe_front", 50, 0): HIT}                               # reaches 3 hits
        lonely = {("pier_0", 5, 5): HIT}                                      # 1 hit
        for step in range(2):
            state.observe(moved(step), {**two_hits, **alerting, **(lonely if step == 0 else {})})
        state.observe(moved(2), alerting)
        regions = sorted(state.ambiguous_regions(), key=lambda r: r["category"])
        self.assertEqual([(r["category"], r["cells"], r["max_hits"]) for r in regions],
                         [("pier_0", 1, 1), ("pipe_front", 2, 2)])
        np.testing.assert_allclose(regions[1]["centre_uv_m"], [1.1, 0.05])
        self.assertEqual(len(state.ambiguous_regions(min_hits=2)), 1)

    def test_calibration_constants_must_match_runtime(self) -> None:
        with TemporaryDirectory() as folder:
            path = Path(folder) / "surface.json"
            data = {"cell_m": CELL_M, "pool_px": POOL_PX, "min_move_m": MIN_MOVE_M,
                    "views_required": VIEWS_REQUIRED, "strata": {"pier_0/pier_face": {"threshold": 1.4}}}
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(load_calibration(path).thresholds, {"pier_0/pier_face": 1.4})
            path.write_text(json.dumps(data | {"views_required": 2}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_calibration(path)


class ConformalTests(unittest.TestCase):
    def test_threshold_keeps_conformal_level(self) -> None:
        values = np.arange(1, 100, dtype=float)          # m = 99
        threshold, level, limited = conformal_threshold(values, 0.05)
        self.assertFalse(limited)
        self.assertEqual(int(np.sum(values >= threshold)), 4)
        self.assertLessEqual((1 + np.sum(values >= threshold)) / 100, 0.05)
        self.assertAlmostEqual(level, 0.05)

    def test_small_stratum_is_data_limited_above_all_values(self) -> None:
        values = np.array([1.0, 1.2, 1.1])
        threshold, level, limited = conformal_threshold(values, 1e-4)
        self.assertTrue(limited)
        self.assertGreater(threshold, 1.2)
        self.assertAlmostEqual(level, 0.25)

    def test_stratum_that_cannot_alert_needs_no_relative_threshold(self) -> None:
        values = np.array([-np.inf] * 50 + [1.3])   # one clean cell reached k pixel hits
        threshold, _, limited = conformal_threshold(values, 0.05)
        self.assertFalse(limited)
        self.assertEqual(threshold, 0.0)

    def test_kth_highest_matches_k_of_n_rule(self) -> None:
        views = [1.0, 2.5, 1.7, 3.0, 0.9]
        statistic = kth_highest(views)
        self.assertEqual(sum(value >= statistic for value in views), VIEWS_REQUIRED)


if __name__ == "__main__":
    unittest.main()
