"""Launch the Unreal map and drive the AUV automatically or manually."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from crack_detection import (
    CrackAnalysis,
    CrackCandidate,
    CrackTracker,
    analyze_frame,
    draw_detections,
)
from inspection_route import PIPE_X_MAX, PIPE_X_MIN, ROUTE, advance_station, angle_delta
from robustness.conditions import (
    NOMINAL, PROFILES, CaptureSchedule, conditioned_route, current_at, describe,
    sample_conditions,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
# Use the client matching this checkout, without installing another dependency.
sys.path.insert(0, str(ROOT / "holoocean/client/src"))
os.environ.setdefault("HOLODECKPATH", str(ROOT / "worlds"))

import cv2
import numpy as np
import win32api
import win32event
from holoocean.environments import HoloOceanEnvironment

LOG = logging.getLogger("auv_inspection")
TELEMETRY_INTERVAL_TICKS = 3
FINAL_POSITION_TOLERANCE_M = 0.25
FINAL_YAW_TOLERANCE_DEG = 8.0
FINAL_HOLD_TICKS = 15
CAMERA_WARMUP_TICKS = 30
CRACK_REARM_DISTANCE_M = 2.0
ENGINE_VERSION = "5.3"
ENGINE_REGISTRY_KEY = rf"SOFTWARE\EpicGames\Unreal Engine\{ENGINE_VERSION}"
EDITOR_ENV_VAR = "AUV_UNREAL_EDITOR"
KEY_CODES = {
    "forward": ord("W"),
    "backward": ord("S"),
    "left": ord("A"),
    "right": ord("D"),
    "up": ord("R"),
    "down": ord("F"),
    "yaw_left": ord("Q"),
    "yaw_right": ord("E"),
    "escape": 0x1B,
    "continue": 0x20,
}


class EditorEnvironment(HoloOceanEnvironment):
    """Bound waits even when attaching to an editor game process."""

    @property
    def _timeout(self) -> int:
        return 60


def launcher_engine_dir() -> Path | None:
    """Return the UE install directory registered by the Epic Games Launcher."""
    manifest = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Epic/UnrealEngineLauncher/LauncherInstalled.dat"
    if not manifest.is_file():
        return None
    data = json.loads(manifest.read_text(encoding="utf-8"))
    match = next((i for i in data.get("InstallationList", []) if i["AppName"] == f"UE_{ENGINE_VERSION}"), None)
    return Path(match["InstallLocation"]) if match else None


def registry_engine_dir() -> Path | None:
    """Return the UE install directory from the engine-version registry key."""
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ENGINE_REGISTRY_KEY) as key:
            value, _ = winreg.QueryValueEx(key, "InstalledDirectory")
    except OSError:
        return None
    return Path(value)


def find_editor(explicit: str | None) -> Path:
    """Resolve UnrealEditor.exe: --editor, env var, Epic Launcher, then registry."""
    override = explicit or os.environ.get(EDITOR_ENV_VAR)
    if override:
        editor = Path(override)
    else:
        engine_dir = launcher_engine_dir() or registry_engine_dir()
        if engine_dir is None:
            raise FileNotFoundError(
                f"UE {ENGINE_VERSION} not found; pass --editor or set {EDITOR_ENV_VAR} "
                "to path/to/UnrealEditor.exe")
        editor = engine_dir / "Engine/Binaries/Win64/UnrealEditor.exe"
    if not editor.is_file():
        raise FileNotFoundError(editor)
    return editor


def is_key_pressed(key_code: int) -> bool:
    """Return whether a Windows virtual key is currently held down."""
    return bool(win32api.GetAsyncKeyState(key_code) & 0x8000)


def update_manual_target(
    target: np.ndarray,
    delta_seconds: float,
    move_speed: float,
    yaw_speed: float,
    env_min: np.ndarray,
    env_max: np.ndarray,
) -> np.ndarray:
    """Update a PID pose target from keyboard input relative to the AUV heading."""
    updated = target.copy()
    movement = move_speed * delta_seconds
    rotation = yaw_speed * delta_seconds

    forward = float(is_key_pressed(KEY_CODES["forward"])) - float(
        is_key_pressed(KEY_CODES["backward"])
    )
    lateral = float(is_key_pressed(KEY_CODES["left"])) - float(
        is_key_pressed(KEY_CODES["right"])
    )
    direction = np.asarray([forward, lateral], dtype=np.float32)
    direction_length = float(np.linalg.norm(direction))
    if direction_length > 0:
        direction /= direction_length
        yaw_radians = np.deg2rad(updated[5])
        updated[0] += movement * (
            direction[0] * np.cos(yaw_radians)
            - direction[1] * np.sin(yaw_radians)
        )
        updated[1] += movement * (
            direction[0] * np.sin(yaw_radians)
            + direction[1] * np.cos(yaw_radians)
        )
    if is_key_pressed(KEY_CODES["up"]):
        updated[2] += movement
    if is_key_pressed(KEY_CODES["down"]):
        updated[2] -= movement
    if is_key_pressed(KEY_CODES["yaw_left"]):
        updated[5] += rotation
    if is_key_pressed(KEY_CODES["yaw_right"]):
        updated[5] -= rotation

    updated[:3] = np.clip(updated[:3], env_min, env_max)
    updated[5] = ((updated[5] + 180.0) % 360.0) - 180.0
    return updated


def enable_inspection_lights(env: HoloOceanEnvironment,
                             intensity: float = NOMINAL.light_intensity,
                             pitch_deg: float = NOMINAL.light_pitch_deg) -> None:
    """Illuminate the camera view with the AUV's two upper headlights."""
    for name in ("flashlight1", "flashlight2"):
        env.turn_on_flashlight(
            name, intensity=intensity, beam_width=1000,
            angle_pitch=pitch_deg, angle_yaw=0,
        )


