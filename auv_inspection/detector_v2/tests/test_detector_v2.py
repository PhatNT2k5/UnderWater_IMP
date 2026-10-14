"""Detector v2 (P4): token geometry, nearest-neighbour scoring and bank data rules, no weights needed."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import numpy as np
import torch

from auv_inspection.detector_v2 import build_bank, scorer, transforms
from auv_inspection.detector_v2.features import PATCH_PX, input_size, roi_cells


class FeatureGeometryTests(unittest.TestCase):
    def test_input_is_whole_patches_close_to_the_scaled_frame(self) -> None:
        self.assertEqual(input_size(480, 640, 1.0), (476, 644))
        height, width = input_size(480, 640, 2.0)
        self.assertEqual((height % PATCH_PX, width % PATCH_PX), (0, 0))
        self.assertLessEqual(abs(height - 960), PATCH_PX // 2)
        self.assertLessEqual(abs(width - 1280), PATCH_PX // 2)

    def test_roi_cells_follow_the_roi_and_erosion(self) -> None:
        roi = np.zeros((480, 640), np.uint8)
        roi[100:380, :] = 255
        cells = roi_cells(roi, (34, 46))
        self.assertTrue(cells[17].all())
        self.assertFalse(cells[2].any())
        eroded = roi_cells(roi, (34, 46), erosion_px=40)
        self.assertLess(eroded.sum(), cells.sum())


class ScorerTests(unittest.TestCase):
    def test_distance_is_one_minus_best_cosine_across_bank_chunks(self) -> None:
        bank = torch.eye(4)
        tokens = torch.tensor([[1.0, 0, 0, 0], [0, 0, 0, 1.0], [0.6, 0.8, 0, 0]])
        with mock.patch.object(scorer, "BANK_CHUNK", 1):
            distance = scorer.nearest_distance(tokens, bank)
        np.testing.assert_allclose(distance.numpy(), [0.0, 0.0, 0.2], atol=1e-6)
        with self.assertRaises(ValueError):
            scorer.nearest_distance(tokens, torch.empty((0, 4)))

    def test_score_map_has_camera_size_and_nan_outside_roi(self) -> None:
        tokens = torch.nn.functional.normalize(torch.ones(4, 6, 3), dim=-1)
        tokens[1, 2] = torch.tensor([1.0, 0.0, 0.0])           # one token unlike the bank
        bank = torch.nn.functional.normalize(torch.ones(1, 3), dim=-1)
        roi = np.zeros((480, 640), np.uint8)
        roi[:, :320] = 255
        detector = scorer.DinoScorer(extractor=None, banks={"pipe_front": bank})
        with mock.patch.object(scorer, "frame_tokens", return_value=tokens):
            scores = detector(np.zeros((480, 640, 3), np.uint8), roi, "pipe_front")
        self.assertEqual(scores.shape, (480, 640))
        self.assertTrue(np.isnan(scores[:, 320:]).all())
        self.assertGreater(float(np.nanmax(scores)), 0.3)
        self.assertAlmostEqual(float(scores[440, 20]), 0.0, places=5)
        with self.assertRaises(ValueError):
            detector(np.zeros((480, 640, 3), np.uint8), roi, "pier_0")

    def test_only_v2_configs_are_loaded(self) -> None:
        with TemporaryDirectory() as folder:
            path = Path(folder)
            self.assertFalse(scorer.is_v2_model(path))
            (path / "config.json").write_text(json.dumps({"model": "PatchCore"}), encoding="utf-8")
            self.assertFalse(scorer.is_v2_model(path))
            with self.assertRaises(ValueError):
                scorer.load_scorer(path, torch.device("cpu"))


class TransformTests(unittest.TestCase):
    def test_nuisance_projection_removes_the_nuisance_direction_only(self) -> None:
        rng = np.random.default_rng(0)
        noise = torch.zeros(500, 6, dtype=torch.float64)
        noise[:, 0] = torch.from_numpy(rng.normal(0, 3.0, 500))   # environment moves axis 0
        noise[:, 1:] = torch.from_numpy(rng.normal(0, 0.1, (500, 5)))
        transform, explained = transforms.nuisance_projection(noise.T @ noise / 500, 1)
        self.assertGreater(explained, 0.9)
        projected = transform.apply(torch.tensor([[1.0, 1.0, 0, 0, 0, 0]]))
        self.assertLess(abs(float(projected[0, 0])), 1e-2)              # nuisance component removed
        self.assertAlmostEqual(float(projected[0, 1]), 1.0, places=3)    # orthogonal component kept
        state = transforms.from_state(transform.state())
        self.assertEqual(state.metric, "cosine")

    def test_mahalanobis_whitening_gives_unit_covariance(self) -> None:
        rng = np.random.default_rng(1)
        bank = torch.from_numpy(rng.normal(0, 1, (4000, 4)) * [5.0, 1.0, 0.2, 2.0]).float()
        transform = transforms.mahalanobis_whitening(bank, shrinkage=0.0)
        whitened = transform.apply(bank).double()
        covariance = torch.cov(whitened.T)
        np.testing.assert_allclose(covariance.numpy(), np.eye(4), atol=0.08)
        self.assertEqual(transform.metric, "euclidean")
        with self.assertRaises(ValueError):
            transforms.mahalanobis_whitening(bank, shrinkage=1.0)

    def test_euclidean_distance_across_bank_chunks(self) -> None:
        bank = torch.tensor([[0.0, 0.0], [3.0, 4.0], [10.0, 0.0]])
        with mock.patch.object(scorer, "BANK_CHUNK", 1):
            distance = scorer.nearest_distance(torch.tensor([[3.0, 0.0], [3.0, 4.0]]), bank, "euclidean")
        np.testing.assert_allclose(distance.numpy(), [3.0, 0.0], atol=1e-5)
        with self.assertRaises(ValueError):
            scorer.nearest_distance(bank, bank, "manhattan")


class BankRuleTests(unittest.TestCase):
    def write_capture(self, root: Path, role: str, profile: str) -> Path:
        root.mkdir()
        (root / "frames.jsonl").write_text("", encoding="utf-8")
        (root / "report.json").write_text(json.dumps({
            "scene_state": "clean", "dataset_role": role, "route_completed": True,
            "conditions": {"profile": profile}}), encoding="utf-8")
        return root

    def test_only_clean_train_profile_train_captures_enter_a_bank(self) -> None:
        with TemporaryDirectory() as folder:
            good = self.write_capture(Path(folder) / "train", "train", "train")
            self.assertEqual(build_bank.load_train_capture(good)[0], [])
            for name, role, profile in (("cal", "calibration", "train"), ("held", "train", "heldout")):
                with self.assertRaises(ValueError):
                    build_bank.load_train_capture(self.write_capture(Path(folder) / name, role, profile))

    def test_augmentation_adds_one_severity_one_copy(self) -> None:
        frame = np.full((480, 640, 3), 120, np.uint8)
        rng = np.random.default_rng(0)
        self.assertEqual(len(build_bank.frame_variants(frame, 10, False, rng)), 1)
        calls = []
        with mock.patch.object(build_bank, "apply_degradations",
                               side_effect=lambda image, items, seed: calls.append(items) or image):
            variants = build_bank.frame_variants(frame, 10, True, rng)
        self.assertEqual([name for name, _ in variants][0], "none")
        self.assertEqual(len(variants), 2)
        self.assertEqual(calls[0][0].severity, build_bank.AUGMENT_SEVERITY)


if __name__ == "__main__":
    unittest.main()
