"""Fit four surface-only PatchCore memory banks from approved clean frames."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections import defaultdict
from pathlib import Path

import anomalib
import cv2
import numpy as np
import torch
import torchvision
from anomalib.models.components import KCenterGreedy

from .model import CATEGORIES, extract_embeddings, iter_tiles, load_roi, make_model, surface_grid, to_tensor


def load_manifest(dataset: Path) -> list[dict]:
    rows = [json.loads(line) for line in (dataset / "manifest.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    if not rows:
        raise ValueError("Training manifest is empty")
    for row in rows:
        if row["dataset_role"] != "train" or row["scene_state"] != "clean":
            raise ValueError(f"Only clean train frames may build the memory bank: {row['image']}")
    return rows


def frame_embeddings(model: torch.nn.Module, image: np.ndarray, roi: np.ndarray,
                     device: torch.device, batch_size: int, rng: np.random.Generator,
                     max_per_frame: int) -> torch.Tensor:
    tiles = list(iter_tiles(image, roi))
    samples: list[torch.Tensor] = []
    for start in range(0, len(tiles), batch_size):
        group = tiles[start:start + batch_size]
        with torch.no_grad():
            embedding = extract_embeddings(model, to_tensor([item[2] for item in group], device))
        for item, feature in zip(group, embedding, strict=True):
            grid = surface_grid(item[3], feature.shape[-2:])
            selected = feature.permute(1, 2, 0)[torch.from_numpy(grid).to(device)]
            if selected.numel():
                samples.append(selected.cpu())
    if not samples:
        raise ValueError("No surface embeddings in frame")
    all_features = torch.cat(samples)
    count = min(max_per_frame, len(all_features))
    indices = rng.choice(len(all_features), size=count, replace=False)
    return all_features[indices]


def fit(dataset: Path, destination: Path, max_candidates: int = 8000,
        coreset_ratio: float = 0.1, batch_size: int = 4) -> dict:
    rows = load_manifest(dataset)
    approval_file = dataset / "roi_approved.json"
    if not approval_file.is_file():
        raise FileNotFoundError(approval_file)
    approvals = json.loads(approval_file.read_text(encoding="utf-8"))
    pending = [row["image"] for row in rows if row["image"] not in approvals]
    if pending:
        raise ValueError(f"Review all surface masks before fitting; {len(pending)} pending")
    rows = [row for row in rows if approvals[row["image"]]["status"] == "approved"]
    if destination.exists():
        raise FileExistsError(destination)
    if not 0 < coreset_ratio <= 1 or max_candidates < 100 or batch_size < 1:
        raise ValueError("Invalid fitting parameters")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = make_model(pre_trained=True, device=device)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    if set(grouped) != set(CATEGORIES):
        raise ValueError("Training data must contain all four structure groups")
    rng = np.random.default_rng(20260926)
    destination.mkdir(parents=True)
    sizes: dict[str, int] = {}
    for category in CATEGORIES:
        reservoir: torch.Tensor | None = None
        seen = 0
        for index, row in enumerate(grouped[category], 1):
            image = cv2.imread(row["source_image"], cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(row["source_image"])
            roi = load_roi(dataset, row)
            features = frame_embeddings(model, image, roi, device, batch_size, rng, 64)
            if reservoir is None:
                reservoir = torch.empty((max_candidates, features.shape[1]), dtype=features.dtype)
            # Uniform reservoir bounds memory while preserving the full route's coverage.
            for feature in features:
                seen += 1
                if seen <= max_candidates:
                    reservoir[seen - 1] = feature
                else:
                    slot = int(rng.integers(seen))
                    if slot < max_candidates:
                        reservoir[slot] = feature
            if index % 20 == 0 or index == len(grouped[category]):
                print(f"{category}: {index}/{len(grouped[category])} frames", flush=True)
        if reservoir is None or seen < 10:
            raise ValueError(f"Insufficient surface embeddings for {category}")
        sampler = KCenterGreedy(reservoir[:min(seen, max_candidates)].to(device),
                                sampling_ratio=coreset_ratio)
        bank = sampler.sample_coreset().cpu()
        torch.save(bank, destination / f"{category}_bank.pt")
        sizes[category] = len(bank)
        print(f"{category}: {len(bank)} coreset features", flush=True)
    torch.save(model.feature_extractor.state_dict(), destination / "backbone.pt")
    manifest_path = dataset / "manifest.jsonl"
    config = {
        "model": "PatchCore", "backbone": "wide_resnet50_2",
        "layers": ["layer2", "layer3"], "tile_size": 256, "tile_step": 128,
        "preprocessing": "RGB ImageNet mean/std, no frame resize",
        "source_dataset": str(dataset.resolve()),
        "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "source_capture": json.loads((dataset / "summary.json").read_text(encoding="utf-8"))["capture"],
        "bank_sizes": sizes, "device": str(device), "python": platform.python_version(),
        "torch": torch.__version__, "torchvision": torchvision.__version__,
        "anomalib": anomalib.__version__, "opencv": cv2.__version__,
        "coreset_ratio": coreset_ratio, "max_candidates_per_group": max_candidates,
    }
    (destination / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--max-candidates", type=int, default=8000)
    parser.add_argument("--coreset-ratio", type=float, default=0.1)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()
    print(json.dumps(fit(args.dataset, args.destination, args.max_candidates,
                         args.coreset_ratio, args.batch_size), indent=2))


if __name__ == "__main__":
    main()
