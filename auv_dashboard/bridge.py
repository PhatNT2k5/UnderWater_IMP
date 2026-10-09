"""Isolate the unmodified inspection runtime inside a dashboard worker process."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime
import hashlib
import json
import logging
from math import atan2, cos, degrees, radians, sin
from pathlib import Path
from queue import Empty, Full
import shutil
import sys
import time
import traceback
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np

from .patchcore_client import PatchCoreClient, decode_image

ROOT = Path(__file__).resolve().parents[1]
INSPECTION = ROOT / "auv_inspection"
PROTECTED_FILES = (
    "auv_inspection/run_inspection.py", "auv_inspection/crack_detection.py",
    "auv_inspection/scenario.json", "auv_inspection/inspection_route.py",
    "holoocean/engine/Content/AUVInspection/Maps/AUVInspection.umap",
)
DAMAGE_HOLD_SECONDS = 5.0

def damage_pause_remaining(started_at: float | None, now: float,
                           hold_seconds: float = DAMAGE_HOLD_SECONDS) -> float:
    """Return the remaining automatic evidence hold time."""
    if started_at is None:
        return 0.0
    return max(0.0, hold_seconds - (now - started_at))


def source_hashes() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PROTECTED_FILES}


def publish_latest(channel: object, message: dict[str, object]) -> None:
    """Drop only stale preview packets; lifecycle and alerts use another queue."""
    try:
        channel.put_nowait(message)
    except Full:
        try:
            channel.get_nowait()
        except Empty:
            pass  # The queue feeder may still be transferring the old preview.
        try:
            channel.put_nowait(message)
        except Full:
            pass  # Preview delivery must never block simulation or stop commands.


def encode_frame(frame: np.ndarray, mask: bool = False, quality: int = 87) -> bytes:
    suffix = ".png" if mask else ".jpg"
    options = [] if mask else [cv2.IMWRITE_JPEG_QUALITY, quality]
    success, image = cv2.imencode(suffix, frame, options)
    if not success:
        raise OSError("Cannot encode dashboard camera frame")
    return image.tobytes()


def prepare_session_scenario(session: Path, viewport_capture: bool = False) -> Path:
    """Copy the source scenario, optionally adding a session-only viewport stream."""
    target = session / "scenario.json"
    if not viewport_capture:
        shutil.copy2(INSPECTION / "scenario.json", target)
        return target
    scenario = json.loads((INSPECTION / "scenario.json").read_text(encoding="utf-8"))
    width, height = 960, 540
    scenario["window_width"] = width
    scenario["window_height"] = height
    main_agent = next(
        agent for agent in scenario["agents"] if agent["agent_name"] == scenario["main_agent"]
    )
    main_agent["sensors"].append({
        "sensor_type": "ViewportCapture",
        "sensor_name": "DashboardThirdPerson",
        "configuration": {"CaptureWidth": width, "CaptureHeight": height},
    })
    target.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    return target


def viewport_pose(position: np.ndarray, yaw: float) -> tuple[list[float], list[float]]:
    """Place the spectator behind/above the AUV; never modify sensor cameras."""
    heading = radians(yaw)
    forward = np.array([cos(heading), sin(heading), 0.0])
    right = np.array([-sin(heading), cos(heading), 0.0])
    eye = position - 4.8 * forward + 2.0 * right + np.array([0.0, 0.0, 2.7])
    look = position + 0.8 * forward - eye
    # This checkout's TeleportCameraCommand applies ConvertAngularVector to a
    # direction, flipping X/Z instead of Y. Negation restores the intended
    # linear direction in Unreal's left-handed frame without editing upstream.
    return eye.tolist(), (-look).tolist()


def run_worker(commands: object, frames: object, events: object, options: dict[str, object]) -> None:
    """Reuse run_inspection.run with process-local adapters, never edit its file."""
    sys.path.insert(0, str(INSPECTION))
    import run_inspection as inspection
    from crack_detection import preprocess_image
    from robustness.geometric_roi import category_from_pose
    from robustness.geometry import load_params

    geometry_params = load_params()

    session = Path(str(options["session"]))
    session.mkdir(parents=True, exist_ok=True)
    prepare_session_scenario(session, bool(options.get("viewport_capture", False)))
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(session / "worker.log", encoding="utf-8")], force=True,
    )
    hashes_before = source_hashes()
    base_environment = inspection.EditorEnvironment
    original_popen = inspection.subprocess.Popen
    original_analyze = inspection.analyze_frame
    original_save = inspection.save_damage_event
    original_draw = inspection.draw_detections
    original_gate = inspection.is_pipe_view
    original_advance = inspection.advance_station
    detector = str(options.get("detector", "Classical"))
    if detector not in {"Classical", "PatchCore"}:
        raise ValueError(f"Unknown dashboard detector: {detector}")
    patchcore_client: PatchCoreClient | None = None
    state: dict[str, object] = {
        "tick": -1, "station": "start", "station_index": 0, "analysis": None,
        "active": False, "damage_pause": False, "damage_pause_started_at": None,
        "pause": False, "stop": False, "continue": False, "follow": bool(options.get("follow", True)), "keys": set(),
        "evidence": None, "viewport_enabled": False,
        "analysis_status": "idle", "analysis_reason": None, "analysis_tick": None, "runtime_tick": -1,
        "position": [0.0, 0.0, 0.0], "yaw": 0.0, "category": None,
    }
    last_publish = 0.0
    last_pipeline_publish = 0.0
    last_evidence_tick: int | None = None
    last_tick = 0.0
    runtime_output: Path | None = None
    engine = None

    def read_commands() -> None:
        while True:
            try:
                command = commands.get_nowait()
            except Empty:
                break
            name = command["type"]
            if name == "stop":
                state["stop"] = True
            elif name == "pause":
                state["pause"] = bool(command["value"])
            elif name == "continue":
                state["continue"] = True
                state["pause"] = False
            elif name == "follow":
                state["follow"] = bool(command["value"])
            elif name == "keys":
                state["keys"] = set(command["value"])

    class DashboardEnvironment(base_environment):
        def step(self, action: np.ndarray, ticks: int = 1, publish: bool = True) -> dict:
            nonlocal last_tick
            last_tick = time.monotonic()
            if options.get("viewport_capture") and not state["viewport_enabled"]:
                self.should_render_viewport(True)
                state["viewport_enabled"] = True
            if state["follow"] and "position" in state:
                eye, look = viewport_pose(np.asarray(state["position"]), float(state["yaw"]))
                self.move_viewport(eye, look)
            observation = super().step(action, ticks=ticks, publish=publish)
            state["tick"] += 1
            pose = observation.get("PoseSensor")
            camera = observation.get("InspectionCamera")
            viewport = observation.get("DashboardThirdPerson")
            if pose is not None:
                state["position"] = np.asarray(pose[:3, 3]).tolist()
                state["yaw"] = degrees(atan2(float(pose[1, 0]), float(pose[0, 0])))
            velocity = observation.get("VelocitySensor")
            state["speed"] = float(np.linalg.norm(np.asarray(velocity).reshape(-1)[:3])) if velocity is not None else 0.0
            state["frame"] = camera
            state["viewport"] = viewport
            state["analysis"] = None
            state["active"] = False
            return observation

    def launch_engine(command: list[str], **kwargs: object) -> object:
        nonlocal engine, runtime_output
        command = [item for item in command if not item.startswith(("-ResX=", "-ResY="))]
        command.extend(["-ResX=960", "-ResY=540", "-ForceRes", "-WinX=40", "-WinY=80"])
        runtime_output = Path(next(item[8:] for item in command if item.startswith("-abslog="))).parent
        engine = original_popen(command, **kwargs)
        events.put({"type": "engine", "pid": engine.pid, "output": str(runtime_output)})
        return engine

    def advance(route: list, station: int, position: list[float]) -> tuple:
        result = original_advance(route, station, position)
        state["station_index"] = result[0]
        state["station"] = route[result[0]][0]
        return result

    def gate(mode: str, station: str, position: np.ndarray) -> bool:
        state["station"] = station
        if detector == "PatchCore":
            # P2: the structure in view comes from pose and geometry, not the station name.
            category = (category_from_pose(np.asarray(position), float(state["yaw"]), geometry_params)
                        if mode == "auto" else None)
            state["category"] = category
            result = category is not None
        else:
            result = original_gate(mode, station, position)
        state["active"] = result
        return result

    class PatchCoreTracker:
        def update(self, analysis: object) -> object | None:
            alerts = getattr(analysis, "alerts", [])
            return alerts[0] if alerts else None

        def reset(self) -> None:
            # The service owns temporal tracks and resets on group/gap changes.
            pass

    def analyze(frame: np.ndarray) -> object:
        if detector == "Classical":
            analysis = original_analyze(frame)
            state["analysis_tick"] = state["tick"]
            state["analysis_status"] = "ready"
        else:
            if patchcore_client is None:
                raise RuntimeError("PatchCore worker is not ready")
            runtime_tick = int(state["runtime_tick"])
            if runtime_tick < 0:
                raise RuntimeError("PatchCore runtime tick was not initialized")
            if runtime_tick % 3:
                previous = state.get("last_patchcore_analysis")
                if previous is None:
                    analysis = SimpleNamespace(candidates=[], alerts=[], analyzed=False,
                                               analysis_tick=None, status="waiting")
                else:
                    analysis = SimpleNamespace(**{**vars(previous), "alerts": [],
                                                   "analyzed": False})
            else:
                category = state.get("category")
                if category is None:
                    raise RuntimeError("PatchCore group could not be determined")
                response = patchcore_client.analyze(
                    frame, runtime_tick, category, str(state["station"]),
                    list(state["position"]), float(state["yaw"]),
                )
                ready = response["status"] == "ready"
                roi = decode_image(response["roi_png_b64"]) if ready else np.zeros(frame.shape[:2], np.uint8)
                heatmap = (decode_image(response["heatmap_png_b64"]) if ready
                           else np.zeros_like(frame[:, :, :3]))
                annotated = (decode_image(response["annotated_png_b64"]) if ready
                             else frame[:, :, :3].copy())
                candidates = [SimpleNamespace(bbox=tuple(item["bbox_xywh"]),
                                              score=item["peak_score"], area_px=item["area_px"])
                              for item in response["candidates"]]
                alerts = [SimpleNamespace(bbox=tuple(item["bbox_xywh"]),
                                          score=item["peak_score"], area_px=item["area_px"])
                          for item in response["alerts"]]
                analysis = SimpleNamespace(candidates=candidates, alerts=alerts,
                                           preprocessed=roi, mask=heatmap,
                                           annotated=annotated, response=response,
                                           analyzed=True, analysis_tick=runtime_tick,
                                           status=response["status"])
                state["last_patchcore_analysis"] = analysis
                state["analysis_status"] = response["status"]
                state["analysis_reason"] = response.get("reason")
                state["analysis_tick"] = runtime_tick
        state["analysis"] = analysis
        return analysis

    def draw(frame: np.ndarray, analysis: object | None) -> np.ndarray:
        if detector == "Classical":
            return original_draw(frame, analysis)
        return getattr(analysis, "annotated", frame[:, :, :3].copy())

    def save_event(output: Path, frame: np.ndarray, analysis: object, candidate: object,
                   mode: str, tick: int, station_name: str, location: np.ndarray,
                   event_index: int) -> dict:
        if detector == "Classical":
            event = original_save(output, frame, analysis, candidate, mode, tick,
                                  station_name, location, event_index)
            evidence_names = ("camera.png", "preprocessed.png", "mask.png", "annotated.png")
        else:
            response = analysis.response
            if response["tick"] != tick or "scores_npz_b64" not in response:
                raise RuntimeError("PatchCore alert lacks same-tick score evidence")
            evidence_dir = output / "damage_events" / f"event_{event_index:03d}"
            evidence_dir.mkdir(parents=True, exist_ok=False)
            images = {
                "camera.png": frame[:, :, :3],
                "roi.png": decode_image(response["roi_png_b64"]),
                "heatmap.png": decode_image(response["heatmap_png_b64"]),
                "mask.png": decode_image(response["mask_png_b64"]),
                "annotated.png": decode_image(response["annotated_png_b64"]),
            }
            for name, image in images.items():
                if not cv2.imwrite(str(evidence_dir / name), image):
                    raise OSError(f"Could not save {evidence_dir / name}")
            (evidence_dir / "scores.npz").write_bytes(base64.b64decode(
                response["scores_npz_b64"], validate=True))
            event = {
                "timestamp": datetime.now().astimezone().isoformat(),
                "tick": tick, "mode": mode, "station": station_name,
                "position_m": location.tolist(), "yaw_deg": response["yaw_deg"],
                "bbox_xywh": list(candidate.bbox),
                "candidate_score": candidate.score,
                "confirmed_regions": response["alerts"],
                "detector": "PatchCore", "category": response["category"],
                "model_dir": response["model_dir"], "threshold": response["threshold"],
                "processing_ms": response["processing_ms"],
                "roi_status": response["roi_status"],
                "event_dir": str(evidence_dir),
            }
            (evidence_dir / "event.json").write_text(json.dumps(event, indent=2),
                                                        encoding="utf-8")
            evidence_names = ("camera.png", "roi.png", "heatmap.png", "annotated.png")
        state["damage_pause"] = True
        state["damage_pause_started_at"] = time.monotonic()
        evidence_dir = Path(event["event_dir"])
        state["evidence"] = {
            "tick": event["tick"],
            "frames": [(evidence_dir / name).read_bytes() for name in evidence_names],
        }
        events.put({"type": "damage", "event": event})
        return event

    def is_key_pressed(key: int) -> bool:
        read_commands()
        if key == inspection.KEY_CODES["escape"]:
            if detector == "PatchCore":
                # Auto mode checks Escape once per run() loop before stepping Unreal.
                state["runtime_tick"] += 1
            return bool(state["stop"])
        return key in state["keys"]

    def preview(_name: str, _preview: np.ndarray) -> None:
        nonlocal last_publish, last_pipeline_publish, last_evidence_tick
        now = time.monotonic()
        preview_fps = float(options.get("preview_fps", 12.0))
        pipeline_fps = float(options.get("pipeline_fps", preview_fps))
        if now - last_publish < 1.0 / max(1.0, min(30.0, preview_fps)):
            return
        raw = state.get("frame")
        if raw is None:
            return
        last_publish = now
        analysis = state["analysis"]
        camera = encode_frame(raw[:, :, :3])
        evidence = state["evidence"] if state["damage_pause"] else None
        evidence_tick = int(evidence["tick"]) if evidence else None
        sparse_pipeline = bool(options.get("sparse_pipeline", False))
        stages = None
        if evidence is not None and (not sparse_pipeline or evidence_tick != last_evidence_tick):
            stages = evidence["frames"]
            last_evidence_tick = evidence_tick
        elif evidence is None and (
            not sparse_pipeline or now - last_pipeline_publish >= 1.0 / max(1.0, pipeline_fps)
        ):
            if analysis is None:
                processed = (preprocess_image(raw) if detector == "Classical"
                             else np.zeros(raw.shape[:2], np.uint8))
                mask = np.zeros_like(raw[:, :, :3]) if detector == "PatchCore" else np.zeros_like(processed)
                annotated = raw[:, :, :3]
            else:
                if detector == "PatchCore" and not hasattr(analysis, "preprocessed"):
                    processed = np.zeros(raw.shape[:2], np.uint8)
                    mask = np.zeros_like(raw[:, :, :3])
                    annotated = raw[:, :, :3]
                else:
                    processed, mask = analysis.preprocessed, analysis.mask
                    annotated = inspection.draw_detections(raw, analysis)
            stages = [
                camera, encode_frame(processed), encode_frame(mask, mask=True), encode_frame(annotated),
            ]
            last_pipeline_publish = now
        packet = {
            "tick": state["runtime_tick"] if detector == "PatchCore" else state["tick"],
            "position": state.get("position", [0, 0, 0]),
            "yaw": state.get("yaw", 0), "speed": state["speed"], "time": now,
            "station": "damage_pause" if state["damage_pause"] else state["station"],
            "station_index": state["station_index"], "total_stations": len(inspection.ROUTE),
            "detector_active": state["active"], "damage_pause": state["damage_pause"],
            "damage_pause_remaining_seconds": damage_pause_remaining(
                state["damage_pause_started_at"], now) if state["damage_pause"] else 0.0,
            "camera": camera,
            "viewport": encode_frame(state["viewport"][:, :, :3], quality=78)
            if state.get("viewport") is not None else None,
            "frames": stages,
            "evidence_tick": evidence_tick,
            "candidate_count": len(analysis.candidates) if analysis is not None else 0,
            "detector": detector, "analysis_tick": state["analysis_tick"],
            "analysis_status": state["analysis_status"],
            "analysis_reason": state["analysis_reason"],
        }
        publish_latest(frames, packet)

    def resume_damage_pause(automatic: bool) -> int:
        state["continue"] = False
        state["damage_pause"] = False
        state["damage_pause_started_at"] = None
        state["evidence"] = None
        text = ("Đã giữ vị trí 5 giây và tự tiếp tục khảo sát"
                if automatic else "Đã tiếp tục khảo sát theo lệnh người dùng")
        events.put({"type": "damage_resumed", "automatic": automatic})
        events.put({"type": "status", "text": text})
        return 32

    def wait_key(_delay: int) -> int:
        read_commands()
        while state["pause"] and not state["stop"]:
            time.sleep(0.03)
            read_commands()
        if state["stop"]:
            return 27
        if state["continue"]:
            return resume_damage_pause(automatic=False)
        if state["damage_pause"] and damage_pause_remaining(
                state["damage_pause_started_at"], time.monotonic()) <= 0:
            return resume_damage_pause(automatic=True)
        time.sleep(max(0.0, 1.0 / 30.0 - (time.monotonic() - last_tick)))
        return -1

    try:
        if detector == "PatchCore":
            if options["mode"] != "auto":
                raise ValueError("PatchCore currently supports the auto inspection route only")
            events.put({"type": "status", "text": "Đang nạp PatchCore…"})
            patchcore_client = PatchCoreClient(
                ROOT, session, Path(str(options["patchcore_model"])),
                Path(str(options["patchcore_reference"])),
                Path(str(options["patchcore_thresholds"])),
            )
        events.put({"type": "status", "text": "Đang khởi động Unreal…"})
        args = argparse.Namespace(
            editor=None, headless=False, steps=int(options["steps"]), mode=str(options["mode"]),
            move_speed=2.0, yaw_speed=45.0,
        )
        with (
            patch.object(inspection, "HERE", session),
            patch.object(inspection, "EditorEnvironment", DashboardEnvironment),
            patch.object(inspection.subprocess, "Popen", launch_engine),
            patch.object(inspection, "advance_station", advance),
            patch.object(inspection, "is_pipe_view", gate),
            patch.object(inspection, "CrackTracker", PatchCoreTracker if detector == "PatchCore"
                         else inspection.CrackTracker),
            patch.object(inspection, "analyze_frame", analyze),
            patch.object(inspection, "draw_detections", draw),
            patch.object(inspection, "save_damage_event", save_event),
            patch.object(inspection, "is_key_pressed", is_key_pressed),
            patch.object(inspection.cv2, "imshow", preview),
            patch.object(inspection.cv2, "waitKey", wait_key),
        ):
            inspection.run(args)
        report = json.loads((runtime_output / "report.json").read_text(encoding="utf-8")) if runtime_output else {}
        report["detector"] = detector
        if runtime_output:
            (runtime_output / "report.json").write_text(json.dumps(report, indent=2),
                                                           encoding="utf-8")
        events.put({"type": "finished", "report": report})
    except Exception:
        details = traceback.format_exc()
        logging.exception("Dashboard runtime failed")
        events.put({"type": "error", "text": details})
    finally:
        if patchcore_client is not None:
            try:
                patchcore_client.close()
            except Exception:
                logging.exception("Could not close PatchCore worker cleanly")
        audit = {"before": hashes_before, "after": source_hashes(), "finished_at": datetime.now().isoformat()}
        audit["unchanged"] = audit["before"] == audit["after"]
        (session / "source_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        frames.cancel_join_thread()
