"""Image-quality measurements (P3), reported with every analysed frame.

These are diagnostics, not an alert gate. Gating on them was tried and rejected: bounds at the
1st/99th percentile of clean simulator frames rejected 65-100% of frames already at the mildest
turbidity, weak-light and blur levels, because near-deterministic clean frames give a very
narrow "normal" range (D1), which turns the gate into an out-of-distribution detector. Sensor
noise also triggered the particle count while marine snow level 3 mostly did not.

Alert suppression under environmental change uses the spread of anomaly scores instead
(live_service, `diffuse_anomaly`). These metrics are kept to decide in P5 whether a frame is good
enough to count as evidence that a surface is clean.

Metrics, all on the ROI unless stated:
- sharpness: Laplacian variance / grey-level variance (contrast-independent blur measure);
- contrast: grey-level standard deviation;
- brightness: mean grey level; saturated_fraction: share of pixels >= 250;
- particles_per_100k_px: small bright blobs over the whole frame (white top-hat).
"""
from __future__ import annotations

import cv2
import numpy as np

TOPHAT_KERNEL_PX = 9
PARTICLE_STEP = 25          # grey levels above the local background
PARTICLE_AREA_PX = (3, 150)


def measure(frame: np.ndarray, roi: np.ndarray) -> dict[str, float]:
    if frame.ndim != 3 or roi.shape != frame.shape[:2]:
        raise ValueError("Expected a BGR frame and a matching ROI")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    inside = roi > 0
    if not inside.any():
        raise ValueError("ROI is empty")
    values = gray[inside].astype(np.float32)
    variance = float(values.var())
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)[inside]
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (TOPHAT_KERNEL_PX, TOPHAT_KERNEL_PX))
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    _, _, stats, _ = cv2.connectedComponentsWithStats((tophat > PARTICLE_STEP).astype(np.uint8))
    areas = stats[1:, cv2.CC_STAT_AREA]
    particles = int(np.count_nonzero((areas >= PARTICLE_AREA_PX[0]) & (areas <= PARTICLE_AREA_PX[1])))
    return {
        "sharpness": round(float(laplacian.var() / max(variance, 1.0)), 5),
        "contrast": round(float(np.sqrt(variance)), 3),
        "brightness": round(float(values.mean()), 3),
        "saturated_fraction": round(float(np.mean(values >= 250)), 5),
        "particles_per_100k_px": round(1e5 * particles / gray.size, 2),
    }
