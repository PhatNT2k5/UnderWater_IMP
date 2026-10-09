"""Run PatchCore inference as a separate JSON-lines worker process."""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import io
import json
from pathlib import Path
import sys
import time

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

ROI_MODES = ("geometry", "reference")


@dataclass
class Session:
    model: torch.nn.Module
    banks: dict[str, torch.Tensor]
    references: list[ReferenceFrame]
    thresholds: dict[str, float]
    tracker: AlertTracker
    device: torch.device
    model_dir: Path
    roi_mode: str = "geometry"
    geometry: GeometryParams | None = None


def create_session(model_dir: Path, reference_dataset: Path,
                   thresholds_file: Path, roi_mode: str = "geometry") -> Session:
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
    model = load_model(model_dir, CATEGORIES[0], device)
    banks = {category: torch.load(model_dir / f"{category}_bank.pt",
                                  map_location=device, weights_only=True)
             for category in CATEGORIES}
    # The reference dataset stays required: the approval gate fingerprints it.
    references = load_references(reference_dataset) if roi_mode == "reference" else []
    return Session(model=model, banks=banks, references=references,
                   thresholds=thresholds, tracker=AlertTracker(), device=device,
                   model_dir=model_dir.resolve(), roi_mode=roi_mode,
                   geometry=load_params() if roi_mode == "geometry" else None)


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


def analyze_request(session: Session, request: dict) -> dict:
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
    frame = decode_frame(request["camera_png_b64"])
    start = time.perf_counter()
    roi, roi_status = select_roi(session, frame, request, category, station, position_m, yaw_deg)
    identity = {"type": "result", "detector": "PatchCore", "tick": tick,
                "category": category, "station": station,
                "position_m": position_m.tolist(), "yaw_deg": yaw_deg,
                "model_dir": str(session.model_dir),
                "threshold": session.thresholds[category], "roi_status": roi_status}
    # Unusable frames neither confirm nor erase evidence; the tracker's own
    # max_gap_ticks drops tracks that go unobserved for too long.
    if roi is None:
        return {**identity, "status": "analysis_unavailable", "candidates": [],
                "alerts": [], "processing_ms": (time.perf_counter() - start) * 1000}
    # A heavily eroded ROI (large pose uncertainty) can pass the pixel minimum yet cover no
    # 256 px tile enough to score; report it instead of failing inside predict_map.
    if next(iter_tiles(frame, roi), None) is None:
        return {**identity, "status": "analysis_unavailable", "reason": "no_surface_tiles",
                "candidates": [], "alerts": [], "processing_ms": (time.perf_counter() - start) * 1000}
    session.model.memory_bank = session.banks[category]
    scores = predict_map(session.model, frame, roi, session.device)
    if not np.isfinite(scores).any():
        return {**identity, "status": "analysis_unavailable", "reason": "no_surface_scores",
                "candidates": [], "alerts": [],
                "processing_ms": (time.perf_counter() - start) * 1000}
    candidates = extract_candidates(scores, session.thresholds[category])
    alerts = session.tracker.step(category, tick, candidates)
    heatmap, annotated = visualize(frame, roi, scores, candidates, alerts)
    binary_mask = (np.isfinite(scores) & (scores >= session.thresholds[category])).astype(np.uint8) * 255
    response = {**identity, "status": "ready", "candidates": list(map(candidate_dict, candidates)),
            "alerts": list(map(candidate_dict, alerts)),
            "roi_png_b64": encode_png(roi), "heatmap_png_b64": heatmap,
            "mask_png_b64": encode_png(binary_mask), "annotated_png_b64": annotated,
            "processing_ms": (time.perf_counter() - start) * 1000}
    if alerts or request.get("include_scores", False):
        score_bytes = io.BytesIO()
        np.savez_compressed(score_bytes, scores=scores)
        response["scores_npz_b64"] = base64.b64encode(score_bytes.getvalue()).decode("ascii")
        response["processing_ms"] = (time.perf_counter() - start) * 1000
    return response


def serve(session: Session) -> None:
    print(json.dumps({"type": "ready", "detector": "PatchCore", "roi_mode": session.roi_mode,
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
    args = parser.parse_args()
    serve(create_session(args.model_dir, args.reference_dataset, args.thresholds_file,
                         args.roi_mode))


if __name__ == "__main__":
    main()
