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
from robustness.evaluate_capture import (
    PATCHCORE_MODEL, PATCHCORE_REFERENCE, PATCHCORE_THRESHOLDS, classical_detector, evaluate,
    patchcore_detector)

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
    return {
        "detector": result["detector"], "capture": Path(result["capture"]).name,
        "condition": condition_name([Degradation(**item) for item in result["degradations"]]),
        "recall": f"{recall['count']}/{recall['total']}" if recall["total"] else "n/a",
        "false_alerts": result["false_alerts"],
        "false_alerts_per_100m": round(result["false_alerts_per_100m"] or 0.0, 2),
        "frame_flag_rate": None if flags["rate"] is None else round(flags["rate"], 3),
        "analysed_share": round(analysed / total, 3) if total else None,
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


def run(captures: list[tuple[Path, Path | None]], detectors: list[str], conditions: list[str],
        destination: Path, seed: int) -> list[dict]:
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    for detector_name in detectors:
        for capture, inventory_path in captures:
            inventory = load_inventory(inventory_path) if inventory_path else None
            for condition in conditions:
                output = destination / f"{detector_name}__{capture.name}__{condition.replace(':', '')}.json"
                if output.exists():
                    result = json.loads(output.read_text(encoding="utf-8"))
                else:
                    # A fresh detector per run so no tracker state leaks between conditions.
                    detector = (classical_detector() if detector_name == "classical" else
                                patchcore_detector(PATCHCORE_MODEL, PATCHCORE_REFERENCE, PATCHCORE_THRESHOLDS))
                    result = evaluate(capture, detector_name, detector, inventory,
                                      parse_condition(condition), seed)
                    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
                rows.append(summary_row(result))
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
    parser.add_argument("--detector", action="append", choices=("classical", "patchcore"))
    parser.add_argument("--condition", action="append",
                        help=f"none or factor:severity[+factor:severity]; default {DEFAULT_CONDITIONS}")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    captures = [(capture, inventory) for capture, inventory in args.mixed] + [(c, None) for c in args.clean]
    if not captures:
        parser.error("Give at least one --mixed or --clean capture")
    run(captures, args.detector or ["classical", "patchcore"],
        args.condition or list(DEFAULT_CONDITIONS), args.destination, args.seed)


if __name__ == "__main__":
    main()
