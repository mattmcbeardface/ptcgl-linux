import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ptcgl_linux.desktop import run_desktop_app
from ptcgl_linux.runtime import RuntimePaths


def make_paths(root: Path) -> RuntimePaths:
    prefix = root / "prefix"

    return RuntimePaths(
        data_dir=root,
        prefix=prefix,
        umu=root / "umu-run",
        proton=root / "proton",
        steamrt4=root / "steamrt4",
        game=prefix / "game.exe",
    )


class DesktopTests(unittest.TestCase):
    def test_installed_game_launches_without_first_launch_ui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_paths(Path(tmp))
            paths.game.parent.mkdir(parents=True)
            paths.game.write_text("", encoding="utf-8")

            first_launch = Mock(return_value=99)

            with patch(
                "ptcgl_linux.desktop.launch_game",
                return_value=0,
            ) as launch:
                result = run_desktop_app(
                    paths=paths,
                    first_launch=first_launch,
                )

            self.assertEqual(result, 0)
            launch.assert_called_once_with(paths=paths)
            first_launch.assert_not_called()

    def test_missing_game_runs_first_launch_ui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_paths(Path(tmp))
            first_launch = Mock(return_value=0)

            with patch(
                "ptcgl_linux.desktop.launch_game"
            ) as launch:
                result = run_desktop_app(
                    paths=paths,
                    first_launch=first_launch,
                )

            self.assertEqual(result, 0)
            first_launch.assert_called_once_with(paths)
            launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
