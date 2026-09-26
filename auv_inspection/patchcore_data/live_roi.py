"""Match a live camera frame to a reviewed clean surface mask."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class ReferenceFrame:
    image: str
    source_image: Path
    mask: Path
    category: str
    station: str
    position_m: np.ndarray
    yaw_deg: float


def load_references(dataset: Path) -> list[ReferenceFrame]:
    approved = json.loads((dataset / "roi_approved.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    references = []
    for row in rows:
        entry = approved.get(row["image"])
        if entry is None or entry.get("status") != "approved":
            continue
        references.append(ReferenceFrame(
            image=row["image"], source_image=Path(row["source_image"]),
            mask=dataset / entry["mask"], category=row["category"],
            station=row["station"], position_m=np.asarray(row["position_m"], np.float32),
            yaw_deg=float(row["yaw_deg"]),
        ))
    if not references:
        raise ValueError("No approved clean reference masks")
    return references


def angular_distance(first: float, second: float) -> float:
    return abs((first - second + 180.0) % 360.0 - 180.0)


def nearest_reference(references: list[ReferenceFrame], category: str,
                      station: str, position_m: np.ndarray,
                      yaw_deg: float) -> tuple[ReferenceFrame | None, float, float]:
    candidates = [item for item in references if item.category == category
                  and item.station == station]
    if not candidates:
        return None, float("inf"), float("inf")
    selected = min(candidates, key=lambda item: (
        float(np.linalg.norm(item.position_m - position_m))
        + 0.02 * angular_distance(item.yaw_deg, yaw_deg)))
    return (selected, float(np.linalg.norm(selected.position_m - position_m)),
            angular_distance(selected.yaw_deg, yaw_deg))


def aligned_mask(source: np.ndarray, target: np.ndarray,
                 mask: np.ndarray) -> tuple[np.ndarray | None, int]:
    detector = cv2.ORB_create(nfeatures=1500)
    source_points, source_descriptors = detector.detectAndCompute(source, None)
    target_points, target_descriptors = detector.detectAndCompute(target, None)
    if source_descriptors is None or target_descriptors is None:
        return None, 0
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(source_descriptors,
                                                       target_descriptors, k=2)
    good = [first for first, second in pairs if first.distance < 0.7 * second.distance]
    if len(good) < 20:
        return None, len(good)
    src = np.float32([source_points[match.queryIdx].pt for match in good])
    dst = np.float32([target_points[match.trainIdx].pt for match in good])
    matrix, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                                    ransacReprojThreshold=3.0)
    count = 0 if inliers is None else int(inliers.sum())
    if matrix is None or count < 15:
        return None, count
    scale = float(np.hypot(matrix[0, 0], matrix[1, 0]))
    if not 0.9 <= scale <= 1.1 or np.linalg.norm(matrix[:, 2]) > 80:
        return None, count
    warped = cv2.warpAffine(mask, matrix, (target.shape[1], target.shape[0]),
                            flags=cv2.INTER_NEAREST, borderValue=0)
    if np.count_nonzero(warped) < 1000:
        return None, count
    return warped, count


def match_roi(frame: np.ndarray, references: list[ReferenceFrame],
              category: str, station: str, position_m: np.ndarray,
              yaw_deg: float) -> tuple[np.ndarray | None, dict]:
    reference, distance_m, yaw_error_deg = nearest_reference(
        references, category, station, position_m, yaw_deg)
    if reference is None:
        return None, {"status": "reference_unavailable", "distance_m": None,
                      "yaw_error_deg": None}
    if distance_m > 0.5 or yaw_error_deg > 8.0:
        return None, {"status": "reference_unavailable", "distance_m": distance_m,
                      "yaw_error_deg": yaw_error_deg}
    mask = cv2.imread(str(reference.mask), cv2.IMREAD_GRAYSCALE)
    if mask is None or mask.shape != frame.shape[:2]:
        return None, {"status": "reference_mask_invalid", "reference": reference.image}
    if distance_m <= 0.07 and yaw_error_deg <= 1.0:
        return mask, {"status": "ready", "method": "pose_match",
                      "reference": reference.image, "distance_m": distance_m,
                      "yaw_error_deg": yaw_error_deg}
    source = cv2.imread(str(reference.source_image), cv2.IMREAD_GRAYSCALE)
    if source is None or source.shape != mask.shape:
        return None, {"status": "reference_image_invalid", "reference": reference.image}
    target = cv2.cvtColor(frame[:, :, :3], cv2.COLOR_BGR2GRAY)
    warped, inliers = aligned_mask(source, target, mask)
    if warped is None:
        return None, {"status": "registration_failed", "reference": reference.image,
                      "distance_m": distance_m, "yaw_error_deg": yaw_error_deg,
                      "inliers": inliers}
    return warped, {"status": "ready", "method": "orb_affine",
                    "reference": reference.image, "distance_m": distance_m,
                    "yaw_error_deg": yaw_error_deg, "inliers": inliers}


def audit(reference_dataset: Path, target_dataset: Path, destination: Path) -> dict:
    references = load_references(reference_dataset)
    rows = [json.loads(line) for line in (target_dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    approved = json.loads((target_dataset / "roi_approved.json").read_text(encoding="utf-8"))
    report: dict = {"reference_dataset": str(reference_dataset.resolve()),
                    "target_dataset": str(target_dataset.resolve()), "frames": len(rows),
                    "status_counts": {}, "category_counts": {}, "iou": []}
    for row in rows:
        frame = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
        if frame is None:
            raise FileNotFoundError(row["source_image"])
        mask, status = match_roi(frame, references, row["category"], row["station"],
                                 np.asarray(row["position_m"], np.float32), row["yaw_deg"])
        name = status["status"]
        report["status_counts"][name] = report["status_counts"].get(name, 0) + 1
        by_category = report["category_counts"].setdefault(row["category"], {})
        by_category[name] = by_category.get(name, 0) + 1
        if mask is not None:
            target_mask = cv2.imread(str(target_dataset / approved[row["image"]]["mask"]),
                                     cv2.IMREAD_GRAYSCALE)
            if target_mask is None:
                raise FileNotFoundError(row["image"])
            intersection = np.count_nonzero((mask > 0) & (target_mask > 0))
            union = np.count_nonzero((mask > 0) | (target_mask > 0))
            report["iou"].append(intersection / union if union else 0.0)
    report["iou_median"] = float(np.median(report["iou"])) if report["iou"] else None
    report["iou_min"] = float(np.min(report["iou"])) if report["iou"] else None
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {key: value for key, value in report.items() if key != "iou"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference_dataset", type=Path)
    parser.add_argument("target_dataset", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.reference_dataset, args.target_dataset,
                           args.destination), indent=2))


if __name__ == "__main__":
    main()
