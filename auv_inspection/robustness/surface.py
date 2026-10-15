"""Unrolled surface coordinates in metres, shared by every view of the same structure (P5).

Evidence about a defect has to be accumulated where the defect is on the structure, not where
it appears in an image: the same crack moves across the image as the AUV passes, while marine
snow and glints do not stay at one surface location. Coordinates are lengths on the surface,
so a cell of a given size covers the same area everywhere:

- pipe: u = x along the axis, v = arc length around it from the side facing the camera group
  (front: +y, back: -y), positive upwards; the cut at the far side is never in view;
- pier: u = z (height), v = perimeter position around the square section, counter-clockwise
  from the (+x, +y) corner; v wraps at 8 * half-width.
"""
from __future__ import annotations

import numpy as np

from inspection_route import PIER_CENTERS_X, PIER_Y
from robustness.geometry import (
    DEFAULT_PARAMS, IMAGE_HEIGHT, IMAGE_WIDTH, GeometryParams, camera_frame, pixel_rays,
    structure_hits)


def pier_perimeter_m(params: GeometryParams = DEFAULT_PARAMS) -> float:
    return 8 * params.pier_half_width_m


def surface_uv(points: np.ndarray, category: str,
               params: GeometryParams = DEFAULT_PARAMS) -> np.ndarray:
    """(N, 2) surface coordinates in metres of (N, 3) points on the structure of `category`."""
    points = np.atleast_2d(np.asarray(points, float))
    if category in ("pipe_front", "pipe_back"):
        side = 1.0 if category == "pipe_front" else -1.0
        angle = np.arctan2(points[:, 2] - params.pipe_axis_z, side * points[:, 1])
        return np.column_stack([points[:, 0], params.pipe_radius_m * angle])
    if category not in ("pier_0", "pier_1"):
        raise ValueError(f"Unknown structure category: {category}")
    half = params.pier_half_width_m
    dx = points[:, 0] - PIER_CENTERS_X[int(category[-1])]
    dy = points[:, 1] - PIER_Y
    # Faces in counter-clockwise order, each contributing 2 * half of perimeter.
    perimeter = np.select(
        [dy >= np.abs(dx), dx <= -np.abs(dy), dy <= -np.abs(dx)],
        [half - dx, 3 * half - dy, 5 * half + dx],
        7 * half + dy)
    return np.column_stack([points[:, 2], perimeter])


def surface_point(uv: np.ndarray, category: str, params: GeometryParams = DEFAULT_PARAMS) -> np.ndarray:
    """Inverse of `surface_uv`: (N, 3) points on the structure for (N, 2) surface coordinates."""
    uv = np.atleast_2d(np.asarray(uv, float))
    u, v = uv[:, 0], uv[:, 1]
    if category in ("pipe_front", "pipe_back"):
        side = 1.0 if category == "pipe_front" else -1.0
        angle = v / params.pipe_radius_m
        return np.column_stack([u, side * params.pipe_radius_m * np.cos(angle),
                                params.pipe_axis_z + params.pipe_radius_m * np.sin(angle)])
    if category not in ("pier_0", "pier_1"):
        raise ValueError(f"Unknown structure category: {category}")
    half = params.pier_half_width_m
    s = np.mod(v, 8 * half)
    dx = np.select([s < 2 * half, s < 4 * half, s < 6 * half], [half - s, -half, s - 5 * half], half)
    dy = np.select([s < 2 * half, s < 4 * half, s < 6 * half], [half, 3 * half - s, -half], s - 7 * half)
    return np.column_stack([PIER_CENTERS_X[int(category[-1])] + dx, PIER_Y + dy, u])


def render_uv(position: np.ndarray, yaw_deg: float, category: str,
              params: GeometryParams = DEFAULT_PARAMS, step: int = 4) -> np.ndarray:
    """(H/step, W/step, 2) surface coordinates of each grid pixel centre; NaN where no hit."""
    origin, forward, right, up = camera_frame(position, yaw_deg, params)
    centre = (step - 1) / 2  # grid cell (i, j) covers pixels [i*step, (i+1)*step)
    us, vs = np.meshgrid(centre + np.arange(0, IMAGE_WIDTH, step),
                         centre + np.arange(0, IMAGE_HEIGHT, step))
    rays = pixel_rays(us, vs, forward, right, up)
    t = structure_hits(category, origin, rays, params)
    uv = np.full((len(rays), 2), np.nan)
    hit = np.isfinite(t)
    if hit.any():
        uv[hit] = surface_uv(origin + t[hit, None] * rays[hit], category, params)
    return uv.reshape(*us.shape, 2)
