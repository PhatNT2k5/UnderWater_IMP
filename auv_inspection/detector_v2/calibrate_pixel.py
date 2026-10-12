"""Per-group absolute score thresholds for a v2 model from clean calibration captures (P4).

v1 kept its locked PatchCore thresholds; a new feature space needs its own. The statistic matches
the surface rule: every clean cell with at least VIEWS_REQUIRED separated views contributes its
k-th highest cell maximum (geometric ROI, 24 px margin, no diffuse gate since the gate itself
needs these thresholds). The threshold per structure group is the conformal upper quantile at the
same per-cell level as `robustness/calibrate_surface.py`. The output has the v1 thresholds-file
shape (`model_dir`, `groups.<group>.threshold`) so the live service loads it unchanged; the
relative stratum thresholds are calibrated afterwards with `calibrate_surface.py --model-dir`.
Run in .venv-patchcore.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import sys

import cv2
import numpy as np
import torch

INSPECTION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSPECTION))
from robustness.calibrate_surface import FALSE_CELLS_PER_100M, conformal_threshold, kth_highest  # noqa: E402
from robustness.geometric_roi import category_from_pose, geometric_roi  # noqa: E402
from robustness.geometry import load_params  # noqa: E402
from robustness.metrics import surveyed_length_m  # noqa: E402
from robustness.surface_evidence import MIN_MOVE_M, VIEWS_REQUIRED, frame_cells  # noqa: E402

from .scorer import load_scorer  # noqa: E402

SCORE_MARGIN_PX = 24  # live_service.DEFAULT_SCORE_MARGIN_PX (not imported to keep this torch-light)


def calibrate(model_dir: Path, captures: list[Path], destination: Path) -> dict:
    from auv_inspection.patchcore_data.live_service import interior
    if destination.exists():
        raise FileExistsError(destination)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    scorer = load_scorer(model_dir, device)
    params = load_params()
    per_group: dict[str, list[float]] = defaultdict(list)
    evaluated, length, sources = 0, 0.0, []
    for capture in captures:
        report = json.loads((capture / "report.json").read_text(encoding="utf-8"))
        if report.get("scene_state") != "clean" or report.get("dataset_role") != "calibration":
            raise ValueError(f"Pixel thresholds need clean calibration captures: {capture}")
        rows = sorted((json.loads(line) for line in (capture / "frames.jsonl").read_text(
            encoding="utf-8").splitlines() if line), key=lambda row: row["tick"])
        views: dict = defaultdict(list)
        last: dict = {}
        positions = []
        for row in rows:
            position, yaw = np.asarray(row["position_m"], float), float(row["yaw_deg"])
            category = category_from_pose(position, yaw, params)
            roi = geometric_roi(position, yaw, category, params)[0] if category else None
            if roi is None:
                continue
            frame = cv2.imread(str(capture / row["image"]), cv2.IMREAD_COLOR)
            scores = scorer(frame, roi, category)
            scores[~interior(roi, SCORE_MARGIN_PX)] = np.nan
            if not np.isfinite(scores).any():
                continue
            positions.append(row["position_m"])
            values, _, _ = frame_cells(scores, position, yaw, category, params)
            for key, (score, _) in values.items():
                if key in last and np.linalg.norm(position - last[key]) < MIN_MOVE_M:
                    continue
                last[key] = position
                views[key].append(score)
        cells = {key: value for key, value in views.items() if len(value) >= VIEWS_REQUIRED}
        for key, value in cells.items():
            per_group[key[0]].append(kth_highest(value))
        run_length = surveyed_length_m(positions)
        evaluated += len(cells)
        length += run_length
        sources.append({"capture": str(capture), "map_sha256": report.get("map_sha256"),
                        "evaluated_cells": len(cells), "surveyed_length_m": round(run_length, 1)})
        print(json.dumps(sources[-1]), flush=True)
    alpha = FALSE_CELLS_PER_100M / (100 * evaluated / length)
    groups = {}
    for group, values in sorted(per_group.items()):
        threshold, level, limited = conformal_threshold(np.asarray(values), alpha)
        groups[group] = {"threshold": threshold, "cells": len(values), "achieved_level": level,
                         "data_limited": limited, "calibration_p50": float(np.median(values)),
                         "calibration_max": float(np.max(values))}
    result = {"model_dir": str(model_dir.resolve()),
              "created": datetime.now().astimezone().isoformat(timespec="seconds"),
              "method": "conformal upper quantile of the per-cell k-th highest absolute score",
              "views_required": VIEWS_REQUIRED, "min_move_m": MIN_MOVE_M, "score_margin_px": SCORE_MARGIN_PX,
              "alpha_per_cell": alpha, "evaluated_cells": evaluated, "surveyed_length_m": round(length, 1),
              "sources": sources, "groups": groups}
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, help="Default: <model_dir>/pixel_thresholds.json")
    args = parser.parse_args()
    result = calibrate(args.model_dir, args.captures, args.output or args.model_dir / "pixel_thresholds.json")
    print(json.dumps({group: item["threshold"] for group, item in result["groups"].items()}, indent=2))


if __name__ == "__main__":
    main()
