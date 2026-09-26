"""Validate captured camera frames and prepare a reviewable dataset manifest."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from collections import defaultdict
from pathlib import Path

import cv2


CATEGORIES = ("pipe_front", "pipe_back", "pier_0", "pier_1")


def load_capture(capture: Path) -> tuple[dict, list[dict]]:
    """Check capture provenance, image dimensions and manifest consistency."""
    report_path = capture / "report.json"
    frames_path = capture / "frames.jsonl"
    if not report_path.is_file() or not frames_path.is_file():
        raise FileNotFoundError("Capture requires report.json and frames.jsonl")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in frames_path.read_text(encoding="utf-8").splitlines()]
    expected_count = report.get("captured_frame_count", report.get("clean_frame_count"))
    if len(rows) != expected_count:
        raise ValueError("Image manifest count differs from report.json")
    seen: set[str] = set()
    for row in rows:
        relative = Path(row["image"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Image path escapes capture: {relative}")
        if row["category"] not in CATEGORIES:
            raise ValueError(f"Unknown image category: {row['category']}")
        if relative.as_posix() in seen:
            raise ValueError(f"Duplicate image: {relative}")
        seen.add(relative.as_posix())
        image_path = capture / relative
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None or image.shape[:2] != (row["height"], row["width"]):
            raise ValueError(f"Missing, unreadable or wrong-size image: {image_path}")
    return report, rows


def choose_keyframes(rows: list[dict]) -> list[dict]:
    """Spread review frames across every pipe scan and pier orbit level."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        station = row["station"]
        level = station.split("_level_")[1].split("_")[0] if "_level_" in station else "scan"
        groups[f"{row['category']}_{level}"].append(row)
    selected: list[dict] = []
    for group in groups.values():
        positions = sorted({round(index * (len(group) - 1) / 5) for index in range(6)})
        selected.extend(group[index] for index in positions)
    return sorted(selected, key=lambda row: row["tick"])


def prepare_capture(capture: Path, destination: Path) -> dict:
    report, rows = load_capture(capture)
    destination.mkdir(parents=True, exist_ok=False)
    capture = capture.resolve()
    manifest = []
    for row in rows:
        image_path = (capture / row["image"]).resolve()
        manifest.append({
            **row,
            "source_image": str(image_path),
            "capture_id": capture.name,
            "dataset_role": report.get("dataset_role", "train"),
            "scene_state": report.get("scene_state", "clean"),
        })
    with (destination / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for row in manifest:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    keyframes = choose_keyframes(manifest)
    (destination / "keyframes.json").write_text(
        json.dumps(keyframes, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    cards = "\n".join(
        f'<figure><a href="{Path(row["source_image"]).as_uri()}">'
        f'<img src="{Path(row["source_image"]).as_uri()}" width="320"></a>'
        f'<figcaption>{html.escape(row["category"])} — '
        f'{html.escape(row["station"])} — tick {row["tick"]}</figcaption></figure>'
        for row in keyframes
    )
    (destination / "review.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>AUV capture review</title>'
        '<style>body{font:14px sans-serif;background:#111;color:#eee}'
        'main{display:flex;flex-wrap:wrap}figure{margin:8px}img{height:240px;object-fit:contain}'
        '</style><h1>AUV capture review</h1><main>' + cards + '</main>',
        encoding="utf-8",
    )
    source_hash = hashlib.sha256((capture / "frames.jsonl").read_bytes()).hexdigest()
    summary = {
        "capture": str(capture),
        "capture_manifest_sha256": source_hash,
        "route_completed": report.get("route_completed"),
        "map_sha256": report.get("map_sha256"),
        "dataset_role": report.get("dataset_role", "train"),
        "scene_state": report.get("scene_state", "clean"),
        "frames": len(manifest),
        "keyframes": len(keyframes),
        "by_category": {category: sum(row["category"] == category for row in manifest)
                        for category in CATEGORIES},
    }
    (destination / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare_capture(args.capture, args.destination), indent=2))


if __name__ == "__main__":
    main()
