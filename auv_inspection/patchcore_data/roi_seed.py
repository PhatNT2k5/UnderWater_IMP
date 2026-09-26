"""Suggest editable polygons for the consistent pipe and pier camera views."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def suggested_polygon(image: np.ndarray, category: str) -> list[list[int]] | None:
    height, width = image.shape[:2]
    blue = (image[:, :, 0].astype(np.int16) - image[:, :, 2].astype(np.int16) > 22)
    blue &= image[:, :, 0].astype(np.int16) - image[:, :, 1].astype(np.int16) > 7
    if category.startswith("pipe_"):
        scan = blue[int(height * 0.52):int(height * 0.68)].mean(axis=0)
        valid = scan < 0.45
        if np.count_nonzero(valid) < 100:
            return None
        intervals = np.where(np.diff(np.r_[False, valid, False]))[0].reshape(-1, 2)
        left, right = max(intervals, key=lambda part: part[1] - part[0])
        if right - left < 100:
            return None
        top = round(height * 0.37)
        bottom = round(height * 0.79)
        return [[int(left), top], [int(right - 1), top],
                [int(right - 1), bottom], [int(left), bottom]]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    textured = (gray > 28) & ~blue
    counts = textured[int(height * 0.08):int(height * 0.92)].sum(axis=0)
    valid = counts > height * 0.18
    if np.count_nonzero(valid) < 50:
        return None
    intervals = np.where(np.diff(np.r_[False, valid, False]))[0].reshape(-1, 2)
    left, right = max(intervals, key=lambda part: part[1] - part[0])
    if right - left < 50:
        return None
    left = max(0, int(left) - 18)
    right = min(width - 1, int(right) + 18)
    return [[left, 0], [right, 0], [right, height - 1], [left, height - 1]]


def seed(dataset: Path) -> dict:
    keyframes = json.loads((dataset / "keyframes.json").read_text(encoding="utf-8"))
    suggestions: dict[str, list[list[int]]] = {}
    samples: dict[str, list[np.ndarray]] = {}
    for row in keyframes:
        image = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(row["source_image"])
        polygon = suggested_polygon(image, row["category"])
        if polygon is None:
            continue
        suggestions[row["image"]] = polygon
        preview = image.copy()
        cv2.polylines(preview, [np.array(polygon, np.int32)], True, (0, 255, 255), 3)
        samples.setdefault(row["category"], []).append(cv2.resize(preview, (320, 240)))
    (dataset / "roi_suggestions.json").write_text(json.dumps(suggestions, indent=2), encoding="utf-8")
    for category, images in samples.items():
        while len(images) % 3:
            images.append(np.zeros_like(images[0]))
        sheet = np.concatenate([np.concatenate(images[i:i + 3], axis=1)
                                for i in range(0, len(images), 3)], axis=0)
        cv2.imwrite(str(dataset / f"roi_suggestions_{category}.jpg"), sheet)
    return {category: sum(row["category"] == category and row["image"] in suggestions
                          for row in keyframes) for category in ("pipe_front", "pipe_back", "pier_0", "pier_1")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    print(json.dumps(seed(parser.parse_args().dataset), indent=2))


if __name__ == "__main__":
    main()
