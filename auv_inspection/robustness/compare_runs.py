"""Compare two benchmark result directories for one detector, field by field (code equivalence).

Every result file of the detector in the reference directory must exist in the candidate directory
with identical scoring fields (defects, false alerts, length, events, availability, ambiguity).
Timing fields are ignored. Prints a JSON summary; exit code 1 when anything differs.

    python -m auv_inspection.robustness.compare_runs <reference_dir> <candidate_dir> --detector NAME
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

FIELDS = ("defects", "false_alerts", "surveyed_length_m", "false_alerts_per_100m", "events", "availability",
          "ambiguity", "frame_flag_rate_without_defect", "degradations", "frames")


def compare(reference: Path, candidate: Path, detector: str) -> dict:
    files = sorted(f for f in reference.glob(f"{detector}__capture_*.json") if "__pose" not in f.name)
    if not files:
        raise FileNotFoundError(f"No {detector} results in {reference}")
    differences = []
    for file in files:
        other = candidate / file.name
        if not other.is_file():
            differences.append({"file": file.name, "missing": True})
            continue
        a, b = json.loads(file.read_text(encoding="utf-8")), json.loads(other.read_text(encoding="utf-8"))
        changed = [name for name in FIELDS if a.get(name) != b.get(name)]
        if changed:
            differences.append({"file": file.name, "fields": changed})
    return {"detector": detector, "reference": str(reference), "candidate": str(candidate),
            "runs": len(files), "runs_compared": len(files) - sum(d.get("missing", False) for d in differences),
            "identical": not differences, "fields": list(FIELDS), "differences": differences}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--detector", required=True)
    args = parser.parse_args()
    result = compare(args.reference, args.candidate, args.detector)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["identical"] else 1)


if __name__ == "__main__":
    main()
