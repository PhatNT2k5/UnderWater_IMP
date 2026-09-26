"""Propose crack centerlines from aligned clean/mixed frame differences."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def centerline(changed: np.ndarray) -> list[list[int]]:
    ys, xs = np.nonzero(changed)
    if len(xs) < 2:
        return []
    left, right = int(xs.min()), int(xs.max())
    edges = np.linspace(left, right + 1, min(9, right - left + 2), dtype=int)
    points = []
    for x0, x1 in zip(edges[:-1], edges[1:], strict=True):
        selected = (xs >= x0) & (xs < x1)
        if selected.any():
            points.append([int(np.median(xs[selected])), int(np.median(ys[selected]))])
    return points


def propose(clean_dataset: Path, mixed_dataset: Path,
            category_ids: dict[str, str], pixel_threshold: int = 8,
            visible_pixels: int = 30) -> dict:
    clean_rows = [json.loads(line) for line in (clean_dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    mixed_rows = [json.loads(line) for line in (mixed_dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    clean_lookup = {(row["category"], row["tick"]): row for row in clean_rows}
    labels: dict[str, dict] = {"locked": False, "source": "aligned_clean_difference_proposal",
                               "frames": {}}
    counts = {"visible": 0, "unclear": 0, "absent": 0}
    for row in mixed_rows:
        defect_id = category_ids.get(row["category"])
        if defect_id is None:
            continue
        reference = clean_lookup.get((row["category"], row["tick"]))
        if reference is None:
            raise ValueError(f"No aligned clean frame: {row['image']}")
        clean = cv2.imread(reference["source_image"], cv2.IMREAD_COLOR)
        mixed = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
        if clean is None or mixed is None or clean.shape != mixed.shape:
            raise ValueError(f"Cannot compare {row['image']}")
        changed = cv2.absdiff(clean, mixed).max(axis=2) >= pixel_threshold
        count = int(np.count_nonzero(changed))
        if count >= visible_pixels:
            ys, xs = np.nonzero(changed)
            x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            points = centerline(changed)
            entry = {"visibility": "visible", "shape": "polyline", "points": points,
                     "bbox": [x0, y0, x1, y1], "category": row["category"],
                     "changed_pixels": count, "review_status": "proposed"}
        elif count > 0:
            entry = {"visibility": "unclear", "shape": None, "points": [],
                     "category": row["category"], "changed_pixels": count,
                     "review_status": "proposed"}
        else:
            entry = {"visibility": "absent", "shape": None, "points": [],
                     "category": row["category"], "changed_pixels": 0,
                     "review_status": "proposed"}
        labels["frames"].setdefault(row["image"], {})[defect_id] = entry
        counts[entry["visibility"]] += 1
    (mixed_dataset / "damage_label_proposals.json").write_text(
        json.dumps(labels, indent=2), encoding="utf-8")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clean_dataset", type=Path)
    parser.add_argument("mixed_dataset", type=Path)
    parser.add_argument("--pipe-front-id")
    parser.add_argument("--pipe-back-id")
    parser.add_argument("--pier-0-id")
    parser.add_argument("--pier-1-id")
    args = parser.parse_args()
    ids = {category: value for category, value in {
        "pipe_front": args.pipe_front_id, "pipe_back": args.pipe_back_id,
        "pier_0": args.pier_0_id, "pier_1": args.pier_1_id,
    }.items() if value}
    if not ids:
        parser.error("At least one physical defect ID is required")
    print(json.dumps(propose(args.clean_dataset, args.mixed_dataset, ids), indent=2))


if __name__ == "__main__":
    main()
