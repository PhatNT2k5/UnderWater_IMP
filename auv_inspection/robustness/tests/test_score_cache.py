"""P8 token-grid cache: exact round trip, hit/miss counts, float32 only."""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from robustness.score_cache import GridCache, cache_path  # noqa: E402


class GridCacheTests(unittest.TestCase):
    def test_round_trip_is_exact_and_counts_hits(self) -> None:
        with TemporaryDirectory() as folder:
            path = cache_path(Path(folder), Path("capture_x"), "marine_snow3", 0, "abc")
            self.assertEqual(path.name, "capture_x__marine_snow3__seed0__abc.npz")
            grid = np.random.default_rng(0).random((69, 92)).astype(np.float32)
            cache = GridCache(path)
            self.assertIsNone(cache.get(12, "pier_0"))
            cache.put(12, "pier_0", grid)
            cache.save()
            reloaded = GridCache(path)
            np.testing.assert_array_equal(reloaded.get(12, "pier_0"), grid)
            self.assertIsNone(reloaded.get(12, "pier_1"))
            self.assertEqual((reloaded.hits, reloaded.misses), (1, 1))
            with self.assertRaises(ValueError):
                reloaded.put(13, "pier_0", grid.astype(np.float16))

    def test_saves_from_two_runs_are_merged(self) -> None:
        with TemporaryDirectory() as folder:
            path = Path(folder) / "c.npz"
            first, second = GridCache(path), GridCache(path)   # both opened before either saves
            first.put(1, "pipe_front", np.ones((2, 2), np.float32))
            second.put(2, "pipe_front", np.zeros((2, 2), np.float32))
            first.save()
            second.save()
            merged = GridCache(path)
            self.assertIsNotNone(merged.get(1, "pipe_front"))
            self.assertIsNotNone(merged.get(2, "pipe_front"))
            self.assertEqual(list(Path(folder).glob("*.tmp.npz")), [])


if __name__ == "__main__":
    unittest.main()
