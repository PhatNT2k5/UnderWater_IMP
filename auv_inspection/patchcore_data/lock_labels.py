"""Freeze a fully reviewed test label file before threshold-blind evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .calibrate import load_labels


def lock(dataset: Path) -> dict:
    summary = json.loads((dataset / "summary.json").read_text(encoding="utf-8"))
    if summary["dataset_role"] != "test" or summary["scene_state"] != "mixed":
        raise ValueError("Only a mixed test dataset can be locked")
    label_path = dataset / "damage_labels.json"
    labels = load_labels(dataset)
    if labels.get("locked"):
        raise ValueError("Labels are already locked")
    inventory = labels.get("defects", {})
    if not inventory:
        raise ValueError("Physical defect inventory is required")
    rows = [line for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    labels["locked"] = True
    label_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")
    digest = hashlib.sha256(label_path.read_bytes()).hexdigest()
    receipt = {"dataset": str(dataset.resolve()), "labels_sha256": digest,
               "physical_defects": len(inventory), "frames": len(rows)}
    (dataset / "label_lock.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    print(json.dumps(lock(parser.parse_args().dataset), indent=2))


if __name__ == "__main__":
    main()
