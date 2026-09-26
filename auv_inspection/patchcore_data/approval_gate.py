"""Bind PatchCore dashboard approval to the artifacts actually evaluated."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


MODEL_FILES = (
    "backbone.pt", "config.json", "pipe_front_bank.pt", "pipe_back_bank.pt",
    "pier_0_bank.pt", "pier_1_bank.pt",
)
REFERENCE_FILES = ("summary.json", "manifest.jsonl", "roi_approved.json")


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(paths: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as stream:
            digest.update(hashlib.file_digest(stream, "sha256").digest())
    return digest.hexdigest()


def model_fingerprint(model_dir: Path) -> str:
    return fingerprint([model_dir / name for name in MODEL_FILES], model_dir)


def reference_fingerprint(dataset: Path) -> str:
    masks = sorted((dataset / "roi_masks").glob("*.png"))
    if not masks:
        raise ValueError("Reference dataset has no ROI masks")
    return fingerprint([dataset / name for name in REFERENCE_FILES] + masks, dataset)


def approval_matches(model_dir: Path, reference_dataset: Path,
                     thresholds_file: Path, evaluation_file: Path) -> bool:
    """Require a passed B evaluation for these exact live artifacts."""
    try:
        result = json.loads(evaluation_file.read_text(encoding="utf-8"))
        acceptance = result["acceptance"]
        if not all(acceptance.get(key) is True for key in (
            "passed", "all_inventory_observable", "recall_at_least_95_percent",
            "small_or_thin_recall_at_least_90_percent", "false_alerts_at_most_2",
        )):
            return False
        return (
            Path(result["model_dir"]).resolve() == model_dir.resolve()
            and Path(result["reference_dataset"]).resolve() == reference_dataset.resolve()
            and Path(result["thresholds"]).resolve() == thresholds_file.resolve()
            and result["model_sha256"] == model_fingerprint(model_dir)
            and result["reference_sha256"] == reference_fingerprint(reference_dataset)
            and result["thresholds_sha256"] == file_sha256(thresholds_file)
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False
