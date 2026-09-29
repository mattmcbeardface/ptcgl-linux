"""Handler for tpcitcgapp:// authentication callbacks.

OAuth callback contents must never be written to logs.
"""

from __future__ import annotations

import os
import subprocess
from urllib.parse import urlsplit

from .runtime import RuntimePaths, runtime_paths


CALLBACK_SCHEME = "tpcitcgapp"
CALLBACK_HOST = "callback"


class CallbackError(RuntimeError):
    """Raised when an authentication callback cannot be delivered."""


def validate_callback_url(url: str) -> None:
    """Validate a Pokémon TCG Live authentication callback.

    The URL contents are intentionally never included in exception messages.
    """

    if not url:
        raise CallbackError("missing authentication callback")

    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in url):
        raise CallbackError("invalid authentication callback")

    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise CallbackError("invalid authentication callback") from exc

    if parsed.scheme.lower() != CALLBACK_SCHEME:
        raise CallbackError("invalid authentication callback scheme")

    if parsed.netloc.lower() != CALLBACK_HOST:
        raise CallbackError("invalid authentication callback target")


def _validate_runtime(paths: RuntimePaths) -> None:
    if not paths.umu.is_file():
        raise CallbackError("UMU runtime is unavailable")

    if not paths.proton.is_dir():
        raise CallbackError("GE-Proton runtime is unavailable")

    if not paths.prefix.is_dir():
        raise CallbackError("Pokémon TCG Live prefix is unavailable")

    if not paths.game.is_file():
        raise CallbackError("Pokémon TCG Live is unavailable")


def handle_callback(
    url: str,
    *,
    paths: RuntimePaths | None = None,
) -> int:
    """Deliver an OAuth callback to Pokémon TCG Live.

    The callback URL is passed only as a process argument. Standard output and
    standard error are discarded so authentication material cannot be
    accidentally persisted by UMU, Proton, Wine, or the game.
    """

    validate_callback_url(url)

    if paths is None:
        paths = runtime_paths()

    _validate_runtime(paths)

    env = os.environ.copy()
    env.update(
        {
            "GAMEID": "0",
            "WINEPREFIX": str(paths.prefix),
            "PROTONPATH": str(paths.proton),
            "PROTON_VERB": "runinprefix",
            "UMU_CONTAINER_NSENTER": "1",
        }
    )

    try:
        subprocess.Popen(
            [
                str(paths.umu),
                str(paths.game),
                url,
            ],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError as exc:
        raise CallbackError(
            "unable to deliver authentication callback"
        ) from exc

    return 0
