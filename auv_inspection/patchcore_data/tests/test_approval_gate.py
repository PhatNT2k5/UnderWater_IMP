"""Ensure a passed evaluation applies only to unchanged live artifacts and scoring code."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from auv_inspection.patchcore_data.approval_gate import (
    MODEL_FILES, REFERENCE_FILES, SCORING_CODE, approval_matches, code_hashes, code_matches,
    file_sha256, model_fingerprint, reference_fingerprint, registered_candidate_matches,
)


def write_code(root: Path, files: tuple[str, ...] = SCORING_CODE) -> None:
    for name in files:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(f"# {name}\nvalue = 1\n".encode("ascii"))


class ApprovalGateTests(unittest.TestCase):
    def test_rejects_changed_threshold_model_reference_or_code(self) -> None:
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
            code_root = root / "repo"
            write_code(code_root)
            evaluation = root / "evaluation.json"
            result = {
                "model_dir": str(model),
                "reference_dataset": str(reference),
                "thresholds": str(thresholds),
                "model_sha256": model_fingerprint(model),
                "reference_sha256": reference_fingerprint(reference),
                "thresholds_sha256": file_sha256(thresholds),
                "code_sha256": code_hashes(code_root),
                "acceptance": {
                    "passed": True,
                    "all_inventory_observable": True,
                    "recall_at_least_95_percent": True,
                    "small_or_thin_recall_at_least_90_percent": True,
                    "false_alerts_at_most_2": True,
                },
            }
            evaluation.write_text(json.dumps(result), encoding="utf-8")
            self.assertTrue(approval_matches(model, reference, thresholds, evaluation, code_root))

            thresholds.write_text('{"changed": true}', encoding="utf-8")
            self.assertFalse(approval_matches(model, reference, thresholds, evaluation, code_root))
            thresholds.write_text("{}", encoding="utf-8")

            bank = model / "pier_0_bank.pt"
            bank.write_bytes(b"different bank")
            self.assertFalse(approval_matches(model, reference, thresholds, evaluation, code_root))
            bank.write_bytes(b"pier_0_bank.pt")

            (masks / "frame.png").write_bytes(b"different mask")
            self.assertFalse(approval_matches(model, reference, thresholds, evaluation, code_root))
            (masks / "frame.png").write_bytes(b"mask")

            service = code_root / "auv_inspection/patchcore_data/live_service.py"
            original = service.read_bytes()
            service.write_bytes(original + b"value = 2\n")
            self.assertFalse(approval_matches(model, reference, thresholds, evaluation, code_root))
            service.write_bytes(original)
            self.assertTrue(approval_matches(model, reference, thresholds, evaluation, code_root))

            # An evaluation from before code hashing (D11) no longer approves anything.
            evaluation.write_text(json.dumps({k: v for k, v in result.items() if k != "code_sha256"}),
                                  encoding="utf-8")
            self.assertFalse(approval_matches(model, reference, thresholds, evaluation, code_root))

            result["acceptance"]["all_inventory_observable"] = False
            evaluation.write_text(json.dumps(result), encoding="utf-8")
            self.assertFalse(approval_matches(model, reference, thresholds, evaluation, code_root))

    def test_code_hash_ignores_line_endings_and_needs_every_required_file(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = ("a.py", "pkg/b.py")
            write_code(root, files)
            recorded = code_hashes(root, files)
            path = root / "a.py"
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
            self.assertTrue(code_matches(recorded, root, files))
            self.assertFalse(code_matches({"a.py": recorded["a.py"]}, root, files))
            self.assertFalse(code_matches(None, root, files))
            (root / "pkg/b.py").write_text("value = 3\n", encoding="ascii")
            self.assertFalse(code_matches(recorded, root, files))

    def test_registered_candidate_needs_its_directory_every_hash_and_the_code(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / "out" / "v2"
            model.mkdir(parents=True)
            for name in ("config.json", "pixel_thresholds.json"):
                (model / name).write_text(name, encoding="utf-8")
            code = ("scorer.py",)
            write_code(root, code)
            registration = root / "registration.json"
            content = {"candidate": {
                "model_dir": "out/v2",
                "sha256": {name: file_sha256(model / name) for name in ("config.json", "pixel_thresholds.json")},
            }, "code_sha256": code_hashes(root, code)}
            registration.write_text(json.dumps(content), encoding="utf-8")
            self.assertTrue(registered_candidate_matches(model, registration, root, code))
            self.assertFalse(registered_candidate_matches(root / "out", registration, root, code))

            (root / "scorer.py").write_text("value = 2\n", encoding="ascii")
            self.assertFalse(registered_candidate_matches(model, registration, root, code))
            write_code(root, code)
            registration.write_text(json.dumps({"candidate": content["candidate"]}), encoding="utf-8")
            self.assertFalse(registered_candidate_matches(model, registration, root, code))
            registration.write_text(json.dumps(content), encoding="utf-8")

            (root / "scorer.py").write_text("value = 2\n", encoding="ascii")    # a later, proven revision
            revision = {"code_sha256": code_hashes(root, code),
                        "equivalence": {"identical": True, "runs": 84, "runs_compared": 84}}
            registration.write_text(json.dumps({**content, "code_revisions": [revision]}), encoding="utf-8")
            self.assertTrue(registered_candidate_matches(model, registration, root, code))
            for evidence in ({"identical": False, "runs": 84, "runs_compared": 84},
                             {"identical": True, "runs": 84, "runs_compared": 80},
                             {"identical": True, "runs": 0, "runs_compared": 0}):
                registration.write_text(json.dumps({**content, "code_revisions": [
                    {**revision, "equivalence": evidence}]}), encoding="utf-8")
                self.assertFalse(registered_candidate_matches(model, registration, root, code))
            write_code(root, code)
            registration.write_text(json.dumps(content), encoding="utf-8")

            (model / "pixel_thresholds.json").write_text("changed", encoding="utf-8")
            self.assertFalse(registered_candidate_matches(model, registration, root, code))
            (model / "pixel_thresholds.json").unlink()
            self.assertFalse(registered_candidate_matches(model, registration, root, code))
            self.assertFalse(registered_candidate_matches(model, root / "missing.json", root, code))


if __name__ == "__main__":
    unittest.main()
