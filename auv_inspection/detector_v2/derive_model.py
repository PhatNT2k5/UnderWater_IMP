"""Derive a v2 model that reuses another model's banks and adds a linear transform (P4.3).

nuisance: scatter of token changes between bank-capture frames and the same frames degraded by
  each factor at severity 1 (the bank's augmentation level), per structure group; the transform
  removes its top-k eigenvectors. Only clean train-profile train captures are accepted.
mahalanobis: whitening from each group's own bank (mean and shrunk covariance).
nuisance_mahalanobis: the nuisance projection of an existing nuisance model (--from-nuisance),
  then whitening estimated on the projected bank.
The new directory gets its own config.json and transforms.pt; thresholds must be calibrated
again (calibrate_pixel.py, calibrate_surface.py) because the score scale changes.
Run in .venv-patchcore.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import sys

import cv2
import numpy as np
import torch

INSPECTION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSPECTION))
from robustness.degradation import PIPELINE_ORDER, Degradation, apply_degradations  # noqa: E402
from robustness.geometric_roi import category_from_pose, geometric_roi  # noqa: E402
from robustness.geometry import load_params  # noqa: E402

from .build_bank import AUGMENT_SEVERITY, CATEGORIES, EROSION_PX, load_train_capture  # noqa: E402
from .features import frame_tokens, load_extractor, roi_cells  # noqa: E402
from .transforms import from_state, mahalanobis_whitening, nuisance_projection  # noqa: E402


def nuisance_scatter(base_config: dict, captures: list[Path], frames_per_capture: int,
                     seed: int) -> tuple[dict[str, torch.Tensor], dict[str, int]]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    extractor = load_extractor(device, float(base_config["scale"]))
    params = load_params()
    rng = np.random.default_rng(seed)
    scatter: dict[str, torch.Tensor] = {}
    counts: dict[str, int] = defaultdict(int)
    for capture in captures:
        rows, _ = load_train_capture(capture)
        usable = []
        for row in rows:
            position, yaw = np.asarray(row["position_m"], float), float(row["yaw_deg"])
            category = category_from_pose(position, yaw, params)
            roi = geometric_roi(position, yaw, category, params)[0] if category else None
            if roi is not None:
                usable.append((row, category, roi))
        picked = rng.choice(len(usable), min(frames_per_capture, len(usable)), replace=False)
        for index in picked:
            row, category, roi = usable[int(index)]
            frame = cv2.imread(str(capture / row["image"]), cv2.IMREAD_COLOR)
            clean = frame_tokens(extractor, frame)
            cells = torch.from_numpy(roi_cells(roi, clean.shape[:2], EROSION_PX)).to(device)
            reference = clean[cells].float()
            for factor in PIPELINE_ORDER:
                degraded = apply_degradations(frame, [Degradation(factor, AUGMENT_SEVERITY)], int(row["tick"]))
                delta = frame_tokens(extractor, degraded)[cells].float() - reference
                block = (delta.T @ delta).double().cpu()
                scatter[category] = scatter.get(category, torch.zeros_like(block)) + block
                counts[category] += len(delta)
        print(json.dumps({"capture": capture.name, "frames": len(picked), "token_pairs": dict(counts)}), flush=True)
    return {category: scatter[category] / counts[category] for category in scatter}, dict(counts)


def derive(base: Path, destination: Path, kind: str, captures: list[Path], k: int,
           shrinkage: float, frames_per_capture: int, seed: int = 20261014,
           from_nuisance: Path | None = None, geometry_file: str | None = None) -> dict:
    if destination.exists():
        raise FileExistsError(destination)
    config = json.loads((base / "config.json").read_text(encoding="utf-8"))
    if config.get("transform_file"):
        raise ValueError("Derive from a model without a transform")
    bank_dir = Path(config.get("bank_dir", base)).resolve()
    meta: dict = {"kind": kind}
    if kind == "nuisance":
        scatters, counts = nuisance_scatter(config, captures, frames_per_capture, seed)
        if set(scatters) != set(CATEGORIES):
            raise ValueError(f"Nuisance pairs missing for {set(CATEGORIES) - set(scatters)}")
        states, explained = {}, {}
        for category, scatter in scatters.items():
            transform, explained[category] = nuisance_projection(scatter, k)
            states[category] = transform.state()
        meta.update({"k": k, "severity": AUGMENT_SEVERITY, "factors": list(PIPELINE_ORDER),
                     "frames_per_capture": frames_per_capture, "token_pairs": counts,
                     "explained_share": {c: round(v, 4) for c, v in explained.items()},
                     "captures": [str(c) for c in captures]})
    elif kind == "mahalanobis":
        states = {category: mahalanobis_whitening(torch.load(bank_dir / f"{category}_bank.pt",
                                                             weights_only=True), shrinkage).state()
                  for category in CATEGORIES}
        meta.update({"shrinkage": shrinkage})
    elif kind == "nuisance_mahalanobis":
        if from_nuisance is None:
            raise ValueError("nuisance_mahalanobis needs --from-nuisance")
        source = json.loads((from_nuisance / "config.json").read_text(encoding="utf-8"))
        if Path(source.get("bank_dir", "")).resolve() != bank_dir or source["transform"]["kind"] != "nuisance":
            raise ValueError("--from-nuisance must be a nuisance model on the same banks")
        projections = torch.load(from_nuisance / source["transform_file"], weights_only=True)
        states = {}
        for category in CATEGORIES:
            projection = from_state(projections[category])
            projected = projection.apply(torch.load(bank_dir / f"{category}_bank.pt", weights_only=True))
            states[category] = [projection.state(), mahalanobis_whitening(projected, shrinkage).state()]
        meta.update({"shrinkage": shrinkage, "nuisance_model": str(from_nuisance.resolve()),
                     "nuisance": source["transform"]})
    elif kind == "geometry":
        # Same banks and features, another ROI geometry (P8: pier floor); needs its own thresholds.
        if not geometry_file:
            raise ValueError("geometry needs --geometry-file")
        states = None
    else:
        raise ValueError(f"Unknown transform kind {kind!r}")
    destination.mkdir(parents=True)
    derived = {**config, "bank_dir": str(bank_dir), "base_model": str(base.resolve()),
               "created": datetime.now().astimezone().isoformat(timespec="seconds")}
    if states is not None:
        torch.save(states, destination / "transforms.pt")
        derived.update({"transform_file": "transforms.pt", "transform": meta})
    if geometry_file:
        derived["geometry_file"] = geometry_file  # relative to the repository root
    (destination / "config.json").write_text(json.dumps(derived, indent=2), encoding="utf-8")
    return derived


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base_model", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("kind", choices=("nuisance", "mahalanobis", "nuisance_mahalanobis", "geometry"))
    parser.add_argument("--geometry-file", help="Geometry calibration for the ROI, relative to the repository "
                                                "root, e.g. auv_inspection/robustness/calibration/geometry_v3.json")
    parser.add_argument("--from-nuisance", type=Path, help="Nuisance model whose projection to reuse")
    parser.add_argument("--captures", nargs="*", type=Path, default=[], help="Bank (train) captures for nuisance")
    parser.add_argument("--k", type=int, default=8)
    parser.add_argument("--shrinkage", type=float, default=0.1)
    parser.add_argument("--frames-per-capture", type=int, default=100)
    args = parser.parse_args()
    if args.kind == "nuisance" and not args.captures:
        parser.error("nuisance needs --captures")
    result = derive(args.base_model, args.destination, args.kind, args.captures, args.k,
                    args.shrinkage, args.frames_per_capture, from_nuisance=args.from_nuisance,
                    geometry_file=args.geometry_file)
    print(json.dumps({key: result.get(key) for key in ("transform", "geometry_file")}, indent=2))


if __name__ == "__main__":
    main()
