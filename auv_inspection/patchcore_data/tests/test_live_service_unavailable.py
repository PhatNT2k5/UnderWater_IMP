"""Unusable frames must not erase tracker evidence collected on usable frames."""
from __future__ import annotations

import unittest
from unittest import mock

import numpy as np
import torch

from auv_inspection.patchcore_data import live_service
from auv_inspection.patchcore_data.alerts import AlertTracker, Candidate


def candidate(x: float) -> Candidate:
    return Candidate((int(x), 100, 3, 3), (x, 101.5), 60.0, 9)


def unavailable_request(tick: int) -> dict:
    return {"tick": tick, "category": "pipe_front", "station": "pipe_front_scan_010",
            "position_m": [0.0, 2.0, -10.3], "yaw_deg": -90.0,
            "camera_png_b64": live_service.encode_png(np.zeros((480, 640, 3), np.uint8))}


class UnavailableFrameTests(unittest.TestCase):
    def test_unavailable_frame_keeps_tracker_state(self) -> None:
        tracker = AlertTracker()
        tracker.step("pipe_front", 0, [candidate(100)])
        session = live_service.Session(
            model=torch.nn.Identity(), banks={}, references=[], tracker=tracker,
            thresholds={"pipe_front": 60.0}, device=torch.device("cpu"), model_dir=None)
        with mock.patch.object(live_service, "match_roi",
                               return_value=(None, {"status": "reference_unavailable"})):
            response = live_service.analyze_request(session, unavailable_request(3))

        self.assertEqual(response["status"], "analysis_unavailable")
        self.assertEqual(tracker.last_tick, 0)
        self.assertEqual(len(tracker.tracks), 1)

    def test_evidence_survives_interleaved_unavailable_frames(self) -> None:
        # Live sampling every 3 ticks with every other frame unusable (2026-09-27 session pattern).
        tracker = AlertTracker()
        self.assertEqual(tracker.step("pipe_front", 0, [candidate(100)]), [])
        self.assertEqual(tracker.step("pipe_front", 6, [candidate(157)]), [])
        self.assertEqual(len(tracker.step("pipe_front", 12, [candidate(214)])), 1)

    def test_long_unobserved_gap_still_drops_stale_tracks(self) -> None:
        tracker = AlertTracker()
        tracker.step("pipe_front", 0, [candidate(100)])
        tracker.step("pipe_front", 6, [candidate(157)])
        self.assertEqual(tracker.step("pipe_front", 30, [candidate(385)]), [])


if __name__ == "__main__":
    unittest.main()
