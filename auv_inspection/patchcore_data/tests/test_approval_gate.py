"""Ensure a passed evaluation applies only to unchanged live artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from auv_inspection.patchcore_data.approval_gate import (
    MODEL_FILES, REFERENCE_FILES, approval_matches, file_sha256,
    model_fingerprint, reference_fingerprint, registered_candidate_matches,
)


class ApprovalGateTests(unittest.TestCase):
    def test_rejects_changed_threshold_model_or_reference(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / "model"
            reference = root / "reference"
            masks = reference / "roi_masks"
            model.mkdir()
            masks.mkdir(parents=True)
            for name in MODEL_FILES:
                (model / name).write_bytes(name.encode("ascii"))
            for name in REFERENCE_FILES:
                (reference / name).write_bytes(name.encode("ascii"))
            (masks / "frame.png").write_bytes(b"mask")
            thresholds = root / "thresholds.json"
            thresholds.write_text("{}", encoding="utf-8")
            evaluation = root / "evaluation.json"
            result = {
                "model_dir": str(model),
                "reference_dataset": str(reference),
                "thresholds": str(thresholds),
                "model_sha256": model_fingerprint(model),
                "reference_sha256": reference_fingerprint(reference),
                "thresholds_sha256": file_sha256(thresholds),
                "acceptance": {
                    "passed": True,
                    "all_inventory_observable": True,
                    "recall_at_least_95_percent": True,
                    "small_or_thin_recall_at_least_90_percent": True,
                    "false_alerts_at_most_2": True,
                },
            }
            evaluation.write_text(json.dumps(result), encoding="utf-8")
            self.assertTrue(approval_matches(model, reference, thresholds, evaluation))

            thresholds.write_text('{"changed": true}', encoding="utf-8")
            self.assertFalse(approval_matches(model, reference, thresholds, evaluation))
            thresholds.write_text("{}", encoding="utf-8")

            bank = model / "pier_0_bank.pt"
            bank.write_bytes(b"different bank")
            self.assertFalse(approval_matches(model, reference, thresholds, evaluation))
            bank.write_bytes(b"pier_0_bank.pt")

            (masks / "frame.png").write_bytes(b"different mask")
            self.assertFalse(approval_matches(model, reference, thresholds, evaluation))
            (masks / "frame.png").write_bytes(b"mask")

            result["acceptance"]["all_inventory_observable"] = False
            evaluation.write_text(json.dumps(result), encoding="utf-8")
            self.assertFalse(approval_matches(model, reference, thresholds, evaluation))


    def test_registered_candidate_needs_its_directory_and_every_hash(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / "out" / "v2"
            model.mkdir(parents=True)
            for name in ("config.json", "pixel_thresholds.json"):
                (model / name).write_text(name, encoding="utf-8")
            registration = root / "registration.json"
            registration.write_text(json.dumps({"candidate": {
                "model_dir": "out/v2",
                "sha256": {name: file_sha256(model / name) for name in ("config.json", "pixel_thresholds.json")},
            }}), encoding="utf-8")
            self.assertTrue(registered_candidate_matches(model, registration, root))
            self.assertFalse(registered_candidate_matches(root / "out", registration, root))

            (model / "pixel_thresholds.json").write_text("changed", encoding="utf-8")
            self.assertFalse(registered_candidate_matches(model, registration, root))
            (model / "pixel_thresholds.json").unlink()
            self.assertFalse(registered_candidate_matches(model, registration, root))
            self.assertFalse(registered_candidate_matches(model, root / "missing.json", root))

if __name__ == "__main__":
    unittest.main()
