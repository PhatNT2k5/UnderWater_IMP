"""P3 image-quality measurements respond to the factors they are meant to describe."""
from __future__ import annotations

import unittest

import cv2
import numpy as np

from auv_inspection.robustness.quality import measure


def textured() -> np.ndarray:
    rng = np.random.default_rng(0)
    grey = cv2.GaussianBlur(rng.integers(40, 200, (480, 640)).astype(np.uint8), (5, 5), 0)
    return cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR)


class QualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.roi = np.zeros((480, 640), np.uint8)
        self.roi[80:400, 80:560] = 255

    def test_blur_lowers_sharpness(self) -> None:
        frame = textured()
        self.assertLess(measure(cv2.GaussianBlur(frame, (9, 9), 3), self.roi)["sharpness"],
                        measure(frame, self.roi)["sharpness"])

    def test_dark_frame_has_low_brightness_and_contrast(self) -> None:
        frame = textured()
        dark = (frame * 0.3).astype(np.uint8)
        bright, dim = measure(frame, self.roi), measure(dark, self.roi)
        self.assertLess(dim["brightness"], bright["brightness"])
        self.assertLess(dim["contrast"], bright["contrast"])

    def test_small_bright_blobs_count_as_particles(self) -> None:
        frame = np.full((480, 640, 3), 60, np.uint8)
        self.assertEqual(measure(frame, self.roi)["particles_per_100k_px"], 0)
        for x in range(50, 600, 40):
            cv2.circle(frame, (x, 240), 2, (230, 230, 230), -1)
        self.assertGreater(measure(frame, self.roi)["particles_per_100k_px"], 3)

    def test_empty_or_mismatched_roi_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            measure(textured(), np.zeros((480, 640), np.uint8))
        with self.assertRaises(ValueError):
            measure(textured(), np.zeros((10, 10), np.uint8))


if __name__ == "__main__":
    unittest.main()
