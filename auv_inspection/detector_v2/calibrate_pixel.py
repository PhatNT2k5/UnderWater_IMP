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
from robustness.degradation import PIPELINE_ORDER, Degradation, apply_degradations  # noqa: E402
from robustness.geometric_roi import category_from_pose, geometric_roi  # noqa: E402
from robustness.geometry import params_dict  # noqa: E402
from robustness.metrics import surveyed_length_m  # noqa: E402
from robustness.surface_evidence import MIN_MOVE_M, VIEWS_REQUIRED, frame_cells  # noqa: E402

from .build_bank import AUGMENT_SEVERITY  # noqa: E402
from .scorer import load_scorer  # noqa: E402

SCORE_MARGIN_PX = 24  # live_service.DEFAULT_SCORE_MARGIN_PX (not imported to keep this torch-light)


def capture_cells(scorer, params, capture: Path, degradation: Degradation | None = None
                  ) -> tuple[dict, float, dict]:
    """Per clean cell with >= VIEWS_REQUIRED separated views: its k-th highest absolute cell maximum."""
    from auv_inspection.patchcore_data.live_service import interior
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
        if degradation is not None:
            frame = apply_degradations(frame, [degradation], int(row["tick"]))
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
    cells = {key: kth_highest(value) for key, value in views.items() if len(value) >= VIEWS_REQUIRED}
    return cells, surveyed_length_m(positions), report


def calibrate(model_dir: Path, captures: list[Path], destination: Path, severity1: bool = False) -> dict:
    """Pixel thresholds; with `severity1` the strict thresholds of P9 instead: each clean cell's
    statistic is its maximum over every degradation factor at severity 1 (the level the bank was
    augmented with), so a score above them is unusual even under mild environmental change."""
    from auv_inspection.patchcore_data.live_service import model_geometry
    if destination.exists():
        raise FileExistsError(destination)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    scorer = load_scorer(model_dir, device)
    params = model_geometry(model_dir)  # the ROI geometry the model is scored with
    variants = ([Degradation(factor, AUGMENT_SEVERITY) for factor in PIPELINE_ORDER] if severity1 else [None])
    per_group: dict[str, list[float]] = defaultdict(list)
    evaluated, length, sources = 0, 0.0, []
    for capture in captures:
        combined: dict = {}
        run_length, report = 0.0, {}
        for degradation in variants:
            cells, run_length, report = capture_cells(scorer, params, capture, degradation)
            for key, value in cells.items():
                combined[key] = max(combined.get(key, -np.inf), value)
            print(json.dumps({"capture": capture.name, "degradation": degradation.factor if degradation else None,
                              "cells": len(cells)}), flush=True)
        for key, value in combined.items():
            per_group[key[0]].append(value)
        evaluated += len(combined)
        length += run_length
        sources.append({"capture": str(capture), "map_sha256": report.get("map_sha256"),
                        "evaluated_cells": len(combined), "surveyed_length_m": round(run_length, 1)})
        print(json.dumps(sources[-1]), flush=True)
    alpha = FALSE_CELLS_PER_100M / (100 * evaluated / length)
    groups = {}
    for group, values in sorted(per_group.items()):
        threshold, level, limited = conformal_threshold(np.asarray(values), alpha)
        groups[group] = {"threshold": threshold, "cells": len(values), "achieved_level": level,
                         "data_limited": limited, "calibration_p50": float(np.median(values)),
                         "calibration_max": float(np.max(values))}
    method = "conformal upper quantile of the per-cell k-th highest absolute score"
    if severity1:
        method += (", per cell the maximum over every degradation factor at severity "
                   f"{AUGMENT_SEVERITY} ({', '.join(PIPELINE_ORDER)})")
    result = {"model_dir": str(model_dir.resolve()),
              "created": datetime.now().astimezone().isoformat(timespec="seconds"),
              "kind": "strict" if severity1 else "pixel", "method": method,
              "views_required": VIEWS_REQUIRED, "min_move_m": MIN_MOVE_M, "score_margin_px": SCORE_MARGIN_PX,
              "alpha_per_cell": alpha, "geometry": params_dict(params), "evaluated_cells": evaluated, "surveyed_length_m": round(length, 1),
              "sources": sources, "groups": groups}
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--strict", action="store_true",
                        help="P9 strict thresholds (max over severity-1 degradations); default output "
                             "<model_dir>/strict_thresholds.json")
    parser.add_argument("--output", type=Path, help="Default: <model_dir>/pixel_thresholds.json")
    args = parser.parse_args()
    default = "strict_thresholds.json" if args.strict else "pixel_thresholds.json"
    result = calibrate(args.model_dir, args.captures, args.output or args.model_dir / default, args.strict)
    print(json.dumps({group: item["threshold"] for group, item in result["groups"].items()}, indent=2))


if __name__ == "__main__":
    main()
