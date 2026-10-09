"""Physical defect inventories: where each defect is on a map, and alert-to-defect matching.

Recall is counted per physical defect, not per frame: a defect counts as detected when any
alert of the run localizes onto it, and as observable when it was in view (geometry.in_view)
in at least `min_views` frames. Positions are estimated by projecting confirmed true-alert
boxes onto the structure (`locate_event`) and must be reviewed on images before use.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from robustness.geometry import DEFAULT_PARAMS, GeometryParams, in_view, pixel_to_surface


@dataclass(frozen=True)
class Defect:
    defect_id: str
    category: str
    world: np.ndarray            # point, or start of the crack segment
    radius_m: float              # localization tolerance (plus extent for point defects)
    end: np.ndarray | None = None  # end of the crack segment for long cracks

    def distance_to(self, point: np.ndarray) -> float:
        if self.end is None:
            return float(np.linalg.norm(self.world - point))
        segment = self.end - self.world
        t = float(np.clip((point - self.world) @ segment / (segment @ segment), 0.0, 1.0))
        return float(np.linalg.norm(self.world + t * segment - point))

    def centre(self) -> np.ndarray:
        return self.world if self.end is None else (self.world + self.end) / 2


@dataclass(frozen=True)
class Inventory:
    map_sha256: str
    defects: tuple[Defect, ...]


def load_inventory(path: Path) -> Inventory:
    data = json.loads(path.read_text(encoding="utf-8"))
    defects = tuple(Defect(item["id"], item["category"], np.asarray(item["world_m"], float),
                           float(item["radius_m"]),
                           np.asarray(item["end_m"], float) if "end_m" in item else None)
                    for item in data["defects"])
    if len({defect.defect_id for defect in defects}) != len(defects):
        raise ValueError(f"Duplicate defect ids in {path}")
    return Inventory(data["map_sha256"], defects)


def event_category(event: dict) -> str:
    if event.get("category"):
        return str(event["category"])
    station = str(event["station"])
    if station.startswith(("pipe_front", "pipe_back")):
        return "pipe_front" if station.startswith("pipe_front") else "pipe_back"
    raise ValueError(f"Cannot infer structure category from station {station!r}")


def locate_box(bbox_xywh: list[int], camera: np.ndarray, yaw_deg: float, category: str,
               params: GeometryParams = DEFAULT_PARAMS) -> np.ndarray | None:
    """World point under the centre of an alert box, or None if the ray misses the structure."""
    x, y, width, height = bbox_xywh
    hit = pixel_to_surface(x + width / 2, y + height / 2, camera, yaw_deg, category, params)
    return None if hit is None else hit.world


def locate_event(event_json: Path, default_yaw_deg: float = -90.0) -> tuple[str, np.ndarray | None]:
    """Classical events store no yaw; pipe-front scans always hold -90 degrees."""
    event = json.loads(event_json.read_text(encoding="utf-8"))
    yaw = event.get("yaw_deg")
    category = event_category(event)
    return category, locate_box(event["bbox_xywh"], np.asarray(event["position_m"], float),
                                default_yaw_deg if yaw is None else float(yaw), category)


def match_defect(point: np.ndarray | None, category: str,
                 defects: tuple[Defect, ...]) -> str | None:
    """Nearest defect of the same structure within its radius."""
    if point is None:
        return None
    candidates = [(defect.distance_to(point), defect) for defect in defects
                  if defect.category == category]
    candidates = [(distance, defect) for distance, defect in candidates if distance <= defect.radius_m]
    return min(candidates, key=lambda item: item[0])[1].defect_id if candidates else None


def defects_in_view(defects: tuple[Defect, ...], camera: np.ndarray, yaw_deg: float,
                    category: str, params: GeometryParams = DEFAULT_PARAMS) -> list[str]:
    return [defect.defect_id for defect in defects if defect.category == category
            and in_view(defect.centre(), camera, yaw_deg, category, params=params)]
