"""Run detectors over captures and degradation conditions; write per-run JSON and a summary table.

Reused for every phase comparison (baseline v1.1 in P1, detector v2 in P4, acceptance in P7).
Each (detector, capture, condition) result is stored separately and never overwritten.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from robustness.defect_inventory import load_inventory  # noqa: E402
from robustness.degradation import Degradation, parse_degradation
from robustness.evaluate_capture import DETECTORS, evaluate_many, make_detector

DEFAULT_CONDITIONS = ("none", "turbidity:2", "turbidity:4", "marine_snow:3", "marine_snow:5",
                      "illumination:4", "motion_blur:3")


def condition_name(degradations: list[Degradation]) -> str:
    return "+".join(f"{item.factor}{item.severity}" for item in degradations) or "none"


def parse_condition(text: str) -> list[Degradation]:
    return [] if text == "none" else [parse_degradation(part) for part in text.split("+")]


def summary_row(result: dict) -> dict:
    recall = result["defects"]["recall"]
    flags = result["frame_flag_rate_without_defect"]
    analysed = sum(group.get("analysed", 0) for group in result["availability"].values())
    total = sum(sum(group.values()) for group in result["availability"].values())
    noise = result.get("pose_noise") or {"sigma_m": 0.0, "sigma_yaw_deg": 0.0}
    return {
        "detector": result["detector"], "capture": Path(result["capture"]).name,
        "condition": condition_name([Degradation(**item) for item in result["degradations"]]),
        "pose_noise": f"{noise['sigma_m']}m/{noise['sigma_yaw_deg']}deg",
        "recall": f"{recall['count']}/{recall['total']}" if recall["total"] else "n/a",
        "false_alerts": result["false_alerts"],
        "false_alerts_per_100m": round(result["false_alerts_per_100m"] or 0.0, 2),
        "frame_flag_rate": None if flags["rate"] is None else round(flags["rate"], 3),
        "analysed_share": round(analysed / total, 3) if total else None,
        "diffuse_share": round(sum(group.get("diffuse_anomaly", 0) for group in
                                   result["availability"].values()) / total, 3) if total else None,
        # Results written before the timing fix averaged in skipped frames (~0 ms); hide them.
        "ms_per_frame": (round(result["processing_ms_median"], 1)
                         if result.get("timing_basis") == "analysed_frames_only"
                         and result["processing_ms_median"] is not None else None),
    }


def markdown_table(rows: list[dict]) -> str:
    headers = list(rows[0])
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(row[key]) for key in headers) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def result_path(destination: Path, detector: str, capture: Path, condition: str,
                pose_noise: tuple[float, float]) -> Path:
    noise = f"__pose{pose_noise[0]}m{pose_noise[1]}deg" if any(pose_noise) else ""
    return destination / f"{detector}__{capture.name}__{condition.replace(':', '')}{noise}.json"


def run(captures: list[tuple[Path, Path | None]], detectors: list[str], conditions: list[str],
        destination: Path, seed: int, pose_noise: tuple[float, float] = (0.0, 0.0)) -> list[dict]:
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    for capture, inventory_path in captures:
        inventory = load_inventory(inventory_path) if inventory_path else None
        for condition in conditions:
            paths = {name: result_path(destination, name, capture, condition, pose_noise)
                     for name in detectors}
            missing = [name for name, path in paths.items() if not path.exists()]
            if missing:
                # Fresh detectors per run so no tracker state leaks between conditions; every
                # frame is degraded once and shared by all detectors.
                fresh = evaluate_many(capture, {name: make_detector(name) for name in missing},
                                      inventory, parse_condition(condition), seed, pose_noise)
                for name, result in fresh.items():
                    paths[name].write_text(json.dumps(result, indent=2), encoding="utf-8")
            for name in detectors:
                rows.append(summary_row(json.loads(paths[name].read_text(encoding="utf-8"))))
                print(json.dumps(rows[-1]), flush=True)
    (destination / "summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (destination / "summary.md").write_text(markdown_table(rows), encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("destination", type=Path)
    parser.add_argument("--mixed", nargs=2, action="append", default=[], metavar=("CAPTURE", "INVENTORY"),
                        type=Path, help="Capture of a map with defects and its inventory JSON")
    parser.add_argument("--clean", action="append", default=[], type=Path, help="Capture of a clean map")
    parser.add_argument("--detector", action="append", choices=DETECTORS)
    parser.add_argument("--condition", action="append",
                        help=f"none or factor:severity[+factor:severity]; default {DEFAULT_CONDITIONS}")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--pose-noise", type=float, nargs=2, default=(0.0, 0.0),
                        metavar=("SIGMA_M", "SIGMA_YAW_DEG"))
    args = parser.parse_args()
    captures = [(capture, inventory) for capture, inventory in args.mixed] + [(c, None) for c in args.clean]
    if not captures:
        parser.error("Give at least one --mixed or --clean capture")
    run(captures, args.detector or list(DETECTORS), args.condition or list(DEFAULT_CONDITIONS),
        args.destination, args.seed, tuple(args.pose_noise))


if __name__ == "__main__":
    main()
