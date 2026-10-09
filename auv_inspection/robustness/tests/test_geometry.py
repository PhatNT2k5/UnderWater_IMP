"""Pinhole camera and structure intersections used to localize alerts."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from robustness.geometry import (  # noqa: E402
    DEFAULT_PARAMS, FOCAL_PX, GeometryParams, in_view, load_params, pixel_to_surface, project,
    render_hits, surface_coordinates)

PIPE_RADIUS_M = DEFAULT_PARAMS.pipe_radius_m

FRONT_CAMERA = np.array([0.0, 2.0, -10.3])
FRONT_YAW = -90.0


class GeometryTests(unittest.TestCase):
    def test_focal_length_matches_80_degree_horizontal_fov(self) -> None:
        self.assertAlmostEqual(FOCAL_PX, 381.36, places=1)

    def test_image_centre_hits_pipe_front_at_standoff_minus_radius(self) -> None:
        hit = pixel_to_surface(320, 240, FRONT_CAMERA, FRONT_YAW, "pipe_front")
        self.assertIsNotNone(hit)
        self.assertAlmostEqual(hit.distance_m, 2.0 - PIPE_RADIUS_M, places=6)
        np.testing.assert_allclose(hit.world, [0.0, PIPE_RADIUS_M, -10.3], atol=1e-6)

    def test_project_inverts_pixel_to_surface(self) -> None:
        for u, v in ((100, 200), (320, 240), (500, 300)):
            hit = pixel_to_surface(u, v, FRONT_CAMERA, FRONT_YAW, "pipe_front")
            pu, pv, _ = project(hit.world, FRONT_CAMERA, FRONT_YAW)
            self.assertAlmostEqual(pu, u, places=4)
            self.assertAlmostEqual(pv, v, places=4)

    def test_image_right_points_to_negative_x_when_facing_pipe_from_front(self) -> None:
        left = pixel_to_surface(100, 240, FRONT_CAMERA, FRONT_YAW, "pipe_front").world
        right = pixel_to_surface(540, 240, FRONT_CAMERA, FRONT_YAW, "pipe_front").world
        self.assertGreater(left[0], right[0])

    def test_back_of_pipe_and_points_behind_camera_are_not_in_view(self) -> None:
        self.assertTrue(in_view(np.array([0.0, PIPE_RADIUS_M, -10.3]), FRONT_CAMERA, FRONT_YAW, "pipe_front"))
        self.assertFalse(in_view(np.array([0.0, -PIPE_RADIUS_M, -10.3]), FRONT_CAMERA, FRONT_YAW, "pipe_front"))
        self.assertFalse(in_view(np.array([0.0, 4.0, -10.3]), FRONT_CAMERA, FRONT_YAW, "pipe_front"))

    def test_pier_face_hit_and_surface_coordinates(self) -> None:
        camera = np.array([-10.0, -6.5 + 2.8, -6.8])
        hit = pixel_to_surface(320, 240, camera, -90.0, "pier_0")
        np.testing.assert_allclose(hit.world, [-10.0, -6.5 + 0.95, -6.8], atol=1e-6)
        height, angle = surface_coordinates(hit.world, "pier_0")
        self.assertAlmostEqual(height, -6.8)
        self.assertAlmostEqual(angle, 90.0)

    def test_rays_missing_the_structure_return_none(self) -> None:
        self.assertIsNone(pixel_to_surface(320, 5, FRONT_CAMERA, FRONT_YAW, "pipe_front"))

    def test_vectorized_render_matches_single_pixel_queries(self) -> None:
        params = GeometryParams(camera_lateral_m=0.1, camera_pitch_deg=3.0, pipe_radius_m=0.45)
        hits = render_hits(FRONT_CAMERA, FRONT_YAW, "pipe_front", params, step=40)
        for row, v in enumerate(range(20, 480, 40)):
            for col, u in enumerate(range(20, 640, 40)):
                single = pixel_to_surface(u, v, FRONT_CAMERA, FRONT_YAW, "pipe_front", params)
                if single is None:
                    self.assertTrue(np.isinf(hits[row, col]), (u, v))
                else:
                    self.assertAlmostEqual(hits[row, col], single.distance_m, places=6)

    def test_pitch_down_moves_the_pipe_up_in_the_image(self) -> None:
        level = render_hits(FRONT_CAMERA, FRONT_YAW, "pipe_front", step=4)
        pitched = render_hits(FRONT_CAMERA, FRONT_YAW, "pipe_front",
                              GeometryParams(camera_pitch_deg=5.0), step=4)
        rows = lambda hits: np.mean(np.nonzero(np.isfinite(hits))[0])  # noqa: E731
        self.assertLess(rows(pitched), rows(level))

    def test_missing_calibration_file_falls_back_to_defaults(self) -> None:
        self.assertEqual(load_params(Path("does/not/exist.json")), DEFAULT_PARAMS)


if __name__ == "__main__":
    unittest.main()
