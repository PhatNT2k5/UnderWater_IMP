"""Base per-view hit rate of clean surface cells for the frame-adaptive evidence of P9.

Scores clean calibration captures with exactly the runtime rules of a model (ROI, margins, gate,
region-filtered evidence, as `create_session` is given them), folds every analysed frame into surface
cells and counts the cells at hit level. The base rate is pooled hits / pooled cell views; the live
service's `NoiseModel` weighs a hit by how much its frame's own hit rate exceeds this rate. No
threshold is tuned on defect data. Run in .venv-patchcore.

    python -m auv_inspection.robustness.calibrate_noise <model_dir> <clean calibration capture>... [--p8-rules]
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "auv_inspection"))
from robustness.geometric_roi import category_from_pose  # noqa: E402
from robustness.surface_evidence import frame_cells, is_hit  # noqa: E402

REFERENCE = ROOT / "auv_inspection/output/patchcore_dataset_clean_20260925"
RADIUS_M = 0.6  # the alert merge radius: hits nearer than this to a cell can be the same defect


def calibrate(model_dir: Path, captures: list[Path], destination: Path, p8_rules: bool,
              severity1: bool = False) -> dict:
    """With `severity1` every frame is scored once per degradation factor at severity 1 (the bank's
    augmentation level) and the rate is pooled over all of them."""
    from auv_inspection.patchcore_data.live_service import (
        DEFAULT_SCORE_MARGIN_PX, GATE_MIN_REGION_PX, create_session, score_request, without_small_hits)
    if destination.exists():
        raise FileExistsError(destination)
    rules = dict(gate_min_region_px=GATE_MIN_REGION_PX, gate_region_share=False,
                 evidence_min_region_px=GATE_MIN_REGION_PX, gate_spread_all_regions=True) if p8_rules else {}
    thresholds_file = model_dir / "pixel_thresholds.json"
    session = create_session(model_dir, REFERENCE, thresholds_file, "geometry", DEFAULT_SCORE_MARGIN_PX, True,
                             "surface", model_dir / "surface_calibration.json", border_margin=True, **rules)
    calibration = session.evidence.calibration
    from robustness.degradation import PIPELINE_ORDER, Degradation, apply_degradations
    from auv_inspection.detector_v2.build_bank import AUGMENT_SEVERITY
    variants = [Degradation(factor, AUGMENT_SEVERITY) for factor in PIPELINE_ORDER] if severity1 else [None]
    cells = hits = frames = gated = 0
    sources = []
    for capture, degradation in ((c, d) for c in captures for d in variants):
        report = json.loads((capture / "report.json").read_text(encoding="utf-8"))
        if report.get("scene_state") != "clean" or report.get("dataset_role") != "calibration":
            raise ValueError(f"Noise calibration needs clean calibration captures: {capture}")
        start, capture_cells, capture_hits = time.time(), 0, 0
        for row in sorted(map(json.loads, (capture / "frames.jsonl").open(encoding="utf-8")), key=lambda r: r["tick"]):
            position, yaw = np.asarray(row["position_m"], float), float(row["yaw_deg"])
            category = category_from_pose(position, yaw, session.geometry)
            if category is None:
                continue
            request = {"tick": row["tick"], "category": category, "station": row["station"],
                       "position_m": row["position_m"], "yaw_deg": yaw}
            frame = cv2.imread(str(capture / row["image"]), cv2.IMREAD_COLOR)
            if degradation is not None:
                frame = apply_degradations(frame, [degradation], int(row["tick"]))
            response, _, scores, _ = score_request(session, request, frame, time.perf_counter())
            if scores is None:
                gated += response.get("reason") == "diffuse_anomaly"
                continue
            if session.evidence_min_region_px:
                scores = without_small_hits(scores, session.thresholds[category], calibration.lowest_threshold(category),
                                            session.evidence_min_region_px)
            values, _, _ = frame_cells(scores, position, yaw, category, session.geometry)
            frames += 1
            capture_cells += len(values)
            capture_hits += sum(is_hit(v, session.thresholds[category], calibration.threshold(k)) for k, v in values.items())
        cells += capture_cells
        hits += capture_hits
        sources.append({"capture": str(capture), "degradation": degradation.factor if degradation else None,
                        "map_sha256": report.get("map_sha256"), "cell_views": capture_cells, "hits": capture_hits})
        print(json.dumps({**sources[-1], "seconds": round(time.time() - start)}), flush=True)
    if hits == 0:
        raise ValueError("No clean hits: the base rate cannot be estimated")
    result = {"model_dir": str(model_dir.resolve()), "created": datetime.now().astimezone().isoformat(timespec="seconds"),
              "method": "pooled per-view hit rate of clean calibration cells under the runtime rules",
              "base_hit_rate": hits / cells, "radius_m": RADIUS_M, "cell_views": cells, "hits": hits,
              "frames": frames, "frames_gated": gated, "p8_rules": p8_rules,
              "severity1": severity1,
              "pixel_thresholds_sha256": hashlib.sha256(thresholds_file.read_bytes()).hexdigest(),
              "sources": sources}
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--p8-rules", action="store_true", help="Score with the P8 gate and evidence rules")
    parser.add_argument("--severity1", action="store_true",
                        help="Pool the rate over every degradation factor at severity 1; default output "
                             "<model_dir>/noise_calibration_severity1.json")
    parser.add_argument("--output", type=Path, help="Default: <model_dir>/noise_calibration.json")
    args = parser.parse_args()
    default = "noise_calibration_severity1.json" if args.severity1 else "noise_calibration.json"
    result = calibrate(args.model_dir, args.captures, args.output or args.model_dir / default,
                       args.p8_rules, args.severity1)
    print(json.dumps({key: result[key] for key in ("base_hit_rate", "cell_views", "hits", "frames_gated")}))


if __name__ == "__main__":
    main()
