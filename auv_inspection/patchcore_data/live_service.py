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
# P8 gate (opt-in): marine snow particles make many small above-threshold regions (median 14-25 per
# frame, 32-53 px) and the "> 6 regions" rule dropped 97-99% of the defect views lost under it,
# while the defect cells still hit (P8.1). Regions smaller than 2x2 detector-v2 tokens (7 px at
# scale 2) are not counted towards regions or spread; random clutter is left to the surface rule,
# which needs 3 separated views of one cell. The single-large-region rule is dropped: it blocked
# the large hole on map B (15 of 25 gated defect views without degradation).
GATE_MIN_REGION_PX = 196


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
    border_margin: bool = False              # apply the margin at the image border as well
    diffuse_gate: bool = False
    evidence: SurfaceEvidence | None = None  # set when the alert rule is "surface"
    scorer: Scorer | None = None             # detector v2 (P4) instead of PatchCore
    gate_min_region_px: int = 0              # P8 gate: ignore smaller above-threshold regions
    gate_region_share: bool = True           # P8 gate drops the single-large-region rule
    evidence_min_region_px: int = 0          # P8: only regions this large can give surface hits
    gate_spread_all_regions: bool = False    # P8: gate spread over all regions, count over large ones
    strict_thresholds: dict[str, float] | None = None  # P9: absolute-only hit level per group


def create_session(model_dir: Path, reference_dataset: Path,
                   thresholds_file: Path, roi_mode: str = "geometry",
                   score_margin_px: int = 0, diffuse_gate: bool = False,
                   alert_rule: str = "track",
                   surface_calibration: Path = SURFACE_CALIBRATION_FILE,
                   border_margin: bool = False, gate_min_region_px: int = 0,
                   gate_region_share: bool = True, evidence_min_region_px: int = 0,
                   gate_spread_all_regions: bool = False,
                   strict_thresholds_file: Path | None = None) -> Session:
    if score_margin_px < 0 or gate_min_region_px < 0 or evidence_min_region_px < 0:
        raise ValueError("score_margin_px and the region sizes must be non-negative")
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
    strict = None
    if strict_thresholds_file is not None:
        strict_file = json.loads(strict_thresholds_file.read_text(encoding="utf-8"))
        if Path(strict_file["model_dir"]).resolve() != model_dir.resolve() or strict_file.get("kind") != "strict":
            raise ValueError("Strict thresholds refer to a different model or are not strict thresholds")
        strict = {category: float(strict_file["groups"][category]["threshold"]) for category in CATEGORIES}
        if any(strict[c] < thresholds[c] for c in CATEGORIES):
            raise ValueError("A strict threshold below the pixel threshold would loosen the hit rule")
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
                   geometry=model_geometry(model_dir) if roi_mode == "geometry" else None,
                   score_margin_px=score_margin_px, border_margin=border_margin,
                   diffuse_gate=diffuse_gate,
                   evidence=(surface_evidence(surface_calibration, thresholds_file, thresholds, strict)
                             if alert_rule == "surface" else None),
                   scorer=scorer, gate_min_region_px=gate_min_region_px,
                   gate_region_share=gate_region_share, evidence_min_region_px=evidence_min_region_px,
                   gate_spread_all_regions=gate_spread_all_regions, strict_thresholds=strict)


def model_geometry(model_dir: Path) -> GeometryParams:
    """Geometry of the ROI: the default calibration, or the file a v2 model names (P8: pier floor)."""
    config = model_dir / "config.json"
    name = json.loads(config.read_text(encoding="utf-8")).get("geometry_file") if config.is_file() else None
    if not name:
        return load_params()
    path = Path(name) if Path(name).is_absolute() else Path(__file__).resolve().parents[2] / name
    if not path.is_file():
        raise FileNotFoundError(f"Geometry calibration named by {config} is missing: {path}")
    return load_params(path)


def surface_evidence(calibration_file: Path, thresholds_file: Path, thresholds: dict[str, float],
                     strict_thresholds: dict[str, float] | None = None) -> SurfaceEvidence:
    calibration = load_calibration(calibration_file)
    if calibration.pixel_thresholds_sha256 != hashlib.sha256(thresholds_file.read_bytes()).hexdigest():
        raise ValueError("Surface calibration was made with a different pixel threshold file")
    return SurfaceEvidence(calibration, thresholds, strict_thresholds)