def is_pipe_view(mode: str, station_name: str, location: np.ndarray) -> bool:
    """Inspect camera frames along the full manually measured pipe span."""
    x, y, z = map(float, location)
    near_pipe = (
        PIPE_X_MIN - 0.5 <= x <= PIPE_X_MAX + 0.5
        and abs(y) <= 3.5
        and -12.0 <= z <= -8.5
    )
    scanning = station_name.startswith(("pipe_front_scan", "pipe_back_scan"))
    return near_pipe and (mode == "manual" or scanning)


def save_damage_event(
    output: Path,
    frame: np.ndarray,
    analysis: CrackAnalysis,
    candidate: CrackCandidate,
    mode: str,
    tick: int,
    station_name: str,
    location: np.ndarray,
    event_index: int,
) -> dict:
    """Save the original frame and reproducible detection evidence."""
    event_dir = output / "damage_events" / f"event_{event_index:03d}"
    event_dir.mkdir(parents=True, exist_ok=False)
    images = {
        "camera.png": frame[:, :, :3],
        "preprocessed.png": analysis.preprocessed,
        "mask.png": analysis.mask,
        "annotated.png": draw_detections(frame, analysis),
    }
    for name, image in images.items():
        if not cv2.imwrite(str(event_dir / name), image):
            raise OSError(f"Could not save {event_dir / name}")
    event = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "tick": tick,
        "mode": mode,
        "station": station_name,
        "position_m": location.tolist(),
        "bbox_xywh": list(candidate.bbox),
        "candidate_score": candidate.score,
        "event_dir": str(event_dir),
    }
    (event_dir / "event.json").write_text(
        json.dumps(event, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return event


def clean_capture_category(station_name: str, location: np.ndarray) -> str | None:
    """Select pipe scans and pier orbits, excluding route transitions."""
    if is_pipe_view("auto", station_name, location):
        return "pipe_front" if station_name.startswith("pipe_front_scan") else "pipe_back"
    if "_orbit_" in station_name:
        if station_name.startswith("pier_0_level_"):
            return "pier_0"
        if station_name.startswith("pier_1_level_"):
            return "pier_1"
    return None


def save_clean_structure_frame(
    output: Path,
    frame: np.ndarray,
    tick: int,
    station_name: str,
    location: np.ndarray,
    yaw: float,
    category: str,
    rotation_rpy_deg: list[float] | None = None,
) -> dict:
    """Save an unmodified sensor frame and append its route metadata."""
    if category not in {"pipe_front", "pipe_back", "pier_0", "pier_1"}:
        raise ValueError(f"Unknown clean capture category: {category}")
    images = output / "images" / category
    images.mkdir(parents=True, exist_ok=True)
    image_name = f"frame_{tick:06d}.png"
    image_path = images / image_name
    if not cv2.imwrite(str(image_path), frame[:, :, :3]):
        raise OSError(f"Could not save {image_path}")
    record = {
        "image": f"images/{category}/{image_name}",
        "timestamp": datetime.now().astimezone().isoformat(),
        "tick": tick,
        "station": station_name,
        "structure": "pipe" if category.startswith("pipe_") else "pier",
        "category": category,
        "position_m": location.tolist(),
        "yaw_deg": yaw,
        "width": int(frame.shape[1]),
        "height": int(frame.shape[0]),
    }
    if rotation_rpy_deg is not None:
        record["rotation_rpy_deg"] = rotation_rpy_deg
    with (output / "frames.jsonl").open("a", encoding="utf-8") as manifest:
        manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def rotation_rpy_from_pose(pose: np.ndarray) -> list[float]:
    """Convert a PoseSensor matrix to the agent roll, pitch and yaw degrees."""
    rotation = pose[:3, :3]
    roll = np.arctan2(rotation[2, 1], rotation[2, 2])
    pitch = np.arctan2(-rotation[2, 0], np.hypot(rotation[0, 0], rotation[1, 0]))
    yaw = np.arctan2(rotation[1, 0], rotation[0, 0])
    return np.degrees([roll, pitch, yaw]).tolist()


def load_preview_rows(capture: Path, ticks: list[int]) -> list[dict]:
    """Find saved camera poses for a short inspection preview."""
    manifest = capture / "frames.jsonl"
    if not manifest.is_file():
        raise FileNotFoundError(manifest)
    wanted = set(ticks)
    rows: dict[int, dict] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = json.loads(line)
        tick = row.get("tick")
        if tick not in wanted:
            continue
        if tick in rows:
            raise ValueError(f"Duplicate preview tick: {tick}")
        if len(row.get("position_m", [])) != 3 or "yaw_deg" not in row:
            raise ValueError(f"Preview pose is incomplete at tick {tick}")
        source_image = capture / row["image"]
        if not source_image.is_file():
            raise FileNotFoundError(source_image)
        rows[tick] = row
    missing = wanted.difference(rows)
    if missing:
        raise ValueError(f"Preview ticks not found: {sorted(missing)}")
    return [rows[tick] for tick in ticks]


def capture_pose_previews(
    env: HoloOceanEnvironment,
    rows: list[dict],
    source: Path,
    output: Path,
    agent_name: str,
    map_hash: str,
) -> None:
    """Teleport only in the running game and save camera views at known poses."""
    records = []
    agent = env.agents[agent_name]
    zeros = np.zeros(3, dtype=np.float32)
    for row in rows:
        location = np.asarray(row["position_m"], dtype=np.float32)
        rotation = np.asarray(
            row.get("rotation_rpy_deg", [0.0, 0.0, row["yaw_deg"]]),
            dtype=np.float32,
        )
        if rotation.shape != (3,) or not np.isfinite(rotation).all():
            raise ValueError(f"Invalid preview rotation at tick {row['tick']}")
        target = np.concatenate((location, rotation))
        agent.set_physics_state(location, rotation, zeros, zeros)
        state = None
        for _ in range(12):
            state = env.step(target)
        if state is None or "PoseSensor" not in state or "InspectionCamera" not in state:
            raise RuntimeError(f"Preview sensors missing at tick {row['tick']}")
        first_location = np.asarray(state["PoseSensor"][:3, 3], dtype=np.float32)
        correction = location - first_location
        corrected_agent_location = location + correction
        corrected_target = np.concatenate((corrected_agent_location, rotation))
        agent.set_physics_state(corrected_agent_location, rotation, zeros, zeros)
        for _ in range(12):
            state = env.step(corrected_target)
        actual_pose = state["PoseSensor"]
        actual_location = np.asarray(actual_pose[:3, 3], dtype=np.float32)
        actual_yaw = float(np.degrees(np.arctan2(actual_pose[1, 0], actual_pose[0, 0])))
        position_error = float(np.linalg.norm(actual_location - location))
        yaw_error = abs(angle_delta(float(rotation[2]), actual_yaw))
        if position_error > 0.05 or yaw_error > 1.0:
            raise RuntimeError(
                f"Preview pose mismatch at tick {row['tick']}: "
                f"position={position_error:.2f} m, yaw={yaw_error:.1f} deg"
            )
        frame = state["InspectionCamera"][:, :, :3]
        image_name = f"preview_{row['tick']:06d}.png"
        if not cv2.imwrite(str(output / image_name), frame):
            raise OSError(f"Could not save {output / image_name}")
        reference = cv2.imread(str(source / row["image"]), cv2.IMREAD_COLOR)
        if reference is None or reference.shape != frame.shape:
            raise ValueError(f"Reference image shape mismatch at tick {row['tick']}")
        side_by_side = np.concatenate((reference, frame), axis=1)
        comparison_name = f"compare_{row['tick']:06d}.png"
        if not cv2.imwrite(str(output / comparison_name), side_by_side):
            raise OSError(f"Could not save {output / comparison_name}")
        records.append({
            "source_tick": row["tick"], "station": row["station"],
            "category": row["category"], "source_image": str(source / row["image"]),
            "preview_image": image_name, "comparison_image": comparison_name,
            "position_m": actual_location.tolist(), "yaw_deg": actual_yaw,
            "position_error_m": position_error, "yaw_error_deg": yaw_error,
            "agent_location_correction_m": correction.tolist(),
        })
    report = {
        "mode": "pose_preview", "reference_capture": str(source),
        "map_sha256": map_hash, "frames": records,
        "note": "The left half of each comparison is the reference capture; the right half is the current saved map.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    capture_clean_pipe = bool(getattr(args, "capture_clean_pipe", False))
    capture_clean_structures = bool(getattr(args, "capture_clean_structures", False))
    capture_structures = bool(getattr(args, "capture_structures", False))
    preview_source = getattr(args, "preview_source", None)
    preview_ticks = getattr(args, "preview_ticks", None)
    preview_rows = load_preview_rows(preview_source, preview_ticks) if preview_source else None
    capture_enabled = capture_clean_pipe or capture_clean_structures or capture_structures
    capture_every_ticks = int(getattr(args, "capture_every_ticks", 10))
    if sum((capture_clean_pipe, capture_clean_structures, capture_structures)) > 1:
        raise ValueError("Choose one capture mode")
    if capture_enabled and args.mode != "auto":
        raise ValueError("Structure capture requires auto mode")
    dataset_role = getattr(args, "dataset_role", None) if capture_structures else "train"
    scene_state = getattr(args, "scene_state", None) if capture_structures else "clean"
    if capture_structures and (dataset_role is None or scene_state is None):
        raise ValueError("Neutral capture requires dataset role and scene state")
    if capture_every_ticks < 1:
        raise ValueError("Capture interval must be positive")
    randomize_profile = getattr(args, "randomize", None)
    if randomize_profile and (args.mode != "auto" or preview_source):
        raise ValueError("Randomized conditions require an auto route run")
    conditions = (sample_conditions(randomize_profile, int(args.seed))
                  if randomize_profile else NOMINAL)
    # Nominal runs read the module ROUTE at call time so QA harness patches still apply.
    route = conditioned_route(conditions) if randomize_profile else ROUTE
    capture_schedule = CaptureSchedule(
        conditions.capture_interval_ticks if randomize_profile
        else (capture_every_ticks, capture_every_ticks), conditions.seed)
    scenario = json.loads((HERE / "scenario.json").read_text(encoding="utf-8"))
    project = ROOT / "holoocean/engine/Holodeck.uproject"
    world_override = getattr(args, "world", None)
    if world_override:
        if not world_override.startswith("/Game/AUVInspection/Maps/") or ".." in world_override:
            raise ValueError("World override must name a map under /Game/AUVInspection/Maps/")
        scenario["world"] = world_override
    map_file = project.parent / "Content" / (scenario["world"].removeprefix("/Game/") + ".umap")
    if not map_file.is_file():
        raise FileNotFoundError("Build the map first with build_map.py")
    map_hash = None
    if capture_enabled or preview_source:
        with map_file.open("rb") as map_stream:
            map_hash = hashlib.file_digest(map_stream, "sha256").hexdigest()
    output_prefix = (
        "preview_poses" if preview_source else
        f"capture_{dataset_role}_{scene_state}" if capture_structures
        else "clean_structures" if capture_clean_structures
        else "clean_pipe" if capture_clean_pipe else "run"
    )
    output = HERE / "output" / datetime.now().strftime(
        f"{output_prefix}_%Y%m%d_%H%M%S_%f"
    )
    output.mkdir(parents=True)
    if randomize_profile:
        (output / "conditions.json").write_text(json.dumps(describe(conditions), indent=2),
                                                encoding="utf-8")
        LOG.info("Randomized conditions: %s", json.dumps(describe(conditions)))
    ticks_per_sec = int(scenario.get("ticks_per_sec", 30))
    key = str(uuid.uuid4())
    semaphore = win32event.CreateSemaphore(None, 0, 1, "Global\\HOLODECK_LOADING_SEM" + key)
    command = [str(find_editor(args.editor)), str(project), scenario["world"], "-game",
               "-HolodeckOn", f"--HolodeckUUID={key}", "-TicksPerSec=30", "-FramesPerSec=0",
               "-windowed", "-ResX=1280", "-ResY=720", "-nosplash", "-unattended",
               "-nosound", f"-abslog={output / 'unreal.log'}"]
    if args.headless:
        command.append("-RenderOffScreen")
    process = None
    env = None
    telemetry: list[dict] = []
    reached: list[str] = []
    completed = False
    stopped_by_user = False
    stopped_for_damage = False
    damage_events: list[dict] = []
    clean_frame_count = 0
    clean_frames_by_category = {
        "pipe_front": 0, "pipe_back": 0, "pier_0": 0, "pier_1": 0,
    }
    tracker = CrackTracker()
    paused_pose: list[float] | None = None
    last_damage_position: np.ndarray | None = None
    try:
        LOG.info("Starting Unreal; output: %s", output)
        process = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 180
        while win32event.WaitForSingleObject(semaphore, 250) != win32event.WAIT_OBJECT_0:
            if process.poll() is not None:
                raise RuntimeError(f"Unreal exited with {process.returncode}; inspect {output / 'unreal.log'}")
            if time.monotonic() > deadline:
                raise TimeoutError("Unreal startup exceeded 180 seconds")
        env = EditorEnvironment(start_world=False, uuid=key, scenario=scenario,
                                ticks_per_sec=30, frames_per_sec=False)
        state = env.reset()
        enable_inspection_lights(env, conditions.light_intensity, conditions.light_pitch_deg)
        LOG.info("Two onboard inspection lights enabled")
        current_enabled = any(conditions.current_mps) or bool(conditions.current_variation_mps)
        if current_enabled:
            env.set_ocean_currents(scenario["main_agent"], current_at(conditions, 0, ticks_per_sec))
        if preview_rows is not None:
            capture_pose_previews(
                env, preview_rows, preview_source, output,
                scenario["main_agent"], map_hash,
            )
            LOG.info("Saved %d camera previews to %s", len(preview_rows), output)
            return
        station = 0
        final_hold = 0
        delta_seconds = 1.0 / ticks_per_sec
        initial_agent = scenario["agents"][0]
        manual_target = np.asarray(
            initial_agent["location"] + initial_agent.get("rotation", [0, 0, 0]),
            dtype=np.float32,
        )
        env_min = np.asarray(scenario["env_min"], dtype=np.float32)
        env_max = np.asarray(scenario["env_max"], dtype=np.float32)
        if args.mode == "manual":
            LOG.info(
                "Manual controls: W/S=forward/back, A/D=strafe, "
                "R/F=up/down, Q/E=yaw, Space=continue after alert, Esc=exit"
            )
        for tick in range(args.steps):
            if not getattr(args, "ignore_global_escape", False) and is_key_pressed(KEY_CODES["escape"]):
                stopped_by_user = True
                break

            if paused_pose is not None:
                station_name = "damage_pause"
                target = np.asarray(paused_pose, dtype=np.float32)
            elif args.mode == "auto":
                pose = state.get("PoseSensor")
                if pose is None:
                    raise RuntimeError("PoseSensor missing")
                station, passed = advance_station(
                    route, station, np.asarray(pose[:3, 3]).tolist()
                )
                reached.extend(passed)
                station_name, target_values = route[station]
                target = np.asarray(target_values, dtype=np.float32)
            else:
                manual_target = update_manual_target(
                    manual_target,
                    delta_seconds,
                    args.move_speed,
                    args.yaw_speed,
                    env_min,
                    env_max,
                )
                station_name = "manual"
                target = manual_target.copy()

            if current_enabled and tick > 0 and tick % ticks_per_sec == 0:
                env.set_ocean_currents(scenario["main_agent"],
                                       current_at(conditions, tick, ticks_per_sec))
            state = env.step(target)
            pose = state.get("PoseSensor")
            if pose is None:
                raise RuntimeError("PoseSensor missing")
            location = np.asarray(pose[:3, 3])
            distance = float(np.linalg.norm(location - target[:3]))
            yaw = float(np.degrees(np.arctan2(pose[1, 0], pose[0, 0])))
            yaw_error = abs(angle_delta(float(target[5]), yaw))
            if paused_pose is None and args.mode == "auto" and station == len(route) - 1:
                if distance < FINAL_POSITION_TOLERANCE_M and yaw_error < FINAL_YAW_TOLERANCE_DEG:
                    final_hold += 1
                else:
                    final_hold = 0
            if tick % TELEMETRY_INTERVAL_TICKS == 0:
                sample = {
                    "tick": tick,
                    "mode": args.mode,
                    "target": station_name,
                    "position_m": location.tolist(),
                    "command": target.tolist(),
                    "target_distance_m": distance,
                    "yaw_deg": yaw,
                    "yaw_error_deg": yaw_error,
                }
                telemetry.append(sample)
            frame = state.get("InspectionCamera")
            analysis = None
            if frame is not None and paused_pose is None and tick >= CAMERA_WARMUP_TICKS:
                pipe_view = is_pipe_view(args.mode, station_name, location)
                if capture_enabled:
                    category = clean_capture_category(station_name, location)
                    if capture_clean_pipe and category not in {"pipe_front", "pipe_back"}:
                        category = None
                    if category is not None and capture_schedule.due(tick):
                        save_clean_structure_frame(
                            output, frame, tick, station_name, location, yaw, category,
                            rotation_rpy_from_pose(pose),
                        )
                        clean_frame_count += 1
                        clean_frames_by_category[category] += 1
                elif pipe_view:
                    analysis = analyze_frame(frame)
                    candidate = tracker.update(analysis)
                    rearmed = last_damage_position is None or float(
                        np.linalg.norm(location - last_damage_position)
                    ) >= CRACK_REARM_DISTANCE_M
                    if candidate is not None and rearmed:
                        event = save_damage_event(
                            output, frame, analysis, candidate, args.mode, tick,
                            station_name, location, len(damage_events) + 1,
                        )
                        damage_events.append(event)
                        last_damage_position = location.copy()
                        tracker.reset()
                        paused_pose = location.tolist() + [0.0, 0.0, yaw]
                        if args.mode == "manual":
                            manual_target = np.asarray(paused_pose, dtype=np.float32)
                        LOG.warning(
                            "POSSIBLE PIPE DAMAGE at %s; image captured at %s: %s",
                            location.round(2), event["timestamp"], event["event_dir"],
                        )
                        if args.headless:
                            stopped_for_damage = True
                else:
                    tracker.reset()
            if not args.headless and frame is not None:
                preview = draw_detections(frame, analysis) if analysis is not None else frame[:, :, :3].copy()
                cv2.putText(
                    preview,
                    f"Mode: {args.mode.upper()} | Target: {station_name} | Distance: {distance:.2f} m",
                    (12, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )
                if capture_enabled:
                    cv2.putText(
                        preview, f"STRUCTURE CAPTURE: {clean_frame_count} frames",
                        (12, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (255, 255, 255), 1,
                    )
                if args.mode == "manual":
                    cv2.putText(
                        preview,
                        "W/S: move  A/D: strafe  R/F: depth  Q/E: yaw  ESC: exit",
                        (12, 46),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (255, 255, 255),
                        1,
                    )
                if paused_pose is not None:
                    cv2.putText(
                        preview, "POSSIBLE DAMAGE - IMAGE SAVED | SPACE: CONTINUE",
                        (12, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2,
                    )
                cv2.imshow("AUV navigation", preview)
                key = cv2.waitKey(1) & 0xFF
                if key == 27:
                    stopped_by_user = True
                    break
                if paused_pose is not None and key == KEY_CODES["continue"]:
                    paused_pose = None
                    tracker.reset()
                    LOG.info("Continuing after crack alert")
            if stopped_for_damage:
                break
            if args.mode == "auto" and final_hold >= FINAL_HOLD_TICKS:
                reached.append(station_name)
                LOG.info("Reached %s at %s", station_name, location.round(2))
                completed = True
                break
        report = {
            "mode": args.mode,
            "route_completed": completed if args.mode == "auto" else None,
            "reached_stations": reached,
            "total_stations": len(route) if args.mode == "auto" else None,
            "telemetry_samples": len(telemetry),
            "stopped_by_user": stopped_by_user,
            "stopped_for_damage": stopped_for_damage,
            "damage_event_count": len(damage_events),
            "damage_events": damage_events,
        }
        if randomize_profile:
            report["conditions"] = describe(conditions)
        if capture_enabled:
            report.update({
                "capture_clean_pipe": capture_clean_pipe,
                "capture_clean_structures": capture_clean_structures,
                "capture_structures": capture_structures,
                "dataset_role": dataset_role,
                "scene_state": scene_state,
                "map_sha256": map_hash,
                "world": scenario["world"],
                "captured_frame_count": clean_frame_count,
                "captured_frames_by_category": clean_frames_by_category,
                "clean_frame_count": clean_frame_count,
                "capture_every_ticks": capture_every_ticks,
                "clean_frames_by_category": clean_frames_by_category,
                "clean_images_dir": str(output / "images"),
            })
            required_categories = (
                clean_frames_by_category if (capture_clean_structures or capture_structures)
                else {key: clean_frames_by_category[key] for key in ("pipe_front", "pipe_back")}
            )
            if not all(required_categories.values()):
                LOG.warning(
                    "Structure capture is missing images from one or more structures: %s",
                    required_categories,
                )
        (output / "telemetry.json").write_text(
            json.dumps(telemetry, indent=2), encoding="utf-8"
        )
        (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        LOG.info("Result: %s", json.dumps(report))
        if not telemetry:
            raise RuntimeError("No telemetry samples collected")
    finally:
        if env is not None:
            env.__on_exit__()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        win32api.CloseHandle(semaphore)
        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--editor", help=f"Path to UnrealEditor.exe (default: ${EDITOR_ENV_VAR}, "
                        "Epic Launcher, then the UE registry key)")
    parser.add_argument("--world", help="Map asset path under /Game/AUVInspection/Maps/ for an isolated capture")
    parser.add_argument("--steps", type=int, default=60000)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--ignore-global-escape", action="store_true",
                        help="Ignore desktop Escape during headless capture; Ctrl+C still stops the process")
    capture_group = parser.add_mutually_exclusive_group()
    capture_group.add_argument(
        "--capture-clean-structures", action="store_true",
        help="Save clean camera frames from both pipe sides and both pier orbits",
    )
    capture_group.add_argument(
        "--capture-clean-pipe", action="store_true",
        help="Save clean camera frames from the pipe scans only",
    )
    capture_group.add_argument(
        "--capture-structures", action="store_true",
        help="Save unlabeled pipe and pier frames for calibration or evaluation",
    )
    capture_group.add_argument(
        "--preview-source", type=Path,
        help="Reference capture folder with frames.jsonl for a short camera preview",
    )
    parser.add_argument(
        "--preview-ticks", type=str,
        help="Comma-separated ticks from --preview-source, e.g. 3900,3910,3920",
    )
    parser.add_argument(
        "--dataset-role", choices=("train", "calibration", "test"),
        help="Purpose of a --capture-structures session",
    )
    parser.add_argument(
        "--scene-state", choices=("clean", "mixed"),
        help="Map state declared by the operator; individual frames are not labeled",
    )
    parser.add_argument(
        "--capture-every-ticks", type=int, default=10,
        help="Capture one eligible frame every N simulation ticks (default: 10)",
    )
    parser.add_argument(
        "--randomize", choices=sorted(PROFILES),
        help="Sample standoff, route jitter, current, lights and capture timing for this run "
             "(train: around nominal; heldout: outside the train ranges). Requires --seed",
    )
    parser.add_argument("--seed", type=int, help="Seed for --randomize; recorded in conditions.json")
    parser.add_argument(
        "--mode", choices=("auto", "manual"), default="auto", help="AUV control mode"
    )
    parser.add_argument(
        "--move-speed", type=float, default=2.0, help="Manual movement speed in m/s"
    )
    parser.add_argument(
        "--yaw-speed", type=float, default=45.0, help="Manual yaw speed in degrees/s"
    )
    args = parser.parse_args()
    if args.ignore_global_escape and not (args.headless and
            (args.capture_structures or args.capture_clean_structures or args.capture_clean_pipe)):
        parser.error("--ignore-global-escape requires headless capture")
    if args.steps < 1:
        parser.error("--steps must be positive")
    if args.move_speed <= 0:
        parser.error("--move-speed must be positive")
    if args.yaw_speed <= 0:
        parser.error("--yaw-speed must be positive")
    if args.mode == "manual" and args.headless:
        parser.error("--mode manual cannot be combined with --headless")
    if (args.capture_clean_pipe or args.capture_clean_structures or args.capture_structures) and args.mode != "auto":
        parser.error("structure capture requires --mode auto")
    if args.capture_structures and (args.dataset_role is None or args.scene_state is None):
        parser.error("--capture-structures requires --dataset-role and --scene-state")
    if not args.capture_structures and (args.dataset_role is not None or args.scene_state is not None):
        parser.error("--dataset-role and --scene-state require --capture-structures")
    if args.capture_every_ticks < 1:
        parser.error("--capture-every-ticks must be positive")
    if bool(args.randomize) != (args.seed is not None):
        parser.error("--randomize and --seed must be used together")
    if args.randomize and (args.mode != "auto" or args.preview_source):
        parser.error("--randomize requires an auto route run")
    if bool(args.preview_source) != bool(args.preview_ticks):
        parser.error("--preview-source and --preview-ticks must be used together")
    if args.preview_source:
        try:
            args.preview_ticks = [int(value.strip()) for value in args.preview_ticks.split(",")]
        except ValueError:
            parser.error("--preview-ticks must contain integers")
        if not args.preview_ticks or len(args.preview_ticks) != len(set(args.preview_ticks)):
            parser.error("--preview-ticks must contain unique ticks")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args)


if __name__ == "__main__":
    main()
