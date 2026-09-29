"""Managed UMU launcher installation."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from .artifacts import (
    ArtifactError,
    download_verified,
    safe_extract_tar,
    verify_sha256,
)
from .paths import cache_home, data_home


UMU_VERSION = "1.4.4"
UMU_ARCHIVE_NAME = f"umu-launcher-{UMU_VERSION}-zipapp.tar"
UMU_ARCHIVE_URL = (
    "https://github.com/Open-Wine-Components/umu-launcher/"
    f"releases/download/{UMU_VERSION}/{UMU_ARCHIVE_NAME}"
)
UMU_ARCHIVE_SHA256 = (
    "eb590691841f7fad3fc3ad8fd5db4ccb"
    "87849fe7948e62b28ece7a4ee48cc851"
)


def install_umu(
    *,
    app_data: Path | None = None,
    artifact_cache: Path | None = None,
    url: str = UMU_ARCHIVE_URL,
    expected_sha256: str = UMU_ARCHIVE_SHA256,
    archive_name: str = UMU_ARCHIVE_NAME,
) -> Path:
    if app_data is None:
        app_data = data_home()

    if artifact_cache is None:
        artifact_cache = cache_home() / "artifacts"

    toolchain = app_data / "toolchain"
    destination = toolchain / "umu"
    runner = destination / "umu-run"

    if runner.is_file():
        return runner

    toolchain.mkdir(parents=True, exist_ok=True)
    os.chmod(toolchain, 0o700)

    artifact_cache.mkdir(parents=True, exist_ok=True)
    os.chmod(artifact_cache, 0o700)

    archive = artifact_cache / archive_name

    if archive.exists() and not verify_sha256(archive, expected_sha256):
        archive.unlink()

    if not archive.exists():
        download_verified(
            url,
            archive,
            expected_sha256,
        )

    staging = Path(
        tempfile.mkdtemp(
            prefix=".umu-staging-",
            dir=toolchain,
        )
    )

    try:
        safe_extract_tar(archive, staging)

        staged = staging / "umu"
        staged_runner = staged / "umu-run"

        if not staged_runner.is_file():
            raise ArtifactError(
                "UMU archive did not contain umu/umu-run"
            )

        os.chmod(staged_runner, 0o755)

        if destination.exists():
            raise ArtifactError(
                f"UMU destination already exists without a valid runner: "
                f"{destination}"
            )

        os.replace(staged, destination)

        return runner

    finally:
        shutil.rmtree(staging, ignore_errors=True)
