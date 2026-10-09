"""Geometric ROI, pose-derived structure groups, pose noise and the fitted calibration."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from robustness.calibrate_geometry import DATASET, iou, load_frames  # noqa: E402
from robustness.geometric_roi import (  # noqa: E402
    category_from_pose, erosion_px, geometric_roi)
from robustness.geometry import (  # noqa: E402
    CALIBRATION_FILE, DEFAULT_PARAMS, load_params, render_surface)

PIPE_FRONT = (np.array([0.0, 2.0, -10.3]), -90.0)
PIPE_BACK = (np.array([0.0, -2.0, -10.3]), 90.0)
PIER_0 = (np.array([-10.0, -6.5 + 2.8, -6.8]), -90.0)


class GeometricRoiTests(unittest.TestCase):
    def test_category_follows_the_structure_in_view(self) -> None:
        self.assertEqual(category_from_pose(*PIPE_FRONT), "pipe_front")
        self.assertEqual(category_from_pose(*PIPE_BACK), "pipe_back")
        self.assertEqual(category_from_pose(*PIER_0), "pier_0")
        self.assertIsNone(category_from_pose(np.array([0.0, 8.0, -10.3]), -90.0))  # too far
        self.assertIsNone(category_from_pose(np.array([0.0, 2.0, -10.3]), 90.0))   # facing away

    def test_roi_covers_the_pipe_band_and_shrinks_with_pose_uncertainty(self) -> None:
        sharp, status = geometric_roi(*PIPE_FRONT, "pipe_front", pose_sigma_m=0.0, pose_sigma_yaw_deg=0.0)
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["erosion_px"], 0)
        rows = np.nonzero(sharp.any(axis=1))[0]
        self.assertLess(rows.min(), 240)
        self.assertGreater(rows.max(), 240)
        loose, status = geometric_roi(*PIPE_FRONT, "pipe_front", pose_sigma_m=0.1, pose_sigma_yaw_deg=2.0)
        self.assertGreater(status["erosion_px"], 0)
        self.assertLess(np.count_nonzero(loose), np.count_nonzero(sharp))
        self.assertTrue(np.all(sharp[loose > 0] > 0))  # erosion only removes pixels

    def test_grazing_silhouette_band_is_excluded(self) -> None:
        full, _ = geometric_roi(*PIPE_FRONT, "pipe_front", pose_sigma_m=0.0, pose_sigma_yaw_deg=0.0,
                                max_incidence_deg=90.0)
        limited, status = geometric_roi(*PIPE_FRONT, "pipe_front", pose_sigma_m=0.0,
                                        pose_sigma_yaw_deg=0.0)
        self.assertEqual(status["max_incidence_deg"], 70.0)
        self.assertLess(np.count_nonzero(limited), np.count_nonzero(full))
        self.assertTrue(np.all(full[limited > 0] > 0))
        self.assertTrue(limited[240, 320])                       # face-on centre kept
        top = np.nonzero(full[:, 320])[0].min()
        self.assertFalse(limited[top, 320])                      # grazing rim dropped

    def test_surface_normals_face_the_camera_on_pipe_and_pier(self) -> None:
        _, cosine = render_surface(*PIPE_FRONT, "pipe_front", step=16)
        self.assertGreater(cosine[cosine.shape[0] // 2, cosine.shape[1] // 2], 0.99)
        _, cosine = render_surface(*PIER_0, "pier_0", step=16)
        self.assertGreater(cosine[cosine.shape[0] // 2, cosine.shape[1] // 2], 0.99)

    def test_erosion_grows_with_uncertainty_and_closeness(self) -> None:
        self.assertGreater(erosion_px(1.0, 0.1, 0.0), erosion_px(3.0, 0.1, 0.0))
        self.assertGreater(erosion_px(2.0, 0.0, 2.0), erosion_px(2.0, 0.0, 0.5))
        with self.assertRaises(ValueError):
            geometric_roi(*PIPE_FRONT, "pipe_front", pose_sigma_m=-0.1)

    def test_far_or_missing_structure_is_reported_not_guessed(self) -> None:
        mask, status = geometric_roi(np.array([0.0, 8.0, -10.3]), -90.0, "pipe_front")
        self.assertIsNone(mask)
        self.assertEqual(status["status"], "no_structure_in_range")


@unittest.skipUnless(CALIBRATION_FILE.is_file() and DATASET.is_dir(), "needs calibration and reviewed masks")
class CalibrationTests(unittest.TestCase):
    def test_calibration_records_held_out_agreement_above_acceptance(self) -> None:
        report = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
        for category, values in report["after"]["validate"].items():
            self.assertGreaterEqual(values["iou_median"], 0.85, category)

    def test_calibrated_geometry_beats_defaults_on_human_polygon_masks(self) -> None:
        approved = json.loads((DATASET / "roi_approved.json").read_text(encoding="utf-8"))
        frames = [frame for frame in load_frames(DATASET)
                  if approved[frame["image"]].get("method") == "orb_affine"][::6]
        calibrated = load_params()
        before = np.median([iou(frame, DEFAULT_PARAMS) for frame in frames])
        after = np.median([iou(frame, calibrated) for frame in frames])
        self.assertGreater(after, before)
        self.assertGreaterEqual(after, 0.85)


if __name__ == "__main__":
    unittest.main()
