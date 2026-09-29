"""Managed GE-Proton installation."""

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


PROTON_RELEASE = "GE-Proton11-7"
PROTON_DIRECTORY = "GE-Proton11-7-x86_64"
PROTON_ARCHIVE_NAME = f"{PROTON_DIRECTORY}.tar.gz"
PROTON_ARCHIVE_URL = (
    "https://github.com/GloriousEggroll/proton-ge-custom/"
    f"releases/download/{PROTON_RELEASE}/{PROTON_ARCHIVE_NAME}"
)
PROTON_ARCHIVE_SHA256 = (
    "c5448b76a230384e2d7bc6beb5ccb97b"
    "afb7e2c3b6c527cb03a1a546bbcb00a0"
)


def _validate_proton_tree(root: Path) -> None:
    required = (
        root / "proton",
        root / "toolmanifest.vdf",
        root / "compatibilitytool.vdf",
        root / "version",
        root / "files",
    )

    missing = [
        str(path.relative_to(root))
        for path in required
        if not path.exists()
    ]

    if missing:
        raise ArtifactError(
            "GE-Proton installation is incomplete; missing: "
            + ", ".join(missing)
        )

    if not (root / "proton").is_file():
        raise ArtifactError("GE-Proton proton launcher is not a file")

    if not (root / "files").is_dir():
        raise ArtifactError("GE-Proton files directory is invalid")

    try:
        version = (
            (root / "version")
            .read_text(encoding="utf-8")
            .strip()
        )
    except OSError as exc:
        raise ArtifactError(
            f"unable to read GE-Proton version file: {exc}"
        ) from exc

    if PROTON_RELEASE not in version:
        raise ArtifactError(
            f"unexpected GE-Proton version marker: {version!r}"
        )

    broken = [
        path
        for path in root.rglob("*")
        if path.is_symlink() and not path.exists()
    ]

    if broken:
        sample = ", ".join(
            str(path.relative_to(root))
            for path in broken[:5]
        )

        raise ArtifactError(
            "GE-Proton installation contains broken symlinks: "
            + sample
        )


def install_proton(
    *,
    app_data: Path | None = None,
    artifact_cache: Path | None = None,
    archive_url: str = PROTON_ARCHIVE_URL,
    expected_sha256: str = PROTON_ARCHIVE_SHA256,
    archive_name: str = PROTON_ARCHIVE_NAME,
    directory_name: str = PROTON_DIRECTORY,
) -> Path:
    """Install the pinned GE-Proton build atomically.

    Existing valid installations are reused. Existing invalid installations
    are not silently replaced.
    """

    if app_data is None:
        app_data = data_home()

    if artifact_cache is None:
        artifact_cache = cache_home() / "artifacts"

    proton_parent = app_data / "toolchain" / "proton"
    destination = proton_parent / directory_name

    if destination.exists():
        _validate_proton_tree(destination)
        return destination

    proton_parent.mkdir(parents=True, exist_ok=True)
    os.chmod(proton_parent, 0o700)

    artifact_cache.mkdir(parents=True, exist_ok=True)
    os.chmod(artifact_cache, 0o700)

    archive = artifact_cache / archive_name

    if archive.exists():
        if verify_sha256(archive, expected_sha256):
            os.chmod(archive, 0o600)
        else:
            archive.unlink()

    if not archive.exists():
        download_verified(
            archive_url,
            archive,
            expected_sha256,
        )

    staging = Path(
        tempfile.mkdtemp(
            prefix=".proton-staging-",
            dir=proton_parent,
        )
    )

    try:
        safe_extract_tar(
            archive,
            staging,
        )

        staged = staging / directory_name

        if not staged.is_dir():
            raise ArtifactError(
                "GE-Proton archive did not contain expected "
                f"top-level directory: {directory_name}"
            )

        _validate_proton_tree(staged)

        if destination.exists():
            raise ArtifactError(
                f"GE-Proton destination unexpectedly exists: "
                f"{destination}"
            )

        os.replace(
            staged,
            destination,
        )

        _validate_proton_tree(destination)

        return destination

    finally:
        shutil.rmtree(
            staging,
            ignore_errors=True,
        )
