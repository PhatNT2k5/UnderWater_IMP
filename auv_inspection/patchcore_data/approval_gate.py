"""Bind PatchCore dashboard approval to the artifacts and scoring code actually evaluated."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


MODEL_FILES = (
    "backbone.pt", "config.json", "pipe_front_bank.pt", "pipe_back_bank.pt",
    "pier_0_bank.pt", "pier_1_bank.pt",
)
REFERENCE_FILES = ("summary.json", "manifest.jsonl", "roi_approved.json")
# Code that turns a frame into scores and alerts (live_service and every project module it
# imports, paths relative to the repository root). An approval recorded for other code is void
# (D11: fixing logic must not keep showing "accepted").
SCORING_CODE = (
    "auv_inspection/detector_v2/__init__.py",
    "auv_inspection/detector_v2/features.py",
    "auv_inspection/detector_v2/scorer.py",
    "auv_inspection/detector_v2/transforms.py",
    "auv_inspection/inspection_route.py",
    "auv_inspection/patchcore_data/__init__.py",
    "auv_inspection/patchcore_data/alerts.py",
    "auv_inspection/patchcore_data/live_roi.py",
    "auv_inspection/patchcore_data/live_service.py",
    "auv_inspection/patchcore_data/model.py",
    "auv_inspection/patchcore_data/predict.py",
    "auv_inspection/robustness/__init__.py",
    "auv_inspection/robustness/geometric_roi.py",
    "auv_inspection/robustness/geometry.py",
    "auv_inspection/robustness/quality.py",
    "auv_inspection/robustness/surface.py",
    "auv_inspection/robustness/surface_evidence.py",
)


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def code_sha256(path: Path) -> str:
    """SHA256 of a source file with CRLF normalised to LF, so Git line-ending conversion is neutral."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def code_hashes(root: Path, files: tuple[str, ...] = SCORING_CODE) -> dict[str, str]:
    return {name: code_sha256(root / name) for name in files}


def code_matches(recorded: object, root: Path, required: tuple[str, ...] = SCORING_CODE) -> bool:
    """Recorded hashes cover every required file and all still match the working tree."""
    if not isinstance(recorded, dict) or not set(required) <= set(recorded):
        return False
    return all((root / name).is_file() and code_sha256(root / name) == digest
               for name, digest in recorded.items())


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
                     thresholds_file: Path, evaluation_file: Path, code_root: Path | None = None) -> bool:
    """Require a passed B evaluation for these exact live artifacts and scoring code.

    `code_root` (the repository root) defaults to two levels above this package; the
    evaluation must record `code_sha256` for every file in SCORING_CODE.
    """
    code_root = code_root or Path(__file__).resolve().parents[2]
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
            and code_matches(result.get("code_sha256"), code_root)
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def registered_candidate_matches(model_dir: Path, registration_file: Path, root: Path,
                                 required_code: tuple[str, ...] = SCORING_CODE) -> bool:
    """Detector v2 default: every file and the scoring code of the P7 candidate still match.

    This checks the artifacts that were scored on held-out data, not that they passed the
    acceptance criteria (they did not: robustness/acceptance_preregistration.json, P7 result).
    """
    try:
        registration = json.loads(registration_file.read_text(encoding="utf-8"))
        candidate = registration["candidate"]
        if (root / candidate["model_dir"]).resolve() != model_dir.resolve() or not candidate["sha256"]:
            return False
        if not code_matches(registration.get("code_sha256"), root, required_code):
            return False
        return all((model_dir / name).is_file() and file_sha256(model_dir / name) == digest
                   for name, digest in candidate["sha256"].items())
    except (OSError, ValueError, KeyError, TypeError):
        return False
