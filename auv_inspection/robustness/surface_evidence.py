"""Accumulate anomaly evidence on surface cells across views and alert per surface region (P5).

Per analysed frame, every 10 cm surface cell in view gets two values from the highest PatchCore
score among the pixels that land on it: the score itself and the score divided by the frame's
median score inside the scored ROI. A view of a cell is a hit when the score reaches the locked
pixel threshold of its group AND the normalised value reaches the threshold of its stratum
(structure group x element). A cell keeps a view only if the camera moved at least MIN_MOVE_M
since its last kept view, so consecutive near-identical frames do not count as independent
evidence. A cell alerts at VIEWS_REQUIRED hits; new alert cells within MERGE_RADIUS_M of an
earlier alert on the same structure join that alert instead of raising a new one.

Why this rule (measured on the development captures, GENERALIZATION_PLAN.md, P5):
- the normalised value removes global score shifts (turbidity, blur), the absolute threshold
  rejects structures whose relative score rises with stand-off distance (flanges seen beyond the
  train range); either alone left 1-32 false alerts per capture where both together left 0-1;
- pipe joints (flanges every 3 m and the pipe ends) score consistently high on clean surface;
  they get their own threshold (Mondrian stratum) rather than a blind spot;
- k-of-n views is the online form of "k-th highest view value >= threshold"; marine snow still
  defeats it (hits several % of views at random) and needs image-level treatment (P4).

Stratum thresholds come from clean calibration captures by `calibrate_surface.py` (conformal
upper quantile of the per-cell k-th highest normalised value, calibrated separately from the
pixel threshold); this module only applies them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import numpy as np

from inspection_route import PIPE_X_MAX, PIPE_X_MIN
from robustness.geometry import GeometryParams
from robustness.surface import render_uv

CELL_M = 0.10
POOL_PX = 4
MIN_MOVE_M = 0.30
VIEWS_REQUIRED = 3
MERGE_RADIUS_M = 0.6
# Flange rings every 3 m (seen in the clean captures at x = -9, 3, 15 and as the strongest clean
# score cells). On the development map A capture (2.77 m stand-off) clean cells stay above the
# pipe-body level up to 0.4-0.5 m from a ring centre (ring, shadow, projection offset up to 0.2 m).
PIPE_JOINTS_X = tuple(3.0 * k for k in range(-5, 6)) + (PIPE_X_MIN, PIPE_X_MAX)
JOINT_HALF_WIDTH_M = 0.5
# v2: recalibrated with geometry v2 (surface cells move with the geometry); v1 kept for comparison.
CALIBRATION_FILE = Path(__file__).resolve().parent / "calibration" / "surface_v2.json"

CellKey = tuple[str, int, int]


def element_of(category: str, u: float) -> str:
    """Surface element type used as calibration stratum."""
    if category.startswith("pipe_"):
        near_joint = min(abs(u - x) for x in PIPE_JOINTS_X) <= JOINT_HALF_WIDTH_M
        return "pipe_joint" if near_joint else "pipe_body"
    return "pier_face"


def stratum(category: str, u: float) -> str:
    return f"{category}/{element_of(category, u)}"


def pooled(scores: np.ndarray) -> np.ndarray:
    """Max over POOL_PX x POOL_PX blocks, NaN where the whole block is unscored."""
    height, width = scores.shape
    blocks = scores.reshape(height // POOL_PX, POOL_PX, width // POOL_PX, POOL_PX)
    highest = np.where(np.isfinite(blocks), blocks, -np.inf).max(axis=(1, 3))
    return np.where(np.isfinite(highest), highest, np.nan).astype(np.float32)


CellValue = tuple[float, float]  # (highest score on the cell, that score / frame median)


def frame_cells(scores: np.ndarray, position: np.ndarray, yaw_deg: float, category: str,
                params: GeometryParams) -> tuple[dict[CellKey, CellValue], np.ndarray, np.ndarray]:
    """(score, normalised score) per surface cell in view, plus the pooled grid's cell indices.

    Returns (values, keys_u, keys_v) where keys_* are (H/POOL_PX, W/POOL_PX) integer grids
    (-1 where a pooled pixel has no score or misses the structure).
    """
    finite = np.isfinite(scores)
    if not finite.any():
        return {}, np.empty(0), np.empty(0)
    baseline = float(np.median(scores[finite]))
    if baseline <= 0:
        raise ValueError("Median PatchCore score must be positive to normalise")
    grid = pooled(scores)
    uv = render_uv(position, yaw_deg, category, params, POOL_PX)
    valid = np.isfinite(grid) & np.isfinite(uv[..., 0])
    keys_u = np.full(grid.shape, -1, np.int64)
    keys_v = np.full(grid.shape, -1, np.int64)
    keys_u[valid] = np.floor(uv[valid][:, 0] / CELL_M).astype(np.int64)
    keys_v[valid] = np.floor(uv[valid][:, 1] / CELL_M).astype(np.int64)
    highest: dict[CellKey, float] = {}
    for iu, iv, value in zip(keys_u[valid], keys_v[valid], grid[valid]):
        key = (category, int(iu), int(iv))
        highest[key] = max(highest.get(key, -np.inf), float(value))
    values = {key: (value, value / baseline) for key, value in highest.items()}
    return values, keys_u, keys_v


@dataclass(frozen=True)
class SurfaceCalibration:
    thresholds: dict[str, float]          # stratum -> threshold on the normalised cell value
    source_sha256: str = ""
    pixel_thresholds_sha256: str = ""     # pixel threshold file the calibration was made with

    def lowest_threshold(self, category: str) -> float:
        """Lowest stratum threshold of a structure group (frame-level hit test of the gate)."""
        values = [value for name, value in self.thresholds.items() if name.startswith(f"{category}/")]
        if not values:
            raise KeyError(f"No surface calibration for group {category}")
        return min(values)

    def threshold(self, key: CellKey) -> float:
        name = stratum(key[0], (key[1] + 0.5) * CELL_M)
        if name not in self.thresholds:
            raise KeyError(f"No surface calibration for stratum {name}")
        return self.thresholds[name]


def load_calibration(path: Path = CALIBRATION_FILE) -> SurfaceCalibration:
    raw = path.read_bytes()
    data = json.loads(raw)
    for key, expected in (("cell_m", CELL_M), ("min_move_m", MIN_MOVE_M),
                          ("views_required", VIEWS_REQUIRED), ("pool_px", POOL_PX)):
        if data[key] != expected:
            raise ValueError(f"Surface calibration {key}={data[key]} differs from runtime {expected}")
    return SurfaceCalibration({name: float(item["threshold"]) for name, item in data["strata"].items()},
                              hashlib.sha256(raw).hexdigest(), data.get("pixel_thresholds_sha256", ""))


@dataclass
class CellState:
    last_position: np.ndarray
    views: int = 0
    hits: int = 0
    alert_id: int | None = None


@dataclass(frozen=True)
class SurfaceAlert:
    alert_id: int
    category: str
    cells: tuple[CellKey, ...]
    surface_uv_m: tuple[float, float]


def is_hit(value: CellValue, pixel_threshold: float, stratum_threshold: float) -> bool:
    return value[0] >= pixel_threshold and value[1] >= stratum_threshold


@dataclass
class SurfaceEvidence:
    calibration: SurfaceCalibration
    pixel_thresholds: dict[str, float]      # locked per-group PatchCore thresholds
    cells: dict[CellKey, CellState] = field(default_factory=dict)
    alerts: list[SurfaceAlert] = field(default_factory=list)

    def observe(self, position: np.ndarray,
                values: dict[CellKey, CellValue]) -> tuple[list[SurfaceAlert], list[CellKey]]:
        """Add one analysed frame; return new alerts and the cells that reached the rule now."""
        position = np.asarray(position, float)
        reached: list[CellKey] = []
        for key, value in values.items():
            state = self.cells.get(key)
            if state is None:
                state = self.cells[key] = CellState(position)
            elif np.linalg.norm(position - state.last_position) < MIN_MOVE_M:
                continue
            state.last_position = position
            state.views += 1
            if is_hit(value, self.pixel_thresholds[key[0]], self.calibration.threshold(key)):
                state.hits += 1
                if state.hits == VIEWS_REQUIRED and state.alert_id is None:
                    reached.append(key)
        new_alerts = []
        for key in reached:
            existing = self._nearby_alert(key)
            if existing is not None:
                self.cells[key].alert_id = existing
                continue
            alert = SurfaceAlert(len(self.alerts) + 1, key[0], (key,),
                                 ((key[1] + 0.5) * CELL_M, (key[2] + 0.5) * CELL_M))
            self.alerts.append(alert)
            self.cells[key].alert_id = alert.alert_id
            new_alerts.append(alert)
        return new_alerts, reached

    def _nearby_alert(self, key: CellKey) -> int | None:
        radius = MERGE_RADIUS_M / CELL_M
        for other, state in self.cells.items():
            if (state.alert_id is not None and other[0] == key[0]
                    and np.hypot(other[1] - key[1], other[2] - key[2]) <= radius):
                return state.alert_id
        return None

    def coverage(self, min_views: int = VIEWS_REQUIRED) -> dict[str, int]:
        """Cells per structure group with at least min_views kept views (inspected surface)."""
        counts: dict[str, int] = {}
        for (category, _, _), state in self.cells.items():
            if state.views >= min_views:
                counts[category] = counts.get(category, 0) + 1
        return counts
