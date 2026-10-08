"""Pinhole camera and known-structure geometry: pixel <-> point on the pipe or a pier.

Used in P1 to localize alerts on the physical structure and to decide whether a known
defect is in view. P2 builds the geometric ROI on the same model.

Approximations (to be calibrated in P2 against the 552 reviewed masks):
- The camera is placed at the PoseSensor position with the AUV yaw and zero roll/pitch;
  the CameraLeftSocket offset is not documented and is ignored (decimetre-level error).
- Pipe: cylinder along x with axis (y = 0, z = PIPE_AXIS_Z) and radius PIPE_RADIUS_M,
  estimated from the pipe's angular height in nominal frames.
- Pier: the square column box used for route clearance (half-width 0.95 m).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, radians, sin, tan

import numpy as np

from inspection_route import PIER_CENTERS_X, PIER_Y, PIPE_X_MAX, PIPE_X_MIN

IMAGE_WIDTH, IMAGE_HEIGHT = 640, 480
HORIZONTAL_FOV_DEG = 80.0
FOCAL_PX = (IMAGE_WIDTH / 2) / tan(radians(HORIZONTAL_FOV_DEG / 2))  # ~381.4 px
PIPE_AXIS_Z = -10.3
PIPE_RADIUS_M = 0.5
PIER_HALF_WIDTH_M = 0.95
PIER_Z_RANGE = (-12.0, 1.6)


@dataclass(frozen=True)
class SurfacePoint:
    category: str            # pipe_front, pipe_back, pier_0, pier_1
    world: np.ndarray        # x, y, z in metres
    distance_m: float        # camera to point along the ray


def camera_basis(yaw_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Forward, image-right and image-up unit vectors for a level camera."""
    yaw = radians(yaw_deg)
    forward = np.array([cos(yaw), sin(yaw), 0.0])
    right = np.array([sin(yaw), -cos(yaw), 0.0])
    return forward, right, np.array([0.0, 0.0, 1.0])


def pixel_ray(u: float, v: float, yaw_deg: float) -> np.ndarray:
    forward, right, up = camera_basis(yaw_deg)
    ray = forward + ((u - IMAGE_WIDTH / 2) / FOCAL_PX) * right - ((v - IMAGE_HEIGHT / 2) / FOCAL_PX) * up
    return ray / np.linalg.norm(ray)


def project(point: np.ndarray, camera: np.ndarray, yaw_deg: float) -> tuple[float, float, float] | None:
    """Pixel (u, v) and forward depth of a world point, or None when behind the camera."""
    forward, right, up = camera_basis(yaw_deg)
    offset = np.asarray(point, float) - np.asarray(camera, float)
    depth = float(offset @ forward)
    if depth <= 1e-6:
        return None
    u = IMAGE_WIDTH / 2 + FOCAL_PX * float(offset @ right) / depth
    v = IMAGE_HEIGHT / 2 - FOCAL_PX * float(offset @ up) / depth
    return u, v, depth


def intersect_pipe(origin: np.ndarray, direction: np.ndarray) -> float | None:
    """Nearest positive ray parameter hitting the pipe cylinder within its length."""
    oy, oz = origin[1], origin[2] - PIPE_AXIS_Z
    dy, dz = direction[1], direction[2]
    a = dy * dy + dz * dz
    if a < 1e-12:
        return None
    b = 2 * (oy * dy + oz * dz)
    c = oy * oy + oz * oz - PIPE_RADIUS_M ** 2
    disc = b * b - 4 * a * c
    if disc < 0:
        return None
    for t in sorted(((-b - disc ** 0.5) / (2 * a), (-b + disc ** 0.5) / (2 * a))):
        if t > 1e-6 and PIPE_X_MIN <= origin[0] + t * direction[0] <= PIPE_X_MAX:
            return t
    return None


def intersect_pier(origin: np.ndarray, direction: np.ndarray, pier_index: int) -> float | None:
    """Slab test against one square pier column."""
    center_x = PIER_CENTERS_X[pier_index]
    low = np.array([center_x - PIER_HALF_WIDTH_M, PIER_Y - PIER_HALF_WIDTH_M, PIER_Z_RANGE[0]])
    high = np.array([center_x + PIER_HALF_WIDTH_M, PIER_Y + PIER_HALF_WIDTH_M, PIER_Z_RANGE[1]])
    t_near, t_far = -np.inf, np.inf
    for axis in range(3):
        if abs(direction[axis]) < 1e-12:
            if not low[axis] <= origin[axis] <= high[axis]:
                return None
            continue
        t1 = (low[axis] - origin[axis]) / direction[axis]
        t2 = (high[axis] - origin[axis]) / direction[axis]
        t_near, t_far = max(t_near, min(t1, t2)), min(t_far, max(t1, t2))
    if t_near > t_far or t_far <= 1e-6:
        return None
    return float(t_near if t_near > 1e-6 else t_far)


def structure_hit(category: str, origin: np.ndarray, direction: np.ndarray) -> float | None:
    if category.startswith("pipe_"):
        return intersect_pipe(origin, direction)
    if category in ("pier_0", "pier_1"):
        return intersect_pier(origin, direction, int(category[-1]))
    raise ValueError(f"Unknown structure category: {category}")


def pixel_to_surface(u: float, v: float, camera: np.ndarray, yaw_deg: float,
                     category: str) -> SurfacePoint | None:
    origin = np.asarray(camera, float)
    direction = pixel_ray(u, v, yaw_deg)
    t = structure_hit(category, origin, direction)
    if t is None:
        return None
    return SurfacePoint(category, origin + t * direction, float(t))


def in_view(point: np.ndarray, camera: np.ndarray, yaw_deg: float, category: str,
            margin_px: float = 20.0, occlusion_tolerance_m: float = 0.15) -> bool:
    """True when the point projects inside the image and is the first structure hit."""
    projected = project(point, camera, yaw_deg)
    if projected is None:
        return False
    u, v, _ = projected
    if not (margin_px <= u <= IMAGE_WIDTH - margin_px and margin_px <= v <= IMAGE_HEIGHT - margin_px):
        return False
    hit = pixel_to_surface(u, v, camera, yaw_deg, category)
    expected = float(np.linalg.norm(np.asarray(point, float) - np.asarray(camera, float)))
    return hit is not None and abs(hit.distance_m - expected) <= occlusion_tolerance_m


def surface_coordinates(point: np.ndarray, category: str) -> tuple[float, float]:
    """Pipe: (x along the axis, angle around it); pier: (height, angle around the axis)."""
    x, y, z = map(float, point)
    if category.startswith("pipe_"):
        return x, degrees(atan2(z - PIPE_AXIS_Z, y))
    center_x = PIER_CENTERS_X[int(category[-1])]
    return z, degrees(atan2(y - PIER_Y, x - center_x))
