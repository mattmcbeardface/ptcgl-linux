"""Pokémon TCG Live installation and repair operations."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .proton import install_proton
from .runtime import RuntimePaths, runtime_paths, vc_runtime_paths
from .umu import install_umu


class InstallError(RuntimeError):
    """Raised when installation cannot be completed."""


def _umu_environment(paths: RuntimePaths) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "GAMEID": "0",
            "WINEPREFIX": str(paths.prefix),
            "PROTONPATH": str(paths.proton),
        }
    )
    return env


def _required_prefix_paths(paths: RuntimePaths) -> tuple[Path, ...]:
    return (
        paths.prefix / "drive_c",
        paths.prefix / "system.reg",
        paths.prefix / "user.reg",
        paths.prefix / "userdef.reg",
    )


def _missing_prefix_paths(paths: RuntimePaths) -> list[Path]:
    return [
        path
        for path in _required_prefix_paths(paths)
        if not path.exists()
    ]


def ensure_umu(paths: RuntimePaths) -> Path:
    """Return the usable UMU runner, installing it outside Flatpak if needed."""

    if paths.umu.is_file():
        return paths.umu

    # A Flatpak build packages UMU under /app. If it is missing there,
    # downloading another copy into writable application data would hide
    # a broken package rather than repair it.
    if os.environ.get("FLATPAK_ID"):
        raise InstallError("packaged UMU runtime is unavailable")

    try:
        runner = install_umu(app_data=paths.data_dir)
    except Exception as exc:
        raise InstallError("unable to install UMU runtime") from exc

    if not runner.is_file():
        raise InstallError("UMU runtime installation did not produce a runner")

    return runner


def ensure_proton(paths: RuntimePaths) -> Path:
    """Install or reuse the known-good GE-Proton runtime."""

    try:
        proton = install_proton(app_data=paths.data_dir)
    except Exception as exc:
        raise InstallError("unable to install GE-Proton runtime") from exc

    if not proton.is_dir():
        raise InstallError("GE-Proton installation did not produce a runtime")

    return proton


def initialize_prefix(paths: RuntimePaths) -> None:
    """Initialize the Proton prefix if its required files are absent."""

    if not _missing_prefix_paths(paths):
        return

    paths.prefix.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [str(paths.umu), ""],
            env=_umu_environment(paths),
            check=False,
        )
    except OSError as exc:
        raise InstallError("unable to initialize Proton prefix") from exc

    missing = _missing_prefix_paths(paths)

    if missing:
        names = ", ".join(path.name for path in missing)
        raise InstallError(
            f"Proton prefix initialization incomplete; missing: {names}"
        )


def install_vcrun2019(paths: RuntimePaths) -> None:
    """Install the Visual C++ 2019 runtime into the prefix."""

    required = vc_runtime_paths(paths)

    if all(path.is_file() for path in required):
        return

    try:
        result = subprocess.run(
            [
                str(paths.umu),
                "winetricks",
                "-q",
                "vcrun2019",
            ],
            env=_umu_environment(paths),
            check=False,
        )
    except OSError as exc:
        raise InstallError("unable to run winetricks") from exc

    if result.returncode != 0:
        raise InstallError(
            f"vcrun2019 installation failed with exit code "
            f"{result.returncode}"
        )

    missing = [
        path.name
        for path in required
        if not path.is_file()
    ]

    if missing:
        raise InstallError(
            "vcrun2019 installation incomplete; missing: "
            + ", ".join(missing)
        )


def bootstrap_runtime(
    *,
    paths: RuntimePaths | None = None,
) -> RuntimePaths:
    """Prepare the compatibility environment required by PTCGL."""

    if paths is None:
        paths = runtime_paths()

    ensure_umu(paths)
    ensure_proton(paths)
    initialize_prefix(paths)
    install_vcrun2019(paths)

    return paths
