"""Desktop application entry point."""

from __future__ import annotations

from collections.abc import Callable

from .launcher import launch_game
from .runtime import RuntimePaths, runtime_paths


FirstLaunchRunner = Callable[[RuntimePaths], int]


def run_desktop_app(
    *,
    paths: RuntimePaths | None = None,
    first_launch: FirstLaunchRunner | None = None,
) -> int:
    """Launch the game directly, or provision it on first launch."""

    if paths is None:
        paths = runtime_paths()

    if paths.game.is_file():
        return launch_game(paths=paths)

    if first_launch is None:
        from .gui import run_first_launch

        first_launch = run_first_launch

    return first_launch(paths)
