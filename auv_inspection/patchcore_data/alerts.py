"""Extract and temporally confirm spatial PatchCore anomaly candidates."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class Candidate:
    bbox: tuple[int, int, int, int]
    center: tuple[float, float]
    peak_score: float
    area: int


def extract_candidates(scores: np.ndarray, threshold: float,
                       min_area: int = 2, max_candidates: int = 30) -> list[Candidate]:
    """Keep small connected high-score regions, including narrow cracks."""
    binary = (np.isfinite(scores) & (scores >= threshold)).astype(np.uint8)
    count, labels, stats, centers = cv2.connectedComponentsWithStats(binary, 8)
    candidates = []
    for component in range(1, count):
        x, y, width, height, area = map(int, stats[component])
        if area < min_area:
            continue
        peak = float(np.max(scores[labels == component]))
        candidates.append(Candidate((x, y, width, height),
                                    (float(centers[component, 0]),
                                     float(centers[component, 1])), peak, area))
    return sorted(candidates, key=lambda item: item.peak_score, reverse=True)[:max_candidates]


class AlertTracker:
    """Require three spatially consistent analyzed frames before alerting."""

    def __init__(self, required_hits: int = 3, max_gap_ticks: int = 15,
                 max_motion_px: float = 60.0,
                 max_speed_px_per_tick: float = 13.0) -> None:
        self.required_hits = required_hits
        self.max_gap_ticks = max_gap_ticks
        self.max_motion_px = max_motion_px
        self.max_speed_px_per_tick = max_speed_px_per_tick
        self.category: str | None = None
        self.tracks: list[dict] = []
        self.last_tick: int | None = None

    def reset(self) -> None:
        self.tracks = []
        self.last_tick = None

    def step(self, category: str, tick: int,
             candidates: list[Candidate]) -> list[Candidate]:
        if category != self.category:
            self.reset()
            self.category = category
        if self.last_tick is not None and (tick <= self.last_tick or
                                           tick - self.last_tick > self.max_gap_ticks):
            self.reset()
        self.last_tick = tick
        unmatched = set(range(len(self.tracks)))
        updated: list[dict] = []
        alerts = []
        for candidate in candidates:
            matches = []
            for index in unmatched:
                old = self.tracks[index]
                elapsed = tick - old["tick"]
                previous = np.asarray(old["center"], np.float32)
                current = np.asarray(candidate.center, np.float32)
                speed = float(np.linalg.norm(current - previous)) / elapsed
                predicted = previous + np.asarray(old["velocity"], np.float32) * elapsed
                error = float(np.linalg.norm(current - predicted))
                tolerance = (self.max_speed_px_per_tick * elapsed
                             if old["hits"] == 1 else self.max_motion_px)
                if speed <= self.max_speed_px_per_tick and error <= tolerance:
                    matches.append((error, index))
            if matches:
                _, index = min(matches)
                unmatched.remove(index)
                old = self.tracks[index]
                elapsed = tick - old["tick"]
                velocity = ((candidate.center[0] - old["center"][0]) / elapsed,
                            (candidate.center[1] - old["center"][1]) / elapsed)
                track = {"center": candidate.center, "velocity": velocity,
                         "tick": tick, "hits": old["hits"] + 1,
                         "alerted": old["alerted"]}
            else:
                track = {"center": candidate.center, "velocity": (0.0, 0.0),
                         "tick": tick, "hits": 1, "alerted": False}
            if track["hits"] >= self.required_hits and not track["alerted"]:
                alerts.append(candidate)
                track["alerted"] = True
            updated.append(track)
        self.tracks = updated
        return alerts
