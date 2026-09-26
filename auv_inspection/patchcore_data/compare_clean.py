"""Suggest damage labels by comparing repeatable route frames with clean capture."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def compare(clean_dataset: Path, mixed_dataset: Path, destination: Path,
            pixel_threshold: int = 8) -> dict:
    clean_rows = [json.loads(line) for line in (clean_dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    mixed_rows = [json.loads(line) for line in (mixed_dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    if any(row["scene_state"] != "clean" for row in clean_rows):
        raise ValueError("Reference dataset must be clean")
    if any(row["scene_state"] != "mixed" for row in mixed_rows):
        raise ValueError("Target dataset must be mixed")
    clean_lookup = {(row["category"], row["tick"]): row for row in clean_rows}
    destination.mkdir(parents=True, exist_ok=False)
    findings: list[dict] = []
    thumbnails: dict[str, list[tuple[int, np.ndarray]]] = {}
    for row in mixed_rows:
        reference = clean_lookup.get((row["category"], row["tick"]))
        if reference is None:
            continue
        clean = cv2.imread(reference["source_image"], cv2.IMREAD_COLOR)
        mixed = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
        if clean is None or mixed is None or clean.shape != mixed.shape:
            raise ValueError(f"Cannot compare frame: {row['image']}")
        delta = cv2.absdiff(clean, mixed).max(axis=2)
        changed = (delta >= pixel_threshold).astype(np.uint8)
        count, _, stats, _ = cv2.connectedComponentsWithStats(changed, 8)
        boxes = []
        for component in range(1, count):
            x, y, width, height, area = map(int, stats[component])
            if area >= 2:
                boxes.append([x, y, width, height, area])
        if not boxes:
            continue
        total_pixels = int(np.count_nonzero(changed))
        findings.append({"image": row["image"], "category": row["category"],
                         "tick": row["tick"], "changed_pixels": total_pixels,
                         "boxes": boxes, "pixel_threshold": pixel_threshold})
        thumbnail = mixed.copy()
        thumbnail[changed > 0] = (0, 0, 255)
        for x, y, width, height, area in boxes:
            if area >= 5:
                cv2.rectangle(thumbnail, (x, y), (x + width, y + height), (0, 255, 255), 1)
        thumbnail = cv2.resize(thumbnail, (320, 240))
        cv2.putText(thumbnail, f"tick {row['tick']} changed {total_pixels}",
                    (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
        thumbnails.setdefault(row["category"], []).append((total_pixels, thumbnail))
    with (destination / "change_manifest.jsonl").open("w", encoding="utf-8") as handle:
        for item in findings:
            handle.write(json.dumps(item) + "\n")
    for category, items in thumbnails.items():
        selected = [image for _, image in sorted(items, key=lambda item: item[0], reverse=True)[:30]]
        while len(selected) % 3:
            selected.append(np.zeros_like(selected[0]))
        sheet = np.concatenate([np.concatenate(selected[i:i + 3], axis=1)
                                for i in range(0, len(selected), 3)], axis=0)
        cv2.imwrite(str(destination / f"changes_{category}.jpg"), sheet)
    report = {"paired_frames": sum((row["category"], row["tick"]) in clean_lookup
                                   for row in mixed_rows),
              "frames_with_changes": len(findings),
              "by_category": {category: sum(item["category"] == category for item in findings)
                              for category in ("pipe_front", "pipe_back", "pier_0", "pier_1")}}
    (destination / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clean_dataset", type=Path)
    parser.add_argument("mixed_dataset", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--pixel-threshold", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(compare(args.clean_dataset, args.mixed_dataset,
                             args.destination, args.pixel_threshold), indent=2))


if __name__ == "__main__":
    main()
