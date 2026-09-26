"""Run both pipe scans offscreen, auto-continue alerts, and save camera evidence.

This QA harness uses the production controller, sensors and detector unchanged.
It truncates only the in-memory route after the final back scan. No map is saved.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
import subprocess
from unittest.mock import patch

import cv2
import numpy as np

import run_inspection as inspection
from crack_detection import CrackAnalysis


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=6000)
    args = parser.parse_args()
    if args.steps < 1:
        parser.error("--steps must be positive")

    evidence = inspection.HERE / "output" / datetime.now().strftime("detector_qa_%Y%m%d_%H%M%S")
    evidence.mkdir(parents=True, exist_ok=False)
    source_map = inspection.ROOT / "holoocean/engine/Content/AUVInspection/Maps/AUVInspection.umap"
    map_hash = hashlib.sha256(source_map.read_bytes()).hexdigest()
    route_end = max(i for i, (name, _) in enumerate(inspection.ROUTE) if name.startswith("pipe_back_scan"))
    route = inspection.ROUTE[:route_end + 1]
    original_popen = subprocess.Popen
    original_analyze = inspection.analyze_frame
    original_gate = inspection.is_pipe_view
    current_station = ""
    current_location: list[float] = []
    frames: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    run_output: Path | None = None

    def start_offscreen(command: list[str], **kwargs: object) -> subprocess.Popen:
        nonlocal run_output
        log_argument = next(value for value in command if value.startswith("-abslog="))
        run_output = Path(log_argument.removeprefix("-abslog=")).parent
        return original_popen([*command, "-RenderOffScreen"], **kwargs)

    def record_gate(mode: str, station: str, location: np.ndarray) -> bool:
        nonlocal current_station, current_location
        current_station = station
        current_location = location.tolist()
        return original_gate(mode, station, location)

    def record_analysis(frame: np.ndarray) -> CrackAnalysis:
        analysis = original_analyze(frame)
        side = "front" if current_station.startswith("pipe_front") else "back"
        counts[side] += 1
        sample: dict[str, object] = {
            "station": current_station,
            "position_m": current_location.copy(),
            "candidate_boxes": [list(item.bbox) for item in analysis.candidates],
        }
        if counts[side] % 30 == 1:
            name = f"{side}_{counts[side]:05d}.png"
            if not cv2.imwrite(str(evidence / name), frame[:, :, :3]):
                raise OSError(f"Cannot write camera evidence: {name}")
            sample["camera"] = name
        frames.append(sample)
        return analysis

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.info("Both-side detector QA evidence: %s", evidence)
    run_args = argparse.Namespace(
        editor=None, steps=args.steps, headless=False, mode="auto", move_speed=2.0, yaw_speed=45.0,
    )
    try:
        # Preserve the real alert/save/rearm path; simulate Space without a GUI.
        with (
            patch.object(inspection, "ROUTE", route),
            patch.object(inspection.subprocess, "Popen", start_offscreen),
            patch.object(inspection, "is_pipe_view", record_gate),
            patch.object(inspection, "analyze_frame", record_analysis),
            patch.object(inspection, "is_key_pressed", return_value=False),
            patch.object(inspection.cv2, "imshow"),
            patch.object(inspection.cv2, "waitKey", return_value=32),
        ):
            inspection.run(run_args)
    finally:
        (evidence / "frames.json").write_text(json.dumps(frames, indent=2), encoding="utf-8")

    if run_output is None:
        raise RuntimeError("The runtime did not produce an output directory")
    report = json.loads((run_output / "report.json").read_text(encoding="utf-8"))
    summary = {
        "run_output": str(run_output),
        "completed_both_pipe_scans": report["route_completed"],
        "inspected_frames": dict(counts),
        "front_alerts": sum(event["station"].startswith("pipe_front") for event in report["damage_events"]),
        "back_alerts": sum(event["station"].startswith("pipe_back") for event in report["damage_events"]),
        "map_sha256_before": map_hash,
        "map_sha256_after": hashlib.sha256(source_map.read_bytes()).hexdigest(),
        "scope": "Both pipe sides only; piers omitted. Space simulated after each saved alert.",
    }
    (evidence / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logging.info("Detector QA summary: %s", json.dumps(summary))
    if not report["route_completed"] or not counts["back"]:
        raise RuntimeError("Both-side QA is incomplete; inspect the saved report")
    if summary["map_sha256_before"] != summary["map_sha256_after"]:
        raise RuntimeError("Map changed during QA; inspect concurrent editor activity")


if __name__ == "__main__":
    main()
