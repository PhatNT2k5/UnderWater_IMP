"""Structure-following route for the saved, manually edited AUVInspection map.

Coordinates were read from the map on 2026-09-22 (meters, client frame).
This module neither loads nor writes Unreal assets. Update the geometry below
if structures are moved; this is a fixed route, not online obstacle avoidance.
"""
from __future__ import annotations

from math import atan2, ceil, cos, degrees, dist, pi, radians, sin
import random

Waypoint = tuple[str, list[float]]
ROUTE_LOOKAHEAD_M = 1.2
PIPE_X_MIN = -18.01
PIPE_X_MAX = 15.11
PIPE_Z = -10.3
PIPE_OFFSET = 2.0
PIER_Y = -6.5
PIER_RADIUS = 2.8
PIER_DEPTHS = (-9.2, -6.8, -4.4, -2.0)
PIER_CENTERS_X = (-10.0, 10.0)
# Conservative axis-aligned bounds incl. flanges and pier footings, plus the margin
# for the AUV body and position tolerance.
STRUCTURE_BOXES = [((PIPE_X_MIN, -0.8, -12.4), (PIPE_X_MAX, 0.8, -9.74))] + [
    box for x in PIER_CENTERS_X for box in (
        ((x - 0.95, -7.45, -10.4), (x + 0.95, -5.55, 1.6)),
        ((x - 2.0, -8.5, -12.0), (x + 2.0, -4.5, -10.4)),
    )
]
CLEARANCE_MARGIN_M = 0.65


def angle_delta(target: float, current: float) -> float:
    return (target - current + 180.0) % 360.0 - 180.0


def advance_station(
    route: list[Waypoint],
    station: int,
    location: list[float],
    lookahead_m: float = ROUTE_LOOKAHEAD_M,
) -> tuple[int, list[str]]:
    """Move the target ahead without stopping at intermediate waypoints."""
    passed: list[str] = []
    while station < len(route) - 1:
        name, pose = route[station]
        if dist(location, pose[:3]) >= lookahead_m:
            break
        passed.append(name)
        station += 1
    return station, passed


def build_route(pipe_offset: float = PIPE_OFFSET,
                pier_radius: float = PIER_RADIUS) -> list[Waypoint]:
    """Inspect both pipe sides, then four full rings around each pier.

    Defaults reproduce the validated route; other standoffs are for randomized captures.
    """
    route: list[Waypoint] = []

    def append(name: str, x: float, y: float, z: float, yaw: float) -> None:
        target = [x, y, z, 0.0, 0.0, yaw]
        if not route:
            route.append((name, target))
            return
        previous = route[-1][1]
        # Short segments keep the position controller close to each surface.
        count = max(1, ceil(dist(previous[:3], target[:3]) / 0.8))
        for step in range(1, count + 1):
            fraction = step / count
            pose = [a + fraction * (b - a) for a, b in zip(previous, target)]
            pose[5] = angle_delta(
                previous[5] + fraction * angle_delta(yaw, previous[5]), 0.0
            )
            route.append((f"{name}_{step:03d}", pose))

    append("start", -14.0, 3.5, PIPE_Z, -90.0)
    append("pipe_approach", -14.0, pipe_offset, PIPE_Z, -90.0)
    append("pipe_front_start", PIPE_X_MIN, pipe_offset, PIPE_Z, -90.0)
    append("pipe_front_scan", PIPE_X_MAX, pipe_offset, PIPE_Z, -90.0)
    # Go beyond the end before crossing y=0; never cut through the pipe.
    append("pipe_end_outbound", 18.0, pipe_offset, PIPE_Z, -90.0)
    append("pipe_end_round", 18.0, -pipe_offset, PIPE_Z, 90.0)
    append("pipe_back_start", PIPE_X_MAX, -pipe_offset, PIPE_Z, 90.0)
    append("pipe_back_scan", PIPE_X_MIN, -pipe_offset, PIPE_Z, 90.0)
    append("transit_rise", PIPE_X_MIN, -pipe_offset, PIER_DEPTHS[0], 90.0)
    append("transit_pier_front", PIPE_X_MIN, PIER_Y + pier_radius, PIER_DEPTHS[0], -90.0)

    for pier_index, center_x in enumerate(PIER_CENTERS_X):
        depths = PIER_DEPTHS if pier_index == 0 else tuple(reversed(PIER_DEPTHS))
        for level, z in enumerate(depths):
            append(f"pier_{pier_index}_level_{level}_entry", center_x, PIER_Y + pier_radius, z, -90.0)
            # Small arcs avoid the straight chords through a pier and keep
            # the forward camera pointing inward throughout the circuit.
            for step in range(1, 25):
                theta = radians(90.0 + step * 15.0)
                x = center_x + pier_radius * cos(theta)
                y = PIER_Y + pier_radius * sin(theta)
                yaw = degrees(atan2(PIER_Y - y, center_x - x))
                append(f"pier_{pier_index}_level_{level}_orbit_{step:02d}", x, y, z, yaw)
    return route


def smooth_noise(count: int, rng: random.Random, period_range: tuple[float, float] = (15.0, 60.0),
                 components: int = 3) -> list[float]:
    """Low-frequency noise in [-1, 1] over waypoint index; avoids zig-zag targets."""
    waves = [(rng.uniform(*period_range), rng.uniform(0, 2 * pi)) for _ in range(components)]
    raw = [sum(sin(2 * pi * index / period + phase) for period, phase in waves)
           for index in range(count)]
    peak = max((abs(value) for value in raw), default=1.0) or 1.0
    return [value / peak for value in raw]


def perturb_route(route: list[Waypoint], rng: random.Random, depth_jitter_m: float,
                  yaw_jitter_deg: float) -> list[Waypoint]:
    """Add smooth depth and heading deviations; names and waypoint count are unchanged."""
    depth = smooth_noise(len(route), rng)
    yaw = smooth_noise(len(route), rng)
    perturbed: list[Waypoint] = []
    for (name, pose), dz, dyaw in zip(route, depth, yaw):
        moved = list(pose)
        moved[2] += depth_jitter_m * dz
        moved[5] = angle_delta(moved[5] + yaw_jitter_deg * dyaw, 0.0)
        perturbed.append((name, moved))
    return perturbed


def clearance_violations(route: list[Waypoint], margin_m: float = CLEARANCE_MARGIN_M,
                         samples_per_segment: int = 20) -> list[tuple[str, list[float]]]:
    """Points on straight segments between waypoints that enter an inflated structure box."""
    violations = []
    for (_, a), (name, b) in zip(route, route[1:]):
        for step in range(samples_per_segment + 1):
            point = [a[i] + (b[i] - a[i]) * step / samples_per_segment for i in range(3)]
            for low, high in STRUCTURE_BOXES:
                if all(low[i] - margin_m <= point[i] <= high[i] + margin_m for i in range(3)):
                    violations.append((name, point))
    return violations


ROUTE = build_route()
