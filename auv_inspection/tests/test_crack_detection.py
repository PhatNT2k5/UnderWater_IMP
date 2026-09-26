import unittest

import cv2
import numpy as np

from auv_inspection.crack_detection import CrackTracker, analyze_frame


def create_pipe_frame() -> np.ndarray:
    frame = np.full((480, 640, 3), (145, 100, 55), dtype=np.uint8)
    frame[175:390] = (135, 110, 85)
    return frame


class CrackDetectionTests(unittest.TestCase):
    def test_rejects_granular_lamp_glare(self) -> None:
        frame = create_pipe_frame()
        rng = np.random.default_rng(7)
        texture = rng.normal(0, 6, (95, 180)).astype(np.int16)
        grid_y, grid_x = np.mgrid[:95, :180]
        glare = np.uint8(
            145 * np.exp(-(((grid_x - 90) / 58) ** 2 + ((grid_y - 48) / 27) ** 2))
        )
        for channel in range(3):
            patch = frame[245:340, 230:410, channel].astype(np.int16)
            frame[245:340, 230:410, channel] = np.uint8(
                np.clip(patch + glare + texture, 0, 255)
            )

        self.assertEqual(analyze_frame(frame).candidates, ())

    def test_detects_branching_dark_crack(self) -> None:
        frame = create_pipe_frame()
        points = ((320, 245), (300, 275), (330, 300), (290, 325))
        for start, end in zip(points, points[1:]):
            cv2.line(frame, start, end, (2, 2, 2), 9)
        cv2.line(frame, (305, 274), (260, 290), (2, 2, 2), 7)
        cv2.line(frame, (329, 299), (380, 278), (2, 2, 2), 7)

        analysis = analyze_frame(frame)

        self.assertTrue(analysis.candidates)
        self.assertGreaterEqual(analysis.candidates[0].area_px, 500)

    def test_detects_broad_dark_damage(self) -> None:
        frame = create_pipe_frame()
        damage = np.array(
            [[285, 265], [335, 245], [370, 280], [345, 325], [292, 315]],
            dtype=np.int32,
        )
        cv2.fillPoly(frame, [damage], (1, 1, 1))

        self.assertTrue(analyze_frame(frame).candidates)

    def test_detects_large_dark_hole(self) -> None:
        frame = create_pipe_frame()
        hole = np.array(
            [[245, 205], [315, 180], [390, 215], [420, 295],
             [370, 360], [285, 350], [225, 285]],
            dtype=np.int32,
        )
        cv2.fillPoly(frame, [hole], (1, 1, 1))
        cv2.line(frame, (245, 205), (205, 180), (1, 1, 1), 9)
        cv2.line(frame, (370, 350), (415, 390), (1, 1, 1), 9)

        analysis = analyze_frame(frame)
        candidate = analysis.candidates[0]

        self.assertGreater(candidate.area_px, 10_000)
        tracker = CrackTracker()
        self.assertIsNone(tracker.update(analysis))
        self.assertIsNone(tracker.update(analysis))
        self.assertEqual(tracker.update(analysis), candidate)

    def test_rejects_uniformly_dark_frame(self) -> None:
        frame = np.full((480, 640, 3), 12, dtype=np.uint8)

        self.assertEqual(analyze_frame(frame).candidates, ())

    def test_rejects_tall_pipe_flange_edge(self) -> None:
        frame = create_pipe_frame()
        cv2.rectangle(frame, (310, 220), (338, 380), (15, 15, 15), -1)
        cv2.rectangle(frame, (316, 220), (332, 380), (95, 95, 95), -1)

        self.assertEqual(analyze_frame(frame).candidates, ())

    def test_rejects_long_pipe_boundary(self) -> None:
        frame = create_pipe_frame()
        cv2.line(frame, (230, 230), (410, 230), (5, 5, 5), 12)

        self.assertEqual(analyze_frame(frame).candidates, ())


if __name__ == "__main__":
    unittest.main()
