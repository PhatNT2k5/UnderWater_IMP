"""Anomaly score map from DINOv2 tokens and a per-group nearest-neighbour bank.

Score of a token = 1 - highest cosine similarity to the bank of its structure group (0 for an
exact match, up to 2). The token grid is interpolated back to camera resolution and set to NaN
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

BANK_CHUNK = 16384  # bank rows per similarity matmul, bounds GPU memory on the 4 GB card
MODEL_KIND = "DINOv2-kNN"


@torch.inference_mode()
def nearest_distance(tokens: torch.Tensor, bank: torch.Tensor) -> torch.Tensor:
    """1 - max cosine similarity of each token (rows, channels) to the bank (n, channels)."""
    if bank.numel() == 0:
        raise ValueError("Memory bank is empty")
    best = torch.full((tokens.shape[0],), -1.0, device=tokens.device, dtype=torch.float32)
    for start in range(0, bank.shape[0], BANK_CHUNK):
        similarity = tokens @ bank[start:start + BANK_CHUNK].T
        best = torch.maximum(best, similarity.max(dim=1).values.float())
    return 1.0 - best


@dataclass
class DinoScorer:
    extractor: DinoExtractor
    banks: dict[str, torch.Tensor]

    def __call__(self, frame: np.ndarray, roi: np.ndarray, category: str) -> np.ndarray:
        if category not in self.banks:
            raise ValueError(f"No bank for structure group {category}")
        tokens = frame_tokens(self.extractor, frame)
        grid_h, grid_w, channels = tokens.shape
        distance = nearest_distance(tokens.reshape(-1, channels), self.banks[category])
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
    banks = {category: torch.load(model_dir / f"{category}_bank.pt", map_location=device,
                                  weights_only=True).to(extractor.dtype)
             for category in config["bank_sizes"]}
    return DinoScorer(extractor, banks)
