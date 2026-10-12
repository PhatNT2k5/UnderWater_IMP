"""Calibrate the surface alert rule (P5) from clean calibration captures.

For every calibration capture the frames are scored exactly as in the live service (geometric
ROI, 24 px margin, diffuse-anomaly abstention) and folded into surface cells with the runtime
view rule. Each clean cell with at least VIEWS_REQUIRED views contributes its k-th highest
normalised view value, i.e. the stratum threshold at which that clean cell would alert on the
normalised statistic alone.

The runtime hit is the AND of this stratum threshold and the locked pixel threshold. The two are
calibrated separately on purpose: on clean calibration runs no cell reaches k pixel-threshold
hits, so calibrating the joint statistic sets every stratum threshold to 0 and the rule falls
back to the pixel threshold alone (11-32 false alerts per development capture under turbidity
and blur). Each threshold keeps its own level alpha, so their AND keeps it as well.

Threshold per stratum (structure group x element) is the conformal upper quantile at the
per-cell level alpha = budget / (evaluated cells per 100 m), so that the expected number of
clean cells reaching the rule stays within the false-alert budget per 100 m surveyed. With m
calibration cells a conformal p-value cannot go below 1 / (m + 1); a stratum too small for alpha
gets the smallest threshold above all its calibration values and is marked `data_limited` with
the level it actually achieves.

Caveats written into the output: cells of one run are spatially correlated; the guarantee holds
only for conditions exchangeable with the calibration runs (train profile), not for the
held-out conditions, which the benchmark measures instead.
Run in .venv-patchcore (scores with PatchCore).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

INSPECTION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSPECTION))
sys.path.insert(0, str(INSPECTION.parent))
from robustness.geometric_roi import category_from_pose  # noqa: E402
from robustness.metrics import surveyed_length_m  # noqa: E402
from robustness.surface_evidence import (  # noqa: E402
    CALIBRATION_FILE, CELL_M, MIN_MOVE_M, POOL_PX, VIEWS_REQUIRED, frame_cells, stratum)

FALSE_CELLS_PER_100M = 0.5  # half of the acceptance limit (1 false alert / 100 m), chosen up front
MODEL_DIR = INSPECTION / "output/patchcore_model_v1"
REFERENCE = INSPECTION / "output/patchcore_dataset_clean_20260925"
THRESHOLDS = INSPECTION / "output/patchcore_thresholds_v1.json"


def kth_highest(values: list[float], k: int = VIEWS_REQUIRED) -> float:
    return float(np.sort(values)[-k])


def conformal_threshold(values: np.ndarray, alpha: float) -> tuple[float, float, bool]:
    """Smallest threshold whose conformal p-value bound is <= alpha.

    Returns (threshold, achieved level, data_limited). A new clean value reaches the threshold
    with probability at most (1 + allowed) / (m + 1) under exchangeability.
    """
    m = len(values)
    if m == 0:
        raise ValueError("No calibration cells in stratum")
    descending = np.sort(values)[::-1]
    allowed = int(np.floor(alpha * (m + 1))) - 1   # calibration values allowed at or above t
    if allowed < 0:
        limit, level, limited = descending[0], 1.0 / (m + 1), True
    else:
        limit, level, limited = descending[allowed], (allowed + 1) / (m + 1), False
    # -inf: too few clean cells reach k pixel-threshold hits to need a stratum threshold at all.
    return (float(np.nextafter(limit, np.inf)) if np.isfinite(limit) else 0.0), level, limited


def capture_cells(session: object, capture: Path) -> tuple[dict, list[list[float]], dict]:
    """Per-cell normalised view values of one clean capture, analysed positions, status counts."""
    from auv_inspection.patchcore_data.live_service import score_request
    report = json.loads((capture / "report.json").read_text(encoding="utf-8"))
    if report.get("scene_state") != "clean":
        raise ValueError(f"Calibration captures must be clean: {capture}")
    rows = sorted((json.loads(line) for line in (capture / "frames.jsonl").read_text(
        encoding="utf-8").splitlines() if line), key=lambda row: row["tick"])
    views: dict = defaultdict(list)
    last: dict = {}
    positions: list[list[float]] = []
    status: dict[str, int] = defaultdict(int)
    for row in rows:
        position = np.asarray(row["position_m"], float)
        category = category_from_pose(position, float(row["yaw_deg"]), session.geometry)
        if category is None:
            status["no_structure"] += 1
            continue
        frame = cv2.imread(str(capture / row["image"]), cv2.IMREAD_COLOR)
        if frame is None:
            raise OSError(f"Cannot read {row['image']}")
        request = {"tick": row["tick"], "category": category, "station": row["station"],
                   "position_m": row["position_m"], "yaw_deg": row["yaw_deg"]}
        response, _, scores, _ = score_request(session, request, frame, 0.0)
        if scores is None:
            status[response.get("reason", "unavailable")] += 1
            continue
        status["analysed"] += 1
        positions.append(row["position_m"])
        values, _, _ = frame_cells(scores, position, float(row["yaw_deg"]), category, session.geometry)
        for key, (_, normalised) in values.items():
            if key in last and np.linalg.norm(position - last[key]) < MIN_MOVE_M:
                continue
            last[key] = position
            views[key].append(normalised)
    return dict(views), positions, dict(status)


def calibrate(captures: list[Path], destination: Path, model_dir: Path = MODEL_DIR,
              thresholds: Path = THRESHOLDS) -> dict:
    from auv_inspection.patchcore_data.live_service import DEFAULT_SCORE_MARGIN_PX, create_session
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    session = create_session(model_dir, REFERENCE, thresholds, "geometry", DEFAULT_SCORE_MARGIN_PX, True)
    per_stratum: dict[str, list[float]] = defaultdict(list)
    evaluated, length, sources = 0, 0.0, []
    for capture in captures:
        views, positions, status = capture_cells(session, capture)
        report = json.loads((capture / "report.json").read_text(encoding="utf-8"))
        cells = {key: values for key, values in views.items() if len(values) >= VIEWS_REQUIRED}
        for key, values in cells.items():
            per_stratum[stratum(key[0], (key[1] + 0.5) * CELL_M)].append(kth_highest(values))
        run_length = surveyed_length_m(positions)
        evaluated += len(cells)
        length += run_length
        sources.append({"capture": str(capture), "map_sha256": report.get("map_sha256"),
                        "conditions": report.get("conditions"), "frames": status,
                        "evaluated_cells": len(cells), "surveyed_length_m": round(run_length, 1)})
        print(json.dumps({"capture": capture.name, "cells": len(cells), "length_m": round(run_length, 1),
                          "frames": status}), flush=True)
    if length <= 0:
        raise ValueError("Calibration captures surveyed no structure")
    cells_per_100m = 100 * evaluated / length
    alpha = FALSE_CELLS_PER_100M / cells_per_100m
    strata = {}
    for name, values in sorted(per_stratum.items()):
        threshold, level, limited = conformal_threshold(np.asarray(values), alpha)
        strata[name] = {"threshold": round(threshold, 6), "cells": len(values),
                        "achieved_level": level, "data_limited": limited,
                        "calibration_p50": round(float(np.median(values)), 4),
                        "calibration_max": round(float(np.max(values)), 4)}
    result = {
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "cell_m": CELL_M, "pool_px": POOL_PX, "min_move_m": MIN_MOVE_M, "views_required": VIEWS_REQUIRED,
        "statistic": "k-th highest per-view cell max / frame median score",
        "hit_rule": "cell max >= pixel threshold AND cell max / frame median >= stratum threshold",
        "false_cells_per_100m_budget": FALSE_CELLS_PER_100M,
        "evaluated_cells": evaluated, "surveyed_length_m": round(length, 1),
        "cells_per_100m": round(cells_per_100m, 1), "alpha_per_cell": alpha,
        "model_dir": str(model_dir),
        "pixel_thresholds_sha256": hashlib.sha256(thresholds.read_bytes()).hexdigest(),
        "score_margin_px": DEFAULT_SCORE_MARGIN_PX, "diffuse_gate": True,
        "sources": sources, "strata": strata,
        "caveats": ["cells of one run are spatially correlated; runs are the independent units",
                    "conformal level holds only for conditions exchangeable with the calibration runs"],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("captures", nargs="+", type=Path, help="Clean calibration capture folders")
    parser.add_argument("--output", type=Path, default=CALIBRATION_FILE)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR,
                        help="PatchCore v1 (default) or a detector_v2 model directory")
    parser.add_argument("--thresholds", type=Path, default=THRESHOLDS,
                        help="Pixel thresholds of that model (v2: <model_dir>/pixel_thresholds.json)")
    args = parser.parse_args()
    result = calibrate(args.captures, args.output, args.model_dir, args.thresholds)
    print(json.dumps({name: {key: item[key] for key in ("threshold", "cells", "data_limited")}
                      for name, item in result["strata"].items()}, indent=2))


if __name__ == "__main__":
    main()
