"""Scoring logic of the capture replay harness, with a scripted detector."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from robustness.defect_inventory import Defect, Inventory  # noqa: E402
from robustness.evaluate_capture import FrameResult, evaluate  # noqa: E402

MAP_HASH = "f" * 64
DEFECT = Defect("d1", "pipe_front", np.array([0.0, 0.5, -10.3]), 0.6)


def write_capture(root: Path, xs: list[float], scene_state: str = "mixed") -> Path:
    (root / "images").mkdir(parents=True)
    with (root / "frames.jsonl").open("w", encoding="utf-8") as manifest:
        for index, x in enumerate(xs):
            image = f"images/frame_{index:03d}.png"
            cv2.imwrite(str(root / image), np.zeros((480, 640, 3), np.uint8))
            manifest.write(json.dumps({"image": image, "tick": index * 10, "station": "pipe_front_scan_001",
                                       "category": "pipe_front", "position_m": [x, 2.0, -10.3],
                                       "yaw_deg": -90.0}) + "\n")
    (root / "report.json").write_text(json.dumps({"map_sha256": MAP_HASH, "scene_state": scene_state}),
                                      encoding="utf-8")
    return root


def scripted(alert_ticks: set[int], box: tuple[int, int, int, int] = (310, 230, 20, 20)):
    def step(frame: np.ndarray, row: dict) -> FrameResult:
        alert = row["tick"] in alert_ticks
        return FrameResult(True, alert, list(box) if alert else None)
    return step


class EvaluateCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.xs = [-3.0 + 0.3 * index for index in range(21)]  # passes over the defect at x = 0

    def test_alert_on_defect_counts_as_detection_and_rearm_suppresses_repeats(self) -> None:
        capture = write_capture(Path(self.temp.name), self.xs)
        result = evaluate(capture, "scripted", scripted({100, 110}), Inventory(MAP_HASH, (DEFECT,)), [], 0)
        self.assertEqual(result["defects"]["detected"], ["d1"])
        self.assertEqual(result["defects"]["recall"]["rate"], 1.0)
        self.assertEqual(len(result["events"]), 1)  # tick 110 is within 2 m of the first alert
        self.assertEqual(result["false_alerts"], 0)

    def test_alert_away_from_defects_is_a_false_alert(self) -> None:
        capture = write_capture(Path(self.temp.name), self.xs)
        result = evaluate(capture, "scripted", scripted({0}), Inventory(MAP_HASH, (DEFECT,)), [], 0)
        self.assertEqual(result["false_alerts"], 1)
        self.assertEqual(result["defects"]["detected"], [])
        self.assertEqual(result["frame_flag_rate_without_defect"]["count"], 1)

    def test_clean_capture_needs_no_inventory_and_mixed_needs_matching_map(self) -> None:
        clean = write_capture(Path(self.temp.name) / "clean", self.xs, scene_state="clean")
        result = evaluate(clean, "scripted", scripted(set()), None, [], 0)
        self.assertEqual(result["false_alerts"], 0)
        self.assertGreater(result["surveyed_length_m"], 5.0)
        mixed = write_capture(Path(self.temp.name) / "mixed", self.xs)
        with self.assertRaises(ValueError):
            evaluate(mixed, "scripted", scripted(set()), None, [], 0)
        with self.assertRaises(ValueError):
            evaluate(mixed, "scripted", scripted(set()), Inventory("0" * 64, (DEFECT,)), [], 0)


if __name__ == "__main__":
    unittest.main()
