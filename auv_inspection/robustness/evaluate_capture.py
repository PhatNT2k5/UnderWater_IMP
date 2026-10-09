"""Replay a capture through a detector, optionally degraded, and score it per physical defect.

Metrics (GENERALIZATION_PLAN.md section 5): recall over observable physical defects, false
alerts per 100 m surveyed, frame-level flag rate on frames with no defect in view (Wilson
95%), analysis availability per structure group, and processing time. Runtime alert logic is
mirrored: three-frame confirmation inside each detector and a 2 m re-arm distance.

Caveats recorded in every result: capture frames are sampled every few ticks (not every tick
as at runtime), consecutive frames are correlated so Wilson intervals are indicative, and
defect visibility is geometric (lighting is not modelled).
Run in .venv-patchcore (needs torch for PatchCore; Classical needs only OpenCV).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
import time
from typing import Callable

import cv2
import numpy as np

INSPECTION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSPECTION))
sys.path.insert(0, str(INSPECTION.parent))
from crack_detection import CrackTracker, analyze_frame  # noqa: E402
from robustness.defect_inventory import (  # noqa: E402
    Inventory, defects_in_view, load_inventory, locate_box, match_defect)
from robustness.degradation import Degradation, apply_degradations, parse_degradation  # noqa: E402
from robustness.geometric_roi import (  # noqa: E402
    DEFAULT_POSE_SIGMA_M, DEFAULT_POSE_SIGMA_YAW_DEG, category_from_pose)
from robustness.geometry import load_params, params_dict  # noqa: E402

GEOMETRY = load_params()  # calibrated if calibration/geometry_v1.json exists
from robustness.metrics import fraction, rate_per_100m, surveyed_length_m  # noqa: E402

REARM_DISTANCE_M = 2.0
MIN_VIEWS_OBSERVABLE = 3
PATCHCORE_MODEL = INSPECTION / "output/patchcore_model_v1"
PATCHCORE_REFERENCE = INSPECTION / "output/patchcore_dataset_clean_20260925"
PATCHCORE_THRESHOLDS = INSPECTION / "output/patchcore_thresholds_v1.json"


@dataclass(frozen=True)
class FrameResult:
    available: bool                  # the detector analysed this frame
    flagged: bool                    # at least one above-threshold candidate (before tracking)
    alert_bbox: list[int] | None     # confirmed alert box in this frame
    category: str | None = None      # structure group the detector used, if it chose one
    reason: str | None = None        # why an unavailable frame was not analysed, if known


Detector = Callable[[np.ndarray, dict], FrameResult]


def classical_detector() -> Detector:
    """Runtime gate: pipe scans only; tracker resets when leaving the pipe or after an alert."""
    tracker = CrackTracker()
    state = {"category": None}

    def step(frame: np.ndarray, row: dict) -> FrameResult:
        if row["category"] not in ("pipe_front", "pipe_back"):
            tracker.reset()
            return FrameResult(False, False, None)
        if row["category"] != state["category"]:
            tracker.reset()
            state["category"] = row["category"]
        analysis = analyze_frame(frame)
        candidate = tracker.update(analysis)
        if candidate is not None:
            tracker.reset()
        return FrameResult(True, bool(analysis.candidates),
                           list(candidate.bbox) if candidate is not None else None)

    return step


def patchcore_detector(model_dir: Path, reference: Path, thresholds: Path,
                       roi_mode: str = "reference", score_margin_px: int = 0,
                       diffuse_gate: bool = False) -> Detector:
    """reference: P0/v1.1 ROI and capture categories; geometry: P2 ROI and pose-derived groups."""
    from auv_inspection.patchcore_data.live_service import (
        analyze_request, create_session, encode_png)
    session = create_session(model_dir, reference, thresholds, roi_mode, score_margin_px, diffuse_gate)

    def step(frame: np.ndarray, row: dict) -> FrameResult:
        category = row["category"]
        if roi_mode == "geometry":
            category = category_from_pose(np.asarray(row["position_m"]), row["yaw_deg"], session.geometry)
            if category is None:
                return FrameResult(False, False, None)
        request = {"tick": row["tick"], "category": category, "station": row["station"],
                   "position_m": row["position_m"], "yaw_deg": row["yaw_deg"],
                   "camera_png_b64": encode_png(frame)}
        for key in ("pose_sigma_m", "pose_sigma_yaw_deg"):
            if key in row:
                request[key] = row[key]
        response = analyze_request(session, request)
        if response["status"] != "ready":
            return FrameResult(False, False, None, category, response.get("reason"))
        alerts = response["alerts"]
        return FrameResult(True, bool(response["candidates"]),
                           alerts[0]["bbox_xywh"] if alerts else None, category)

    return step


DETECTORS = ("classical", "patchcore", "patchcore_geo", "patchcore_geo_m", "patchcore_geo_md")


def make_detector(name: str) -> Detector:
    """classical; patchcore = v1.1 reference ROI; patchcore_geo = P2 geometric ROI;
    _m adds the P3 scoring margin; _md adds the margin and the diffuse-anomaly gate."""
    if name == "classical":
        return classical_detector()
    if name == "patchcore":
        return patchcore_detector(PATCHCORE_MODEL, PATCHCORE_REFERENCE, PATCHCORE_THRESHOLDS, "reference")
    if name.startswith("patchcore_geo") and name in DETECTORS:
        from auv_inspection.patchcore_data.live_service import DEFAULT_SCORE_MARGIN_PX
        return patchcore_detector(PATCHCORE_MODEL, PATCHCORE_REFERENCE, PATCHCORE_THRESHOLDS, "geometry",
                                  DEFAULT_SCORE_MARGIN_PX if name.endswith(("_m", "_md")) else 0,
                                  name.endswith("_md"))
    raise ValueError(f"Unknown detector {name!r}; choose from {DETECTORS}")


def perceived_pose(row: dict, pose_noise: tuple[float, float], seed: int) -> dict:
    """Pose given to the detector: true pose plus seeded navigation error (D14).

    The detector is told its uncertainty, as a real navigation filter would report it.
    """
    sigma_m, sigma_yaw = pose_noise
    if not sigma_m and not sigma_yaw:
        return row
    rng = np.random.default_rng([seed, int(row["tick"])])
    noisy = dict(row)
    noisy["position_m"] = (np.asarray(row["position_m"], float) + rng.normal(0, sigma_m, 3)).tolist()
    noisy["yaw_deg"] = float(row["yaw_deg"]) + float(rng.normal(0, sigma_yaw))
    noisy["pose_sigma_m"] = max(sigma_m, DEFAULT_POSE_SIGMA_M)
    noisy["pose_sigma_yaw_deg"] = max(sigma_yaw, DEFAULT_POSE_SIGMA_YAW_DEG)
    return noisy


def load_capture(capture: Path) -> tuple[list[dict], dict]:
    report = json.loads((capture / "report.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (capture / "frames.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    return sorted(rows, key=lambda row: row["tick"]), report


@dataclass
class Score:
    """Per-detector accumulators while frames are replayed once for all detectors."""
    status: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    negatives: int = 0
    flagged_negatives: int = 0
    events: list[dict] = field(default_factory=list)
    last_alert: np.ndarray | None = None
    elapsed: list[float] = field(default_factory=list)


def record(score: Score, result: FrameResult, row: dict, perceived: dict, visible: list[str],
           defects: tuple, elapsed_ms: float) -> None:
    category = row["category"]
    if result.available:  # skipped frames cost ~0 ms and would hide the real latency
        score.elapsed.append(elapsed_ms)
    status = "analysed" if result.available else "unavailable"
    if not result.available and result.reason == "diffuse_anomaly":
        status = "diffuse_anomaly"  # an abstention the operator sees, unlike missing geometry
    score.status[category][status] += 1
    if result.available and not visible:
        score.negatives += 1
        score.flagged_negatives += result.flagged
    if result.alert_bbox is None:
        return
    believed = np.asarray(perceived["position_m"], float)
    if score.last_alert is not None and np.linalg.norm(believed - score.last_alert) < REARM_DISTANCE_M:
        return
    score.last_alert = believed
    alert_category = result.category or category
    point = locate_box(result.alert_bbox, believed, float(perceived["yaw_deg"]), alert_category, GEOMETRY)
    score.events.append({"tick": row["tick"], "category": alert_category, "bbox_xywh": result.alert_bbox,
                         "world_m": None if point is None else np.round(point, 3).tolist(),
                         "defect": match_defect(point, alert_category, defects)})


def evaluate_many(capture: Path, detectors: dict[str, Detector], inventory: Inventory | None,
                  degradations: list[Degradation], seed: int,
                  pose_noise: tuple[float, float] = (0.0, 0.0)) -> dict[str, dict]:
    """Replay each frame once (one degradation) through every detector.

    Ground truth (visibility, negatives, groups) uses the true pose; the detectors and the
    alert localization use the perceived pose, as on a real AUV.
    """
    rows, report = load_capture(capture)
    if inventory is not None and inventory.map_sha256 != report.get("map_sha256"):
        raise ValueError("Inventory map hash does not match the capture map")
    if inventory is None and report.get("scene_state") != "clean":
        raise ValueError("Captures of mixed scenes need a defect inventory")
    defects = inventory.defects if inventory else ()
    views: Counter[str] = Counter()
    positions: dict[str, list[list[float]]] = defaultdict(list)
    scores = {name: Score() for name in detectors}
    for row in rows:
        frame = cv2.imread(str(capture / row["image"]), cv2.IMREAD_COLOR)
        if frame is None:
            raise OSError(f"Cannot read {row['image']}")
        if degradations:
            frame = apply_degradations(frame, degradations, seed + int(row["tick"]))
        camera, yaw, category = np.asarray(row["position_m"], float), float(row["yaw_deg"]), row["category"]
        positions[category].append(row["position_m"])
        visible = defects_in_view(defects, camera, yaw, category, GEOMETRY)
        views.update(visible)
        perceived = perceived_pose(row, pose_noise, seed)
        for name, detector in detectors.items():
            start = time.perf_counter()
            result = detector(frame, perceived)
            record(scores[name], result, row, perceived, visible, defects,
                   (time.perf_counter() - start) * 1000)
    observable = [defect.defect_id for defect in defects if views[defect.defect_id] >= MIN_VIEWS_OBSERVABLE]
    length = sum(surveyed_length_m(items) for items in positions.values())
    results = {}
    for name, score in scores.items():
        detected = sorted({event["defect"] for event in score.events if event["defect"]} & set(observable))
        false_alerts = [event for event in score.events if event["defect"] is None]
        results[name] = {
            "capture": str(capture), "detector": name, "seed": seed,
            "pose_noise": {"sigma_m": pose_noise[0], "sigma_yaw_deg": pose_noise[1]},
            "geometry": params_dict(GEOMETRY),
            "degradations": [{"factor": item.factor, "severity": item.severity} for item in degradations],
            "conditions": report.get("conditions"), "frames": len(rows),
            "defects": {"observable": observable, "detected": detected,
                        "views": dict(views), "recall": fraction(len(detected), len(observable))},
            "false_alerts": len(false_alerts), "surveyed_length_m": round(length, 1),
            "false_alerts_per_100m": rate_per_100m(len(false_alerts), length),
            "frame_flag_rate_without_defect": fraction(score.flagged_negatives, score.negatives),
            "availability": {key: dict(value) for key, value in score.status.items()},
            "processing_ms_median": float(np.median(score.elapsed)) if score.elapsed else None,
            "timing_basis": "analysed_frames_only",
            "events": score.events,
            "caveats": ["capture frames are sampled every few ticks, not every tick as at runtime",
                        "consecutive frames are correlated; Wilson intervals are indicative",
                        "defect visibility is geometric and ignores lighting"],
        }
    return results


def evaluate(capture: Path, detector_name: str, detector: Detector, inventory: Inventory | None,
             degradations: list[Degradation], seed: int,
             pose_noise: tuple[float, float] = (0.0, 0.0)) -> dict:
    return evaluate_many(capture, {detector_name: detector}, inventory, degradations, seed,
                         pose_noise)[detector_name]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("capture", type=Path)
    parser.add_argument("--detector", choices=DETECTORS, required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--inventory", type=Path, help="Defect inventory JSON for a mixed capture")
    target.add_argument("--clean", action="store_true", help="Capture of a defect-free map")
    parser.add_argument("--degradation", type=parse_degradation, action="append", default=[])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--pose-noise", type=float, nargs=2, default=(0.0, 0.0),
                        metavar=("SIGMA_M", "SIGMA_YAW_DEG"), help="Navigation error given to the detector")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Refusing to overwrite {args.output}")
    result = evaluate(args.capture, args.detector, make_detector(args.detector),
                      None if args.clean else load_inventory(args.inventory),
                      args.degradation, args.seed, tuple(args.pose_noise))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = {key: result[key] for key in ("detector", "degradations", "false_alerts",
                                            "false_alerts_per_100m", "availability")}
    summary["recall"] = result["defects"]["recall"]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
