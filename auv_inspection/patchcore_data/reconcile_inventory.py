"""Separate aligned-difference proposals by physical decal inventory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def reconcile(dataset: Path, inventory_path: Path, changes_path: Path,
              minimum_pixels: int = 30) -> dict:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))["physical_defects"]
    changes = {row["image"]: row for row in
               (json.loads(line) for line in changes_path.read_text(encoding="utf-8").splitlines())}
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    labels: dict = {"locked": False, "source": "aligned_difference_split_by_editor_inventory",
                    "defects": {}, "frames": {}}
    for item in inventory:
        labels["defects"][item["id"]] = {
            "category": item["category"], "size_class": "thin",
            "actor": item["actor"], "camera_observation": item["camera_observation"],
        }
    for row in rows:
        for item in inventory:
            if item["category"] != row["category"]:
                continue
            change = changes.get(row["image"])
            pixels = change["changed_pixels"] if change else 0
            window = item.get("approximate_ticks")
            within_window = window is not None and window[0] <= row["tick"] <= window[1]
            if item["camera_observation"] == "not_resolved_in_sensor":
                visibility = "unclear" if "_level_2_" in row["station"] else "absent"
            elif within_window and pixels >= minimum_pixels:
                visibility = "visible"
            elif within_window and pixels > 0:
                visibility = "unclear"
            else:
                visibility = "absent"
            labels["frames"].setdefault(row["image"], {})[item["id"]] = {
                "visibility": visibility, "shape": None,
                "points": [], "bbox": None, "category": row["category"],
                "changed_pixels": pixels, "review_status": "proposed",
            }
    destination = dataset / "damage_label_proposals.json"
    destination.write_text(json.dumps(labels, indent=2), encoding="utf-8")
    return {item["id"]: sum(frame.get(item["id"], {}).get("visibility") == "visible"
                             for frame in labels["frames"].values()) for item in inventory}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("changes", type=Path, help="Aligned change_manifest.jsonl")
    args = parser.parse_args()
    print(json.dumps(reconcile(args.dataset, args.inventory, args.changes), indent=2))


if __name__ == "__main__":
    main()
