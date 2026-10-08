"""Seeded per-run simulation conditions for randomized captures (GENERALIZATION_PLAN.md, P1 part 2).

`NOMINAL` reproduces the validated runtime exactly. `train` varies conditions around it;
`heldout` draws every varied factor from values *outside* the train ranges, so a model
tuned on train captures is tested on conditions it has never seen (extrapolation).

Water turbidity is not varied in simulation: HoloOcean's water_fog command only edits a
PostProcessVolume tagged "WaterPPV", and the project maps have no such tag. Turbidity is
covered offline by robustness.degradation until a tagged map copy exists.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import cos, pi, radians, sin
import random

from inspection_route import (PIPE_OFFSET, PIER_RADIUS, Waypoint, build_route,
                              clearance_violations, perturb_route)

Interval = tuple[float, float]


@dataclass(frozen=True)
class RunConditions:
    profile: str
    seed: int
    pipe_offset_m: float           # AUV distance from the pipe axis
    pier_radius_m: float           # orbit radius around each pier axis
    depth_jitter_m: float          # amplitude of smooth depth deviation along the route
    yaw_jitter_deg: float          # amplitude of smooth heading deviation
    current_mps: tuple[float, float, float]
    current_variation_mps: float   # amplitude of slow change around the mean current
    light_intensity: float
    light_pitch_deg: float
    capture_interval_ticks: tuple[int, int]  # inclusive range; (10, 10) is the fixed grid


NOMINAL = RunConditions(
    profile="nominal", seed=0, pipe_offset_m=PIPE_OFFSET, pier_radius_m=PIER_RADIUS,
    depth_jitter_m=0.0, yaw_jitter_deg=0.0, current_mps=(0.0, 0.0, 0.0),
    current_variation_mps=0.0, light_intensity=2500.0, light_pitch_deg=0.0,
    capture_interval_ticks=(10, 10),
)

# Each factor maps to one or more disjoint intervals. Pipe offsets keep >= 0.15 m beyond
# the 0.65 m clearance margin (pipe box half-width 0.8 m) to absorb current drift. Pier
# boxes are square, so the inflated corner sits 1.6·√2 ≈ 2.26 m from the axis; orbits pass
# the diagonals and a 2.2 m radius was rejected by clearance_violations().
PROFILES: dict[str, dict[str, list[Interval]]] = {
    "train": {
        "pipe_offset_m": [(1.8, 2.4)],
        "pier_radius_m": [(2.5, 3.1)],
        "depth_jitter_m": [(0.0, 0.15)],
        "yaw_jitter_deg": [(0.0, 4.0)],
        "current_speed_mps": [(0.0, 0.2)],
        "current_variation_mps": [(0.0, 0.05)],
        "light_scale": [(0.75, 1.25)],
        "light_pitch_deg": [(-5.0, 5.0)],
    },
    "heldout": {
        "pipe_offset_m": [(1.6, 1.75), (2.45, 3.0)],
        "pier_radius_m": [(2.35, 2.45), (3.15, 3.6)],
        "depth_jitter_m": [(0.2, 0.35)],
        "yaw_jitter_deg": [(5.0, 9.0)],
        "current_speed_mps": [(0.25, 0.45)],
        "current_variation_mps": [(0.06, 0.12)],
        "light_scale": [(0.4, 0.7), (1.3, 1.6)],
        "light_pitch_deg": [(-12.0, -6.0), (6.0, 12.0)],
    },
}
CAPTURE_INTERVALS = {"train": (7, 13), "heldout": (3, 17)}


def draw(rng: random.Random, intervals: list[Interval]) -> float:
    """Uniform draw over a union of intervals, weighted by interval length."""
    lengths = [high - low for low, high in intervals]
    position = rng.uniform(0.0, sum(lengths))
    for (low, high), length in zip(intervals, lengths):
        if position <= length:
            return low + position
        position -= length
    return intervals[-1][1]


def sample_conditions(profile: str, seed: int) -> RunConditions:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile {profile!r}; choose from {sorted(PROFILES)}")
    ranges = PROFILES[profile]
    rng = random.Random(f"{profile}:{seed}")
    heading = rng.uniform(0.0, 360.0)
    speed = draw(rng, ranges["current_speed_mps"])
    current = (round(speed * cos(radians(heading)), 4), round(speed * sin(radians(heading)), 4), 0.0)
    return RunConditions(
        profile=profile, seed=seed,
        pipe_offset_m=round(draw(rng, ranges["pipe_offset_m"]), 3),
        pier_radius_m=round(draw(rng, ranges["pier_radius_m"]), 3),
        depth_jitter_m=round(draw(rng, ranges["depth_jitter_m"]), 3),
        yaw_jitter_deg=round(draw(rng, ranges["yaw_jitter_deg"]), 2),
        current_mps=current,
        current_variation_mps=round(draw(rng, ranges["current_variation_mps"]), 3),
        light_intensity=round(NOMINAL.light_intensity * draw(rng, ranges["light_scale"]), 1),
        light_pitch_deg=round(draw(rng, ranges["light_pitch_deg"]), 2),
        capture_interval_ticks=CAPTURE_INTERVALS[profile],
    )


def conditioned_route(conditions: RunConditions) -> list[Waypoint]:
    """Route for these conditions; refuses any route that enters a structure's safety box."""
    route = build_route(conditions.pipe_offset_m, conditions.pier_radius_m)
    if conditions.depth_jitter_m or conditions.yaw_jitter_deg:
        route = perturb_route(route, random.Random(f"route:{conditions.profile}:{conditions.seed}"),
                              conditions.depth_jitter_m, conditions.yaw_jitter_deg)
    violations = clearance_violations(route)
    if violations:
        raise ValueError(f"Randomized route violates structure clearance at {violations[0][0]}")
    return route


def current_at(conditions: RunConditions, tick: int, ticks_per_sec: int) -> list[float]:
    """Mean current plus a slow horizontal oscillation (period about 60 s)."""
    if not conditions.current_variation_mps:
        return list(conditions.current_mps)
    phase = 2 * pi * tick / (60.0 * ticks_per_sec)
    x, y, z = conditions.current_mps
    amplitude = conditions.current_variation_mps
    return [x + amplitude * sin(phase), y + amplitude * cos(phase), z]


class CaptureSchedule:
    """Decides capture ticks: the fixed grid for nominal runs, random gaps otherwise."""

    def __init__(self, interval_ticks: tuple[int, int], seed: int) -> None:
        low, high = interval_ticks
        if not 1 <= low <= high:
            raise ValueError("Capture interval must satisfy 1 <= low <= high")
        self.low, self.high = low, high
        self.rng = random.Random(f"capture:{seed}")
        self.next_tick: int | None = None

    def due(self, tick: int) -> bool:
        if self.low == self.high:
            return tick % self.low == 0
        if self.next_tick is None:
            self.next_tick = tick + self.rng.randint(0, self.high - 1)
        if tick < self.next_tick:
            return False
        self.next_tick = tick + self.rng.randint(self.low, self.high)
        return True


def describe(conditions: RunConditions) -> dict:
    return asdict(conditions)
