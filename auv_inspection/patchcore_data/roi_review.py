"""Review propagated surface masks one frame at a time."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def review(dataset: Path) -> None:
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    proposals = json.loads((dataset / "roi_proposals.json").read_text(encoding="utf-8"))
    approved_file = dataset / "roi_approved.json"
    approved = json.loads(approved_file.read_text(encoding="utf-8")) if approved_file.exists() else {}
    window = "AUV ROI review"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    try:
        for index, row in enumerate(rows):
            name = row["image"]
            if name in approved:
                continue
            proposal = proposals.get(name, {})
            if proposal.get("status") != "proposed":
                continue
            image = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
            mask = cv2.imread(str(dataset / proposal["mask"]), cv2.IMREAD_GRAYSCALE)
            if image is None or mask is None or image.shape[:2] != mask.shape:
                raise ValueError(f"Invalid image or ROI mask: {name}")
            overlay = image.copy()
            overlay[mask > 0] = (0.6 * image[mask > 0] +
                                 0.4 * np.array([0, 200, 0])).astype(np.uint8)
            cv2.putText(overlay, f"{index + 1}/{len(rows)} {row['category']} tick {row['tick']}",
                        (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            cv2.putText(overlay, "A:approve X:exclude N:later Q:quit",
                        (8, 464), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            cv2.imshow(window, overlay)
            while True:
                key = cv2.waitKey(50) & 0xFF
                if key == ord("a"):
                    approved[name] = {"status": "approved", "mask": proposal["mask"],
                                      "reviewer": "manual_review"}
                    break
                if key == ord("x"):
                    approved[name] = {"status": "excluded", "reason": "manual_review"}
                    break
                if key == ord("n"):
                    break
                if key in (ord("q"), 27):
                    approved_file.write_text(json.dumps(approved, indent=2), encoding="utf-8")
                    return
            approved_file.write_text(json.dumps(approved, indent=2), encoding="utf-8")
    finally:
        cv2.destroyWindow(window)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    review(parser.parse_args().dataset)


if __name__ == "__main__":
    main()
