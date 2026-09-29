"""Discovery of the ptcgl-linux compatibility runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .paths import data_home


KNOWN_GOOD_UMU_VERSION = "1.4.4"
KNOWN_GOOD_PROTON = "GE-Proton11-7-x86_64"
GAME_RELATIVE_PATH = Path(
    "drive_c/users/steamuser/"
    "The Pokémon Company International/"
    "Pokémon Trading Card Game Live/"
    "Pokemon TCG Live.exe"
)

VC_RUNTIME_DLLS = (
    "concrt140.dll",
    "msvcp140.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
)


@dataclass(frozen=True)
class RuntimePaths:
    data_dir: Path
    prefix: Path
    umu: Path
    proton: Path
    steamrt4: Path
    game: Path


def runtime_paths(home: Path | None = None) -> RuntimePaths:
    if home is None:
        home = Path.home()
        app_data = data_home()
    else:
        app_data = home / ".local" / "share" / "ptcgl-linux"

    prefix = app_data / "prefix"

    return RuntimePaths(
        data_dir=app_data,
        prefix=prefix,
        umu=app_data / "toolchain" / "umu" / "umu-run",
        proton=(
            home
            / ".local"
            / "share"
            / "Steam"
            / "compatibilitytools.d"
            / KNOWN_GOOD_PROTON
        ),
        steamrt4=home / ".local" / "share" / "umu" / "steamrt4",
        game=prefix / GAME_RELATIVE_PATH,
    )


def vc_runtime_paths(paths: RuntimePaths) -> tuple[Path, ...]:
    system32 = paths.prefix / "drive_c" / "windows" / "system32"
    return tuple(system32 / name for name in VC_RUNTIME_DLLS)
