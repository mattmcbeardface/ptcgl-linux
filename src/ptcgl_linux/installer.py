"""Pokémon TCG Live installation and repair operations."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .artifacts import ArtifactError, download_verified, verify_sha256
from .paths import cache_home
from .proton import install_proton
from .runtime import RuntimePaths, runtime_paths, vc_runtime_paths
from .umu import install_umu


PTCGL_INSTALLER_NAME = "PokemonTCGLiveInstaller.msi"
PTCGL_INSTALLER_URL = (
    "https://installer.studio-prod.pokemon.com/installer/"
    "PokemonTCGLiveInstaller.msi"
)
PTCGL_INSTALLER_SHA256 = (
    "cf970aded232fffc52263932bb0dc5627"
    "642a8f489c73485f3d7b5d0c1e5127b"
)


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


def _windows_z_path(path: Path) -> str:
    resolved = path.expanduser().resolve(strict=True)
    return "Z:" + str(resolved).replace("/", "\\")


def ensure_umu(paths: RuntimePaths) -> Path:
    """Return the usable UMU runner, installing it outside Flatpak if needed."""

    if paths.umu.is_file():
        return paths.umu

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


def acquire_ptcgl_installer(
    *,
    artifact_cache: Path | None = None,
) -> Path:
    """Acquire the pinned official Pokémon TCG Live MSI."""

    if artifact_cache is None:
        artifact_cache = cache_home() / "artifacts"

    artifact_cache.mkdir(parents=True, exist_ok=True)
    os.chmod(artifact_cache, 0o700)

    installer = artifact_cache / PTCGL_INSTALLER_NAME

    if installer.exists():
        if verify_sha256(installer, PTCGL_INSTALLER_SHA256):
            os.chmod(installer, 0o600)
            return installer

        installer.unlink()

    try:
        return download_verified(
            PTCGL_INSTALLER_URL,
            installer,
            PTCGL_INSTALLER_SHA256,
        )
    except ArtifactError as exc:
        raise InstallError(
            "unable to acquire Pokémon TCG Live installer"
        ) from exc


def install_game(
    paths: RuntimePaths,
    *,
    artifact_cache: Path | None = None,
) -> Path:
    """Install Pokémon TCG Live into the managed prefix."""

    if paths.game.is_file():
        return paths.game

    installer = acquire_ptcgl_installer(
        artifact_cache=artifact_cache,
    )

    msiexec = (
        paths.prefix
        / "drive_c"
        / "windows"
        / "system32"
        / "msiexec.exe"
    )

    if not msiexec.is_file():
        raise InstallError("Windows Installer is unavailable in prefix")

    windows_installer = _windows_z_path(installer)

    try:
        result = subprocess.run(
            [
                str(paths.umu),
                str(msiexec),
                "/i",
                windows_installer,
                "/quiet",
                "/norestart",
            ],
            env=_umu_environment(paths),
            check=False,
        )
    except OSError as exc:
        raise InstallError(
            "unable to run Pokémon TCG Live installer"
        ) from exc

    if result.returncode != 0:
        raise InstallError(
            "Pokémon TCG Live installer failed with exit code "
            f"{result.returncode}"
        )

    if not paths.game.is_file():
        raise InstallError(
            "Pokémon TCG Live installer completed but game executable "
            "was not found"
        )

    return paths.game


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


def install_ptcgl(
    *,
    paths: RuntimePaths | None = None,
    artifact_cache: Path | None = None,
) -> RuntimePaths:
    """Prepare the runtime and install Pokémon TCG Live."""

    paths = bootstrap_runtime(paths=paths)

    install_game(
        paths,
        artifact_cache=artifact_cache,
    )

    return paths
