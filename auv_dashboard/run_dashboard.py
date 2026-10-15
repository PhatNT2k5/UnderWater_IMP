"""Launch the separate AUV dashboard without editing the inspection project."""
from __future__ import annotations

import argparse
import ctypes
import logging
import multiprocessing as mp
from pathlib import Path
import sys
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autostart", action="store_true")
    parser.add_argument("--steps", type=int, default=60000)
    parser.add_argument("--smoke-test", action="store_true", help="Exercise the live UI and save QA evidence")
    detector = parser.add_mutually_exclusive_group()
    detector.add_argument("--v2-model", type=Path,
                          help="Detector v2 directory to use instead of the registered default "
                               "auv_inspection/output/detector_v2_dino_s2_aug_g2")
    detector.add_argument("--v1", action="store_true",
                          help="Use PatchCore v1 behind its approval gate instead of detector v2")
    parser.add_argument("--world", help="Map to run, e.g. /Game/AUVInspection/Maps/AUVInspection_PatchCoreB_20260926_v3 "
                                        "(default: the scenario map, map A)")
    args = parser.parse_args()
    if args.steps <= 0:
        parser.error("--steps must be positive")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from auv_dashboard.app import MAPS_PREFIX, Dashboard, default_v2_model
    if args.world and (not args.world.startswith(MAPS_PREFIX) or ".." in args.world):
        parser.error(f"--world must name a map under {MAPS_PREFIX}")
    if args.v1:
        v2_model = None
    elif args.v2_model:
        v2_model = args.v2_model.resolve()
    else:
        v2_model = default_v2_model()
        if v2_model is None:
            logging.warning("Detector v2 files differ from the P7 pre-registration; falling back to PatchCore v1")
    logging.info("Detector: %s; world: %s", v2_model or "PatchCore v1", args.world or "scenario default")
    ctypes.windll.user32.SetProcessDPIAware()
    root = tk.Tk()
    dashboard = Dashboard(root, args.steps, args.smoke_test, v2_model, args.world)
    if args.autostart or args.smoke_test:
        root.after(500, dashboard.start)
    root.mainloop()
    if args.smoke_test:
        dashboard.validate_smoke_test()


if __name__ == "__main__":
    mp.freeze_support()
    main()
