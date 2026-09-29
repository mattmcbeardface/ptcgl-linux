import json
import stat
import tempfile
import unittest
from pathlib import Path

from ptcgl_linux.state import (
    InstallState,
    LauncherState,
    RuntimeState,
    StateError,
    default_state,
    load_state,
    save_state,
)


class StateTests(unittest.TestCase):
    def test_missing_state_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = load_state(path)

            self.assertEqual(state, default_state())

    def test_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"

            expected = LauncherState(
                runtime=RuntimeState(
                    umu_version="1.4.4",
                    proton_version="GE-Proton11-7-x86_64",
                    steam_runtime="steamrt4",
                ),
                install=InstallState(
                    prefix_initialized=True,
                    game_executable=(
                        "C:\\users\\steamuser\\"
                        "The Pokémon Company International\\"
                        "Pokémon Trading Card Game Live\\"
                        "Pokemon TCG Live.exe"
                    ),
                ),
            )

            save_state(expected, path)
            actual = load_state(path)

            self.assertEqual(actual, expected)

    def test_state_file_is_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data" / "state.json"

            save_state(default_state(), path)

            file_mode = stat.S_IMODE(path.stat().st_mode)
            dir_mode = stat.S_IMODE(path.parent.stat().st_mode)

            self.assertEqual(file_mode, 0o600)
            self.assertEqual(dir_mode, 0o700)

    def test_invalid_json_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("{not json", encoding="utf-8")

            with self.assertRaises(StateError):
                load_state(path)

    def test_unknown_schema_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"

            payload = {
                "schema_version": 999,
                "runtime": {},
                "install": {},
            }

            path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            with self.assertRaises(StateError):
                load_state(path)

    def test_game_executable_must_not_be_arbitrary_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"

            payload = {
                "schema_version": 1,
                "runtime": {
                    "umu_version": "1.4.4",
                    "proton_version": "GE-Proton11-7-x86_64",
                    "steam_runtime": "steamrt4",
                },
                "install": {
                    "prefix_initialized": False,
                    "game_executable": 123,
                },
            }

            path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            with self.assertRaises(StateError):
                load_state(path)


if __name__ == "__main__":
    unittest.main()
