import hashlib
import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from ptcgl_linux.artifacts import (
    ArtifactError,
    download_verified,
    safe_extract_tar,
    sha256_file,
    verify_sha256,
)
from ptcgl_linux.umu import install_umu


def add_umu_archive_members(
    tar: tarfile.TarFile,
    runner_data: bytes,
) -> None:
    directory = tarfile.TarInfo("umu")
    directory.type = tarfile.DIRTYPE
    directory.mode = 0o755
    tar.addfile(directory)

    runner = tarfile.TarInfo("umu/umu-run")
    runner.size = len(runner_data)
    runner.mode = 0o744
    tar.addfile(runner, io.BytesIO(runner_data))

    alias = tarfile.TarInfo("umu/umu_run.py")
    alias.type = tarfile.SYMTYPE
    alias.linkname = "umu-run"
    alias.mode = 0o777
    tar.addfile(alias)


class ArtifactTests(unittest.TestCase):
    def test_sha256_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload"
            path.write_bytes(b"ptcgl-linux")

            expected = hashlib.sha256(
                b"ptcgl-linux"
            ).hexdigest()

            self.assertEqual(sha256_file(path), expected)
            self.assertTrue(verify_sha256(path, expected))
            self.assertFalse(
                verify_sha256(path, "0" * 64)
            )

    def test_verified_local_download(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.bin"
            destination = root / "downloads" / "artifact.bin"

            payload = b"verified payload"
            source.write_bytes(payload)

            expected = hashlib.sha256(payload).hexdigest()

            download_verified(
                source.as_uri(),
                destination,
                expected,
            )

            self.assertEqual(
                destination.read_bytes(),
                payload,
            )

    def test_hash_mismatch_does_not_publish_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.bin"
            destination = root / "downloads" / "artifact.bin"

            source.write_bytes(b"bad payload")

            with self.assertRaises(ArtifactError):
                download_verified(
                    source.as_uri(),
                    destination,
                    "0" * 64,
                )

            self.assertFalse(destination.exists())

    def test_tar_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "bad.tar"

            with tarfile.open(archive, "w") as tar:
                data = b"unsafe"
                info = tarfile.TarInfo("../escape")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

            with self.assertRaises(ArtifactError):
                safe_extract_tar(
                    archive,
                    root / "extract",
                )

    def test_safe_relative_symlink_is_extracted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "good.tar"
            destination = root / "extract"

            with tarfile.open(archive, "w") as tar:
                add_umu_archive_members(
                    tar,
                    b"#!/bin/sh\nexit 0\n",
                )

            safe_extract_tar(
                archive,
                destination,
            )

            alias = destination / "umu" / "umu_run.py"

            self.assertTrue(alias.is_symlink())
            self.assertEqual(
                os.readlink(alias),
                "umu-run",
            )
            self.assertTrue(alias.resolve().is_file())

    def test_unsafe_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "bad-link.tar"

            with tarfile.open(archive, "w") as tar:
                directory = tarfile.TarInfo("umu")
                directory.type = tarfile.DIRTYPE
                directory.mode = 0o755
                tar.addfile(directory)

                alias = tarfile.TarInfo("umu/escape")
                alias.type = tarfile.SYMTYPE
                alias.linkname = "../../outside"
                tar.addfile(alias)

            with self.assertRaises(ArtifactError):
                safe_extract_tar(
                    archive,
                    root / "extract",
                )

    def test_umu_install_from_local_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "umu-test.tar"

            runner_data = b"#!/bin/sh\nexit 0\n"

            with tarfile.open(archive, "w") as tar:
                add_umu_archive_members(
                    tar,
                    runner_data,
                )

            expected = sha256_file(archive)

            installed = install_umu(
                app_data=root / "data",
                artifact_cache=root / "cache",
                url=archive.as_uri(),
                expected_sha256=expected,
                archive_name="umu-test.tar",
            )

            self.assertTrue(installed.is_file())
            self.assertTrue(installed.stat().st_mode & 0o100)

            alias = installed.parent / "umu_run.py"

            self.assertTrue(alias.is_symlink())
            self.assertEqual(
                os.readlink(alias),
                "umu-run",
            )


if __name__ == "__main__":
    unittest.main()
