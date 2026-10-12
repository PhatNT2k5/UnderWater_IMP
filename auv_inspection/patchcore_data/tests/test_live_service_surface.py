"""P5: the service raises surface alerts once per surface region, with a box in the current frame."""
from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

import numpy as np
import torch

from auv_inspection.patchcore_data import live_service
from auv_inspection.patchcore_data.alerts import AlertTracker
from robustness.surface_evidence import SurfaceCalibration, SurfaceEvidence  # path set by live_service

POOL = live_service.POOL_PX


def surface_session() -> live_service.Session:
    return live_service.Session(
        model=torch.nn.Identity(), banks={"pipe_front": torch.zeros(1)}, references=[],
        thresholds={"pipe_front": 60.0}, tracker=AlertTracker(), device=torch.device("cpu"),
        model_dir=None, roi_mode="geometry", geometry=live_service.load_params(),
        evidence=SurfaceEvidence(SurfaceCalibration(
            {"pipe_front/pipe_body": 1.5, "pipe_front/pipe_joint": 1.5}), {"pipe_front": 60.0}))


def fake_cells(cell: tuple[str, int, int], value: tuple[float, float]):
    keys_u = np.full((480 // POOL, 640 // POOL), -1)
    keys_v = np.full_like(keys_u, -1)
    keys_u[30:33, 50:54], keys_v[30:33, 50:54] = cell[1], cell[2]
    return {cell: value}, keys_u, keys_v


class SurfaceServiceTests(unittest.TestCase):
    def test_calibration_must_match_the_pixel_threshold_file(self) -> None:
        from tempfile import TemporaryDirectory
        import json
        with TemporaryDirectory() as folder:
            calibration, thresholds = Path(folder) / "surface.json", Path(folder) / "thresholds.json"
            thresholds.write_text("{}", encoding="utf-8")
            calibration.write_text(json.dumps({
                "cell_m": 0.1, "pool_px": 4, "min_move_m": 0.3, "views_required": 3,
                "pixel_thresholds_sha256": "0" * 64, "strata": {}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                live_service.surface_evidence(calibration, thresholds, {})

    def test_surface_rule_needs_the_geometric_roi(self) -> None:
        with self.assertRaises(ValueError):
            live_service.create_session(Path("model"), Path("reference"), Path("thresholds.json"),
                                        roi_mode="reference", alert_rule="surface")

    def test_alert_box_covers_the_alerting_cells_in_this_frame(self) -> None:
        session = surface_session()
        scores = np.full((480, 640), 10.0, np.float32)
        scores[125, 205] = 80.0
        cell = ("pipe_front", 15, 2)
        boxes = []
        with mock.patch.object(live_service, "frame_cells", return_value=fake_cells(cell, (80.0, 2.0))):
            for step in range(3):
                position = np.array([step * 0.4, 2.0, -10.2])
                found, alerts = live_service.surface_step(session, scores, "pipe_front", position, -90.0)
                boxes += found
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].bbox, (50 * POOL, 30 * POOL, 4 * POOL, 3 * POOL))
        self.assertEqual(boxes[0].peak_score, 80.0)
        self.assertEqual(len(alerts), 1)
        np.testing.assert_allclose(alerts[0].surface_uv_m, (1.55, 0.25))


if __name__ == "__main__":
    unittest.main()
