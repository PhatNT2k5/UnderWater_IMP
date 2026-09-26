"""Confirm moving defects without joining unrelated camera regions."""
from __future__ import annotations

import unittest

from auv_inspection.patchcore_data.alerts import AlertTracker, Candidate


def candidate(x: float) -> Candidate:
    return Candidate((int(x), 100, 3, 3), (x, 101.5), 60.0, 9)


class AlertTrackerTests(unittest.TestCase):
    def test_consistent_fast_camera_motion_confirms_once(self) -> None:
        tracker = AlertTracker()
        self.assertEqual(tracker.step("pipe_front", 0, [candidate(100)]), [])
        self.assertEqual(tracker.step("pipe_front", 10, [candidate(195)]), [])
        self.assertEqual(len(tracker.step("pipe_front", 20, [candidate(290)])), 1)
        self.assertEqual(tracker.step("pipe_front", 30, [candidate(385)]), [])

    def test_unrelated_jump_and_category_change_do_not_confirm(self) -> None:
        tracker = AlertTracker()
        tracker.step("pipe_front", 0, [candidate(100)])
        tracker.step("pipe_front", 10, [candidate(195)])
        self.assertEqual(tracker.step("pipe_front", 20, [candidate(400)]), [])
        self.assertEqual(tracker.step("pier_0", 30, [candidate(495)]), [])


if __name__ == "__main__":
    unittest.main()
