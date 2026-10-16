"""Cache of detector-v2 token grids for offline experiments (P8).

Scoring a frame with DINOv2 is the slow, GPU-bound part of a benchmark run; everything after the
token grid (ROI, margins, gate, surface rule, scoring) is cheap. A grid depends only on the image
fed to the model (capture frame, degradation and its seed) and the model's banks/transform, so
rule variants can be replayed from cached grids. One `.npz` per capture, condition, degradation
seed and model grid key; entries are keyed "<tick>_<category>". Never used at runtime.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np


class GridCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.grids: dict[str, np.ndarray] = {}
        if path.is_file():
            with np.load(path) as data:
                self.grids = {key: data[key] for key in data.files}
        self.hits = self.misses = 0
        self.dirty = False

    def get(self, tick: int, category: str) -> np.ndarray | None:
        grid = self.grids.get(f"{tick}_{category}")
        self.hits += grid is not None
        self.misses += grid is None
        return grid

    def put(self, tick: int, category: str, grid: np.ndarray) -> None:
        if grid.dtype != np.float32:
            raise ValueError("Cached grids must be float32 to replay scores exactly")
        self.grids[f"{tick}_{category}"] = grid
        self.dirty = True

    def save(self) -> None:
        if not self.dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_file():  # another run may have saved entries since this cache was loaded
            with np.load(self.path) as data:
                for key in data.files:
                    self.grids.setdefault(key, data[key])
        temporary = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp.npz")  # one per process
        np.savez_compressed(temporary, **self.grids)
        os.replace(temporary, self.path)
        self.dirty = False


def cache_path(directory: Path, capture: Path, condition: str, seed: int, model_key: str) -> Path:
    return directory / f"{capture.name}__{condition}__seed{seed}__{model_key}.npz"
