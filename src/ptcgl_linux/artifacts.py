"""Verified artifact download and extraction helpers."""

from __future__ import annotations

import hashlib
import os
import posixpath
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath


CHUNK_SIZE = 1024 * 1024


class ArtifactError(RuntimeError):
    """Raised when an artifact cannot be safely acquired or unpacked."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)

    return digest.hexdigest()


def verify_sha256(path: Path, expected: str) -> bool:
    return sha256_file(path).lower() == expected.lower()


def download_verified(
    url: str,
    destination: Path,
    expected_sha256: str,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(destination.parent, 0o700)

    temp_name: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp:
            temp_name = temp.name

            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    while chunk := response.read(CHUNK_SIZE):
                        temp.write(chunk)
            except (OSError, urllib.error.URLError) as exc:
                raise ArtifactError(
                    f"unable to download artifact from {url}: {exc}"
                ) from exc

            temp.flush()
            os.fsync(temp.fileno())

        temp_path = Path(temp_name)

        if not verify_sha256(temp_path, expected_sha256):
            actual = sha256_file(temp_path)
            raise ArtifactError(
                "artifact SHA-256 mismatch: "
                f"expected {expected_sha256}, got {actual}"
            )

        os.chmod(temp_path, 0o600)
        os.replace(temp_path, destination)
        os.chmod(destination, 0o600)

        return destination

    finally:
        if temp_name is not None:
            temp_path = Path(temp_name)

            if temp_path.exists():
                temp_path.unlink()


def _safe_member_name(name: str) -> str:
    if not name:
        raise ArtifactError("archive contains an empty path")

    path = PurePosixPath(name)

    if path.is_absolute() or ".." in path.parts:
        raise ArtifactError(f"unsafe path in archive: {name}")

    normalized = posixpath.normpath(name)

    if normalized in ("", ".", "..") or normalized.startswith("../"):
        raise ArtifactError(f"unsafe path in archive: {name}")

    return normalized


def _safe_link_target(
    member_name: str,
    link_name: str,
) -> str:
    link_path = PurePosixPath(link_name)

    if link_path.is_absolute():
        raise ArtifactError(
            f"absolute symlink target in archive: "
            f"{member_name} -> {link_name}"
        )

    parent = posixpath.dirname(member_name)
    target = posixpath.normpath(
        posixpath.join(parent, link_name)
    )

    if target in ("", ".", "..") or target.startswith("../"):
        raise ArtifactError(
            f"symlink escapes extraction root: "
            f"{member_name} -> {link_name}"
        )

    return target


def safe_extract_tar(
    archive: Path,
    destination: Path,
) -> None:
    """Extract a restricted tar archive without trusting tar.extract().

    Allowed archive entries:
    - directories
    - regular files
    - relative symbolic links whose target remains inside the archive and
      resolves to a regular file or directory

    Hard links and all device/special entry types are rejected.
    """

    destination.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(archive, "r:*") as tar:
            members = tar.getmembers()

            member_map: dict[str, tarfile.TarInfo] = {}

            for member in members:
                name = _safe_member_name(member.name)

                if name in member_map:
                    raise ArtifactError(
                        f"duplicate archive path: {name}"
                    )

                if not (
                    member.isdir()
                    or member.isfile()
                    or member.issym()
                ):
                    raise ArtifactError(
                        f"unsupported archive entry: {member.name}"
                    )

                member_map[name] = member

            symlink_names = {
                name
                for name, member in member_map.items()
                if member.issym()
            }

            # No regular file or directory may be nested beneath a symlink.
            for name, member in member_map.items():
                if member.issym():
                    continue

                parents = PurePosixPath(name).parents

                for parent in parents:
                    parent_name = str(parent)

                    if (
                        parent_name != "."
                        and parent_name in symlink_names
                    ):
                        raise ArtifactError(
                            f"archive member is nested beneath symlink: "
                            f"{name}"
                        )

            # Validate all links before creating anything.
            for name, member in member_map.items():
                if not member.issym():
                    continue

                target_name = _safe_link_target(
                    name,
                    member.linkname,
                )

                target = member_map.get(target_name)

                if target is None:
                    raise ArtifactError(
                        f"symlink target is not present in archive: "
                        f"{name} -> {member.linkname}"
                    )

                if not (target.isfile() or target.isdir()):
                    raise ArtifactError(
                        f"symlink target is not a regular archive entry: "
                        f"{name} -> {member.linkname}"
                    )

            # Directories first.
            directories = [
                (name, member)
                for name, member in member_map.items()
                if member.isdir()
            ]

            directories.sort(
                key=lambda item: len(PurePosixPath(item[0]).parts)
            )

            for name, member in directories:
                target = destination / Path(name)
                target.mkdir(parents=True, exist_ok=True)
                os.chmod(target, member.mode & 0o777)

            # Regular files second.
            files = [
                (name, member)
                for name, member in member_map.items()
                if member.isfile()
            ]

            for name, member in files:
                target = destination / Path(name)
                target.parent.mkdir(parents=True, exist_ok=True)

                source = tar.extractfile(member)

                if source is None:
                    raise ArtifactError(
                        f"unable to read archive member: {name}"
                    )

                try:
                    with target.open("xb") as output:
                        shutil.copyfileobj(
                            source,
                            output,
                            length=CHUNK_SIZE,
                        )
                finally:
                    source.close()

                os.chmod(target, member.mode & 0o777)

            # Symlinks last, after their validated targets exist.
            links = [
                (name, member)
                for name, member in member_map.items()
                if member.issym()
            ]

            for name, member in links:
                target = destination / Path(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(member.linkname, target)

    except ArtifactError:
        raise
    except (OSError, tarfile.TarError) as exc:
        raise ArtifactError(
            f"unable to extract archive {archive}: {exc}"
        ) from exc
