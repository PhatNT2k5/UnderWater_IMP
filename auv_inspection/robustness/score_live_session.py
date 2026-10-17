"""Score a dashboard live session against a defect inventory (calibrated geometry, as the harness).

Each alert event is located with `locate_event` (box centre ray onto the structure, geometry v2) and
matched to the nearest labelled defect of the same structure within its radius. Prints one line per
alert, the defects found, the false alerts and the analysed-frame statistics.

    python -m auv_inspection.robustness.score_live_session <session_dir> <inventory.json>
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from robustness.defect_inventory import load_inventory, locate_event, match_defect  # noqa: E402
from robustness.geometry import load_params  # noqa: E402


def score(session: Path, inventory_file: Path) -> dict:
    inventory = load_inventory(inventory_file)
    report_files = list(session.glob("output/*/report.json"))
    if len(report_files) != 1:
        raise ValueError(f"Expected one run report in {session}")
    report = json.loads(report_files[0].read_text(encoding="utf-8"))
    params = load_params()
    alerts = []
    for event_file in sorted(session.glob("output/*/damage_events/event_*/event.json")):
        event = json.loads(event_file.read_text(encoding="utf-8"))
        category, point = locate_event(event_file, params=params)
        same = [d for d in inventory.defects if d.category == category]
        nearest = min(same, key=lambda d: d.distance_to(point)) if same and point is not None else None
        alerts.append({"event": event_file.parent.name, "tick": event["tick"], "category": category,
                       "world_m": None if point is None else np.round(point, 3).tolist(),
                       "nearest": None if nearest is None else nearest.defect_id,
                       "distance_m": None if nearest is None else round(float(nearest.distance_to(point)), 3),
                       "defect": match_defect(point, category, inventory.defects)})
    found = sorted({a["defect"] for a in alerts if a["defect"]})
    frames_file = session / "patchcore_frames.jsonl"
    frames = [json.loads(line) for line in frames_file.open(encoding="utf-8")] if frames_file.is_file() else []
    elapsed = sorted(f["processing_ms"] for f in frames if f.get("processing_ms"))
    return {"session": session.name, "route_completed": report.get("route_completed"),
            "stations": f"{len(report.get('reached_stations', []))}/{report.get('total_stations')}",
            "alerts": alerts, "found": found, "defects": len(inventory.defects),
            "false_alerts": sum(a["defect"] is None for a in alerts),
            "frames": len(frames), "unavailable": dict(Counter(f["reason"] for f in frames if f["status"] != "ready")),
            "processing_ms_median": elapsed[len(elapsed) // 2] if elapsed else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("session", type=Path)
    parser.add_argument("inventory", type=Path)
    result = score(parser.parse_args().session, parser.parse_args().inventory)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
