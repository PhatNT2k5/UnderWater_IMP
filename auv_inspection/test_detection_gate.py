import unittest

import numpy as np

from run_inspection import is_pipe_view


class DetectionGateTests(unittest.TestCase):
    def test_front_scan_004_is_inside_full_pipe_span(self) -> None:
        location = np.array([-16.90, 2.06, -10.23])

        self.assertTrue(is_pipe_view("auto", "pipe_front_scan_004", location))

    def test_auto_mode_ignores_non_scan_station(self) -> None:
        location = np.array([-16.90, 2.06, -10.23])

        self.assertFalse(is_pipe_view("auto", "pipe_front_start_006", location))

    def test_view_outside_pipe_span_is_rejected(self) -> None:
        location = np.array([-19.0, 2.0, -10.3])

        self.assertFalse(is_pipe_view("auto", "pipe_front_scan_001", location))


if __name__ == "__main__":
    unittest.main()
