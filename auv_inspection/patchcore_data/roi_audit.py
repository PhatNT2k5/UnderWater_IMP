"""Create contact sheets to review every proposed surface mask."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def create_sheets(dataset: Path) -> dict:
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    proposals = json.loads((dataset / "roi_proposals.json").read_text(encoding="utf-8"))
    groups: dict[str, list[np.ndarray]] = {}
    for row in rows:
        entry = proposals.get(row["image"], {})
        if entry.get("status") != "proposed":
            continue
        image = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
        mask = cv2.imread(str(dataset / entry["mask"]), cv2.IMREAD_GRAYSCALE)
        if image is None or mask is None:
            raise FileNotFoundError(row["image"])
        overlay = image.copy()
        overlay[mask > 0] = (0.75 * image[mask > 0] +
                             0.25 * np.array([0, 220, 0])).astype(np.uint8)
        thumb = cv2.resize(overlay, (160, 120))
        cv2.putText(thumb, f"{row['tick']} {entry.get('method', '?')[0]}",
                    (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        groups.setdefault(row["category"], []).append(thumb)
    counts = {category: len(images) for category, images in groups.items()}
    for category, images in groups.items():
        blank = np.zeros_like(images[0])
        while len(images) % 8:
            images.append(blank)
        sheet = np.concatenate([np.concatenate(images[i:i + 8], axis=1)
                                for i in range(0, len(images), 8)], axis=0)
        cv2.imwrite(str(dataset / f"roi_audit_{category}.jpg"), sheet)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    print(json.dumps(create_sheets(parser.parse_args().dataset), indent=2))


if __name__ == "__main__":
    main()
