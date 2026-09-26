"""Check that clean capture preserves sensor pixels and route provenance."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_inspection import (
    clean_capture_category, load_preview_rows, rotation_rpy_from_pose,
    save_clean_structure_frame,
)
from inspection_route import ROUTE


class CleanStructureCaptureTests(unittest.TestCase):
    def test_saves_raw_camera_pixels_and_all_structure_categories(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            frame = np.arange(24 * 32 * 3, dtype=np.uint8).reshape(24, 32, 3)
            samples = (
                (30, "pipe_front_scan_004", [-16.9, 2.0, -10.3], "pipe_front"),
                (40, "pipe_back_scan_004", [-16.9, -2.0, -10.3], "pipe_back"),
                (50, "pier_0_level_0_orbit_01_001", [-10.0, -3.7, -9.2], "pier_0"),
                (60, "pier_1_level_3_orbit_24_001", [10.0, -3.7, -9.2], "pier_1"),
            )
            for tick, station, position, expected in samples:
                location = np.array(position)
                category = clean_capture_category(station, location)
                self.assertEqual(category, expected)
                record = save_clean_structure_frame(
                    output, frame, tick, station, location, 45.0, category
                )
                self.assertTrue(np.array_equal(
                    cv2.imread(str(output / record["image"])), frame
                ))
            records = [json.loads(line) for line in
                       (output / "frames.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([record["category"] for record in records],
                             [sample[3] for sample in samples])
            self.assertEqual(records[1]["position_m"], [-16.9, -2.0, -10.3])
            self.assertEqual(records[2]["structure"], "pier")

    def test_excludes_transit_and_pier_entry(self) -> None:
        location = np.array([-10.0, -3.7, -9.2])

        self.assertIsNone(clean_capture_category("transit_pier_front_001", location))
        self.assertIsNone(clean_capture_category("pier_0_level_0_entry_001", location))

    def test_preview_uses_saved_pose_and_rejects_missing_tick(self) -> None:
        with TemporaryDirectory() as temporary:
            capture = Path(temporary)
            frame = np.zeros((24, 32, 3), dtype=np.uint8)
            save_clean_structure_frame(
                capture, frame, 3910, "pier_0_level_2_orbit_04_001",
                np.array([-11.2, -4.6, -4.4]), -44.5, "pier_0",
            )
            rows = load_preview_rows(capture, [3910])
            self.assertEqual(rows[0]["position_m"], [-11.2, -4.6, -4.4])
            self.assertEqual(rows[0]["yaw_deg"], -44.5)
            with self.assertRaisesRegex(ValueError, "Preview ticks not found"):
                load_preview_rows(capture, [3920])

    def test_capture_preserves_full_orientation_for_future_previews(self) -> None:
        pose = np.eye(4)
        yaw = np.deg2rad(-45.0)
        pose[:3, :3] = [
            [np.cos(yaw), -np.sin(yaw), 0.0],
            [np.sin(yaw), np.cos(yaw), 0.0],
            [0.0, 0.0, 1.0],
        ]
        rotation = rotation_rpy_from_pose(pose)
        np.testing.assert_allclose(rotation, [0.0, 0.0, -45.0])
        with TemporaryDirectory() as temporary:
            capture = Path(temporary)
            save_clean_structure_frame(
                capture, np.zeros((24, 32, 3), dtype=np.uint8), 4000,
                "pier_0_level_2_orbit_09_001", np.array([-12.3, -7.2, -4.4]),
                -45.0, "pier_0", rotation,
            )
            self.assertEqual(load_preview_rows(capture, [4000])[0]["rotation_rpy_deg"],
                             [0.0, 0.0, -45.0])

    def test_includes_four_orbit_levels_for_each_pier(self) -> None:
        for pier in (0, 1):
            for level in range(4):
                stations = [
                    (name, pose) for name, pose in ROUTE
                    if name.startswith(f"pier_{pier}_level_{level}_orbit_")
                ]
                self.assertTrue(stations)
                self.assertTrue(all(
                    clean_capture_category(name, np.array(pose[:3])) == f"pier_{pier}"
                    for name, pose in stations
                ))


if __name__ == "__main__":
    unittest.main()
