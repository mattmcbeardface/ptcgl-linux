"""Application filesystem paths."""

from __future__ import annotations

import os
from pathlib import Path


def data_home() -> Path:
    root = os.environ.get("XDG_DATA_HOME")
    if root:
        return Path(root) / "ptcgl-linux"

    return Path.home() / ".local" / "share" / "ptcgl-linux"


def config_home() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME")
    if root:
        return Path(root) / "ptcgl-linux"

    return Path.home() / ".config" / "ptcgl-linux"


def cache_home() -> Path:
    root = os.environ.get("XDG_CACHE_HOME")
    if root:
        return Path(root) / "ptcgl-linux"

    return Path.home() / ".cache" / "ptcgl-linux"
