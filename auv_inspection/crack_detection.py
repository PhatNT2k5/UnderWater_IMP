"""Camera-only crack candidates for the manually edited AUV pipeline map.

The processing stages follow the survey by Mohan and Poobal (2018): image
acquisition, preprocessing, segmentation, and geometric feature extraction.
This is a calibrated classical-vision detector, not a trained model.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class CrackCandidate:
    bbox: tuple[int, int, int, int]
    area_px: int
    score: float


@dataclass(frozen=True)
class CrackAnalysis:
    preprocessed: np.ndarray
    mask: np.ndarray
    candidates: tuple[CrackCandidate, ...]


class CrackTracker:
    """Require repeated, spatially consistent candidates before an alert."""

    def __init__(self, required_frames: int = 3, max_gap_px: float = 60.0) -> None:
        if required_frames < 1 or max_gap_px <= 0:
            raise ValueError("Tracker settings must be positive")
        self.required_frames = required_frames
        self.max_gap_px = max_gap_px
        self.reset()

    def reset(self) -> None:
        self.streak = 0
        self.previous_center: tuple[float, float] | None = None

    def update(self, analysis: CrackAnalysis) -> CrackCandidate | None:
        candidate = next((item for item in analysis.candidates if item.score >= 15.0), None)
        if candidate is None:
            self.reset()
            return None
        x, y, width, height = candidate.bbox
        center = (x + width / 2, y + height / 2)
        if self.previous_center is None or np.hypot(
            center[0] - self.previous_center[0], center[1] - self.previous_center[1]
        ) <= self.max_gap_px:
            self.streak += 1
        else:
            self.streak = 1
        self.previous_center = center
        return candidate if self.streak >= self.required_frames else None


def preprocess_image(frame: np.ndarray) -> np.ndarray:
    """Normalize local contrast while retaining narrow surface features."""
    if frame.ndim != 3 or frame.shape[2] < 3 or frame.dtype != np.uint8:
        raise ValueError("Expected a uint8 BGR camera frame with at least 3 channels")
    gray = cv2.cvtColor(frame[:, :, :3], cv2.COLOR_BGR2GRAY)
    equalizer = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(6, 6))
    return equalizer.apply(gray)


def _detect_large_central_hole(
    preprocessed: np.ndarray,
) -> tuple[CrackCandidate | None, np.ndarray]:
    """Detect a large dark void crossing the illuminated center of the pipe."""
    height, width = preprocessed.shape
    x0, x1 = int(width * 0.25), int(width * 0.75)
    y0, y1 = int(height * 0.32), int(height * 0.80)
    core = preprocessed[
        int(height * 0.40):int(height * 0.70),
        int(width * 0.40):int(width * 0.60),
    ]
    region = cv2.GaussianBlur(preprocessed[y0:y1, x0:x1], (7, 7), 0)
    hole_mask = np.zeros_like(preprocessed)

    dark_fraction = float(np.mean(core <= 45))
    core_median = float(np.median(core))
    illuminated_level = float(np.percentile(region, 90))
    if dark_fraction < 0.68 or core_median > 38.0 or illuminated_level < 70.0:
        return None, hole_mask

    segmented = np.uint8(region <= 45) * 255
    segmented = cv2.morphologyEx(
        segmented, cv2.MORPH_CLOSE, np.ones((9, 9), dtype=np.uint8)
    )
    segmented = cv2.morphologyEx(
        segmented, cv2.MORPH_OPEN, np.ones((5, 5), dtype=np.uint8)
    )
    count, labels, stats, _ = cv2.connectedComponentsWithStats(segmented)
    if count <= 1:
        return None, hole_mask

    core_x0 = int(width * 0.40) - x0
    core_x1 = int(width * 0.60) - x0
    core_y0 = int(height * 0.40) - y0
    core_y1 = int(height * 0.70) - y0
    best: tuple[int, int, int, int, int, int] | None = None
    for index in range(1, count):
        x, y, box_width, box_height, area = map(int, stats[index])
        overlap_width = max(0, min(x + box_width, core_x1) - max(x, core_x0))
        overlap_height = max(0, min(y + box_height, core_y1) - max(y, core_y0))
        if overlap_width * overlap_height == 0:
            continue
        if area < region.size * 0.12 or box_width < width * 0.20:
            continue
        if box_height < height * 0.15:
            continue
        if best is None or area > best[-1]:
            best = (index, x, y, box_width, box_height, area)

    if best is None:
        return None, hole_mask
    index, x, y, box_width, box_height, area = best
    component = np.uint8(labels == index) * 255
    hole_mask[y0:y1, x0:x1] = component
    score = 20.0 + 60.0 * dark_fraction + 0.1 * (illuminated_level - 70.0)
    candidate = CrackCandidate(
        bbox=(x + x0, y + y0, box_width, box_height),
        area_px=area,
        score=score,
    )
    return candidate, hole_mask


def detect_cracks(preprocessed: np.ndarray) -> CrackAnalysis:
    """Find coherent dark cracks or broad damage in the central pipe surface."""
    if preprocessed.ndim != 2 or preprocessed.dtype != np.uint8:
        raise ValueError("Expected a uint8 preprocessed grayscale frame")
    height, width = preprocessed.shape
    x0, x1 = int(width * 0.35), int(width * 0.65)
    y0, y1 = int(height * 0.48), int(height * 0.75)
    if x1 - x0 < 32 or y1 - y0 < 32:
        raise ValueError("Camera frame is too small for crack analysis")

    # Smooth the granular pipe texture before measuring dark local contrast.
    # Compute the background BEFORE cropping: reflected ROI borders otherwise
    # join lamp texture into a false dark band along the top of the crop.
    smoothed = cv2.GaussianBlur(preprocessed, (5, 5), 0)
    background = cv2.GaussianBlur(smoothed, (0, 0), sigmaX=9)
    response = cv2.subtract(background, smoothed)[y0:y1, x0:x1]
    region = preprocessed[y0:y1, x0:x1]
    segmented = np.uint8(response >= 18) * 255
    segmented = cv2.morphologyEx(
        segmented, cv2.MORPH_CLOSE, np.ones((3, 3), dtype=np.uint8)
    )

    mask = np.zeros_like(preprocessed)
    mask[y0:y1, x0:x1] = segmented

    hole_candidate, hole_mask = _detect_large_central_hole(preprocessed)
    if hole_candidate is not None:
        return CrackAnalysis(
            preprocessed,
            np.maximum(mask, hole_mask),
            (hole_candidate,),
        )

    count, labels, stats, _ = cv2.connectedComponentsWithStats(segmented)
    candidates: list[CrackCandidate] = []
    for index in range(1, count):
        x, y, box_width, box_height, area = map(int, stats[index])
        if (
            box_height < 12
            or box_width < 7
            or box_height > 2.5 * box_width
            or box_width > 6 * box_height
        ):
            continue
        density = area / (box_width * box_height)
        component = labels[y:y + box_height, x:x + box_width] == index
        mean_level = float(np.mean(region[y:y + box_height, x:x + box_width][component]))

        is_coherent_crack = area >= 500 and density <= 0.65
        is_broad_dark_damage = (
            area >= 280
            and box_width >= 25
            and box_height >= 25
            and density <= 0.45
            and mean_level <= 65.0
        )
        if not (is_coherent_crack or is_broad_dark_damage):
            continue
        # A weak dark halo beside a flange can be large but has no substantial
        # connected core. Require one strong core, not many isolated speckles.
        strong_core = np.uint8(
            component & (response[y:y + box_height, x:x + box_width] >= 40)
        ) * 255
        _, _, core_stats, _ = cv2.connectedComponentsWithStats(strong_core)
        largest_core = int(np.max(core_stats[1:, cv2.CC_STAT_AREA], initial=0))
        if largest_core < max(64, area * 0.25):
            continue
        mean_strength = float(np.mean(response[y:y + box_height, x:x + box_width][component]))
        score = (
            min(area, 1500) / 500.0 + min(box_height, 90) / 60.0
        ) * mean_strength
        candidates.append(CrackCandidate(
            bbox=(x + x0, y + y0, box_width, box_height),
            area_px=area,
            score=score,
        ))

    candidates.sort(key=lambda item: item.score, reverse=True)
    return CrackAnalysis(preprocessed, mask, tuple(candidates))


def analyze_frame(frame: np.ndarray) -> CrackAnalysis:
    """Run preprocessing before segmentation and feature extraction."""
    return detect_cracks(preprocess_image(frame))


def draw_detections(frame: np.ndarray, analysis: CrackAnalysis) -> np.ndarray:
    """Return an annotated copy without modifying the sensor frame."""
    annotated = frame[:, :, :3].copy()
    for candidate in analysis.candidates:
        x, y, width, height = candidate.bbox
        cv2.rectangle(annotated, (x, y), (x + width, y + height), (0, 255, 255), 2)
    return annotated
