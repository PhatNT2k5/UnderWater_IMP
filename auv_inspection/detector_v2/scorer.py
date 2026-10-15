"""Anomaly score map from DINOv2 tokens and a per-group nearest-neighbour bank.

Score of a token = 1 - highest cosine similarity to the bank of its structure group (0 for an
exact match, up to 2), or the Euclidean distance to the nearest bank token after a Mahalanobis
whitening (P4.3). An optional per-group linear transform (`transforms.py`) is applied to tokens
and bank alike. The token grid is interpolated back to camera resolution and set to NaN
outside the ROI, the same contract as `patchcore_data.model.predict_map`, so the margin, the
diffuse-anomaly gate and the surface rule apply unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import cv2
import numpy as np
import torch

from .features import DinoExtractor, MODEL_NAME, frame_tokens, load_extractor
from .transforms import ChainedTransform, FeatureTransform, from_state

BANK_CHUNK = 16384  # bank rows per similarity matmul, bounds GPU memory on the 4 GB card
MODEL_KIND = "DINOv2-kNN"


@torch.inference_mode()
def nearest_distance(tokens: torch.Tensor, bank: torch.Tensor, metric: str = "cosine") -> torch.Tensor:
    """Per token (rows, channels): 1 - max cosine similarity, or min Euclidean distance, to the bank."""
    if bank.numel() == 0:
        raise ValueError("Memory bank is empty")
    if metric not in ("cosine", "euclidean"):
        raise ValueError(f"Unknown metric {metric!r}")
    if metric == "cosine":
        best = torch.full((tokens.shape[0],), -1.0, device=tokens.device, dtype=torch.float32)
        for start in range(0, bank.shape[0], BANK_CHUNK):
            similarity = tokens @ bank[start:start + BANK_CHUNK].T
            best = torch.maximum(best, similarity.max(dim=1).values.float())
        return 1.0 - best
    x = tokens.float()
    nearest = torch.full((x.shape[0],), float("inf"), device=x.device)
    x_norm = (x * x).sum(1, keepdim=True)
    for start in range(0, bank.shape[0], BANK_CHUNK):
        chunk = bank[start:start + BANK_CHUNK].float()
        squared = x_norm + (chunk * chunk).sum(1) - 2 * x @ chunk.T
        nearest = torch.minimum(nearest, squared.min(dim=1).values)
    return nearest.clamp_min(0).sqrt()


@dataclass
class DinoScorer:
    extractor: DinoExtractor
    banks: dict[str, torch.Tensor]                       # already transformed when transforms is set
    transforms: dict[str, FeatureTransform | ChainedTransform] | None = None

    def __call__(self, frame: np.ndarray, roi: np.ndarray, category: str) -> np.ndarray:
        if category not in self.banks:
            raise ValueError(f"No bank for structure group {category}")
        tokens = frame_tokens(self.extractor, frame)
        grid_h, grid_w, channels = tokens.shape
        flat = tokens.reshape(-1, channels)
        transform = (self.transforms or {}).get(category)
        if transform is not None:
            flat = transform.apply(flat).to(self.banks[category].dtype)
        distance = nearest_distance(flat, self.banks[category],
                                    transform.metric if transform is not None else "cosine")
        grid = distance.reshape(grid_h, grid_w).cpu().numpy().astype(np.float32)
        scores = cv2.resize(grid, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR)
        scores[roi == 0] = np.nan
        return scores


def is_v2_model(model_dir: Path) -> bool:
    config = model_dir / "config.json"
    return config.is_file() and json.loads(config.read_text(encoding="utf-8")).get("model") == MODEL_KIND


def load_scorer(model_dir: Path, device: torch.device) -> DinoScorer:
    config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    if config.get("model") != MODEL_KIND or config.get("backbone") != MODEL_NAME:
        raise ValueError(f"Not a {MODEL_KIND} model directory: {model_dir}")
    extractor = load_extractor(device, float(config["scale"]))
    # A derived model (derive_model.py) reuses another model's banks and adds a transform.
    bank_dir = Path(config.get("bank_dir", model_dir))
    banks = {category: torch.load(bank_dir / f"{category}_bank.pt", map_location=device,
                                  weights_only=True)
             for category in config["bank_sizes"]}
    transforms = None
    if config.get("transform_file"):
        states = torch.load(model_dir / config["transform_file"], map_location="cpu", weights_only=True)
        transforms = {category: from_state(state).to(device) for category, state in states.items()}
        banks = {category: transforms[category].apply(bank) for category, bank in banks.items()}
    # Euclidean (whitened) banks stay float32: fp16 loses the small distances.
    banks = {category: bank if transforms and transforms[category].metric == "euclidean"
             else bank.to(extractor.dtype) for category, bank in banks.items()}
    return DinoScorer(extractor, banks, transforms)
