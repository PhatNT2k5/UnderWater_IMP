"""Evaluate locked test routes without changing calibrated thresholds."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import cv2
import numpy as np

from auv_inspection.crack_detection import CrackTracker, analyze_frame

from .approval_gate import file_sha256, model_fingerprint, reference_fingerprint
from .alerts import Candidate
from .calibrate import detected_defects, detect_events, load_labels, load_maps, load_scored, visible_ids
from .model import CATEGORIES


def classical_events(dataset: Path) -> list[tuple[dict, Candidate]]:
    """Replay the unchanged classical detector on captured pipe camera frames."""
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    events = []
    for category in ("pipe_front", "pipe_back"):
        tracker = CrackTracker()
        last_alert_position: np.ndarray | None = None
        for row in sorted((item for item in rows if item["category"] == category),
                          key=lambda item: item["tick"]):
            frame = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
            if frame is None:
                raise FileNotFoundError(row["source_image"])
            found = tracker.update(analyze_frame(frame))
            position = np.asarray(row["position_m"], dtype=np.float32)
            if found is None or (last_alert_position is not None and
                                 np.linalg.norm(position - last_alert_position) < 2.0):
                continue
            x, y, width, height = found.bbox
            events.append((row, Candidate(found.bbox,
                                          (x + width / 2, y + height / 2),
                                          found.score, found.area_px)))
            last_alert_position = position
            tracker.reset()
    return events


def evaluate(clean_dataset: Path, clean_scores: Path, mixed_dataset: Path,
             mixed_scores: Path, thresholds_file: Path, destination: Path) -> dict:
    clean_rows = load_scored(clean_dataset, clean_scores, "test", "clean")
    mixed_rows = load_scored(mixed_dataset, mixed_scores, "test", "mixed")
    labels = load_labels(mixed_dataset, require_locked=True)
    thresholds = json.loads(thresholds_file.read_text(encoding="utf-8"))
    model_dir = json.loads((clean_scores / "report.json").read_text(encoding="utf-8"))["model_dir"]
    reference_dataset = Path(json.loads((Path(model_dir) / "config.json").read_text(
        encoding="utf-8"))["source_dataset"]).resolve()
    mixed_model_dir = json.loads((mixed_scores / "report.json").read_text(encoding="utf-8"))["model_dir"]
    if Path(thresholds["model_dir"]).resolve() != Path(model_dir).resolve():
        raise ValueError("Evaluation scores and calibration use different models")
    if Path(mixed_model_dir).resolve() != Path(model_dir).resolve():
        raise ValueError("Clean and damaged test scores use different models")
    if Path(thresholds["clean_dataset"]).resolve() in {clean_dataset.resolve(), mixed_dataset.resolve()}:
        raise ValueError("Test capture overlaps calibration")
    if Path(thresholds["mixed_dataset"]).resolve() in {clean_dataset.resolve(), mixed_dataset.resolve()}:
        raise ValueError("Test capture overlaps calibration")
    groups: dict[str, dict] = {}
    for category in CATEGORIES:
        clean = load_maps(clean_scores, [row for row in clean_rows if row["category"] == category])
        mixed = load_maps(mixed_scores, [row for row in mixed_rows if row["category"] == category])
        if not clean or not mixed:
            raise ValueError(f"Missing test coverage for {category}")
        threshold = float(thresholds["groups"][category]["threshold"])
        clean_events = detect_events(clean, threshold)
        mixed_events = detect_events(mixed, threshold)
        visible = visible_ids(labels, category)
        detected = detected_defects(mixed_events, labels, category)
        event_rows = []
        for row, candidate in mixed_events:
            event_rows.append({"tick": row["tick"], "image": row["image"],
                               "bbox": candidate.bbox, "peak_score": candidate.peak_score})
        labels_by_id: dict[str, list[int]] = {}
        for row, _ in mixed:
            for defect_id, label in labels.get("frames", {}).get(row["image"], {}).items():
                if label.get("visibility") == "visible":
                    labels_by_id.setdefault(defect_id, []).append(row["tick"])
        latency_ticks = {}
        for defect_id in detected:
            first_visible = min(labels_by_id[defect_id])
            matching_ticks = [row["tick"] for row, candidate in mixed_events
                              if defect_id in detected_defects([(row, candidate)], labels, category)]
            latency_ticks[defect_id] = min(matching_ticks) - first_visible
        groups[category] = {
            "threshold": threshold, "visible_ids": sorted(visible),
            "detected_ids": sorted(detected), "missed_ids": sorted(visible - detected),
            "recall_count": [len(detected), len(visible)],
            "false_alerts_clean_route": len(clean_events),
            "mixed_events": event_rows,
            "latency_ticks": latency_ticks,
            "processing_ms_median": statistics.median(row["processing_ms"] for row, _ in mixed),
            "processing_ms_p95": float(np.percentile([row["processing_ms"] for row, _ in mixed], 95)),
        }
    all_visible = set().union(*(set(group["visible_ids"]) for group in groups.values()))
    all_detected = set().union(*(set(group["detected_ids"]) for group in groups.values()))
    false_total = sum(group["false_alerts_clean_route"] for group in groups.values())
    classical_clean = classical_events(clean_dataset)
    classical_mixed = classical_events(mixed_dataset)
    classical_visible = set().union(*(visible_ids(labels, category)
                                      for category in ("pipe_front", "pipe_back")))
    classical_detected = set().union(*(detected_defects(classical_mixed, labels, category)
                                       for category in ("pipe_front", "pipe_back")))
    inventory = labels.get("defects", {})
    unobservable = sorted(set(inventory) - all_visible)
    small_or_thin = {defect_id for defect_id, meta in inventory.items()
                     if meta.get("size_class") in {"small", "thin"}} & all_visible
    acceptance = {
        "all_inventory_observable": not unobservable,
        "recall_at_least_95_percent": bool(all_visible and len(all_detected) / len(all_visible) >= 0.95),
        "small_or_thin_recall_at_least_90_percent": bool(
            small_or_thin and len(small_or_thin & all_detected) / len(small_or_thin) >= 0.90
        ),
        "false_alerts_at_most_2": false_total <= 2,
    }
    acceptance["passed"] = all(acceptance.values())
    result = {
        "thresholds": str(thresholds_file.resolve()), "model_dir": model_dir,
        "thresholds_sha256": file_sha256(thresholds_file),
        "model_sha256": model_fingerprint(Path(model_dir)),
        "reference_dataset": str(reference_dataset),
        "reference_sha256": reference_fingerprint(reference_dataset),
        "clean_dataset": str(clean_dataset.resolve()),
        "mixed_dataset": str(mixed_dataset.resolve()),
        "visible_physical_defects": len(all_visible),
        "detected_physical_defects": len(all_detected),
        "missed_physical_defects": sorted(all_visible - all_detected),
        "unobservable_inventory_ids": unobservable,
        "small_or_thin_visible_ids": sorted(small_or_thin),
        "small_or_thin_detected_ids": sorted(small_or_thin & all_detected),
        "false_alerts_clean_route": false_total,
        "classical_pipe_comparison": {
            "visible_ids": sorted(classical_visible),
            "detected_ids": sorted(classical_detected),
            "missed_ids": sorted(classical_visible - classical_detected),
            "false_alerts_clean_route": len(classical_clean),
            "pier_scope": "not_supported",
        },
        "acceptance": acceptance,
        "groups": groups,
    }
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clean_dataset", type=Path)
    parser.add_argument("clean_scores", type=Path)
    parser.add_argument("mixed_dataset", type=Path)
    parser.add_argument("mixed_scores", type=Path)
    parser.add_argument("thresholds_file", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = evaluate(args.clean_dataset, args.clean_scores, args.mixed_dataset,
                      args.mixed_scores, args.thresholds_file, args.destination)
    print(json.dumps({key: value for key, value in result.items() if key != "groups"}, indent=2))


if __name__ == "__main__":
    main()
