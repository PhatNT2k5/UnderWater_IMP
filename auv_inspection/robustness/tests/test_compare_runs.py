"""Benchmark result comparison used to prove code revisions equivalent."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from robustness.compare_runs import compare  # noqa: E402


def write(folder: Path, name: str, **fields: object) -> None:
    base = {"defects": {"detected": ["a"]}, "false_alerts": 1, "events": [], "processing_ms_median": 10.0}
    (folder / name).write_text(json.dumps({**base, **fields}), encoding="utf-8")


class CompareRunsTests(unittest.TestCase):
    def test_identical_ignoring_timing_and_differences_reported(self) -> None:
        with TemporaryDirectory() as a_dir, TemporaryDirectory() as b_dir:
            a, b = Path(a_dir), Path(b_dir)
            write(a, "d__capture_x__none.json")
            write(b, "d__capture_x__none.json", processing_ms_median=99.0)
            self.assertTrue(compare(a, b, "d")["identical"])
            write(b, "d__capture_x__none.json", false_alerts=2)
            result = compare(a, b, "d")
            self.assertFalse(result["identical"])
            self.assertEqual(result["differences"], [{"file": "d__capture_x__none.json", "fields": ["false_alerts"]}])
            write(a, "d__capture_y__none.json")
            result = compare(a, b, "d")
            self.assertEqual((result["runs"], result["runs_compared"]), (2, 1))


if __name__ == "__main__":
    unittest.main()
