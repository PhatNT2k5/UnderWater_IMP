"""Pinhole camera and known-structure geometry: pixel <-> point on the pipe or a pier.

Used to localize alerts (P1) and to build the geometric ROI (P2). All functions take a
`GeometryParams`; `DEFAULT_PARAMS` is the uncalibrated model (camera at the PoseSensor,
level, pipe radius 0.5 m, pier half-width 0.95 m). `load_params()` reads the values fitted
to the reviewed ROI masks by `calibrate_geometry.py`.

Remaining approximations: the camera is level apart from a fitted pitch, roll is ignored,
structures are an ideal cylinder and square prisms, and the pose is taken from PoseSensor.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from math import atan2, cos, degrees, radians, sin, tan
from pathlib import Path

import numpy as np

from inspection_route import PIER_CENTERS_X, PIER_Y, PIPE_X_MAX, PIPE_X_MIN

IMAGE_WIDTH, IMAGE_HEIGHT = 640, 480
HORIZONTAL_FOV_DEG = 80.0
FOCAL_PX = (IMAGE_WIDTH / 2) / tan(radians(HORIZONTAL_FOV_DEG / 2))  # ~381.4 px
PIER_Z_RANGE = (-12.0, 1.6)
CATEGORIES = ("pipe_front", "pipe_back", "pier_0", "pier_1")
CALIBRATION_FILE = Path(__file__).resolve().parent / "calibration" / "geometry_v1.json"


@dataclass(frozen=True)
class GeometryParams:
    pipe_radius_m: float = 0.5
    pipe_axis_z: float = -10.3
    pier_half_width_m: float = 0.95
    camera_lateral_m: float = 0.0   # along image-right of the AUV
    camera_forward_m: float = 0.0
    camera_up_m: float = 0.0
    camera_pitch_deg: float = 0.0   # positive looks down


DEFAULT_PARAMS = GeometryParams()


def load_params(path: Path = CALIBRATION_FILE) -> GeometryParams:
    """Calibrated parameters if the calibration file exists, otherwise the defaults."""
    if not path.is_file():
        return DEFAULT_PARAMS
    values = json.loads(path.read_text(encoding="utf-8"))["params"]
    return replace(DEFAULT_PARAMS, **values)


def params_dict(params: GeometryParams) -> dict:
    return asdict(params)


@dataclass(frozen=True)
class SurfacePoint:
    category: str
    world: np.ndarray
    distance_m: float


def camera_frame(position: np.ndarray, yaw_deg: float,
                 params: GeometryParams = DEFAULT_PARAMS) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Camera origin and forward/right/up unit vectors (right and up span the image plane)."""
    yaw, pitch = radians(yaw_deg), radians(params.camera_pitch_deg)
    level = np.array([cos(yaw), sin(yaw), 0.0])
    right = np.array([sin(yaw), -cos(yaw), 0.0])
    forward = cos(pitch) * level + np.array([0.0, 0.0, -sin(pitch)])
    up = np.cross(right, forward)
    origin = (np.asarray(position, float) + params.camera_lateral_m * right
              + params.camera_forward_m * level + np.array([0.0, 0.0, params.camera_up_m]))
    return origin, forward, right, up


