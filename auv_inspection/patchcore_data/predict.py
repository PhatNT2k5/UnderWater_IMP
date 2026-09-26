"""Score a captured frame using its approved ROI and matching PatchCore bank."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch

from .model import CATEGORIES, load_roi, make_model, predict_map


def load_model(model_dir: Path, category: str, device: torch.device) -> torch.nn.Module:
    if category not in CATEGORIES:
        raise ValueError(f"Unknown structure group: {category}")
    config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    if config["model"] != "PatchCore" or config["tile_size"] != 256 or config["tile_step"] != 128:
        raise ValueError("Unsupported PatchCore model configuration")
    model = make_model(pre_trained=False, device=device)
    model.feature_extractor.load_state_dict(torch.load(
        model_dir / "backbone.pt", map_location=device, weights_only=True))
    model.memory_bank = torch.load(model_dir / f"{category}_bank.pt",
                                   map_location=device, weights_only=True)
    model.eval()
    return model


def predict(dataset: Path, model_dir: Path, image_name: str, destination: Path) -> dict:
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    matches = [row for row in rows if row["image"] == image_name]
    if len(matches) != 1:
        raise ValueError(f"Expected one manifest entry for {image_name}; found {len(matches)}")
    row = matches[0]
    image = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(row["source_image"])
    roi = load_roi(dataset, row)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(model_dir, row["category"], device)
    scores = predict_map(model, image, roi, device)
    finite = np.isfinite(scores)
    if not finite.any():
        raise ValueError("No valid surface score")
    valid = scores[finite]
    low, high = np.percentile(valid, [5, 99])
    scaled = np.zeros(scores.shape, np.uint8)
    scaled[finite] = np.clip((valid - low) * 255 / max(high - low, 1e-6), 0, 255).astype(np.uint8)
    heatmap = cv2.applyColorMap(scaled, cv2.COLORMAP_TURBO)
    heatmap[~finite] = 0
    destination.mkdir(parents=True, exist_ok=False)
    np.save(destination / "anomaly_scores.npy", scores)
    cv2.imwrite(str(destination / "camera.png"), image)
    cv2.imwrite(str(destination / "roi.png"), roi)
    cv2.imwrite(str(destination / "heatmap.png"), heatmap)
    info = {
        "detector": "PatchCore", "model_dir": str(model_dir.resolve()),
        "dataset": str(dataset.resolve()), "image": row["image"],
        "tick": row["tick"], "station": row["station"],
        "category": row["category"], "position_m": row["position_m"],
        "yaw_deg": row["yaw_deg"], "maximum_anomaly_score": float(np.max(valid)),
        "threshold": None, "interpretation": "Uncalibrated anomaly distance",
    }
    (destination / "result.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("image_name")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(predict(args.dataset, args.model_dir, args.image_name,
                             args.destination), indent=2))


if __name__ == "__main__":
    main()
