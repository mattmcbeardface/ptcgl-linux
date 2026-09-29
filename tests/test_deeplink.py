import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ptcgl_linux.deeplink import (
    CallbackError,
    handle_callback,
    validate_callback_url,
)
from ptcgl_linux.runtime import RuntimePaths


def make_runtime(root: Path) -> RuntimePaths:
    data = root / "data"
    prefix = data / "prefix"
    umu = data / "toolchain" / "umu" / "umu-run"
    proton = data / "toolchain" / "proton" / "GE-Proton11-7-x86_64"
    steamrt4 = root / "steamrt4"
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
        steamrt4=steamrt4,
        game=game,
    )


class DeeplinkTests(unittest.TestCase):
    def test_valid_callback_is_accepted(self) -> None:
        validate_callback_url(
            "tpcitcgapp://callback?code=test&state=test"
        )

    def test_wrong_scheme_is_rejected(self) -> None:
        with self.assertRaises(CallbackError):
            validate_callback_url(
                "https://callback?code=test"
            )

    def test_wrong_target_is_rejected(self) -> None:
        with self.assertRaises(CallbackError):
            validate_callback_url(
                "tpcitcgapp://other?code=test"
            )

    def test_callback_uses_managed_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = make_runtime(root)

            url = (
                "tpcitcgapp://callback"
                "?code=test-code&state=test-state"
            )

            with patch(
                "ptcgl_linux.deeplink.subprocess.Popen"
            ) as popen:
                result = handle_callback(
                    url,
                    paths=paths,
                )

            self.assertEqual(result, 0)

            args, kwargs = popen.call_args
            command = args[0]

            self.assertEqual(command[0], str(paths.umu))
            self.assertEqual(command[1], str(paths.game))
            self.assertEqual(command[2], url)

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
                env["PROTON_VERB"],
                "runinprefix",
            )
            self.assertEqual(
                env["UMU_CONTAINER_NSENTER"],
                "1",
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

            with self.assertRaises(CallbackError):
                handle_callback(
                    "tpcitcgapp://callback?code=test",
                    paths=paths,
                )


if __name__ == "__main__":
    unittest.main()
