"""Run PatchCore inference as a separate JSON-lines worker process."""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import sys
import time
from typing import Callable

import cv2
import numpy as np
import torch

from .alerts import AlertTracker, Candidate, extract_candidates
from .live_roi import ReferenceFrame, load_references, match_roi
from .model import CATEGORIES, iter_tiles, predict_map
from .predict import load_model

# The geometric ROI lives with the route geometry in auv_inspection (top-level imports).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from robustness.geometric_roi import (  # noqa: E402
    DEFAULT_POSE_SIGMA_M, DEFAULT_POSE_SIGMA_YAW_DEG, geometric_roi)
from robustness.geometry import GeometryParams, load_params  # noqa: E402
from robustness.quality import measure  # noqa: E402
from detector_v2.scorer import is_v2_model, load_scorer  # noqa: E402
from robustness.surface_evidence import (  # noqa: E402
    CALIBRATION_FILE as SURFACE_CALIBRATION_FILE, POOL_PX, SurfaceAlert, SurfaceEvidence,
    frame_cells, load_calibration)

ROI_MODES = ("geometry", "reference")
# track: three image-space detections along a trajectory (v1); surface: k views of one surface
# cell above its calibrated threshold (P5, needs the geometric ROI and surface calibration).
ALERT_RULES = ("track", "surface")
# A patch descriptor mixes a 3x3 neighbourhood of layer2 cells (8 px stride) with layer3 cells
# (16 px), so it sees about +/-24 px around its centre; patches closer than that to the ROI edge
# score water, flange rims or the pipe end cap (P2 live false alerts). Chosen before measuring.
DEFAULT_SCORE_MARGIN_PX = 24
# Defects are local; environmental change spreads anomalies over the surface (NFAD,
# ShiftSplit-AD). "Diffuse" is measured as spread, not area: the share of the ROI above threshold
# *outside the largest connected region*. The first rule (total share > 5%) abstained on a large
# crack seen up close in the P5 live run (5.6-8.3% of the ROI in 1-3 regions). On the development
# set defect frames stay <= 2.4% outside their largest region and <= 5 candidate regions; one
# region larger than 25% of the ROI (defects reached 8.3%) is reported as large-area anomaly.
DIFFUSE_MAX_SHARE = 0.05          # above-threshold share outside the largest region
DIFFUSE_MAX_CANDIDATES = 6
DIFFUSE_MAX_REGION_SHARE = 0.25   # a single above-threshold region


Scorer = Callable[[np.ndarray, np.ndarray, str], np.ndarray]  # (frame, roi, group) -> score map


@dataclass
class Session:
    model: torch.nn.Module | None       # PatchCore v1; None when `scorer` is set
    banks: dict[str, torch.Tensor]
    references: list[ReferenceFrame]
    thresholds: dict[str, float]
    tracker: AlertTracker
    device: torch.device
    model_dir: Path
    roi_mode: str = "geometry"
    geometry: GeometryParams | None = None
    score_margin_px: int = 0
    diffuse_gate: bool = False
    evidence: SurfaceEvidence | None = None  # set when the alert rule is "surface"
    scorer: Scorer | None = None             # detector v2 (P4) instead of PatchCore


def create_session(model_dir: Path, reference_dataset: Path,
                   thresholds_file: Path, roi_mode: str = "geometry",
                   score_margin_px: int = 0, diffuse_gate: bool = False,
                   alert_rule: str = "track",
                   surface_calibration: Path = SURFACE_CALIBRATION_FILE) -> Session:
    if score_margin_px < 0:
        raise ValueError("score_margin_px must be non-negative")
    if alert_rule not in ALERT_RULES:
        raise ValueError(f"alert_rule must be one of {ALERT_RULES}")
    if alert_rule == "surface" and roi_mode != "geometry":
        raise ValueError("The surface alert rule needs the geometric ROI (pose -> surface cells)")
    if roi_mode not in ROI_MODES:
        raise ValueError(f"roi_mode must be one of {ROI_MODES}")
    calibration = json.loads(thresholds_file.read_text(encoding="utf-8"))
    if Path(calibration["model_dir"]).resolve() != model_dir.resolve():
        raise ValueError("Thresholds refer to a different model")
    thresholds = {category: float(calibration["groups"][category]["threshold"])
                  for category in CATEGORIES}
    if any(not np.isfinite(value) for value in thresholds.values()):
        raise ValueError("Non-finite category threshold")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    scorer = load_scorer(model_dir, device) if is_v2_model(model_dir) else None
    if scorer is not None and roi_mode != "geometry":
        raise ValueError("Detector v2 banks were built on the geometric ROI")
    model = None if scorer else load_model(model_dir, CATEGORIES[0], device)
    banks = {} if scorer else {category: torch.load(model_dir / f"{category}_bank.pt",
                                                     map_location=device, weights_only=True)
                               for category in CATEGORIES}
    # The reference dataset stays required: the approval gate fingerprints it.
    references = load_references(reference_dataset) if roi_mode == "reference" else []
    return Session(model=model, banks=banks, references=references,
                   thresholds=thresholds, tracker=AlertTracker(), device=device,
                   model_dir=model_dir.resolve(), roi_mode=roi_mode,
                   geometry=load_params() if roi_mode == "geometry" else None,
                   score_margin_px=score_margin_px, diffuse_gate=diffuse_gate,
                   evidence=(surface_evidence(surface_calibration, thresholds_file, thresholds)
                             if alert_rule == "surface" else None),
                   scorer=scorer)


