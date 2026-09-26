"""Geometry checks for the fixed route; these do not launch Unreal."""
import unittest
from math import cos, dist, radians, sin

from inspection_route import ROUTE, advance_station, angle_delta


class InspectionRouteTests(unittest.TestCase):
    def test_station_advances_without_waiting_at_each_point(self) -> None:
        route = [
            ("a", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            ("b", [0.8, 0.0, 0.0, 0.0, 0.0, 0.0]),
            ("c", [1.6, 0.0, 0.0, 0.0, 0.0, 0.0]),
            ("finish", [2.4, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ]
        station, passed = advance_station(route, 0, [0.0, 0.0, 0.0])
        self.assertEqual(station, 2)
        self.assertEqual(passed, ["a", "b"])
        station, passed = advance_station(route, station, [2.4, 0.0, 0.0])
        self.assertEqual(station, 3)
        self.assertEqual(passed, ["c"])

    def test_short_steps_and_unique_names(self) -> None:
        self.assertEqual(len(ROUTE), len({name for name, _ in ROUTE}))
        for (_, a), (_, b) in zip(ROUTE, ROUTE[1:]):
            self.assertLessEqual(dist(a[:3], b[:3]), 0.80001)

    def test_segments_clear_structure_bounds(self) -> None:
        # Conservative axis-aligned bounds include flanges and pier footings.
        # Expand by 0.65 m for the AUV body and position tolerance.
        boxes = [((-18.01, -0.8, -12.4), (15.11, 0.8, -9.74))]
        for x in (-10.0, 10.0):
            boxes.extend([
                ((x - 0.95, -7.45, -10.4), (x + 0.95, -5.55, 1.6)),
                ((x - 2.0, -8.5, -12.0), (x + 2.0, -4.5, -10.4)),
            ])
        for (_, a), (name, b) in zip(ROUTE, ROUTE[1:]):
            for step in range(21):
                p = [a[i] + (b[i] - a[i]) * step / 20 for i in range(3)]
                for low, high in boxes:
                    intersects = all(low[i] - 0.65 <= p[i] <= high[i] + 0.65 for i in range(3))
                    self.assertFalse(intersects, (name, p))

    def test_camera_faces_pipe_and_piers(self) -> None:
        for name, pose in ROUTE:
            x, y, _, _, _, yaw = pose
            forward = (cos(radians(yaw)), sin(radians(yaw)))
            if 'pipe_front_scan' in name:
                self.assertAlmostEqual(y, 2.0)
                self.assertAlmostEqual(yaw, -90.0)
            elif 'pipe_back_scan' in name:
                self.assertAlmostEqual(y, -2.0)
                self.assertAlmostEqual(yaw, 90.0)
            elif '_orbit_' in name:
                center_x = -10.0 if name.startswith('pier_0_') else 10.0
                direction = (center_x - x, -6.5 - y)
                self.assertGreater(sum(a * b for a, b in zip(forward, direction)) / dist((0, 0), direction), 0.99)

    def test_both_pipe_ends_and_complete_pier_rings(self) -> None:
        for side in ('front', 'back'):
            samples = [p for name, p in ROUTE if name.startswith(f'pipe_{side}_')]
            self.assertLessEqual(min(p[0] for p in samples), -18.01)
            self.assertGreaterEqual(max(p[0] for p in samples), 15.11)
        for pier in range(2):
            for level in range(4):
                samples = [p for name, p in ROUTE if name.startswith(f'pier_{pier}_level_{level}_orbit_')]
                self.assertEqual(len(samples), 24)
                self.assertGreater(max(p[1] for p in samples) - min(p[1] for p in samples), 5.5)
        self.assertEqual(angle_delta(-179, 179), 2)


if __name__ == '__main__':
    unittest.main()
