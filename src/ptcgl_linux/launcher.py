"""Pokémon TCG Live process launching."""

from __future__ import annotations

import os
import subprocess

from .runtime import RuntimePaths, runtime_paths


class LaunchError(RuntimeError):
    """Raised when Pokémon TCG Live cannot be launched."""


def _validate_runtime(paths: RuntimePaths) -> None:
    if not paths.umu.is_file():
        raise LaunchError("UMU runtime is unavailable")

    if not paths.proton.is_dir():
        raise LaunchError("GE-Proton runtime is unavailable")

    if not paths.prefix.is_dir():
        raise LaunchError("Pokémon TCG Live prefix is unavailable")

    if not paths.game.is_file():
        raise LaunchError("Pokémon TCG Live is not installed")


def launch_game(
    *,
    paths: RuntimePaths | None = None,
) -> int:
    """Launch Pokémon TCG Live and return its process exit status."""

    if paths is None:
        paths = runtime_paths()

    _validate_runtime(paths)

    env = os.environ.copy()
    env.update(
        {
            "GAMEID": "0",
            "WINEPREFIX": str(paths.prefix),
            "PROTONPATH": str(paths.proton),
            "UMU_CONTAINER_NSENTER": "1",
        }
    )

    try:
        result = subprocess.run(
            [
                str(paths.umu),
                str(paths.game),
            ],
            env=env,
            check=False,
        )
    except OSError as exc:
        raise LaunchError(
            "unable to launch Pokémon TCG Live"
        ) from exc

    return result.returncode