def surface_evidence(calibration_file: Path, thresholds_file: Path,
                     thresholds: dict[str, float]) -> SurfaceEvidence:
    calibration = load_calibration(calibration_file)
    if calibration.pixel_thresholds_sha256 != hashlib.sha256(thresholds_file.read_bytes()).hexdigest():
        raise ValueError("Surface calibration was made with a different pixel threshold file")
    return SurfaceEvidence(calibration, thresholds)


def interior(roi: np.ndarray, margin_px: int) -> np.ndarray:
    """ROI pixels at least margin_px from the ROI edge; the image border is not an edge."""
    padded = cv2.copyMakeBorder((roi > 0).astype(np.uint8), 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=1)
    distance = cv2.distanceTransform(padded, cv2.DIST_L2, 5)[1:-1, 1:-1]
    return distance >= margin_px


def above_threshold_shape(scores: np.ndarray, threshold: float) -> dict[str, float]:
    """Shares of the scored ROI above threshold: in total, outside the largest region, largest region."""
    finite = np.isfinite(scores)
    above = (finite & (scores >= threshold)).astype(np.uint8)
    _, _, stats, _ = cv2.connectedComponentsWithStats(above, connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest = int(areas.max()) if len(areas) else 0
    scored = max(int(np.count_nonzero(finite)), 1)
    total = int(np.count_nonzero(above))
    return {"anomaly_share": total / scored, "anomaly_spread": (total - largest) / scored,
            "largest_region_share": largest / scored}


def is_diffuse(scores: np.ndarray, threshold: float, candidates: list) -> tuple[bool, dict[str, float]]:
    shape = above_threshold_shape(scores, threshold)
    diffuse = (shape["anomaly_spread"] > DIFFUSE_MAX_SHARE or len(candidates) > DIFFUSE_MAX_CANDIDATES
               or shape["largest_region_share"] > DIFFUSE_MAX_REGION_SHARE)
    return diffuse, shape


def select_roi(session: Session, frame: np.ndarray, request: dict, category: str,
               station: str, position_m: np.ndarray, yaw_deg: float) -> tuple[np.ndarray | None, dict]:
    if session.roi_mode == "reference":
        return match_roi(frame, session.references, category, station, position_m, yaw_deg)
    if session.geometry is None:
        raise ValueError("Geometry ROI mode needs GeometryParams (create_session loads them)")
    return geometric_roi(position_m, yaw_deg, category, session.geometry,
                         float(request.get("pose_sigma_m", DEFAULT_POSE_SIGMA_M)),
                         float(request.get("pose_sigma_yaw_deg", DEFAULT_POSE_SIGMA_YAW_DEG)))


def encode_png(image: np.ndarray) -> str:
    success, data = cv2.imencode(".png", image)
    if not success:
        raise OSError("Could not encode PNG")
    return base64.b64encode(data).decode("ascii")


def decode_frame(encoded: str) -> np.ndarray:
    raw = base64.b64decode(encoded, validate=True)
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None or frame.shape != (480, 640, 3):
        raise ValueError("Expected a valid 640x480 BGR camera PNG")
    return frame


def candidate_dict(candidate: Candidate) -> dict:
    return {"bbox_xywh": list(candidate.bbox), "peak_score": candidate.peak_score,
            "area_px": candidate.area}


def visualize(frame: np.ndarray, roi: np.ndarray, scores: np.ndarray,
              candidates: list[Candidate], alerts: list[Candidate]) -> tuple[str, str]:
    finite = np.isfinite(scores)
    values = scores[finite]
    low, high = np.percentile(values, [5, 99])
    scaled = np.zeros(scores.shape, np.uint8)
    scaled[finite] = np.clip((values - low) * 255 / max(high - low, 1e-6),
                             0, 255).astype(np.uint8)
    heatmap = cv2.applyColorMap(scaled, cv2.COLORMAP_TURBO)
    heatmap[~finite] = 0
    marked = frame.copy()
    for candidate in candidates:
        x, y, width, height = candidate.bbox
        cv2.rectangle(marked, (x, y), (x + width, y + height), (0, 180, 255), 1)
    for candidate in alerts:
        x, y, width, height = candidate.bbox
        cv2.rectangle(marked, (x, y), (x + width, y + height), (0, 0, 255), 2)
    return encode_png(heatmap), encode_png(marked)


def score_request(session: Session, request: dict, frame: np.ndarray,
                  start: float) -> tuple[dict, np.ndarray | None, np.ndarray | None, list[Candidate]]:
    """Validate, choose the ROI and score one frame.

    Returns (response, roi, scores, candidates); when scores is None the response is a finished
    `analysis_unavailable` answer. Shared by the live service and `calibrate_surface.py`.
    """
    tick = int(request["tick"])
    category = str(request["category"])
    station = str(request["station"])
    if category not in CATEGORIES:
        raise ValueError(f"Unknown structure group: {category}")
    position_m = np.asarray(request["position_m"], np.float32)
    if position_m.shape != (3,) or not np.isfinite(position_m).all():
        raise ValueError("position_m must have three finite coordinates")
    yaw_deg = float(request["yaw_deg"])
    if not np.isfinite(yaw_deg):
        raise ValueError("yaw_deg must be finite")
    roi, roi_status = select_roi(session, frame, request, category, station, position_m, yaw_deg)
    identity = {"type": "result", "detector": "PatchCore", "tick": tick,
                "category": category, "station": station,
                "position_m": position_m.tolist(), "yaw_deg": yaw_deg,
                "model_dir": str(session.model_dir),
                "threshold": session.thresholds[category], "roi_status": roi_status}

    def unavailable(**reason: object) -> tuple[dict, None, None, list[Candidate]]:
        return ({**identity, "status": "analysis_unavailable", **reason, "candidates": [],
                 "alerts": [], "processing_ms": (time.perf_counter() - start) * 1000}, None, None, [])

    # Unusable frames neither confirm nor erase evidence; the tracker's own
    # max_gap_ticks drops tracks that go unobserved for too long.
    if roi is None:
        return unavailable()
    # A heavily eroded ROI (large pose uncertainty) can pass the pixel minimum yet cover no
    # 256 px tile enough to score; report it instead of failing inside predict_map.
    if next(iter_tiles(frame, roi), None) is None:
        return unavailable(reason="no_surface_tiles")
    identity["quality"] = measure(frame, roi)
    if session.scorer is not None:
        scores = session.scorer(frame, roi, category)
    else:
        session.model.memory_bank = session.banks[category]
        scores = predict_map(session.model, frame, roi, session.device)
    if session.score_margin_px:
        scores[~interior(roi, session.score_margin_px)] = np.nan
    if not np.isfinite(scores).any():
        return unavailable(reason="no_surface_scores")
    candidates = extract_candidates(scores, session.thresholds[category])
    if session.diffuse_gate:
        diffuse, shape = is_diffuse(scores, session.thresholds[category], candidates)
        if diffuse:
            # Not "clean" and not a defect: widespread anomaly (environment or large-area damage)
            # is reported for the operator and leaves the tracker untouched.
            return unavailable(reason="diffuse_anomaly", candidate_count=len(candidates),
                               **{key: round(value, 4) for key, value in shape.items()})
    return identity, roi, scores, candidates


def surface_step(session: Session, scores: np.ndarray, category: str, position_m: np.ndarray,
                 yaw_deg: float) -> tuple[list[Candidate], list[SurfaceAlert]]:
    """Add the frame to the surface evidence; new alerts with their image box in this frame."""
    if session.evidence is None or session.geometry is None:
        raise ValueError("Surface alert rule needs SurfaceEvidence and GeometryParams")
    values, keys_u, keys_v = frame_cells(scores, position_m, yaw_deg, category, session.geometry)
    new_alerts, _ = session.evidence.observe(position_m, values)
    boxes = []
    for alert in new_alerts:
        in_alert = np.zeros(keys_u.shape, bool)
        for _, cell_u, cell_v in alert.cells:
            in_alert |= (keys_u == cell_u) & (keys_v == cell_v)
        rows, cols = np.nonzero(in_alert)
        x, y = int(cols.min()) * POOL_PX, int(rows.min()) * POOL_PX
        width = (int(cols.max()) - int(cols.min()) + 1) * POOL_PX
        height = (int(rows.max()) - int(rows.min()) + 1) * POOL_PX
        peak = float(np.nanmax(scores[y:y + height, x:x + width]))
        boxes.append(Candidate((x, y, width, height), (x + width / 2, y + height / 2), peak,
                               int(in_alert.sum()) * POOL_PX * POOL_PX))
    return boxes, new_alerts


def analyze_request(session: Session, request: dict) -> dict:
    frame = decode_frame(request["camera_png_b64"])
    start = time.perf_counter()
    response, roi, scores, candidates = score_request(session, request, frame, start)
    if scores is None or roi is None:
        return response
    category = response["category"]
    if session.evidence is not None:
        alerts, surface_alerts = surface_step(session, scores, category,
                                              np.asarray(response["position_m"], float),
                                              response["yaw_deg"])
        response["surface_alerts"] = [
            {"alert_id": item.alert_id, "category": item.category,
             "surface_uv_m": [round(value, 2) for value in item.surface_uv_m]}
            for item in surface_alerts]
    else:
        alerts = session.tracker.step(category, response["tick"], candidates)
    heatmap, annotated = visualize(frame, roi, scores, candidates, alerts)
    binary_mask = (np.isfinite(scores) & (scores >= session.thresholds[category])).astype(np.uint8) * 255
    response.update({"status": "ready", "candidates": list(map(candidate_dict, candidates)),
                     "alerts": list(map(candidate_dict, alerts)),
                     "roi_png_b64": encode_png(roi), "heatmap_png_b64": heatmap,
                     "mask_png_b64": encode_png(binary_mask), "annotated_png_b64": annotated})
    if alerts or request.get("include_scores", False):
        score_bytes = io.BytesIO()
        np.savez_compressed(score_bytes, scores=scores)
        response["scores_npz_b64"] = base64.b64encode(score_bytes.getvalue()).decode("ascii")
    response["processing_ms"] = (time.perf_counter() - start) * 1000
    return response


def serve(session: Session) -> None:
    print(json.dumps({"type": "ready", "detector": "PatchCore", "roi_mode": session.roi_mode,
                      "alert_rule": "surface" if session.evidence is not None else "track",
                      "model_dir": str(session.model_dir)}), flush=True)
    for line in sys.stdin:
        request: dict = {}
        try:
            request = json.loads(line)
            if request.get("type") == "stop":
                break
            if request.get("type") != "analyze":
                raise ValueError("Expected analyze or stop request")
            response = analyze_request(session, request)
        except Exception as error:
            response = {"type": "error", "tick": request.get("tick") if
                        isinstance(request, dict) else None, "message": str(error)}
        print(json.dumps(response), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("reference_dataset", type=Path)
    parser.add_argument("thresholds_file", type=Path)
    parser.add_argument("--roi-mode", choices=ROI_MODES, default="geometry",
                        help="geometry: ROI from pose and structure geometry (P2); "
                             "reference: nearest reviewed clean-frame masks (P0 baseline)")
    parser.add_argument("--score-margin-px", type=int, default=0,
                        help=f"ignore scores this close to the ROI edge (P3 uses {DEFAULT_SCORE_MARGIN_PX})")
    parser.add_argument("--diffuse-gate", action="store_true",
                        help="report frames with widespread above-threshold scores as diffuse_anomaly")
    parser.add_argument("--alert-rule", choices=ALERT_RULES, default="track",
                        help="track: three-frame image track (v1); surface: k views of one surface cell (P5)")
    parser.add_argument("--surface-calibration", type=Path, default=SURFACE_CALIBRATION_FILE)
    args = parser.parse_args()
    serve(create_session(args.model_dir, args.reference_dataset, args.thresholds_file,
                         args.roi_mode, args.score_margin_px, args.diffuse_gate,
                         args.alert_rule, args.surface_calibration))


if __name__ == "__main__":
    main()
