"""Evaluation statistics and physical-defect matching."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from robustness.defect_inventory import (  # noqa: E402
    Defect, defects_in_view, load_inventory, locate_box, match_defect)
from robustness.metrics import rate_per_100m, surveyed_length_m, wilson_interval  # noqa: E402

INVENTORY = Path(__file__).resolve().parents[1] / "inventories" / "map_A.json"


class MetricsTests(unittest.TestCase):
    def test_wilson_interval_matches_reference_values(self) -> None:
        low, high = wilson_interval(0, 10)
        self.assertAlmostEqual(low, 0.0)
        self.assertAlmostEqual(high, 0.2775, places=3)
        low, high = wilson_interval(5, 10)
        self.assertAlmostEqual(low, 0.2366, places=3)
        self.assertAlmostEqual(high, 0.7634, places=3)
        self.assertEqual(wilson_interval(0, 0), (0.0, 1.0))
        with self.assertRaises(ValueError):
            wilson_interval(3, 2)

    def test_surveyed_length_skips_section_jumps(self) -> None:
        positions = [[0, 0, 0], [0.5, 0, 0], [1.0, 0, 0], [20.0, 0, 0], [20.5, 0, 0]]
        self.assertAlmostEqual(surveyed_length_m(positions), 1.5)
        self.assertEqual(rate_per_100m(3, 150.0), 2.0)
        self.assertIsNone(rate_per_100m(1, 0.0))


class InventoryTests(unittest.TestCase):
    def test_map_a_inventory_loads_three_defects(self) -> None:
        inventory = load_inventory(INVENTORY)
        self.assertEqual(len(inventory.defects), 3)
        self.assertTrue(inventory.map_sha256.startswith("daba22ec"))

    def test_alert_box_over_defect_matches_it_and_far_box_does_not(self) -> None:
        defects = (Defect("d1", "pipe_front", np.array([0.0, 0.5, -10.3]), 0.6),)
        camera = np.array([0.0, 2.0, -10.3])
        centre = locate_box([310, 230, 20, 20], camera, -90.0, "pipe_front")
        self.assertEqual(match_defect(centre, "pipe_front", defects), "d1")
        edge = locate_box([600, 230, 20, 20], camera, -90.0, "pipe_front")
        self.assertIsNone(match_defect(edge, "pipe_front", defects))
        self.assertIsNone(match_defect(centre, "pipe_back", defects))
        self.assertIsNone(match_defect(None, "pipe_front", defects))

    def test_long_crack_matches_alerts_anywhere_along_its_segment(self) -> None:
        crack = Defect("c1", "pier_0", np.array([-9.8, -5.55, -8.7]), 0.35, np.array([-10.9, -5.55, -8.0]))
        self.assertEqual(match_defect(np.array([-10.67, -5.55, -8.18]), "pier_0", (crack,)), "c1")
        self.assertIsNone(match_defect(np.array([-10.35, -5.55, -9.4]), "pier_0", (crack,)))
        np.testing.assert_allclose(crack.centre(), [-10.35, -5.55, -8.35])

    def test_defect_visibility_depends_on_camera_position(self) -> None:
        defects = (Defect("d1", "pipe_front", np.array([0.0, 0.5, -10.3]), 0.6),)
        self.assertEqual(defects_in_view(defects, np.array([0.0, 2.0, -10.3]), -90.0, "pipe_front"), ["d1"])
        self.assertEqual(defects_in_view(defects, np.array([5.0, 2.0, -10.3]), -90.0, "pipe_front"), [])


if __name__ == "__main__":
    unittest.main()