def camera_basis(yaw_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Forward, image-right and image-up unit vectors for a level camera."""
    _, forward, right, up = camera_frame(np.zeros(3), yaw_deg)
    return forward, right, up


def pixel_rays(us: np.ndarray, vs: np.ndarray, forward: np.ndarray, right: np.ndarray,
               up: np.ndarray) -> np.ndarray:
    rays = (forward[None, :] + ((np.asarray(us, float).ravel() - IMAGE_WIDTH / 2) / FOCAL_PX)[:, None] * right
            - ((np.asarray(vs, float).ravel() - IMAGE_HEIGHT / 2) / FOCAL_PX)[:, None] * up)
    return rays / np.linalg.norm(rays, axis=1, keepdims=True)


def pixel_ray(u: float, v: float, yaw_deg: float, params: GeometryParams = DEFAULT_PARAMS) -> np.ndarray:
    _, forward, right, up = camera_frame(np.zeros(3), yaw_deg, params)
    return pixel_rays(np.array([u]), np.array([v]), forward, right, up)[0]


def project(point: np.ndarray, position: np.ndarray, yaw_deg: float,
            params: GeometryParams = DEFAULT_PARAMS) -> tuple[float, float, float] | None:
    """Pixel (u, v) and forward depth of a world point, or None when behind the camera."""
    origin, forward, right, up = camera_frame(position, yaw_deg, params)
    offset = np.asarray(point, float) - origin
    depth = float(offset @ forward)
    if depth <= 1e-6:
        return None
    return (IMAGE_WIDTH / 2 + FOCAL_PX * float(offset @ right) / depth,
            IMAGE_HEIGHT / 2 - FOCAL_PX * float(offset @ up) / depth, depth)


def pipe_hits(origin: np.ndarray, rays: np.ndarray, params: GeometryParams) -> np.ndarray:
    """Ray parameter of the nearest pipe hit per ray (inf when missed)."""
    oy, oz = origin[1], origin[2] - params.pipe_axis_z
    dy, dz = rays[:, 1], rays[:, 2]
    a = np.maximum(dy * dy + dz * dz, 1e-12)
    b = 2 * (oy * dy + oz * dz)
    c = oy * oy + oz * oz - params.pipe_radius_m ** 2
    disc = b * b - 4 * a * c
    root = np.sqrt(np.maximum(disc, 0.0))
    result = np.full(len(rays), np.inf)
    for t in ((-b + root) / (2 * a), (-b - root) / (2 * a)):  # near root last so it wins
        x = origin[0] + t * rays[:, 0]
        valid = (disc >= 0) & (t > 1e-6) & (x >= PIPE_X_MIN) & (x <= PIPE_X_MAX)
        result = np.where(valid, t, result)
    return result


def pier_hits(origin: np.ndarray, rays: np.ndarray, pier_index: int, params: GeometryParams) -> np.ndarray:
    center_x, half = PIER_CENTERS_X[pier_index], params.pier_half_width_m
    low = np.array([center_x - half, PIER_Y - half, PIER_Z_RANGE[0]])
    high = np.array([center_x + half, PIER_Y + half, PIER_Z_RANGE[1]])
    safe = np.where(np.abs(rays) < 1e-12, 1e-12, rays)
    t1, t2 = (low - origin) / safe, (high - origin) / safe
    t_near = np.max(np.minimum(t1, t2), axis=1)
    t_far = np.min(np.maximum(t1, t2), axis=1)
    hit = (t_near <= t_far) & (t_far > 1e-6)
    t = np.where(t_near > 1e-6, t_near, t_far)
    return np.where(hit, t, np.inf)


def structure_hits(category: str, origin: np.ndarray, rays: np.ndarray,
                   params: GeometryParams = DEFAULT_PARAMS) -> np.ndarray:
    if category.startswith("pipe_"):
        return pipe_hits(origin, rays, params)
    if category in ("pier_0", "pier_1"):
        return pier_hits(origin, rays, int(category[-1]), params)
    raise ValueError(f"Unknown structure category: {category}")


def intersect_pipe(origin: np.ndarray, direction: np.ndarray,
                   params: GeometryParams = DEFAULT_PARAMS) -> float | None:
    t = float(pipe_hits(np.asarray(origin, float), np.asarray(direction, float)[None, :], params)[0])
    return None if np.isinf(t) else t


def intersect_pier(origin: np.ndarray, direction: np.ndarray, pier_index: int,
                   params: GeometryParams = DEFAULT_PARAMS) -> float | None:
    t = float(pier_hits(np.asarray(origin, float), np.asarray(direction, float)[None, :], pier_index, params)[0])
    return None if np.isinf(t) else t


def pixel_to_surface(u: float, v: float, position: np.ndarray, yaw_deg: float, category: str,
                     params: GeometryParams = DEFAULT_PARAMS) -> SurfacePoint | None:
    origin, forward, right, up = camera_frame(position, yaw_deg, params)
    ray = pixel_rays(np.array([u]), np.array([v]), forward, right, up)
    t = float(structure_hits(category, origin, ray, params)[0])
    if np.isinf(t):
        return None
    return SurfacePoint(category, origin + t * ray[0], t)


def in_view(point: np.ndarray, position: np.ndarray, yaw_deg: float, category: str,
            margin_px: float = 20.0, occlusion_tolerance_m: float = 0.15,
            params: GeometryParams = DEFAULT_PARAMS) -> bool:
    """True when the point projects inside the image and is the first structure hit."""
    projected = project(point, position, yaw_deg, params)
    if projected is None:
        return False
    u, v, _ = projected
    if not (margin_px <= u <= IMAGE_WIDTH - margin_px and margin_px <= v <= IMAGE_HEIGHT - margin_px):
        return False
    hit = pixel_to_surface(u, v, position, yaw_deg, category, params)
    origin = camera_frame(position, yaw_deg, params)[0]
    expected = float(np.linalg.norm(np.asarray(point, float) - origin))
    return hit is not None and abs(hit.distance_m - expected) <= occlusion_tolerance_m


def render_hits(position: np.ndarray, yaw_deg: float, category: str,
                params: GeometryParams = DEFAULT_PARAMS, step: int = 1) -> np.ndarray:
    """Distance to the structure for each pixel of a (H/step, W/step) grid; inf where missed."""
    origin, forward, right, up = camera_frame(position, yaw_deg, params)
    us, vs = np.meshgrid(np.arange(step // 2, IMAGE_WIDTH, step), np.arange(step // 2, IMAGE_HEIGHT, step))
    rays = pixel_rays(us, vs, forward, right, up)
    return structure_hits(category, origin, rays, params).reshape(us.shape)


def surface_normals(points: np.ndarray, category: str, params: GeometryParams = DEFAULT_PARAMS) -> np.ndarray:
    """Outward unit normals at surface points (pipe: radial; pier: nearest box face)."""
    points = np.asarray(points, float)
    if category.startswith("pipe_"):
        normals = np.stack([np.zeros(len(points)), points[:, 1], points[:, 2] - params.pipe_axis_z], axis=1)
        return normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    center = np.array([PIER_CENTERS_X[int(category[-1])], PIER_Y])
    local = (points[:, :2] - center) / params.pier_half_width_m
    axis = np.argmax(np.abs(local), axis=1)
    normals = np.zeros((len(points), 3))
    normals[np.arange(len(points)), axis] = np.sign(local[np.arange(len(points)), axis])
    return normals


def render_surface(position: np.ndarray, yaw_deg: float, category: str,
                   params: GeometryParams = DEFAULT_PARAMS, step: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Per-pixel distance (inf where missed) and cosine of the incidence angle (0 where missed)."""
    origin, forward, right, up = camera_frame(position, yaw_deg, params)
    us, vs = np.meshgrid(np.arange(step // 2, IMAGE_WIDTH, step), np.arange(step // 2, IMAGE_HEIGHT, step))
    rays = pixel_rays(us, vs, forward, right, up)
    t = structure_hits(category, origin, rays, params)
    hit = np.isfinite(t)
    cosine = np.zeros(len(rays))
    if hit.any():
        points = origin + t[hit, None] * rays[hit]
        cosine[hit] = np.clip(-np.sum(rays[hit] * surface_normals(points, category, params), axis=1), 0.0, 1.0)
    return t.reshape(us.shape), cosine.reshape(us.shape)


def surface_coordinates(point: np.ndarray, category: str,
                        params: GeometryParams = DEFAULT_PARAMS) -> tuple[float, float]:
    """Pipe: (x along the axis, angle around it); pier: (height, angle around the axis)."""
    x, y, z = map(float, point)
    if category.startswith("pipe_"):
        return x, degrees(atan2(z - params.pipe_axis_z, y))
    center_x = PIER_CENTERS_X[int(category[-1])]
    return z, degrees(atan2(y - PIER_Y, x - center_x))
