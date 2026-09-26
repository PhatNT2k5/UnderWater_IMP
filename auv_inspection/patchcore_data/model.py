"""Shared tiled PatchCore preprocessing, fitting and inference primitives."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
import torch
from anomalib.models.components import KCenterGreedy
from anomalib.models.image.patchcore.torch_model import PatchcoreModel

TILE_SIZE = 256
TILE_STEP = 128
CATEGORIES = ("pipe_front", "pipe_back", "pier_0", "pier_1")
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def tile_starts(length: int) -> list[int]:
    """Include a final edge tile even when the stride misses the border."""
    if length < TILE_SIZE:
        raise ValueError(f"Image dimension {length} is smaller than {TILE_SIZE}")
    starts = list(range(0, length - TILE_SIZE + 1, TILE_STEP))
    if starts[-1] != length - TILE_SIZE:
        starts.append(length - TILE_SIZE)
    return starts


def iter_tiles(image: np.ndarray, roi: np.ndarray) -> Iterator[tuple[int, int, np.ndarray, np.ndarray]]:
    """Yield only tiles with enough inspected surface."""
    height, width = image.shape[:2]
    if roi.shape != (height, width):
        raise ValueError("ROI and image dimensions differ")
    for y in tile_starts(height):
        for x in tile_starts(width):
            tile_roi = roi[y:y + TILE_SIZE, x:x + TILE_SIZE]
            if np.count_nonzero(tile_roi) < 0.05 * TILE_SIZE * TILE_SIZE:
                continue
            yield x, y, image[y:y + TILE_SIZE, x:x + TILE_SIZE], tile_roi


def to_tensor(images: list[np.ndarray], device: torch.device) -> torch.Tensor:
    array = np.stack([cv2.cvtColor(image, cv2.COLOR_BGR2RGB) for image in images])
    array = (array.astype(np.float32) / 255.0 - MEAN) / STD
    return torch.from_numpy(array.transpose(0, 3, 1, 2).copy()).to(device)


def make_model(pre_trained: bool, device: torch.device) -> PatchcoreModel:
    model = PatchcoreModel(
        layers=["layer2", "layer3"], backbone="wide_resnet50_2",
        pre_trained=pre_trained, num_neighbors=1,
    ).to(device)
    model.eval()
    return model


@torch.no_grad()
def extract_embeddings(model: PatchcoreModel, batch: torch.Tensor) -> torch.Tensor:
    features = model.feature_extractor(batch)
    pooled = {name: model.feature_pooler(value) for name, value in features.items()}
    return model.generate_embedding(pooled)


def surface_grid(roi: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Keep feature centers safely inside the inspected surface."""
    eroded = cv2.erode((roi > 0).astype(np.uint8), np.ones((9, 9), np.uint8))
    return cv2.resize(eroded, (size[1], size[0]), interpolation=cv2.INTER_NEAREST) > 0


@torch.no_grad()
def predict_map(model: PatchcoreModel, image: np.ndarray, roi: np.ndarray,
                device: torch.device, batch_size: int = 4) -> np.ndarray:
    """Merge tiled nearest-neighbor distances at original camera resolution."""
    tiles = list(iter_tiles(image, roi))
    if not tiles:
        raise ValueError("No valid inspected surface tiles")
    if model.memory_bank.numel() == 0:
        raise ValueError("PatchCore memory bank is empty")
    height, width = image.shape[:2]
    accum = np.zeros((height, width), dtype=np.float32)
    count = np.zeros((height, width), dtype=np.float32)
    for start in range(0, len(tiles), batch_size):
        group = tiles[start:start + batch_size]
        embedding = extract_embeddings(model, to_tensor([tile[2] for tile in group], device))
        batch_count, channels, grid_h, grid_w = embedding.shape
        flat = embedding.permute(0, 2, 3, 1).reshape(-1, channels)
        scores, _ = model.nearest_neighbors(flat, n_neighbors=1)
        scores = scores.reshape(batch_count, grid_h, grid_w).cpu().numpy()
        for (x, y, _, tile_roi), grid in zip(group, scores, strict=True):
            high_res = cv2.resize(grid, (TILE_SIZE, TILE_SIZE), interpolation=cv2.INTER_LINEAR)
            valid = (tile_roi > 0).astype(np.float32)
            accum[y:y + TILE_SIZE, x:x + TILE_SIZE] += high_res * valid
            count[y:y + TILE_SIZE, x:x + TILE_SIZE] += valid
    result = np.full((height, width), np.nan, dtype=np.float32)
    np.divide(accum, count, out=result, where=count > 0)
    return result


def load_roi(dataset: Path, row: dict) -> np.ndarray:
    """Require an explicitly approved surface mask for training or scoring."""
    approvals = dataset / "roi_approved.json"
    if not approvals.is_file():
        raise FileNotFoundError(f"Approved surface masks are missing: {approvals}")
    approved = json.loads(approvals.read_text(encoding="utf-8"))
    entry = approved.get(row["image"])
    if not entry or entry.get("status") != "approved":
        raise ValueError(f"Surface mask has not been approved: {row['image']}")
    mask_path = dataset / entry["mask"]
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None or mask.shape != (row["height"], row["width"]):
        raise ValueError(f"Invalid surface mask: {mask_path}")
    return mask
