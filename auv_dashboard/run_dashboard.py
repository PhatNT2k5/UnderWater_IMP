"""Launch the separate AUV dashboard without editing the inspection project."""
from __future__ import annotations

import argparse
import ctypes
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
    parser.add_argument("--v2-model", type=Path,
                        help="Use a detector v2 directory (P4) instead of PatchCore v1, e.g. "
                             "auv_inspection/output/detector_v2_dino_s2_aug_g2")
    args = parser.parse_args()
    if args.steps <= 0:
        parser.error("--steps must be positive")
    ctypes.windll.user32.SetProcessDPIAware()
    from auv_dashboard.app import Dashboard
    root = tk.Tk()
    dashboard = Dashboard(root, args.steps, args.smoke_test, args.v2_model.resolve() if args.v2_model else None)
    if args.autostart or args.smoke_test:
        root.after(500, dashboard.start)
    root.mainloop()
    if args.smoke_test:
        dashboard.validate_smoke_test()


if __name__ == "__main__":
    mp.freeze_support()
    main()
