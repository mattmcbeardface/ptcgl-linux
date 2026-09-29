import tempfile
import unittest
from pathlib import Path

from ptcgl_linux.runtime import (
    GAME_RELATIVE_PATH,
    KNOWN_GOOD_PROTON,
    runtime_paths,
    vc_runtime_paths,
)


class RuntimePathTests(unittest.TestCase):
    def test_runtime_paths_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            paths = runtime_paths(home)

            expected_data = home / ".local" / "share" / "ptcgl-linux"

            self.assertEqual(paths.data_dir, expected_data)
            self.assertEqual(paths.prefix, expected_data / "prefix")
            self.assertEqual(paths.game, paths.prefix / GAME_RELATIVE_PATH)

    def test_known_good_proton_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = runtime_paths(Path(tmp))
            self.assertEqual(paths.proton.name, KNOWN_GOOD_PROTON)

    def test_vc_runtime_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = runtime_paths(Path(tmp))
            dlls = {path.name for path in vc_runtime_paths(paths)}

            self.assertEqual(
                dlls,
                {
                    "concrt140.dll",
                    "msvcp140.dll",
                    "vcruntime140.dll",
                    "vcruntime140_1.dll",
                },
            )


if __name__ == "__main__":
    unittest.main()
