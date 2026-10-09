"""Geometric ROI (P2): the structure surface predicted from pose and known geometry.

Replaces the reference-image ROI (needed a stored frame within 0.5 m / 8 degrees of the same
route station) and the station-name structure groups. Works at any pose on the structure,
in manual mode, and on a real AUV given a navigation pose and as-built geometry.

The mask is eroded by the pixel displacement that the pose uncertainty can cause, so a less
certain pose gives a smaller, safer ROI instead of letting water or seabed into PatchCore.
"""
from __future__ import annotations

from math import ceil, cos, radians

import cv2
import numpy as np

from robustness.geometry import (
    CATEGORIES, DEFAULT_PARAMS, FOCAL_PX, IMAGE_HEIGHT, IMAGE_WIDTH, GeometryParams, render_hits,
    render_surface)

DEFAULT_POSE_SIGMA_M = 0.02      # simulator pose is exact; covers calibration residuals
DEFAULT_POSE_SIGMA_YAW_DEG = 0.5
MAX_RANGE_M = 4.0                # beyond this a pixel covers > 1 cm of surface (GSD = z / f)
# Grazing view: a pixel covers 1/cos(theta) more surface (about 3x at 70 degrees), the surface is
# poorly lit, and the pipe silhouette mixes with water and flange rims. Chosen from this argument
# before testing; P1 data showed the P2 false alerts sitting on that silhouette band.
MAX_INCIDENCE_DEG = 70.0
MIN_ROI_PIXELS = 1000
RENDER_STEP = 2                  # render on a 2-pixel grid, then upsample (nearest)


def category_from_pose(position: np.ndarray, yaw_deg: float, params: GeometryParams = DEFAULT_PARAMS,
                       max_range_m: float = MAX_RANGE_M, min_fraction: float = 0.05) -> str | None:
    """Structure group filling most of the central image region within inspection range."""
    best, best_count = None, 0
    position = np.asarray(position, float)
    for category in CATEGORIES:
        if category == "pipe_front" and position[1] < 0 or category == "pipe_back" and position[1] >= 0:
            continue  # the camera only sees the pipe side it is on
        hits = render_hits(position, yaw_deg, category, params, step=16)
        rows, cols = hits.shape
        centre = hits[rows // 4: 3 * rows // 4, cols // 4: 3 * cols // 4]
        count = int(np.count_nonzero(centre <= max_range_m))
        if count > best_count:
            best, best_count = category, count
    if best is None or best_count < min_fraction * (rows // 2) * (cols // 2):
        return None
    return best


def erosion_px(distance_m: float, pose_sigma_m: float, pose_sigma_yaw_deg: float) -> int:
    """Image displacement (one sigma) from position and heading uncertainty."""
    return int(ceil(FOCAL_PX * pose_sigma_m / max(distance_m, 0.1) + FOCAL_PX * radians(pose_sigma_yaw_deg)))


def geometric_roi(position: np.ndarray, yaw_deg: float, category: str,
                  params: GeometryParams = DEFAULT_PARAMS,
                  pose_sigma_m: float = DEFAULT_POSE_SIGMA_M,
                  pose_sigma_yaw_deg: float = DEFAULT_POSE_SIGMA_YAW_DEG,
                  max_range_m: float = MAX_RANGE_M,
                  max_incidence_deg: float = MAX_INCIDENCE_DEG) -> tuple[np.ndarray | None, dict]:
    """uint8 mask (255 = structure surface to analyse) and a status dict for the response."""
    if pose_sigma_m < 0 or pose_sigma_yaw_deg < 0:
        raise ValueError("Pose uncertainty must be non-negative")
    hits, cosine = render_surface(np.asarray(position, float), yaw_deg, category, params, RENDER_STEP)
    in_range = hits <= max_range_m
    if not in_range.any():
        return None, {"status": "no_structure_in_range", "method": "geometry"}
    surface = in_range & (cosine >= cos(radians(max_incidence_deg)))
    distance = float(np.median(hits[in_range]))
    mask = cv2.resize(surface.astype(np.uint8) * 255, (IMAGE_WIDTH, IMAGE_HEIGHT),
                      interpolation=cv2.INTER_NEAREST)
    margin = erosion_px(distance, pose_sigma_m, pose_sigma_yaw_deg)
    if margin > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * margin + 1, 2 * margin + 1))
        mask = cv2.erode(mask, kernel, borderType=cv2.BORDER_CONSTANT, borderValue=255)
    info = {"method": "geometry", "distance_m": round(distance, 3), "erosion_px": margin,
            "max_incidence_deg": max_incidence_deg,
            "pose_sigma_m": pose_sigma_m, "pose_sigma_yaw_deg": pose_sigma_yaw_deg}
    if np.count_nonzero(mask) < MIN_ROI_PIXELS:
        return None, {"status": "roi_too_small", **info}
    return mask, {"status": "ready", **info}
