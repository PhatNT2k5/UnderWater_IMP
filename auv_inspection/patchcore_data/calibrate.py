"""Choose per-structure alert thresholds from separate clean and damaged routes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .alerts import AlertTracker, Candidate, extract_candidates
from .model import CATEGORIES


def load_scored(dataset: Path, score_dir: Path, role: str, state: str) -> list[dict]:
    dataset_info = json.loads((dataset / "summary.json").read_text(encoding="utf-8"))
    score_info = json.loads((score_dir / "report.json").read_text(encoding="utf-8"))
    if dataset_info["dataset_role"] != role or dataset_info["scene_state"] != state:
        raise ValueError(f"Expected {role}/{state} dataset: {dataset}")
    if Path(score_info["dataset"]).resolve() != dataset.resolve():
        raise ValueError("Score report refers to a different dataset")
    rows = [json.loads(line) for line in (score_dir / "score_manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    if len(rows) != dataset_info["frames"]:
        raise ValueError("Scored frame count differs from dataset manifest")
    return rows


def load_maps(score_dir: Path, rows: list[dict]) -> list[tuple[dict, np.ndarray]]:
    frames = []
    for row in sorted(rows, key=lambda item: item["tick"]):
        with np.load(score_dir / row["score_file"]) as archive:
            frames.append((row, archive["scores"].copy()))
    return frames


def detect_events(frames: list[tuple[dict, np.ndarray]], threshold: float) -> list[tuple[dict, Candidate]]:
    tracker = AlertTracker()
    events = []
    for row, scores in frames:
        for candidate in tracker.step(row["category"], row["tick"],
                                      extract_candidates(scores, threshold)):
            events.append((row, candidate))
    return events


def load_labels(dataset: Path, require_locked: bool = False) -> dict:
    path = dataset / "damage_labels.json"
    if not path.is_file():
        raise FileNotFoundError(f"Reviewed labels are required: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if require_locked and not data.get("locked"):
        raise ValueError("Test labels must be locked before evaluation")
    inventory = data.get("defects", {})
    if not inventory:
        raise ValueError("Physical defect inventory is required")
    for defect_id, meta in inventory.items():
        if meta.get("category") not in CATEGORIES:
            raise ValueError(f"Unknown structure group for {defect_id}")
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    for row in rows:
        frame = data.get("frames", {}).get(row["image"], {})
        for defect_id, meta in inventory.items():
            if meta["category"] != row["category"]:
                continue
            entry = frame.get(defect_id)
            if entry is None or entry.get("review_status") != "reviewed":
                raise ValueError(f"Unreviewed {defect_id} in {row['image']}")
            visibility = entry.get("visibility")
            if visibility not in {"visible", "unclear", "absent"}:
                raise ValueError(f"Invalid visibility for {defect_id} in {row['image']}")
            if visibility == "visible" and (entry.get("shape") not in {"box", "polyline"}
                                            or len(entry.get("points", [])) < 2):
                raise ValueError(f"Visible label has no geometry: {defect_id} in {row['image']}")
    if require_locked:
        import hashlib

        receipt = json.loads((dataset / "label_lock.json").read_text(encoding="utf-8"))
        if receipt["labels_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("Test labels changed after locking")
    return data


def label_box(label: dict) -> tuple[int, int, int, int] | None:
    if label.get("bbox"):
        return tuple(map(int, label["bbox"]))
    points = label.get("points", [])
    if not points:
        return None
    xs, ys = zip(*points, strict=True)
    return min(xs), min(ys), max(xs), max(ys)


def detected_defects(events: list[tuple[dict, Candidate]], labels: dict,
                     category: str) -> set[str]:
    detected: set[str] = set()
    by_image = labels.get("frames", {})
    for row, candidate in events:
        for defect_id, label in by_image.get(row["image"], {}).items():
            if label.get("category") != category or label.get("visibility") != "visible":
                continue
            box = label_box(label)
            if box is None:
                continue
            x, y, width, height = candidate.bbox
            x0, y0, x1, y1 = box
            if x <= x1 + 8 and x + width >= x0 - 8 and y <= y1 + 8 and y + height >= y0 - 8:
                detected.add(defect_id)
    return detected


def visible_ids(labels: dict, category: str) -> set[str]:
    return {defect_id for frame in labels.get("frames", {}).values()
            for defect_id, entry in frame.items()
            if entry.get("category") == category and entry.get("visibility") == "visible"}


def threshold_candidates(clean: list[tuple[dict, np.ndarray]],
                         mixed: list[tuple[dict, np.ndarray]],
                         labels: dict, category: str) -> list[float]:
    clean_peaks = np.asarray([row["max_score"] for row, _ in clean], dtype=np.float64)
    visible_peaks = []
    for row, scores in mixed:
        for entry in labels.get("frames", {}).get(row["image"], {}).values():
            if entry.get("category") != category or entry.get("visibility") != "visible":
                continue
            box = label_box(entry)
            if box is None:
                continue
            x0, y0, x1, y1 = box
            region = scores[max(0, y0):min(scores.shape[0], y1 + 1),
                            max(0, x0):min(scores.shape[1], x1 + 1)]
            finite = region[np.isfinite(region)]
            if finite.size:
                visible_peaks.append(float(finite.max()))
    observed_min = min([float(clean_peaks.min()), *visible_peaks])
    lower = max(0.0, observed_min - 5.0)
    upper = float(clean_peaks.max() + 1e-3)
    grid_size = min(64, max(2, int(np.ceil(upper - lower)) + 1))
    grid = np.linspace(lower, upper, grid_size)
    quantiles = np.percentile(clean_peaks,
                              [0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 85,
                               90, 94, 96, 97, 98, 99, 99.5, 99.9])
    return sorted(set(float(value) for value in [*grid, *quantiles,
                                                  *visible_peaks, upper]))


def calibrate(clean_dataset: Path, clean_scores: Path, mixed_dataset: Path,
              mixed_scores: Path, destination: Path) -> dict:
    clean_rows = load_scored(clean_dataset, clean_scores, "calibration", "clean")
    mixed_rows = load_scored(mixed_dataset, mixed_scores, "calibration", "mixed")
    labels = load_labels(mixed_dataset)
    unobservable = set(labels["defects"]) - set().union(
        *(visible_ids(labels, category) for category in CATEGORIES))
    if unobservable:
        raise ValueError(f"Calibration defects not visible in any frame: {sorted(unobservable)}")
    clean_model = json.loads((clean_scores / "report.json").read_text(encoding="utf-8"))["model_dir"]
    mixed_model = json.loads((mixed_scores / "report.json").read_text(encoding="utf-8"))["model_dir"]
    if Path(clean_model).resolve() != Path(mixed_model).resolve():
        raise ValueError("Clean and damaged scores use different models")
    if clean_dataset.resolve() == mixed_dataset.resolve():
        raise ValueError("Clean and damaged calibration must come from separate captures")
    trials_by_category: dict[str, list[dict]] = {}
    visible_by_category: dict[str, set[str]] = {}
    small_ids = {defect_id for defect_id, meta in labels["defects"].items()
                 if meta.get("size_class") in {"small", "thin"}}
    for category in CATEGORIES:
        clean = load_maps(clean_scores, [row for row in clean_rows if row["category"] == category])
        mixed = load_maps(mixed_scores, [row for row in mixed_rows if row["category"] == category])
        if not clean or not mixed:
            raise ValueError(f"Missing calibration coverage for {category}")
        thresholds = threshold_candidates(clean, mixed, labels, category)
        relevant = visible_ids(labels, category)
        trials = []
        for threshold in thresholds:
            false_events = detect_events(clean, threshold)
            detected = detected_defects(detect_events(mixed, threshold), labels, category)
            trials.append({"threshold": threshold, "false_events": len(false_events),
                           "detected_ids": sorted(detected),
                           "visible_ids": sorted(relevant)})
        trials_by_category[category] = trials
        visible_by_category[category] = relevant

    # Dynamic programming enforces the false-alert budget across all four groups.
    def rank(group_trials: dict[str, dict]) -> tuple[int, int, float]:
        detected = {item for value in group_trials.values()
                    for item in value["detected_ids"]}
        return (len(detected & small_ids), len(detected),
                sum(value["threshold"] for value in group_trials.values()))

    choices: dict[int, dict[str, dict]] = {0: {}}
    for category in CATEGORIES:
        updated: dict[int, dict[str, dict]] = {}
        for used_budget, selected in choices.items():
            for trial in trials_by_category[category]:
                budget = used_budget + trial["false_events"]
                if budget > 2:
                    continue
                proposal = {**selected, category: trial}
                previous = updated.get(budget)
                if previous is None or rank(proposal) > rank(previous):
                    updated[budget] = proposal
        choices = updated
    if not choices:
        raise ValueError("No threshold combination meets <=2 false alerts per clean route")
    def overall_rank(item: tuple[int, dict[str, dict]]) -> tuple[int, int, int, float]:
        budget, selected = item
        detected = {defect_id for trial in selected.values()
                    for defect_id in trial["detected_ids"]}
        return (len(detected & small_ids), len(detected), -budget,
                sum(trial["threshold"] for trial in selected.values()))
    false_total, selected = max(choices.items(), key=overall_rank)
    results = {category: {
        **selected[category],
        "missed_ids": sorted(visible_by_category[category]
                             - set(selected[category]["detected_ids"])),
        "trials": trials_by_category[category],
        "calibration_has_visible_defect": bool(visible_by_category[category]),
    } for category in CATEGORIES}
    output = {
        "model_dir": clean_model,
        "clean_dataset": str(clean_dataset.resolve()),
        "mixed_dataset": str(mixed_dataset.resolve()),
        "selection_rule": "maximize small/thin then all visible defects subject to <=2 false events across the clean route",
        "false_alerts_clean_route": false_total,
        "confirmation": "3 trajectory-consistent scored frames, max 13 px/tick, 60 px prediction error, max 15 tick gap",
        "groups": results,
    }
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clean_dataset", type=Path)
    parser.add_argument("clean_scores", type=Path)
    parser.add_argument("mixed_dataset", type=Path)
    parser.add_argument("mixed_scores", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = calibrate(args.clean_dataset, args.clean_scores, args.mixed_dataset,
                       args.mixed_scores, args.destination)
    print(json.dumps({category: {key: value for key, value in group.items() if key != "trials"}
                      for category, group in result["groups"].items()}, indent=2))


if __name__ == "__main__":
    main()
