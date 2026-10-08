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
from dataclasses import dataclass
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


def patchcore_detector(model_dir: Path, reference: Path, thresholds: Path) -> Detector:
    from auv_inspection.patchcore_data.live_service import (
        analyze_request, create_session, encode_png)
    session = create_session(model_dir, reference, thresholds)

    def step(frame: np.ndarray, row: dict) -> FrameResult:
        response = analyze_request(session, {
            "tick": row["tick"], "category": row["category"], "station": row["station"],
            "position_m": row["position_m"], "yaw_deg": row["yaw_deg"],
            "camera_png_b64": encode_png(frame)})
        if response["status"] != "ready":
            return FrameResult(False, False, None)
        alerts = response["alerts"]
        return FrameResult(True, bool(response["candidates"]),
                           alerts[0]["bbox_xywh"] if alerts else None)

    return step


def load_capture(capture: Path) -> tuple[list[dict], dict]:
    report = json.loads((capture / "report.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (capture / "frames.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    return sorted(rows, key=lambda row: row["tick"]), report


def evaluate(capture: Path, detector_name: str, detector: Detector, inventory: Inventory | None,
             degradations: list[Degradation], seed: int) -> dict:
    rows, report = load_capture(capture)
    if inventory is not None and inventory.map_sha256 != report.get("map_sha256"):
        raise ValueError("Inventory map hash does not match the capture map")
    if inventory is None and report.get("scene_state") != "clean":
        raise ValueError("Captures of mixed scenes need a defect inventory")
    defects = inventory.defects if inventory else ()
    views: Counter[str] = Counter()
    status: dict[str, Counter[str]] = defaultdict(Counter)
    negatives = flagged_negatives = 0
    events: list[dict] = []
    last_alert: np.ndarray | None = None
    positions: dict[str, list[list[float]]] = defaultdict(list)
    elapsed: list[float] = []
    for row in rows:
        frame = cv2.imread(str(capture / row["image"]), cv2.IMREAD_COLOR)
        if frame is None:
            raise OSError(f"Cannot read {row['image']}")
        if degradations:
            frame = apply_degradations(frame, degradations, seed + int(row["tick"]))
        camera, yaw, category = np.asarray(row["position_m"], float), float(row["yaw_deg"]), row["category"]
        positions[category].append(row["position_m"])
        visible = defects_in_view(defects, camera, yaw, category)
        views.update(visible)
        start = time.perf_counter()
        result = detector(frame, row)
        if result.available:  # skipped frames cost ~0 ms and would hide the real latency
            elapsed.append((time.perf_counter() - start) * 1000)
        status[category]["analysed" if result.available else "unavailable"] += 1
        if result.available and not visible:
            negatives += 1
            flagged_negatives += result.flagged
        if result.alert_bbox is None:
            continue
        if last_alert is not None and np.linalg.norm(camera - last_alert) < REARM_DISTANCE_M:
            continue
        last_alert = camera
        point = locate_box(result.alert_bbox, camera, yaw, category)
        events.append({"tick": row["tick"], "category": category, "bbox_xywh": result.alert_bbox,
                       "world_m": None if point is None else np.round(point, 3).tolist(),
                       "defect": match_defect(point, category, defects)})
    observable = [defect.defect_id for defect in defects if views[defect.defect_id] >= MIN_VIEWS_OBSERVABLE]
    detected = sorted({event["defect"] for event in events if event["defect"]} & set(observable))
    false_alerts = [event for event in events if event["defect"] is None]
    length = sum(surveyed_length_m(items) for items in positions.values())
    return {
        "capture": str(capture), "detector": detector_name, "seed": seed,
        "degradations": [{"factor": item.factor, "severity": item.severity} for item in degradations],
        "conditions": report.get("conditions"), "frames": len(rows),
        "defects": {"observable": observable, "detected": detected,
                    "views": dict(views), "recall": fraction(len(detected), len(observable))},
        "false_alerts": len(false_alerts), "surveyed_length_m": round(length, 1),
        "false_alerts_per_100m": rate_per_100m(len(false_alerts), length),
        "frame_flag_rate_without_defect": fraction(flagged_negatives, negatives),
        "availability": {key: dict(value) for key, value in status.items()},
        "processing_ms_median": float(np.median(elapsed)) if elapsed else None,
        "timing_basis": "analysed_frames_only",
        "events": events,
        "caveats": ["capture frames are sampled every few ticks, not every tick as at runtime",
                    "consecutive frames are correlated; Wilson intervals are indicative",
                    "defect visibility is geometric and ignores lighting"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("capture", type=Path)
    parser.add_argument("--detector", choices=("classical", "patchcore"), required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--inventory", type=Path, help="Defect inventory JSON for a mixed capture")
    target.add_argument("--clean", action="store_true", help="Capture of a defect-free map")
    parser.add_argument("--degradation", type=parse_degradation, action="append", default=[])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Refusing to overwrite {args.output}")
    detector = (classical_detector() if args.detector == "classical"
                else patchcore_detector(PATCHCORE_MODEL, PATCHCORE_REFERENCE, PATCHCORE_THRESHOLDS))
    result = evaluate(args.capture, args.detector, detector,
                      None if args.clean else load_inventory(args.inventory),
                      args.degradation, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = {key: result[key] for key in ("detector", "degradations", "false_alerts",
                                            "false_alerts_per_100m", "availability")}
    summary["recall"] = result["defects"]["recall"]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
