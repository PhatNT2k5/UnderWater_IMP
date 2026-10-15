"""Build per-group DINOv2 memory banks from clean train-profile captures (P4).

Bank data rules (GENERALIZATION_PLAN.md, decision log 2026-10-12):
- only clean captures with dataset role `train` and randomisation profile `train`; calibration,
  development and acceptance captures never enter a bank;
- the geometric ROI of each frame selects surface tokens (eroded by EROSION_PX so the bank also
  holds appearances close to the scored region's edge);
- optional offline augmentation adds one copy of each frame degraded by one random factor at
  severity 1 only; the benchmark uses severities 2-5, which therefore stay unseen.
Per frame at most `max_per_frame` random surface tokens enter a uniform reservoir per group;
the bank is a greedy k-center coreset of the reservoir. Never overwrites an existing bank.
Run in .venv-patchcore.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
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

from .features import MODEL_NAME, frame_tokens, load_extractor, roi_cells  # noqa: E402
from .scorer import MODEL_KIND  # noqa: E402

CATEGORIES = ("pipe_front", "pipe_back", "pier_0", "pier_1")
EROSION_PX = 12          # half of the 24 px scoring margin
AUGMENT_SEVERITY = 1


def load_train_capture(capture: Path) -> tuple[list[dict], dict]:
    report = json.loads((capture / "report.json").read_text(encoding="utf-8"))
    profile = (report.get("conditions") or {}).get("profile")
    if (report.get("scene_state"), report.get("dataset_role"), profile) != ("clean", "train", "train"):
        raise ValueError(f"Banks only use clean train-profile train captures: {capture}")
    if not report.get("route_completed"):
        raise ValueError(f"Capture did not complete the route: {capture}")
    rows = [json.loads(line) for line in (capture / "frames.jsonl").read_text(encoding="utf-8").splitlines() if line]
    return sorted(rows, key=lambda row: row["tick"]), report


def frame_variants(frame: np.ndarray, tick: int, augment: bool,
                   rng: np.random.Generator) -> list[tuple[str, np.ndarray]]:
    variants = [("none", frame)]
    if augment:
        factor = str(rng.choice(PIPELINE_ORDER))
        variants.append((factor, apply_degradations(frame, [Degradation(factor, AUGMENT_SEVERITY)], tick)))
    return variants


def build(captures: list[Path], destination: Path, scale: float = 2.0, augment: bool = True,
          max_per_frame: int = 200, max_candidates: int = 60000, coreset_ratio: float = 0.25,
          seed: int = 20261012) -> dict:
    from anomalib.models.components import KCenterGreedy
    if destination.exists():
        raise FileExistsError(destination)
    if not 0 < coreset_ratio <= 1 or max_per_frame < 1 or max_candidates < 100:
        raise ValueError("Invalid bank parameters")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    extractor = load_extractor(device, scale)
    params = load_params()
    rng = np.random.default_rng(seed)
    reservoirs: dict[str, torch.Tensor] = {}
    seen: dict[str, int] = defaultdict(int)
    variant_counts: dict[str, int] = defaultdict(int)
    sources = []
    for capture in captures:
        rows, report = load_train_capture(capture)
        used = 0
        for row in rows:
            position, yaw = np.asarray(row["position_m"], float), float(row["yaw_deg"])
            category = category_from_pose(position, yaw, params)
            if category is None:
                continue
            roi, _ = geometric_roi(position, yaw, category, params)
            if roi is None:
                continue
            frame = cv2.imread(str(capture / row["image"]), cv2.IMREAD_COLOR)
            if frame is None:
                raise OSError(f"Cannot read {row['image']}")
            used += 1
            for name, image in frame_variants(frame, int(row["tick"]), augment, rng):
                variant_counts[name] += 1
                tokens = frame_tokens(extractor, image)
                cells = torch.from_numpy(roi_cells(roi, tokens.shape[:2], EROSION_PX)).to(device)
                surface = tokens[cells].float().cpu()
                if not len(surface):
                    continue
                picked = surface[torch.from_numpy(rng.choice(len(surface), min(max_per_frame, len(surface)),
                                                             replace=False))]
                store = reservoirs.setdefault(category, torch.empty((max_candidates, surface.shape[1])))
                for token in picked:  # uniform reservoir over the whole route and all captures
                    seen[category] += 1
                    if seen[category] <= max_candidates:
                        store[seen[category] - 1] = token
                    else:
                        slot = int(rng.integers(seen[category]))
                        if slot < max_candidates:
                            store[slot] = token
        sources.append({"capture": str(capture), "map_sha256": report.get("map_sha256"),
                        "conditions": report.get("conditions"), "frames_used": used,
                        "frames_sha256": hashlib.sha256((capture / "frames.jsonl").read_bytes()).hexdigest()})
        print(json.dumps({"capture": capture.name, "frames_used": used, "tokens_seen": dict(seen)}), flush=True)
    missing = [category for category in CATEGORIES if seen[category] < 100]
    if missing:
        raise ValueError(f"Too few surface tokens for {missing}")
    destination.mkdir(parents=True)
    sizes = {}
    for category in CATEGORIES:
        candidates = reservoirs[category][:min(seen[category], max_candidates)].to(device)
        bank = KCenterGreedy(candidates, sampling_ratio=coreset_ratio).sample_coreset()
        bank = torch.nn.functional.normalize(bank.float(), dim=-1).cpu()
        torch.save(bank, destination / f"{category}_bank.pt")
        sizes[category] = len(bank)
        print(json.dumps({"category": category, "candidates": len(candidates), "bank": len(bank)}), flush=True)
    config = {
        "model": MODEL_KIND, "backbone": MODEL_NAME, "scale": scale, "score": "1 - max cosine similarity",
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "erosion_px": EROSION_PX, "augment": {"enabled": augment, "severity": AUGMENT_SEVERITY,
                                              "factors": list(PIPELINE_ORDER), "frames": dict(variant_counts)},
        "max_per_frame": max_per_frame, "max_candidates": max_candidates, "coreset_ratio": coreset_ratio,
        "seed": seed, "tokens_seen": dict(seen), "bank_sizes": sizes, "sources": sources,
        "torch": torch.__version__,
    }
    (destination / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("destination", type=Path)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("--no-augment", action="store_true")
    parser.add_argument("--max-per-frame", type=int, default=200)
    parser.add_argument("--max-candidates", type=int, default=60000)
    parser.add_argument("--coreset-ratio", type=float, default=0.25)
    args = parser.parse_args()
    config = build(args.captures, args.destination, args.scale, not args.no_augment,
                   args.max_per_frame, args.max_candidates, args.coreset_ratio)
    print(json.dumps(config["bank_sizes"]))


if __name__ == "__main__":
    main()
