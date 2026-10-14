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
from robustness.evaluate_capture import (  # noqa: E402
    FrameResult, clean_cell_fpr, evaluate, evaluate_many, perceived_pose)
from robustness.evaluate_capture import GEOMETRY  # noqa: E402
from robustness.surface import surface_uv  # noqa: E402

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

    def test_surface_style_detector_reports_every_alert_without_rearm_lock(self) -> None:
        capture = write_capture(Path(self.temp.name), self.xs)
        on_defect, far_left = [310, 230, 20, 20], [20, 230, 20, 20]

        def step(frame: np.ndarray, row: dict) -> FrameResult:
            if row["tick"] == 100:   # two new regions in one frame
                return FrameResult(True, True, on_defect, more_alert_bboxes=(far_left,))
            if row["tick"] == 110:   # another region 0.3 m later, inside the old 2 m lock
                return FrameResult(True, True, far_left)
            return FrameResult(True, False, None)

        step.rearm_distance_m = 0.0
        result = evaluate(capture, "surface", step, Inventory(MAP_HASH, (DEFECT,)), [], 0)
        self.assertEqual([event["tick"] for event in result["events"]], [100, 100, 110])
        self.assertEqual(result["defects"]["detected"], ["d1"])
        self.assertEqual(result["false_alerts"], 2)

    def test_clean_cell_fpr_skips_defect_cells_and_thin_cells(self) -> None:
        u, v = surface_uv(DEFECT.world, "pipe_front", GEOMETRY)[0]
        on_defect = ("pipe_front", int(u // 0.1), int(v // 0.1))
        cells = [(on_defect, 5, True),                      # alert on the labelled defect: not clean
                 (("pipe_front", 40, 0), 5, True),          # clean cell that alerted
                 (("pipe_front", 41, 0), 4, False),         # clean, evaluated
                 (("pipe_front", 42, 0), 2, True)]          # fewer than k views: not evaluated
        result = clean_cell_fpr(cells, (DEFECT,))
        self.assertEqual((result["count"], result["total"]), (1, 2))

    def test_alert_away_from_defects_is_a_false_alert(self) -> None:
        capture = write_capture(Path(self.temp.name), self.xs)
        result = evaluate(capture, "scripted", scripted({0}), Inventory(MAP_HASH, (DEFECT,)), [], 0)
        self.assertEqual(result["false_alerts"], 1)
        self.assertEqual(result["defects"]["detected"], [])
        self.assertEqual(result["frame_flag_rate_without_defect"]["count"], 1)

    def test_pose_noise_is_seeded_and_reports_its_uncertainty(self) -> None:
        row = {"tick": 40, "position_m": [0.0, 2.0, -10.3], "yaw_deg": -90.0}
        self.assertIs(perceived_pose(row, (0.0, 0.0), 1), row)
        first = perceived_pose(row, (0.2, 3.0), 1)
        self.assertEqual(first, perceived_pose(row, (0.2, 3.0), 1))
        self.assertNotEqual(first["position_m"], perceived_pose(row, (0.2, 3.0), 2)["position_m"])
        self.assertEqual((first["pose_sigma_m"], first["pose_sigma_yaw_deg"]), (0.2, 3.0))
        self.assertEqual(row["position_m"], [0.0, 2.0, -10.3])  # ground truth untouched

    def test_frames_are_replayed_once_for_every_detector(self) -> None:
        capture = write_capture(Path(self.temp.name), self.xs)
        calls: list[str] = []

        def counting(name: str):
            def step(frame: np.ndarray, row: dict) -> FrameResult:
                calls.append(name)
                return FrameResult(True, False, None)
            return step

        results = evaluate_many(capture, {"a": counting("a"), "b": counting("b")},
                                Inventory(MAP_HASH, (DEFECT,)), [], 0)
        self.assertEqual(set(results), {"a", "b"})
        self.assertEqual(calls.count("a"), len(self.xs))
        self.assertEqual(calls.count("b"), len(self.xs))

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
