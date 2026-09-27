"""Check UnrealEditor.exe lookup order without touching the real machine setup."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_inspection
from run_inspection import EDITOR_ENV_VAR, find_editor

EDITOR_RELATIVE = Path("Engine/Binaries/Win64/UnrealEditor.exe")


def make_engine(root: Path, name: str) -> Path:
    editor = root / name / EDITOR_RELATIVE
    editor.parent.mkdir(parents=True)
    editor.write_bytes(b"")
    return root / name


class FindEditorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        env = {key: value for key, value in os.environ.items() if key != EDITOR_ENV_VAR}
        self.enterContext(mock.patch.dict(os.environ, env, clear=True))

    def patch_sources(self, launcher: Path | None, registry: Path | None) -> None:
        self.enterContext(mock.patch.object(run_inspection, "launcher_engine_dir", return_value=launcher))
        self.enterContext(mock.patch.object(run_inspection, "registry_engine_dir", return_value=registry))

    def test_explicit_path_wins_over_env_var(self) -> None:
        explicit = make_engine(self.root, "explicit") / EDITOR_RELATIVE
        os.environ[EDITOR_ENV_VAR] = str(make_engine(self.root, "env") / EDITOR_RELATIVE)

        self.assertEqual(find_editor(str(explicit)), explicit)

    def test_env_var_wins_over_launcher(self) -> None:
        env_editor = make_engine(self.root, "env") / EDITOR_RELATIVE
        os.environ[EDITOR_ENV_VAR] = str(env_editor)
        self.patch_sources(make_engine(self.root, "launcher"), None)

        self.assertEqual(find_editor(None), env_editor)

    def test_launcher_wins_over_registry(self) -> None:
        launcher = make_engine(self.root, "launcher")
        self.patch_sources(launcher, make_engine(self.root, "registry"))

        self.assertEqual(find_editor(None), launcher / EDITOR_RELATIVE)

    def test_registry_used_when_launcher_has_no_engine(self) -> None:
        registry = make_engine(self.root, "registry")
        self.patch_sources(None, registry)

        self.assertEqual(find_editor(None), registry / EDITOR_RELATIVE)

    def test_missing_everywhere_names_env_var(self) -> None:
        self.patch_sources(None, None)

        with self.assertRaisesRegex(FileNotFoundError, EDITOR_ENV_VAR):
            find_editor(None)

    def test_resolved_path_must_exist(self) -> None:
        self.patch_sources(None, self.root / "missing")

        with self.assertRaises(FileNotFoundError):
            find_editor(None)


if __name__ == "__main__":
    unittest.main()
