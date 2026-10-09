"""P3: scoring margin at the ROI edge and the diffuse-anomaly abstention."""
from __future__ import annotations

import unittest
from unittest import mock

import numpy as np
import torch

from auv_inspection.patchcore_data import live_service
from auv_inspection.patchcore_data.alerts import AlertTracker, Candidate


def request(tick: int) -> dict:
    return {"tick": tick, "category": "pipe_front", "station": "pipe_front_scan_010",
            "position_m": [0.0, 2.0, -10.3], "yaw_deg": -90.0,
            "camera_png_b64": live_service.encode_png(np.full((480, 640, 3), 90, np.uint8))}


def session(diffuse_gate: bool, margin: int = 0) -> live_service.Session:
    return live_service.Session(
        model=torch.nn.Identity(), banks={"pipe_front": torch.zeros(1)}, references=[],
        thresholds={"pipe_front": 60.0}, tracker=AlertTracker(), device=torch.device("cpu"),
        model_dir=None, roi_mode="reference", score_margin_px=margin, diffuse_gate=diffuse_gate)


def band_roi() -> np.ndarray:
    roi = np.zeros((480, 640), np.uint8)
    roi[100:380, :] = 255
    return roi


class MarginTests(unittest.TestCase):
    def test_interior_ignores_image_border_but_not_roi_edge(self) -> None:
        inside = live_service.interior(band_roi(), 24)
        self.assertTrue(inside[240, 0])        # band touches the image side: still scored
        self.assertTrue(inside[240, 639])
        self.assertFalse(inside[110, 320])     # 10 px from the ROI edge
        self.assertTrue(inside[130, 320])      # 30 px from the ROI edge
        self.assertFalse(inside[50, 320])      # outside the ROI

    def test_margin_masks_edge_scores_before_candidates(self) -> None:
        scores = np.full((480, 640), 10.0, np.float32)
        scores[100:108, 300:320] = 90.0        # rim artefact on the ROI edge
        gated = session(diffuse_gate=False, margin=24)
        with mock.patch.object(live_service, "match_roi", return_value=(band_roi(), {"status": "ready"})), \
                mock.patch.object(live_service, "predict_map", return_value=scores):
            response = live_service.analyze_request(gated, request(0))
        self.assertEqual(response["status"], "ready")
        self.assertEqual(response["candidates"], [])
        self.assertIn("sharpness", response["quality"])


class DiffuseTests(unittest.TestCase):
    def test_share_and_count_limits(self) -> None:
        scores = np.zeros((100, 100), np.float32)
        scores[:4, :] = 70.0                   # 4% above threshold
        self.assertFalse(live_service.is_diffuse(scores, 60.0, [])[0])
        scores[:6, :] = 70.0                   # 6%
        diffuse, share = live_service.is_diffuse(scores, 60.0, [])
        self.assertTrue(diffuse)
        self.assertAlmostEqual(share, 0.06)
        many = [Candidate((0, 0, 1, 1), (0.0, 0.0), 70.0, 1)] * 7
        self.assertTrue(live_service.is_diffuse(np.zeros((10, 10)), 60.0, many)[0])

    def test_nan_scores_are_not_counted(self) -> None:
        scores = np.full((100, 100), np.nan, np.float32)
        scores[:10, :] = 0.0
        scores[:1, :] = 70.0                   # 10% of finite scores
        self.assertTrue(live_service.is_diffuse(scores, 60.0, [])[0])

    def test_diffuse_frame_abstains_and_keeps_tracker(self) -> None:
        widespread = np.full((480, 640), 70.0, np.float32)
        gated = session(diffuse_gate=True)
        gated.tracker.step("pipe_front", 0, [Candidate((100, 100, 3, 3), (101.5, 101.5), 70.0, 9)])
        with mock.patch.object(live_service, "match_roi", return_value=(band_roi(), {"status": "ready"})), \
                mock.patch.object(live_service, "predict_map", return_value=widespread):
            response = live_service.analyze_request(gated, request(3))
        self.assertEqual(response["status"], "analysis_unavailable")
        self.assertEqual(response["reason"], "diffuse_anomaly")
        self.assertGreater(response["anomaly_share"], 0.05)
        self.assertEqual(gated.tracker.last_tick, 0)
        self.assertEqual(len(gated.tracker.tracks), 1)

    def test_gate_off_keeps_v1_2_behaviour(self) -> None:
        widespread = np.full((480, 640), 70.0, np.float32)
        with mock.patch.object(live_service, "match_roi", return_value=(band_roi(), {"status": "ready"})), \
                mock.patch.object(live_service, "predict_map", return_value=widespread):
            response = live_service.analyze_request(session(diffuse_gate=False), request(0))
        self.assertEqual(response["status"], "ready")


if __name__ == "__main__":
    unittest.main()
