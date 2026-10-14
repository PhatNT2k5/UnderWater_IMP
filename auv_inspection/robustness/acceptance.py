"""P7 acceptance report from benchmark results on held-out captures (pre-registered 2026-10-14).

Criteria (GENERALIZATION_PLAN.md, decision log 2026-10-14, fixed before the held-out data):
- recall over physical defects >= 90%: observable defect occurrences (defect x capture x
  condition) that the detector alerted on, pooled over all conditions;
- false alerts <= 1 per 100 m surveyed, pooled over all conditions;
- cell-level FPR <= 5% at 95% confidence: upper Wilson bound of alerting clean surface cells
  (>= k views, not on a labelled defect) over evaluated clean cells.
Uncertainty for recall and false alerts: bootstrap over captures (the independent units).
Per-condition rows and abstention shares are reported for context, not as pass/fail.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np

RECALL_TARGET = 0.90
FALSE_ALERTS_PER_100M_MAX = 1.0
CELL_FPR_MAX = 0.05
BOOTSTRAP_SAMPLES = 2000


def load_runs(directory: Path, detector: str, captures: list[str]) -> list[dict]:
    runs = []
    for capture in captures:
        files = sorted(directory.glob(f"{detector}__{capture}__*.json"))
        files = [f for f in files if "__pose" not in f.name]
        if not files:
            raise FileNotFoundError(f"No results for {detector} on {capture}")
        runs += [json.loads(f.read_text(encoding="utf-8")) for f in files]
    return runs


def capture_totals(runs: list[dict]) -> dict[str, dict[str, float]]:
    """Per capture: detected / observable defect occurrences, false alerts, length, cell counts."""
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for run in runs:
        t = totals[Path(run["capture"]).name]
        t["detected"] += len(run["defects"]["detected"])
        t["observable"] += len(run["defects"]["observable"])
        t["false_alerts"] += run["false_alerts"]
        t["length_m"] += run["surveyed_length_m"]
        fpr = (run.get("ambiguity") or {}).get("clean_cell_fpr")
        if fpr:
            t["cells_alerting"] += fpr["count"]
            t["cells_evaluated"] += fpr["total"]
    return totals


def pooled(totals: dict[str, dict[str, float]], keys: list[str]) -> dict[str, float]:
    recall = sum(totals[k]["detected"] for k in keys) / max(sum(totals[k]["observable"] for k in keys), 1)
    rate = 100 * sum(totals[k]["false_alerts"] for k in keys) / max(sum(totals[k]["length_m"] for k in keys), 1e-9)
    return {"recall": recall, "false_alerts_per_100m": rate}


def bootstrap(totals: dict[str, dict[str, float]], seed: int = 20261014) -> dict[str, list[float]]:
    keys = sorted(totals)
    rng = np.random.default_rng(seed)
    samples = [pooled(totals, list(rng.choice(keys, len(keys), replace=True))) for _ in range(BOOTSTRAP_SAMPLES)]
    return {metric: np.percentile([s[metric] for s in samples], [2.5, 97.5]).round(4).tolist()
            for metric in ("recall", "false_alerts_per_100m")}


def wilson_upper(successes: float, trials: float, z: float = 1.96) -> float:
    if trials <= 0:
        return 1.0
    p = successes / trials
    centre = (p + z * z / (2 * trials)) / (1 + z * z / trials)
    half = z * np.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / (1 + z * z / trials)
    return float(centre + half)


def report(directory: Path, detector: str, mixed: list[str], clean: list[str]) -> dict:
    runs = load_runs(directory, detector, mixed + clean)
    totals = capture_totals(runs)
    point = pooled(totals, sorted(totals))
    alerting = sum(t["cells_alerting"] for t in totals.values())
    evaluated = sum(t["cells_evaluated"] for t in totals.values())
    fpr_upper = wilson_upper(alerting, evaluated)
    by_condition: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for run in runs:
        name = "+".join(f"{d['factor']}{d['severity']}" for d in run["degradations"]) or "none"
        c = by_condition[name]
        c["detected"] += len(run["defects"]["detected"])
        c["observable"] += len(run["defects"]["observable"])
        c["false_alerts"] += run["false_alerts"]
        c["length_m"] += run["surveyed_length_m"]
        availability = run["availability"]
        total = sum(sum(group.values()) for group in availability.values())
        c["abstained"] += sum(group.get("diffuse_anomaly", 0) for group in availability.values())
        c["frames"] += total
    rows = {name: {"recall": f"{int(c['detected'])}/{int(c['observable'])}",
                   "false_alerts": int(c["false_alerts"]),
                   "false_alerts_per_100m": round(100 * c["false_alerts"] / max(c["length_m"], 1e-9), 2),
                   "diffuse_share": round(c["abstained"] / max(c["frames"], 1), 3)}
            for name, c in sorted(by_condition.items())}
    passed = {"recall": point["recall"] >= RECALL_TARGET,
              "false_alerts_per_100m": point["false_alerts_per_100m"] <= FALSE_ALERTS_PER_100M_MAX,
              "cell_fpr": fpr_upper <= CELL_FPR_MAX}
    return {"detector": detector, "captures": {"mixed": mixed, "clean": clean}, "runs": len(runs),
            "recall": round(point["recall"], 4),
            "false_alerts_per_100m": round(point["false_alerts_per_100m"], 3),
            "bootstrap95": bootstrap(totals),
            "cell_fpr": {"alerting": int(alerting), "evaluated": int(evaluated),
                         "rate": alerting / evaluated if evaluated else None, "wilson95_upper": round(fpr_upper, 6)},
            "criteria": {"recall_min": RECALL_TARGET, "false_alerts_per_100m_max": FALSE_ALERTS_PER_100M_MAX,
                         "cell_fpr_upper_max": CELL_FPR_MAX},
            "passed": passed, "accepted": all(passed.values()), "by_condition": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", type=Path, help="Benchmark result directory")
    parser.add_argument("--detector", action="append", required=True)
    parser.add_argument("--mixed", nargs="+", default=[], help="Capture folder names with defects")
    parser.add_argument("--clean", nargs="+", default=[], help="Clean capture folder names")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reports = [report(args.results, name, args.mixed, args.clean) for name in args.detector]
    text = json.dumps(reports, indent=2)
    if args.output:
        if args.output.exists():
            parser.error(f"Refusing to overwrite {args.output}")
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
