"""Regression tests from the user's actual front/back robot camera run."""

from pathlib import Path
import unittest

import cv2
import numpy as np

from auv_inspection.crack_detection import analyze_frame


FIXTURES = Path(__file__).parent / "data/pipe_views"
# Manually reviewed bounds of the visible damage, in sensor pixel coordinates.
DAMAGE_BOUNDS = {
    1: (180, 190, 170, 155),
    2: (80, 175, 245, 205),
    3: (65, 185, 275, 160),
}


def load_frame(index: int) -> np.ndarray:
    path = FIXTURES / f"event_{index:03d}.png"
    frame = cv2.imread(str(path))
    if frame is None:
        raise FileNotFoundError(f"Missing camera regression fixture: {path}")
    return frame


def overlaps_damage(box: tuple[int, int, int, int], expected: tuple[int, int, int, int]) -> bool:
    x, y, width, height = box
    ex, ey, ew, eh = expected
    overlap = max(0, min(x + width, ex + ew) - max(x, ex)) * max(
        0, min(y + height, ey + eh) - max(y, ey)
    )
    return overlap >= width * height * 0.5


class CameraRegressionTests(unittest.TestCase):
    def test_preserves_front_hole_and_both_cracks(self) -> None:
        for index, expected in DAMAGE_BOUNDS.items():
            with self.subTest(event=index):
                analysis = analyze_frame(load_frame(index))
                self.assertTrue(analysis.candidates)
                self.assertTrue(overlaps_damage(analysis.candidates[0].bbox, expected))

    def test_rejects_all_eleven_rear_false_alerts(self) -> None:
        for index in range(4, 15):
            with self.subTest(event=index):
                self.assertEqual(analyze_frame(load_frame(index)).candidates, ())

    def test_detects_damage_facing_the_other_direction(self) -> None:
        for index, (x, y, width, height) in DAMAGE_BOUNDS.items():
            with self.subTest(event=index):
                frame = cv2.flip(load_frame(index), 1)
                expected = (frame.shape[1] - x - width, y, width, height)
                analysis = analyze_frame(frame)
                self.assertTrue(analysis.candidates)
                self.assertTrue(overlaps_damage(analysis.candidates[0].bbox, expected))
