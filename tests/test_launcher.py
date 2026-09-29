import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ptcgl_linux.launcher import LaunchError, launch_game
from ptcgl_linux.runtime import RuntimePaths


def make_runtime(root: Path) -> RuntimePaths:
    data = root / "data"
    prefix = data / "prefix"
    umu = data / "toolchain" / "umu" / "umu-run"
    proton = (
        data
        / "toolchain"
        / "proton"
        / "GE-Proton11-7-x86_64"
    )
    game = prefix / "drive_c" / "Pokemon TCG Live.exe"

    umu.parent.mkdir(parents=True)
    umu.write_text("umu")

    proton.mkdir(parents=True)

    game.parent.mkdir(parents=True)
    game.write_text("game")

    return RuntimePaths(
        data_dir=data,
        prefix=prefix,
        umu=umu,
        proton=proton,
        steamrt4=root / "steamrt4",
        game=game,
    )


class LauncherTests(unittest.TestCase):
    def test_launch_uses_managed_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runtime(Path(tmp))

            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
            )

            with patch(
                "ptcgl_linux.launcher.subprocess.run",
                return_value=completed,
            ) as run:
                result = launch_game(paths=paths)

            self.assertEqual(result, 0)

            args, kwargs = run.call_args

            self.assertEqual(
                args[0],
                [
                    str(paths.umu),
                    str(paths.game),
                ],
            )

            env = kwargs["env"]

            self.assertEqual(env["GAMEID"], "0")
            self.assertEqual(
                env["WINEPREFIX"],
                str(paths.prefix),
            )
            self.assertEqual(
                env["PROTONPATH"],
                str(paths.proton),
            )
            self.assertEqual(
                env["UMU_CONTAINER_NSENTER"],
                "1",
            )

    def test_game_exit_status_is_returned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runtime(Path(tmp))

            completed = subprocess.CompletedProcess(
                args=[],
                returncode=7,
            )

            with patch(
                "ptcgl_linux.launcher.subprocess.run",
                return_value=completed,
            ):
                self.assertEqual(
                    launch_game(paths=paths),
                    7,
                )

    def test_missing_runtime_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            paths = RuntimePaths(
                data_dir=root,
                prefix=root / "prefix",
                umu=root / "missing-umu",
                proton=root / "missing-proton",
                steamrt4=root / "steamrt4",
                game=root / "missing-game",
            )

            with self.assertRaises(LaunchError):
                launch_game(paths=paths)

    def test_os_launch_failure_is_wrapped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_runtime(Path(tmp))

            with patch(
                "ptcgl_linux.launcher.subprocess.run",
                side_effect=OSError("test failure"),
            ):
                with self.assertRaises(LaunchError):
                    launch_game(paths=paths)


if __name__ == "__main__":
    unittest.main()
