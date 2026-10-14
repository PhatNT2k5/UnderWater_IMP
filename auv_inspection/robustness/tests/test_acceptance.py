"""P7 acceptance report on synthetic benchmark results."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from robustness import acceptance  # noqa: E402


def write_run(folder: Path, detector: str, capture: str, condition: str, detected: list[str],
              observable: list[str], false_alerts: int, length: float, cells: tuple[int, int]) -> None:
    degradations = [] if condition == "none" else [{"factor": condition, "severity": 3}]
    (folder / f"{detector}__{capture}__{condition}.json").write_text(json.dumps({
        "capture": f"/x/{capture}", "degradations": degradations,
        "defects": {"detected": detected, "observable": observable},
        "false_alerts": false_alerts, "surveyed_length_m": length,
        "availability": {"pipe_front": {"analysed": 90, "diffuse_anomaly": 10}},
        "ambiguity": {"clean_cell_fpr": {"count": cells[0], "total": cells[1]}}}), encoding="utf-8")


class AcceptanceTests(unittest.TestCase):
    def test_pooled_criteria_and_conditions(self) -> None:
        with TemporaryDirectory() as folder:
            path = Path(folder)
            write_run(path, "d", "capA", "none", ["a", "b", "c"], ["a", "b", "c"], 0, 200.0, (0, 1000))
            write_run(path, "d", "capA", "marine_snow", ["a"], ["a", "b", "c"], 1, 200.0, (1, 1000))
            write_run(path, "d", "capC", "none", [], [], 0, 200.0, (0, 1000))
            result = acceptance.report(path, "d", ["capA"], ["capC"])
        self.assertAlmostEqual(result["recall"], 4 / 6, places=4)
        self.assertAlmostEqual(result["false_alerts_per_100m"], 100 / 600, places=3)
        self.assertEqual(result["cell_fpr"]["alerting"], 1)
        self.assertTrue(result["passed"]["false_alerts_per_100m"])
        self.assertTrue(result["passed"]["cell_fpr"])
        self.assertFalse(result["passed"]["recall"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["by_condition"]["marine_snow3"]["recall"], "1/3")
        self.assertEqual(result["by_condition"]["none"]["diffuse_share"], 0.1)

    def test_missing_results_are_an_error(self) -> None:
        with TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                acceptance.report(Path(folder), "d", ["nothing"], [])

    def test_wilson_upper_bound(self) -> None:
        self.assertAlmostEqual(acceptance.wilson_upper(0, 100), 0.037, places=3)
        self.assertEqual(acceptance.wilson_upper(0, 0), 1.0)


if __name__ == "__main__":
    unittest.main()
