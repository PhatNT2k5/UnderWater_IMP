"""Verify the clean-route false-alert budget spans every structure group."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from auv_inspection.patchcore_data.calibrate import calibrate, detect_events, threshold_candidates
from auv_inspection.patchcore_data.model import CATEGORIES


class CalibrationBudgetTests(unittest.TestCase):
    def test_category_without_damage_still_has_threshold_candidates(self) -> None:
        scores = np.ones((8, 8), dtype=np.float32)
        frames = [({"image": "clean.png", "max_score": 1.0}, scores)]
        thresholds = threshold_candidates(frames, frames, {"frames": {}}, "pier_1")
        self.assertTrue(thresholds)
        self.assertGreater(max(thresholds), 1.0)

    def test_weak_thin_defect_is_considered_below_clean_frame_peaks(self) -> None:
        clean = []
        mixed = []
        labels = {"frames": {}}
        for index, tick in enumerate((0, 3, 6)):
            clean_map = np.full((200, 200), -np.inf, np.float32)
            clean_map[20:22, 20 + index * 70:22 + index * 70] = 10.0 + index
            clean.append(({"category": "pipe_front", "tick": tick,
                           "max_score": 10.0 + index}, clean_map))
            image = f"frame_{tick}.png"
            mixed_map = np.full((200, 200), -np.inf, np.float32)
            mixed_map[40:42, 40:42] = 7.0
            mixed.append(({"category": "pipe_front", "tick": tick,
                           "image": image, "max_score": 7.0}, mixed_map))
            labels["frames"][image] = {"thin_crack": {
                "category": "pipe_front", "visibility": "visible",
                "shape": "box", "points": [[40, 40], [41, 41]],
            }}

        thresholds = threshold_candidates(clean, mixed, labels, "pipe_front")
        self.assertIn(7.0, thresholds)
        self.assertLess(7.0, float(np.median([row["max_score"] for row, _ in clean])))
        self.assertEqual(detect_events(clean, 7.0), [])
        self.assertEqual(len(detect_events(mixed, 7.0)), 1)

    def test_two_false_alerts_are_shared_across_four_groups(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            datasets = {}
            scores = {}
            for state in ("clean", "mixed"):
                dataset = root / f"dataset_{state}"
                score_dir = root / f"scores_{state}"
                dataset.mkdir()
                score_dir.mkdir()
                rows = []
                score_rows = []
                labels = {"defects": {}, "frames": {}}
                for category in CATEGORIES:
                    defect_id = f"defect_{category}"
                    labels["defects"][defect_id] = {
                        "category": category,
                        "size_class": "thin" if category == "pipe_front" else "large",
                    }
                    (score_dir / category).mkdir()
                    for tick in (0, 3, 6):
                        image = f"images/{category}/frame_{tick:06d}.png"
                        score_file = f"{category}/score_{tick:06d}.npz"
                        matrix = np.full((8, 8), -np.inf, np.float32)
                        matrix[2:4, 2:4] = 1.0
                        np.savez_compressed(score_dir / score_file, scores=matrix)
                        rows.append({"image": image, "category": category, "tick": tick})
                        score_rows.append({"image": image, "category": category,
                                           "tick": tick, "score_file": score_file,
                                           "max_score": 1.0})
                        labels["frames"][image] = {defect_id: {
                            "category": category, "visibility": "visible",
                            "shape": "box", "points": [[2, 2], [3, 3]],
                            "review_status": "reviewed",
                        }}
                (dataset / "summary.json").write_text(json.dumps({
                    "dataset_role": "calibration", "scene_state": state,
                    "frames": len(rows),
                }), encoding="utf-8")
                (dataset / "manifest.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
                (score_dir / "score_manifest.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in score_rows), encoding="utf-8")
                (score_dir / "report.json").write_text(json.dumps({
                    "dataset": str(dataset.resolve()), "model_dir": str(root / "model"),
                }), encoding="utf-8")
                if state == "mixed":
                    (dataset / "damage_labels.json").write_text(json.dumps(labels),
                                                                  encoding="utf-8")
                datasets[state], scores[state] = dataset, score_dir
            result = calibrate(datasets["clean"], scores["clean"], datasets["mixed"],
                               scores["mixed"], root / "thresholds.json")
            self.assertEqual(result["false_alerts_clean_route"], 2)
            self.assertEqual(sum(group["false_events"] for group in result["groups"].values()), 2)
            self.assertEqual(sum(len(group["detected_ids"]) for group in result["groups"].values()), 2)
            self.assertIn("defect_pipe_front", result["groups"]["pipe_front"]["detected_ids"])
            label_path = datasets["mixed"] / "damage_labels.json"
            labels = json.loads(label_path.read_text(encoding="utf-8"))
            for frame in labels["frames"].values():
                entry = frame.get("defect_pier_1")
                if entry is not None:
                    entry.update(visibility="absent", shape=None, points=[])
            label_path.write_text(json.dumps(labels), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not visible"):
                calibrate(datasets["clean"], scores["clean"], datasets["mixed"],
                          scores["mixed"], root / "rejected_thresholds.json")


if __name__ == "__main__":
    unittest.main()
