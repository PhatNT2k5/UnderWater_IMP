"""Guard calibration and test evaluation against incomplete damage labels."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from auv_inspection.patchcore_data.calibrate import load_labels


class LabelIntegrityTests(unittest.TestCase):
    def test_visible_defect_requires_reviewed_geometry(self) -> None:
        with TemporaryDirectory() as directory:
            dataset = Path(directory)
            (dataset / "manifest.jsonl").write_text(
                json.dumps({"image": "pipe_front/frame.png", "category": "pipe_front"}) + "\n",
                encoding="utf-8",
            )
            labels = {
                "defects": {"crack_1": {"category": "pipe_front", "size_class": "thin"}},
                "frames": {"pipe_front/frame.png": {"crack_1": {
                    "visibility": "visible", "shape": None, "points": [],
                    "review_status": "reviewed",
                }}},
            }
            label_path = dataset / "damage_labels.json"
            label_path.write_text(json.dumps(labels), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no geometry"):
                load_labels(dataset)
            labels["frames"]["pipe_front/frame.png"]["crack_1"].update(
                shape="polyline", points=[[10, 10], [12, 15]],
            )
            label_path.write_text(json.dumps(labels), encoding="utf-8")
            self.assertEqual(load_labels(dataset)["defects"], labels["defects"])
            labels["locked"] = True
            label_path.write_text(json.dumps(labels), encoding="utf-8")
            (dataset / "label_lock.json").write_text(json.dumps({
                "labels_sha256": hashlib.sha256(label_path.read_bytes()).hexdigest(),
            }), encoding="utf-8")
            load_labels(dataset, require_locked=True)
            labels["frames"]["pipe_front/frame.png"]["crack_1"]["points"][1] = [30, 30]
            label_path.write_text(json.dumps(labels), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after locking"):
                load_labels(dataset, require_locked=True)


if __name__ == "__main__":
    unittest.main()
