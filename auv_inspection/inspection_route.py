"""Structure-following route for the saved, manually edited AUVInspection map.

Coordinates were read from the map on 2026-09-22 (meters, client frame).
This module neither loads nor writes Unreal assets. Update the geometry below
if structures are moved; this is a fixed route, not online obstacle avoidance.
"""
from __future__ import annotations

from math import atan2, ceil, cos, degrees, dist, radians, sin

Waypoint = tuple[str, list[float]]
ROUTE_LOOKAHEAD_M = 1.2
PIPE_X_MIN = -18.01
PIPE_X_MAX = 15.11
PIPE_Z = -10.3
PIPE_OFFSET = 2.0
PIER_Y = -6.5
PIER_RADIUS = 2.8
PIER_DEPTHS = (-9.2, -6.8, -4.4, -2.0)


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


def build_route() -> list[Waypoint]:
    """Inspect both pipe sides, then four full rings around each pier."""
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
    append("pipe_approach", -14.0, PIPE_OFFSET, PIPE_Z, -90.0)
    append("pipe_front_start", PIPE_X_MIN, PIPE_OFFSET, PIPE_Z, -90.0)
    append("pipe_front_scan", PIPE_X_MAX, PIPE_OFFSET, PIPE_Z, -90.0)
    # Go beyond the end before crossing y=0; never cut through the pipe.
    append("pipe_end_outbound", 18.0, PIPE_OFFSET, PIPE_Z, -90.0)
    append("pipe_end_round", 18.0, -PIPE_OFFSET, PIPE_Z, 90.0)
    append("pipe_back_start", PIPE_X_MAX, -PIPE_OFFSET, PIPE_Z, 90.0)
    append("pipe_back_scan", PIPE_X_MIN, -PIPE_OFFSET, PIPE_Z, 90.0)
    append("transit_rise", PIPE_X_MIN, -PIPE_OFFSET, PIER_DEPTHS[0], 90.0)
    append("transit_pier_front", PIPE_X_MIN, PIER_Y + PIER_RADIUS, PIER_DEPTHS[0], -90.0)

    for pier_index, center_x in enumerate((-10.0, 10.0)):
        depths = PIER_DEPTHS if pier_index == 0 else tuple(reversed(PIER_DEPTHS))
        for level, z in enumerate(depths):
            append(f"pier_{pier_index}_level_{level}_entry", center_x, PIER_Y + PIER_RADIUS, z, -90.0)
            # Small arcs avoid the straight chords through a pier and keep
            # the forward camera pointing inward throughout the circuit.
            for step in range(1, 25):
                theta = radians(90.0 + step * 15.0)
                x = center_x + PIER_RADIUS * cos(theta)
                y = PIER_Y + PIER_RADIUS * sin(theta)
                yaw = degrees(atan2(PIER_Y - y, center_x - x))
                append(f"pier_{pier_index}_level_{level}_orbit_{step:02d}", x, y, z, yaw)
    return route


ROUTE = build_route()
