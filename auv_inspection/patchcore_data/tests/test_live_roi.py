"""Check live ROI selection without reference camera images."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import cv2
import numpy as np

from auv_inspection.patchcore_data.live_roi import load_references, match_roi

FRAME = np.zeros((480, 640, 3), np.uint8)
STATION = "pipe_front_scan_010"


def write_dataset(root: Path, masks: dict[str, tuple[list[float], tuple[int, int, int, int]]]) -> Path:
    """Write approved masks; values are (position_m, x0/y0/x1/y1 rectangle)."""
    (root / "roi_masks").mkdir(parents=True)
    manifest, approved = [], {}
    for name, (position, (x0, y0, x1, y1)) in masks.items():
        mask = np.zeros((480, 640), np.uint8)
        mask[y0:y1, x0:x1] = 255
        cv2.imwrite(str(root / "roi_masks" / f"{name}.png"), mask)
        image = f"images/pipe_front/{name}.png"
        manifest.append({"image": image, "category": "pipe_front", "station": STATION,
                         "position_m": position, "yaw_deg": -90.0})
        approved[image] = {"status": "approved", "mask": f"roi_masks/{name}.png"}
    (root / "manifest.jsonl").write_text("\n".join(map(json.dumps, manifest)), encoding="utf-8")
    (root / "roi_approved.json").write_text(json.dumps(approved), encoding="utf-8")
    return root


class LiveRoiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def match(self, x: float, yaw: float = -90.0) -> tuple[np.ndarray | None, dict]:
        references = load_references(self.root)
        return match_roi(FRAME, references, "pipe_front", STATION,
                         np.array([x, 2.0, -10.3], np.float32), yaw)

    def test_pose_match_uses_reference_mask_directly(self) -> None:
        write_dataset(self.root, {"a": ([0.0, 2.0, -10.3], (100, 200, 500, 300)),
                                  "b": ([0.3, 2.0, -10.3], (120, 200, 520, 300))})
        mask, status = self.match(0.02)

        self.assertEqual(status["method"], "pose_match")
        self.assertEqual(np.count_nonzero(mask), 400 * 100)

    def test_between_references_intersects_masks_without_camera_images(self) -> None:
        write_dataset(self.root, {"a": ([0.0, 2.0, -10.3], (100, 200, 500, 300)),
                                  "b": ([0.3, 2.0, -10.3], (120, 200, 520, 300))})
        mask, status = self.match(0.15)

        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["method"], "mask_intersection")
        self.assertEqual(np.count_nonzero(mask), (500 - 120) * 100)

    def test_single_reference_falls_back_to_nearest_mask(self) -> None:
        write_dataset(self.root, {"a": ([0.0, 2.0, -10.3], (100, 200, 500, 300))})
        _, status = self.match(0.2)

        self.assertEqual(status["method"], "nearest_mask")

    def test_far_pose_is_unavailable(self) -> None:
        write_dataset(self.root, {"a": ([0.0, 2.0, -10.3], (100, 200, 500, 300))})
        mask, status = self.match(0.8)

        self.assertIsNone(mask)
        self.assertEqual(status["status"], "reference_unavailable")

    def test_disjoint_masks_report_too_small_roi(self) -> None:
        write_dataset(self.root, {"a": ([0.0, 2.0, -10.3], (0, 0, 100, 100)),
                                  "b": ([0.3, 2.0, -10.3], (300, 300, 400, 400))})
        mask, status = self.match(0.15)

        self.assertIsNone(mask)
        self.assertEqual(status["status"], "roi_too_small")


if __name__ == "__main__":
    unittest.main()
