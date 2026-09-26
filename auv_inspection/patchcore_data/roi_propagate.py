"""Propose surface masks from annotated keyframes without auto-approving them."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from .roi_seed import suggested_polygon


def transform_polygon(source: np.ndarray, target: np.ndarray,
                      polygon: list[list[int]]) -> tuple[np.ndarray | None, int]:
    """Estimate a small local affine camera motion from matched image features."""
    detector = cv2.ORB_create(nfeatures=1500)
    source_points, source_descriptors = detector.detectAndCompute(source, None)
    target_points, target_descriptors = detector.detectAndCompute(target, None)
    if source_descriptors is None or target_descriptors is None:
        return None, 0
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(source_descriptors, target_descriptors, k=2)
    good = [first for first, second in pairs if first.distance < 0.7 * second.distance]
    if len(good) < 12:
        return None, len(good)
    src = np.float32([source_points[match.queryIdx].pt for match in good])
    dst = np.float32([target_points[match.trainIdx].pt for match in good])
    matrix, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                                    ransacReprojThreshold=3.0)
    if matrix is None or inliers is None or int(inliers.sum()) < 10:
        return None, 0 if inliers is None else int(inliers.sum())
    transformed = cv2.transform(np.asarray(polygon, np.float32)[None], matrix)[0]
    return transformed, int(inliers.sum())


def propose(dataset: Path, reference_dataset: Path | None = None) -> dict:
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    reference_dataset = reference_dataset or dataset
    keyframes = json.loads((reference_dataset / "keyframes.json").read_text(encoding="utf-8"))
    polygons = json.loads((reference_dataset / "roi_polygons.json").read_text(encoding="utf-8"))
    approved_file = dataset / "roi_approved.json"
    approved = json.loads(approved_file.read_text(encoding="utf-8")) if approved_file.exists() else {}
    mask_dir = dataset / "roi_masks"
    mask_dir.mkdir(exist_ok=True)
    proposals: dict[str, dict] = {}
    for row in rows:
        same_group = [key for key in keyframes if key["category"] == row["category"]
                      and key["image"] in polygons]
        if not same_group:
            proposals[row["image"]] = {"status": "missing_keyframe"}
            continue
        reference = min(same_group, key=lambda key: (
            0 if key["station"] == row["station"] else 1,
            float(np.linalg.norm(np.asarray(key["position_m"]) - np.asarray(row["position_m"]))),
            abs(key["yaw_deg"] - row["yaw_deg"]),
        ))
        target = cv2.imread(row["source_image"], cv2.IMREAD_GRAYSCALE)
        if target is None:
            raise FileNotFoundError(row["source_image"])
        if reference_dataset.resolve() == dataset.resolve() and reference["image"] == row["image"]:
            points = np.asarray(polygons[reference["image"]], dtype=np.float32)
            inliers = -1
        else:
            source = cv2.imread(reference["source_image"], cv2.IMREAD_GRAYSCALE)
            if source is None:
                raise FileNotFoundError(reference["source_image"])
            points, inliers = transform_polygon(source, target, polygons[reference["image"]])
        method = "orb_affine"
        if points is None or len(points) < 3:
            color = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
            fallback = suggested_polygon(color, row["category"]) if color is not None else None
            if fallback is None:
                proposals[row["image"]] = {"status": "registration_failed",
                                            "reference": reference["image"], "inliers": inliers}
                continue
            points = np.asarray(fallback, dtype=np.float32)
            method = "geometry_fallback"
        mask = np.zeros(target.shape, dtype=np.uint8)
        cv2.fillPoly(mask, [np.round(points).astype(np.int32)], 255)
        color = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
        geometry = suggested_polygon(color, row["category"]) if color is not None else None
        if geometry is not None:
            geometry_mask = np.zeros_like(mask)
            cv2.fillPoly(geometry_mask, [np.asarray(geometry, np.int32)], 255)
            intersection = np.count_nonzero((mask > 0) & (geometry_mask > 0))
            union = np.count_nonzero((mask > 0) | (geometry_mask > 0))
            if union == 0 or intersection / union < 0.7:
                mask = geometry_mask
                method = "geometry_fallback"
        if np.count_nonzero(mask) < 1000:
            if geometry is None:
                proposals[row["image"]] = {"status": "insufficient_surface",
                                            "reference": reference["image"], "inliers": inliers}
                continue
            mask.fill(0)
            cv2.fillPoly(mask, [np.asarray(geometry, np.int32)], 255)
            method = "geometry_fallback"
        relative_mask = Path("roi_masks") / f"{row['category']}_{row['tick']:06d}.png"
        cv2.imwrite(str(dataset / relative_mask), mask)
        proposals[row["image"]] = {"status": "proposed", "mask": relative_mask.as_posix(),
                                    "reference": reference["image"], "inliers": inliers,
                                    "method": method}
        if reference_dataset.resolve() == dataset.resolve() and reference["image"] == row["image"]:
            approved[row["image"]] = {"status": "approved", "mask": relative_mask.as_posix(),
                                      "reviewer": "keyframe_polygon"}
    (dataset / "roi_proposals.json").write_text(json.dumps(proposals, indent=2), encoding="utf-8")
    approved_file.write_text(json.dumps(approved, indent=2), encoding="utf-8")
    return {status: sum(item["status"] == status for item in proposals.values())
            for status in ("proposed", "missing_keyframe", "registration_failed",
                           "insufficient_surface")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--reference-dataset", type=Path,
                        help="Approved clean dataset supplying polygons for a new capture")
    args = parser.parse_args()
    print(json.dumps(propose(args.dataset, args.reference_dataset), indent=2))


if __name__ == "__main__":
    main()
