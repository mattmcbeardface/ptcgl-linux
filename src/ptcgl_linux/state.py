"""Persistent launcher state.

State must never contain credentials, OAuth callbacks, authorization codes,
access tokens, or refresh tokens.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .paths import data_home
from .runtime import KNOWN_GOOD_PROTON, KNOWN_GOOD_UMU_VERSION


STATE_SCHEMA_VERSION = 1
DEFAULT_STEAM_RUNTIME = "steamrt4"


class StateError(RuntimeError):
    """Raised when persisted launcher state is invalid."""


@dataclass
class RuntimeState:
    umu_version: str = KNOWN_GOOD_UMU_VERSION
    proton_version: str = KNOWN_GOOD_PROTON
    steam_runtime: str = DEFAULT_STEAM_RUNTIME


@dataclass
class InstallState:
    prefix_initialized: bool = False
    game_executable: str | None = None


@dataclass
class LauncherState:
    schema_version: int = STATE_SCHEMA_VERSION
    runtime: RuntimeState = field(default_factory=RuntimeState)
    install: InstallState = field(default_factory=InstallState)


def state_path() -> Path:
    return data_home() / "state.json"


def default_state() -> LauncherState:
    return LauncherState()


def _validate_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise StateError(f"{field_name} must be a non-empty string")
    return value


def _decode_state(payload: Any) -> LauncherState:
    if not isinstance(payload, dict):
        raise StateError("state root must be a JSON object")

    schema_version = payload.get("schema_version")

    if schema_version != STATE_SCHEMA_VERSION:
        raise StateError(
            f"unsupported state schema version: {schema_version!r}"
        )

    runtime_payload = payload.get("runtime")
    install_payload = payload.get("install")

    if not isinstance(runtime_payload, dict):
        raise StateError("runtime must be a JSON object")

    if not isinstance(install_payload, dict):
        raise StateError("install must be a JSON object")

    runtime = RuntimeState(
        umu_version=_validate_string(
            runtime_payload.get("umu_version"),
            "runtime.umu_version",
        ),
        proton_version=_validate_string(
            runtime_payload.get("proton_version"),
            "runtime.proton_version",
        ),
        steam_runtime=_validate_string(
            runtime_payload.get("steam_runtime"),
            "runtime.steam_runtime",
        ),
    )

    prefix_initialized = install_payload.get("prefix_initialized")

    if not isinstance(prefix_initialized, bool):
        raise StateError("install.prefix_initialized must be a boolean")

    game_executable = install_payload.get("game_executable")

    if game_executable is not None and not isinstance(game_executable, str):
        raise StateError(
            "install.game_executable must be a string or null"
        )

    install = InstallState(
        prefix_initialized=prefix_initialized,
        game_executable=game_executable,
    )

    return LauncherState(
        schema_version=STATE_SCHEMA_VERSION,
        runtime=runtime,
        install=install,
    )


def load_state(path: Path | None = None) -> LauncherState:
    if path is None:
        path = state_path()

    if not path.exists():
        return default_state()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError(f"unable to read state file {path}: {exc}") from exc

    return _decode_state(payload)


def save_state(
    state: LauncherState,
    path: Path | None = None,
) -> None:
    if path is None:
        path = state_path()

    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)

    # Application state may eventually contain local installation metadata.
    # Keep the directory private even though secrets are forbidden here.
    os.chmod(directory, 0o700)

    payload = json.dumps(
        asdict(state),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"

    temp_name: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".state.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        temp_path = Path(temp_name)
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
        os.chmod(path, 0o600)

    finally:
        if temp_name is not None:
            temp_path = Path(temp_name)

            if temp_path.exists():
                temp_path.unlink()
