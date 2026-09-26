"""Draw reusable surface polygons on representative clean camera frames."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def edit_polygons(dataset: Path) -> None:
    keyframes = json.loads((dataset / "keyframes.json").read_text(encoding="utf-8"))
    output = dataset / "roi_polygons.json"
    polygons: dict[str, list[list[int]]] = (
        json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    )
    suggestions_path = dataset / "roi_suggestions.json"
    suggestions: dict[str, list[list[int]]] = (
        json.loads(suggestions_path.read_text(encoding="utf-8"))
        if suggestions_path.exists() else {}
    )
    window = "AUV surface ROI"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    index = 0
    points: list[list[int]] = []

    def on_mouse(event: int, x: int, y: int, _flags: int, _param: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append([x, y])
        elif event == cv2.EVENT_RBUTTONDOWN and points:
            points.pop()

    cv2.setMouseCallback(window, on_mouse)
    try:
        while index < len(keyframes):
            record = keyframes[index]
            name = record["image"]
            image = cv2.imread(record["source_image"], cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(record["source_image"])
            points = [list(point) for point in polygons.get(name, suggestions.get(name, []))]
            while True:
                display = image.copy()
                if points:
                    path = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
                    cv2.polylines(display, [path], len(points) >= 3, (0, 255, 255), 2)
                    for point in points:
                        cv2.circle(display, tuple(point), 3, (0, 255, 255), -1)
                cv2.putText(display, f"{index + 1}/{len(keyframes)} {record['category']}",
                            (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
                cv2.putText(display, "Left:add Right:undo S:save N:skip R:reset Q:quit",
                            (8, 464), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (255, 255, 255), 1)
                cv2.imshow(window, display)
                key = cv2.waitKey(20) & 0xFF
                if key == ord("r"):
                    points.clear()
                elif key == ord("s"):
                    if len(points) < 3:
                        continue
                    polygons[name] = points.copy()
                    output.write_text(json.dumps(polygons, indent=2), encoding="utf-8")
                    index += 1
                    break
                elif key == ord("n"):
                    index += 1
                    break
                elif key == ord("q") or key == 27:
                    return
    finally:
        cv2.destroyWindow(window)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    edit_polygons(parser.parse_args().dataset)


if __name__ == "__main__":
    main()
