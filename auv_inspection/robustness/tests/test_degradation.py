"""Degradations must be reproducible and get monotonically worse with severity."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import cv2
import numpy as np

from auv_inspection.robustness.degradation import (
    PIPELINE_ORDER, SEVERITY_LEVELS, Degradation, apply_degradations, degrade_folder)


def textured_frame() -> np.ndarray:
    """Lit concrete-like texture with a dark crack, fully deterministic."""
    rng = np.random.default_rng(1234)
    base = cv2.GaussianBlur(rng.uniform(80, 200, (480, 640)).astype(np.float32), (0, 0), 2.0)
    yy, xx = np.indices((480, 640))
    spot = np.exp(-(((xx - 320) / 260.0) ** 2 + ((yy - 240) / 180.0) ** 2))
    gray = base * (0.4 + 0.6 * spot)
    cv2.line(gray, (150, 350), (480, 150), 15.0, 2)
    return np.repeat(np.clip(gray, 0, 255).astype(np.uint8)[..., None], 3, axis=2)


def series(factor: str, frame: np.ndarray) -> list[np.ndarray]:
    return [apply_degradations(frame, [Degradation(factor, level)], seed=3)
            for level in SEVERITY_LEVELS]


def strictly_increasing(values: list[float]) -> bool:
    return all(later > earlier for earlier, later in zip(values, values[1:]))


class DegradationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = textured_frame()

    def test_same_seed_is_reproducible_and_seed_changes_stochastic_output(self) -> None:
        combo = [Degradation("turbidity", 3), Degradation("marine_snow", 3),
                 Degradation("sensor_noise", 2)]
        first = apply_degradations(self.frame, combo, seed=5)
        self.assertTrue(np.array_equal(first, apply_degradations(self.frame, combo, seed=5)))
        self.assertFalse(np.array_equal(first, apply_degradations(self.frame, combo, seed=6)))

    def test_every_factor_keeps_shape_and_dtype(self) -> None:
        for factor in PIPELINE_ORDER:
            output = apply_degradations(self.frame, [Degradation(factor, 5)], seed=0)
            self.assertEqual(output.shape, self.frame.shape, factor)
            self.assertEqual(output.dtype, np.uint8, factor)

    def test_invalid_requests_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            apply_degradations(self.frame, [Degradation("fog", 1)], seed=0)
        with self.assertRaises(ValueError):
            apply_degradations(self.frame, [Degradation("jpeg", 1), Degradation("jpeg", 2)], seed=0)
        with self.assertRaises(ValueError):
            apply_degradations(self.frame, [Degradation("jpeg", 6)], seed=0)
        with self.assertRaises(ValueError):
            apply_degradations(self.frame[..., 0], [Degradation("jpeg", 1)], seed=0)

    def test_turbidity_lowers_contrast_with_severity(self) -> None:
        contrast = [float(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).std())
                    for image in series("turbidity", self.frame)]
        self.assertTrue(strictly_increasing(contrast[::-1]), contrast)

    def test_turbidity_is_stronger_for_farther_pixels(self) -> None:
        depth = np.full(self.frame.shape[:2], 1.0, np.float32)
        depth[:, 320:] = 4.0
        output = apply_degradations(self.frame, [Degradation("turbidity", 3)], seed=0, depth_m=depth)
        near = float(cv2.cvtColor(output[:, 100:300], cv2.COLOR_BGR2GRAY).std())
        far = float(cv2.cvtColor(output[:, 340:540], cv2.COLOR_BGR2GRAY).std())
        self.assertGreater(near, far)

    def test_blur_factors_remove_detail_with_severity(self) -> None:
        for factor in ("defocus", "motion_blur"):
            sharpness = [float(cv2.Laplacian(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
                         for image in series(factor, self.frame)]
            self.assertTrue(strictly_increasing(sharpness[::-1]), (factor, sharpness))

    def test_illumination_darkens_with_severity(self) -> None:
        brightness = [float(image.mean()) for image in series("illumination", self.frame)]
        self.assertTrue(strictly_increasing(brightness[::-1]), brightness)

    def test_noise_particles_and_compression_grow_with_severity(self) -> None:
        reference = self.frame.astype(np.float32)
        for factor in ("sensor_noise", "marine_snow", "jpeg"):
            error = [float(np.abs(image.astype(np.float32) - reference).mean())
                     for image in series(factor, self.frame)]
            self.assertTrue(strictly_increasing(error), (factor, error))

    def test_folder_degradation_records_parameters_and_refuses_overwrite(self) -> None:
        with TemporaryDirectory() as temp:
            source, destination = Path(temp) / "src", Path(temp) / "dst"
            (source / "pipe_front").mkdir(parents=True)
            for index in range(2):
                cv2.imwrite(str(source / "pipe_front" / f"frame_{index}.png"), self.frame)
            record = degrade_folder(source, destination, [Degradation("turbidity", 2)], seed=9)

            self.assertEqual(record["images"], 2)
            self.assertTrue((destination / "pipe_front" / "frame_1.png").is_file())
            saved = json.loads((destination / "degradation.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["degradations"], [{"factor": "turbidity", "severity": 2}])
            with self.assertRaises(FileExistsError):
                degrade_folder(source, destination, [Degradation("turbidity", 2)], seed=9)


if __name__ == "__main__":
    unittest.main()
