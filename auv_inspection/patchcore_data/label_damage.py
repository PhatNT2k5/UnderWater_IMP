"""Annotate visible physical defects in a captured mixed scene."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def label_dataset(dataset: Path, defect_id: str, category: str,
                  size_class: str = "unknown") -> None:
    if not defect_id.strip():
        raise ValueError("Defect ID must be nonempty")
    summary = json.loads((dataset / "summary.json").read_text(encoding="utf-8"))
    if summary["scene_state"] != "mixed":
        raise ValueError("Damage labels require a mixed-scene capture")
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    rows = [row for row in rows if row["category"] == category]
    if not rows:
        raise ValueError(f"No frames for category {category}")
    labels_path = dataset / "damage_labels.json"
    labels = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else {}
    proposals_path = dataset / "damage_label_proposals.json"
    proposals = json.loads(proposals_path.read_text(encoding="utf-8")) if proposals_path.exists() else {}
    if labels.get("locked"):
        raise ValueError("This dataset's damage labels are locked")
    inventory = labels.setdefault("defects", {})
    existing = inventory.get(defect_id)
    if existing and existing["category"] != category:
        raise ValueError("Defect ID is already assigned to another category")
    inventory[defect_id] = {"category": category, "size_class": size_class}
    entries: dict[str, dict] = labels.setdefault("frames", {})
    window = "AUV damage labeling"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    index = 0
    shape_type = "box"
    points: list[list[int]] = []
    dragging = False
    previous_visible: tuple[str, str, list[list[int]]] | None = None

    def on_mouse(event: int, x: int, y: int, _flags: int, _param: object) -> None:
        nonlocal dragging
        if shape_type == "box":
            if event == cv2.EVENT_LBUTTONDOWN:
                points[:] = [[x, y], [x, y]]
                dragging = True
            elif event == cv2.EVENT_MOUSEMOVE and dragging:
                points[1] = [x, y]
            elif event == cv2.EVENT_LBUTTONUP and dragging:
                points[1] = [x, y]
                dragging = False
        elif event == cv2.EVENT_LBUTTONDOWN:
            points.append([x, y])
        elif event == cv2.EVENT_RBUTTONDOWN and points:
            points.pop()

    cv2.setMouseCallback(window, on_mouse)
    try:
        while index < len(rows):
            row = rows[index]
            name = row["image"]
            image = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(row["source_image"])
            current = entries.get(name, {}).get(defect_id)
            if current is None:
                current = proposals.get("frames", {}).get(name, {}).get(defect_id)
            if current and current.get("shape") in {"box", "polyline"}:
                shape_type = current["shape"]
                points = [list(point) for point in current["points"]]
            else:
                points = []
            while True:
                display = image.copy()
                if points:
                    path = np.asarray(points, np.int32).reshape((-1, 1, 2))
                    if shape_type == "box" and len(points) == 2:
                        cv2.rectangle(display, tuple(points[0]), tuple(points[1]), (0, 255, 255), 2)
                    elif len(points) > 1:
                        cv2.polylines(display, [path], False, (0, 255, 255), 2)
                cv2.putText(display, f"{index + 1}/{len(rows)} {defect_id} {row['category']} {shape_type}",
                            (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(display, "B:box L:line C:copy A:accept S:visible U:unclear N:absent P:prev Q:quit",
                            (8, 463), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)
                if current and current.get("visibility") == "visible" and len(points) < 2:
                    cv2.putText(display, "Proposal: draw this defect, then press S",
                                (8, 443), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
                cv2.imshow(window, display)
                key = cv2.waitKey(30) & 0xFF
                if key in (ord("b"), ord("l")):
                    shape_type = "box" if key == ord("b") else "polyline"
                    points.clear()
                elif key == ord("a") and current is not None:
                    if current.get("visibility") == "visible" and (
                            current.get("shape") not in {"box", "polyline"}
                            or len(current.get("points", [])) < 2):
                        continue
                    accepted = dict(current)
                    accepted["review_status"] = "reviewed"
                    entries.setdefault(name, {})[defect_id] = accepted
                    if accepted.get("visibility") == "visible":
                        previous_visible = (row["category"], accepted["shape"],
                                            [list(point) for point in accepted["points"]])
                    index += 1
                    break
                elif key == ord("c") and previous_visible is not None:
                    category, previous_shape, previous_points = previous_visible
                    if category == row["category"]:
                        shape_type = previous_shape
                        points = [point.copy() for point in previous_points]
                elif key == ord("s"):
                    if len(points) < 2:
                        continue
                    entries.setdefault(name, {})[defect_id] = {
                        "visibility": "visible", "shape": shape_type,
                        "points": points.copy(), "category": row["category"],
                        "review_status": "reviewed",
                    }
                    previous_visible = (row["category"], shape_type, [point.copy() for point in points])
                    index += 1
                    break
                elif key in (ord("u"), ord("n")):
                    entries.setdefault(name, {})[defect_id] = {
                        "visibility": "unclear" if key == ord("u") else "absent",
                        "shape": None, "points": [], "category": row["category"],
                        "review_status": "reviewed",
                    }
                    index += 1
                    break
                elif key == ord("p"):
                    index = max(0, index - 1)
                    break
                elif key in (ord("q"), 27):
                    labels_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")
                    return
            labels_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")
    finally:
        cv2.destroyWindow(window)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("defect_id", help="Stable physical defect ID across frames")
    parser.add_argument("--category", required=True,
                        choices=("pipe_front", "pipe_back", "pier_0", "pier_1"))
    parser.add_argument("--size-class", default="unknown",
                        choices=("small", "thin", "large", "unknown"))
    args = parser.parse_args()
    label_dataset(args.dataset, args.defect_id, args.category, args.size_class)


if __name__ == "__main__":
    main()
