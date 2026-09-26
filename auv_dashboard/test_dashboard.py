"""Check preview backpressure and the camera coordinate boundary without Unreal."""
from __future__ import annotations

from math import radians
import logging
from pathlib import Path
from queue import Queue
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from auv_dashboard import bridge
from auv_dashboard.bridge import (
    damage_pause_remaining, encode_frame, patchcore_category, publish_latest, viewport_pose,
)
from auv_dashboard.widgets import project_3d


class DashboardBridgeTests(unittest.TestCase):
    def test_patchcore_uses_runtime_tick_even_if_reset_steps_camera(self) -> None:
        sys.path.insert(0, str(bridge.INSPECTION))
        import run_inspection as inspection

        requested: list[int] = []
        frame = np.zeros((480, 640, 3), np.uint8)

        class FakeEnvironment:
            def step(self, _action: np.ndarray, ticks: int = 1,
                     publish: bool = True) -> dict:
                return {"PoseSensor": np.eye(4), "InspectionCamera": frame,
                        "VelocitySensor": np.zeros(3)}

        class FakeClient:
            def __init__(self, *_args: object) -> None:
                pass

            def analyze(self, _frame: np.ndarray, tick: int, category: str,
                        _station: str, _position: list[float], _yaw: float) -> dict:
                requested.append(tick)
                return {"status": "analysis_unavailable", "tick": tick,
                        "category": category, "candidates": [], "alerts": []}

            def close(self) -> None:
                pass

        class FrameQueue(Queue):
            def cancel_join_thread(self) -> None:
                pass

        def fake_run(_args: object) -> None:
            environment = inspection.EditorEnvironment()
            environment.step(np.zeros(6))  # Simulate a camera step during reset().
            tracker = inspection.CrackTracker()
            for _ in range(7):
                inspection.is_key_pressed(inspection.KEY_CODES["escape"])
                observation = environment.step(np.zeros(6))
                self.assertTrue(inspection.is_pipe_view("auto", "pipe_front_scan_004",
                                                        np.zeros(3)))
                analysis = inspection.analyze_frame(observation["InspectionCamera"])
                self.assertIsNone(tracker.update(analysis))

        with TemporaryDirectory() as directory:
            events = Queue()
            with (patch.object(inspection, "EditorEnvironment", FakeEnvironment),
                  patch.object(inspection, "run", fake_run),
                  patch.object(bridge, "PatchCoreClient", FakeClient)):
                bridge.run_worker(Queue(), FrameQueue(), events, {
                    "session": str(Path(directory)), "steps": 7, "mode": "auto",
                    "detector": "PatchCore", "follow": False,
                    "patchcore_model": "unused", "patchcore_reference": "unused",
                    "patchcore_thresholds": "unused",
                })
            kinds = [events.get_nowait()["type"] for _ in range(events.qsize())]
            self.assertNotIn("error", kinds)
            self.assertIn("finished", kinds)
            logging.shutdown()
        self.assertEqual(requested, [0, 3, 6])

    def test_damage_pause_countdown_expires_after_five_seconds(self) -> None:
        self.assertEqual(damage_pause_remaining(None, 100.0), 0.0)
        self.assertAlmostEqual(damage_pause_remaining(10.0, 12.25), 2.75)
        self.assertEqual(damage_pause_remaining(10.0, 15.0), 0.0)
        self.assertEqual(damage_pause_remaining(10.0, 16.0), 0.0)

    def test_patchcore_covers_scan_stations_and_skips_transitions(self) -> None:
        self.assertEqual(patchcore_category("pipe_front_scan_004"), "pipe_front")
        self.assertEqual(patchcore_category("pipe_back_scan_019"), "pipe_back")
        self.assertEqual(patchcore_category("pier_0_level_2_orbit_003"), "pier_0")
        self.assertEqual(patchcore_category("pier_1_level_0_orbit_008"), "pier_1")
        self.assertIsNone(patchcore_category("pier_0_approach"))

    def test_route_projection_preserves_depth_and_height(self) -> None:
        center, origin = (0.0, 0.0, 0.0), (100.0, 100.0)
        ground = project_3d((0.0, 0.0, 0.0), center, 0.0, radians(30), 10.0, origin)
        higher = project_3d((0.0, 0.0, 1.0), center, 0.0, radians(30), 10.0, origin)
        farther = project_3d((0.0, 1.0, 0.0), center, 0.0, radians(30), 10.0, origin)
        self.assertLess(higher[1], ground[1])
        self.assertGreater(farther[1], ground[1])

    def test_slow_ui_keeps_recent_frames_without_growing_queue(self) -> None:
        channel = Queue(maxsize=2)
        for tick in range(1000):
            publish_latest(channel, {"tick": tick})
        self.assertEqual(channel.qsize(), 2)
        self.assertEqual([channel.get_nowait()["tick"] for _ in range(2)], [998, 999])

    def test_mask_encoding_preserves_each_pixel(self) -> None:
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[230:334, 224:346] = 255
        encoded = encode_frame(mask, mask=True)
        decoded = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        np.testing.assert_array_equal(mask, decoded)

    def test_color_camera_encoding_keeps_bgr_channels_and_resolution(self) -> None:
        frame = np.full((480, 640, 3), (220, 130, 30), dtype=np.uint8)
        decoded = cv2.imdecode(np.frombuffer(encode_frame(frame), dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape, frame.shape)
        np.testing.assert_allclose(decoded[240, 320], frame[240, 320], atol=3)

    def test_spectator_looks_towards_auv_after_upstream_conversion(self) -> None:
        for yaw in (-180, -90, 0, 90, 180):
            with self.subTest(yaw=yaw):
                position = np.array([-14.0, 2.0, -10.3])
                original = position.copy()
                eye, command = viewport_pose(position, yaw)
                # Mirror TeleportCameraCommand's actual angular-vector conversion.
                engine_direction = np.asarray(command) * np.array([-1, 1, -1])
                heading = np.deg2rad(yaw)
                target = position + 0.8 * np.array([np.cos(heading), np.sin(heading), 0.0])
                intended_engine_direction = (target - eye) * np.array([1, -1, 1])
                np.testing.assert_allclose(engine_direction, intended_engine_direction, atol=1e-12)
                np.testing.assert_array_equal(position, original)
                self.assertLess(engine_direction[2], 0)


if __name__ == "__main__":
    unittest.main()
