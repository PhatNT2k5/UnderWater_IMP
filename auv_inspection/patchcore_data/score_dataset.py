"""Save uncalibrated tiled PatchCore score maps for one captured route."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import torch

from .model import CATEGORIES, load_roi, predict_map
from .predict import load_model


def score_dataset(dataset: Path, model_dir: Path, destination: Path) -> dict:
    if destination.exists():
        raise FileExistsError(destination)
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    if not rows:
        raise ValueError("Dataset manifest is empty")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    destination.mkdir(parents=True)
    summary: list[dict] = []
    for category in CATEGORIES:
        selected = [row for row in rows if row["category"] == category]
        if not selected:
            continue
        model = load_model(model_dir, category, device)
        (destination / category).mkdir()
        for index, row in enumerate(selected, 1):
            image = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(row["source_image"])
            roi = load_roi(dataset, row)
            start = time.perf_counter()
            scores = predict_map(model, image, roi, device)
            elapsed_ms = (time.perf_counter() - start) * 1000
            if not np.isfinite(scores).any():
                raise ValueError(f"No valid surface scores: {row['image']}")
            relative = Path(category) / f"score_{row['tick']:06d}.npz"
            np.savez_compressed(destination / relative, scores=scores)
            summary.append({
                "image": row["image"], "tick": row["tick"],
                "station": row["station"], "category": category,
                "score_file": relative.as_posix(),
                "max_score": float(np.nanmax(scores)), "processing_ms": elapsed_ms,
            })
            if index % 20 == 0 or index == len(selected):
                print(f"{category}: {index}/{len(selected)} frames", flush=True)
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
    with (destination / "score_manifest.jsonl").open("w", encoding="utf-8") as handle:
        for row in summary:
            handle.write(json.dumps(row) + "\n")
    report = {
        "model_dir": str(model_dir.resolve()), "dataset": str(dataset.resolve()),
        "dataset_role": rows[0]["dataset_role"], "scene_state": rows[0]["scene_state"],
        "frames": len(summary),
        "median_processing_ms": float(np.median([row["processing_ms"] for row in summary])),
    }
    (destination / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(score_dataset(args.dataset, args.model_dir, args.destination), indent=2))


if __name__ == "__main__":
    main()
