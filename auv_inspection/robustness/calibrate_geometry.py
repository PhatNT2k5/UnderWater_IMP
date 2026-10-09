"""Fit camera/structure geometry to the reviewed ROI masks and save calibration/geometry_v1.json.

Fitted: pipe radius, pipe axis height, pier half-width, camera lateral offset and pitch.
Fixed at 0: camera forward and vertical offsets. With a single standoff in the clean data
they trade off exactly against pipe radius / pier width and pipe axis height respectively,
so fitting them would be unidentifiable.

Split by blocks so validation covers unseen route sections: pipe frames with x < 0 fit,
x >= 0 validate; pier levels 0-1 fit, levels 2-3 validate. Objective: mean (1 - IoU) on a
4-pixel grid. The reviewed masks are human-approved approximations (part ORB-propagated,
part geometric seeds), so IoU against them is an agreement score, not ground truth.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import minimize

from robustness.geometry import (
    CALIBRATION_FILE, DEFAULT_PARAMS, IMAGE_HEIGHT, IMAGE_WIDTH, GeometryParams, params_dict,
    render_hits)

DATASET = Path(__file__).resolve().parents[2] / "patchcore_artifacts/patchcore_dataset_clean_20260925"
FITTED = ("pipe_radius_m", "pipe_axis_z", "pier_half_width_m", "camera_lateral_m", "camera_pitch_deg")
BOUNDS = {"pipe_radius_m": (0.3, 0.8), "pipe_axis_z": (-10.8, -9.8), "pier_half_width_m": (0.6, 1.2),
          "camera_lateral_m": (-0.4, 0.4), "camera_pitch_deg": (-10.0, 10.0)}
GRID_STEP = 4


def load_frames(dataset: Path) -> list[dict]:
    approved = json.loads((dataset / "roi_approved.json").read_text(encoding="utf-8"))
    frames = []
    for line in (dataset / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = json.loads(line)
        entry = approved.get(row["image"])
        if not entry or entry.get("status") != "approved":
            continue
        mask = cv2.imread(str(dataset / entry["mask"]), cv2.IMREAD_GRAYSCALE)
        if mask is None or mask.shape != (IMAGE_HEIGHT, IMAGE_WIDTH):
            raise OSError(f"Bad mask for {row['image']}")
        offset = GRID_STEP // 2
        frames.append({**row, "truth": mask[offset::GRID_STEP, offset::GRID_STEP] > 0,
                       "split": split_of(row)})
    return frames


def split_of(row: dict) -> str:
    if row["category"].startswith("pipe_"):
        return "fit" if row["position_m"][0] < 0 else "validate"
    level = int(row["station"].split("_level_")[1].split("_")[0])
    return "fit" if level <= 1 else "validate"


def iou(frame: dict, params: GeometryParams) -> float:
    predicted = np.isfinite(render_hits(np.asarray(frame["position_m"]), frame["yaw_deg"],
                                        frame["category"], params, GRID_STEP))
    union = np.count_nonzero(predicted | frame["truth"])
    return np.count_nonzero(predicted & frame["truth"]) / union if union else 1.0


def with_values(values: np.ndarray) -> GeometryParams:
    return replace(DEFAULT_PARAMS, **{name: float(value) for name, value in zip(FITTED, values)})


def summarize(frames: list[dict], params: GeometryParams) -> dict:
    summary: dict = {}
    for split in ("fit", "validate"):
        for category in ("pipe_front", "pipe_back", "pier_0", "pier_1"):
            scores = [iou(frame, params) for frame in frames
                      if frame["split"] == split and frame["category"] == category]
            summary.setdefault(split, {})[category] = {
                "frames": len(scores), "iou_median": round(float(np.median(scores)), 4),
                "iou_p10": round(float(np.percentile(scores, 10)), 4)}
    return summary


def calibrate(dataset: Path) -> dict:
    frames = load_frames(dataset)
    fit = [frame for frame in frames if frame["split"] == "fit"]
    # Equal weight per structure group so 339 pier frames do not dominate the pipe.
    groups = {category: [frame for frame in fit if frame["category"] == category]
              for category in ("pipe_front", "pipe_back", "pier_0", "pier_1")}

    def loss(values: np.ndarray) -> float:
        params = with_values(values)
        return float(np.mean([1.0 - np.mean([iou(frame, params) for frame in group[::2]])
                              for group in groups.values()]))

    start = np.array([getattr(DEFAULT_PARAMS, name) for name in FITTED])
    result = minimize(loss, start, method="Powell", bounds=[BOUNDS[name] for name in FITTED],
                      options={"xtol": 1e-3, "ftol": 1e-4, "maxiter": 40})
    params = with_values(result.x)
    digest = hashlib.sha256()
    for name in ("manifest.jsonl", "roi_approved.json"):
        digest.update((dataset / name).read_bytes())
    return {
        "created": date.today().isoformat(),
        "dataset": dataset.name, "dataset_sha256": digest.hexdigest(),
        "grid_step_px": GRID_STEP, "fitted": list(FITTED),
        "fixed": {"camera_forward_m": 0.0, "camera_up_m": 0.0},
        "params": {name: round(value, 4) for name, value in params_dict(params).items()},
        "optimizer": {"method": "Powell", "loss": round(float(result.fun), 5),
                      "evaluations": int(result.nfev)},
        "before": summarize(frames, DEFAULT_PARAMS), "after": summarize(frames, params),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--output", type=Path, default=CALIBRATION_FILE)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Refusing to overwrite {args.output}; write a new version instead")
    report = calibrate(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("params", "optimizer", "before", "after")}, indent=2))


if __name__ == "__main__":
    main()
