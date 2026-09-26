"""Exercise light off/on at a backscan pose; logs only, no image recording."""
from __future__ import annotations

import argparse
import copy
import logging
from unittest.mock import patch

import run_inspection as inspection

BACKSCAN_POSE = [10.0, -2.0, -10.3, 0.0, 0.0, 90.0]


class LightCheckEnvironment(inspection.EditorEnvironment):
    """Hold the AUV still and toggle only the onboard light for comparison."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        scenario = copy.deepcopy(kwargs["scenario"])
        scenario["agents"][0]["location"] = BACKSCAN_POSE[:3]
        scenario["agents"][0]["rotation"] = BACKSCAN_POSE[3:]
        kwargs["scenario"] = scenario
        super().__init__(*args, **kwargs)
        self.check_tick = 0

    def step(self, action: inspection.np.ndarray, ticks: int = 1, publish: bool = True) -> dict:
        if self.check_tick == 0:
            self.turn_off_flashlight("flashlight1")
            self.turn_off_flashlight("flashlight2")
        elif self.check_tick == 180:
            inspection.enable_inspection_lights(self)
        self.check_tick += 1
        return super().step(action, ticks=ticks, publish=publish)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # Repeated holds keep the standard recorder running for a short comparison.
    route = [(f"flashlight_check_hold_{index:02d}", BACKSCAN_POSE) for index in range(100)]
    args = argparse.Namespace(
        editor=None, headless=True, steps=360, mode="auto",
        move_speed=2.0, yaw_speed=45.0,
    )
    with patch.object(inspection, "EditorEnvironment", LightCheckEnvironment), patch.object(inspection, "ROUTE", route):
        inspection.run(args)


if __name__ == "__main__":
    main()