def interior(roi: np.ndarray, margin_px: int, image_border: bool = False) -> np.ndarray:
    """ROI pixels at least margin_px from the ROI edge.

    By default the image border is not an edge (the surface continues out of frame). With
    `image_border` it is: v2 false alerts on the extended development set sat within 24 px of
    the frame border, where the lights fall off and tokens see the frame edge.
    """
    padded = cv2.copyMakeBorder((roi > 0).astype(np.uint8), 1, 1, 1, 1, cv2.BORDER_CONSTANT,
                                value=0 if image_border else 1)
    distance = cv2.distanceTransform(padded, cv2.DIST_L2, 5)[1:-1, 1:-1]
    return distance >= margin_px


def hit_mask(scores: np.ndarray, threshold: float, relative_threshold: float | None = None,
             strict_threshold: float | None = None) -> np.ndarray:
    """Pixels at hit level: above the threshold (and the relative test when given), or at or above the
    strict threshold (P9)."""
    finite = np.isfinite(scores)
    above = finite & (scores >= threshold)
    if relative_threshold is not None:
        above &= scores >= relative_threshold * float(np.median(scores[finite]))
    if strict_threshold is not None:
        above |= finite & (scores >= strict_threshold)
    return above


def above_threshold_shape(scores: np.ndarray, threshold: float,
                          relative_threshold: float | None = None, min_region_px: int = 0,
                          strict_threshold: float | None = None) -> dict[str, float]:
    """Shares of the scored ROI above threshold: in total, outside the largest region, largest region.

    With `relative_threshold` a pixel must also reach that multiple of the frame's median score,
    i.e. count as a surface-rule hit, so a global score shift does not read as a diffuse anomaly.
    """
    finite = np.isfinite(scores)
    above = hit_mask(scores, threshold, relative_threshold, strict_threshold)
    _, _, stats, _ = cv2.connectedComponentsWithStats(above.astype(np.uint8), connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    if min_region_px:
        areas = areas[areas >= min_region_px]
    largest = int(areas.max()) if len(areas) else 0
    scored = max(int(np.count_nonzero(finite)), 1)
    total = int(areas.sum()) if min_region_px else int(np.count_nonzero(above))
    return {"anomaly_share": total / scored, "anomaly_spread": (total - largest) / scored,
            "largest_region_share": largest / scored,
            "regions": int(np.count_nonzero(areas >= 2))}  # extract_candidates' minimum area


def is_diffuse(scores: np.ndarray, threshold: float, candidates: list,
               relative_threshold: float | None = None, min_region_px: int = 0,
               region_share: bool = True, spread_all_regions: bool = False,
               strict_threshold: float | None = None) -> tuple[bool, dict[str, float]]:
    """`min_region_px` and `region_share=False` give the P8 gate (see GATE_MIN_REGION_PX);
    `spread_all_regions` keeps the spread over regions of every size, as in the original gate, so
    only the region count ignores particle-sized regions."""
    shape = above_threshold_shape(scores, threshold, relative_threshold, min_region_px, strict_threshold)
    if spread_all_regions and min_region_px:
        shape["anomaly_spread"] = above_threshold_shape(scores, threshold, relative_threshold,
                                                        strict_threshold=strict_threshold)["anomaly_spread"]
    regions = len(candidates) if relative_threshold is None and not min_region_px else shape["regions"]
    diffuse = (shape["anomaly_spread"] > DIFFUSE_MAX_SHARE or regions > DIFFUSE_MAX_CANDIDATES
               or (region_share and shape["largest_region_share"] > DIFFUSE_MAX_REGION_SHARE))
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
        scores[~interior(roi, session.score_margin_px, session.border_margin)] = np.nan
    if not np.isfinite(scores).any():
        return unavailable(reason="no_surface_scores")
    candidates = extract_candidates(scores, session.thresholds[category])
    if session.diffuse_gate:
        # With the surface rule the gate counts surface-rule hits (absolute AND relative), as the
        # evidence does; v2's absolute threshold alone abstained on half the frames at turbidity 2.
        relative = (session.evidence.calibration.lowest_threshold(category)
                    if session.evidence is not None else None)
        diffuse, shape = is_diffuse(scores, session.thresholds[category], candidates, relative,
                                    session.gate_min_region_px, session.gate_region_share,
                                    session.gate_spread_all_regions,
                                    session.strict_thresholds[category] if session.strict_thresholds else None)
        if diffuse:
            # Not "clean" and not a defect: widespread anomaly (environment or large-area damage)
            # is reported for the operator and leaves the tracker untouched.
            return unavailable(reason="diffuse_anomaly", candidate_count=len(candidates),
                               **{key: round(value, 4) for key, value in shape.items()})
    return identity, roi, scores, candidates


def without_small_hits(scores: np.ndarray, threshold: float, relative_threshold: float,
                       min_region_px: int, strict_threshold: float | None = None) -> np.ndarray:
    """Copy of `scores` in which hit-level regions (absolute AND relative, as the gate counts them)
    smaller than `min_region_px` are capped just below the pixel threshold: the cells are still
    viewed, but such regions cannot be evidence (P8: particle-sized clutter)."""
    above = hit_mask(scores, threshold, relative_threshold, strict_threshold)
    _, labels, stats, _ = cv2.connectedComponentsWithStats(above.astype(np.uint8), connectivity=8)
    small = np.isin(labels, 1 + np.flatnonzero(stats[1:, cv2.CC_STAT_AREA] < min_region_px)) & above
    capped = scores.copy()
    capped[small] = np.nextafter(np.float32(threshold), np.float32(-np.inf))
    return capped


def surface_step(session: Session, scores: np.ndarray, category: str, position_m: np.ndarray,
                 yaw_deg: float) -> tuple[list[Candidate], list[SurfaceAlert]]:
    """Add the frame to the surface evidence; new alerts with their image box in this frame."""
    if session.evidence is None or session.geometry is None:
        raise ValueError("Surface alert rule needs SurfaceEvidence and GeometryParams")
    evidence_scores = scores
    if session.evidence_min_region_px:
        evidence_scores = without_small_hits(scores, session.thresholds[category],
                                             session.evidence.calibration.lowest_threshold(category),
                                             session.evidence_min_region_px,
                                             session.strict_thresholds[category] if session.strict_thresholds else None)
    values, keys_u, keys_v = frame_cells(evidence_scores, position_m, yaw_deg, category, session.geometry)
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
    parser.add_argument("--border-margin", action="store_true",
                        help="also ignore scores within the margin of the image border")
    parser.add_argument("--gate-min-region-px", type=int, default=0,
                        help=f"P8 gate: ignore smaller above-threshold regions (P8 uses {GATE_MIN_REGION_PX})")
    parser.add_argument("--no-gate-region-share", action="store_true",
                        help="P8 gate: do not abstain on one large above-threshold region")
    parser.add_argument("--p8-rules", action="store_true",
                        help="P8 candidate rules: the P8 gate (regions counted from GATE_MIN_REGION_PX, no "
                             "single-large-region rule, spread over all regions) and evidence only from regions "
                             "of at least GATE_MIN_REGION_PX; overrides the separate gate/evidence options")
    parser.add_argument("--strict-thresholds", type=Path,
                        help="P9: absolute-only hit thresholds (calibrate_pixel --strict output)")
    parser.add_argument("--gate-spread-all-regions", action="store_true",
                        help="P8 gate: spread over regions of every size, region count over large ones")
    parser.add_argument("--evidence-min-region-px", type=int, default=0,
                        help=f"P8: smaller hit-level regions give no surface evidence (P8 uses {GATE_MIN_REGION_PX})")
    args = parser.parse_args()
    if args.p8_rules:
        args.gate_min_region_px = args.evidence_min_region_px = GATE_MIN_REGION_PX
        args.no_gate_region_share = args.gate_spread_all_regions = True
    serve(create_session(args.model_dir, args.reference_dataset, args.thresholds_file,
                         args.roi_mode, args.score_margin_px, args.diffuse_gate,
                         args.alert_rule, args.surface_calibration, args.border_margin,
                         args.gate_min_region_px, not args.no_gate_region_share,
                         args.evidence_min_region_px, args.gate_spread_all_regions,
                         args.strict_thresholds))


if __name__ == "__main__":
    main()
