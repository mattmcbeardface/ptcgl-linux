import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from ptcgl_linux.artifacts import ArtifactError, sha256_file
from ptcgl_linux.proton import (
    PROTON_DIRECTORY,
    PROTON_RELEASE,
    install_proton,
)


def make_proton_archive(path: Path) -> None:
    with tarfile.open(path, "w:gz") as tar:
        directories = (
            PROTON_DIRECTORY,
            f"{PROTON_DIRECTORY}/files",
            f"{PROTON_DIRECTORY}/files/lib",
        )

        for name in directories:
            member = tarfile.TarInfo(name)
            member.type = tarfile.DIRTYPE
            member.mode = 0o755
            tar.addfile(member)

        files = {
            f"{PROTON_DIRECTORY}/proton":
                b"#!/usr/bin/env python3\n",
            f"{PROTON_DIRECTORY}/toolmanifest.vdf":
                b'"manifest"\n',
            f"{PROTON_DIRECTORY}/compatibilitytool.vdf":
                b'"compatibilitytools"\n',
            f"{PROTON_DIRECTORY}/version":
                f"1234567890 {PROTON_RELEASE}\n".encode(),
            f"{PROTON_DIRECTORY}/files/lib/library.so.1":
                b"library",
        }

        for name, payload in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            member.mode = (
                0o755
                if name.endswith("/proton")
                else 0o644
            )
            tar.addfile(
                member,
                io.BytesIO(payload),
            )

        link = tarfile.TarInfo(
            f"{PROTON_DIRECTORY}/files/lib/library.so"
        )
        link.type = tarfile.SYMTYPE
        link.linkname = "library.so.1"
        tar.addfile(link)


class ProtonTests(unittest.TestCase):
    def test_install_from_local_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.tar.gz"

            make_proton_archive(source)

            expected = sha256_file(source)

            installed = install_proton(
                app_data=root / "data",
                artifact_cache=root / "cache",
                archive_url=source.as_uri(),
                expected_sha256=expected,
                archive_name="test-proton.tar.gz",
            )

            self.assertEqual(
                installed.name,
                PROTON_DIRECTORY,
            )

            self.assertTrue(
                (installed / "proton").is_file()
            )

            self.assertIn(
                PROTON_RELEASE,
                (installed / "version").read_text(),
            )

            alias = (
                installed
                / "files"
                / "lib"
                / "library.so"
            )

            self.assertTrue(alias.is_symlink())
            self.assertTrue(alias.resolve().is_file())

    def test_valid_existing_install_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.tar.gz"

            make_proton_archive(source)

            expected = sha256_file(source)

            first = install_proton(
                app_data=root / "data",
                artifact_cache=root / "cache",
                archive_url=source.as_uri(),
                expected_sha256=expected,
                archive_name="test-proton.tar.gz",
            )

            marker = first / "reuse-marker"
            marker.write_text("preserved")

            second = install_proton(
                app_data=root / "data",
                artifact_cache=root / "cache",
                archive_url=source.as_uri(),
                expected_sha256=expected,
                archive_name="test-proton.tar.gz",
            )

            self.assertEqual(first, second)
            self.assertEqual(
                marker.read_text(),
                "preserved",
            )

    def test_invalid_existing_install_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = (
                root
                / "data"
                / "toolchain"
                / "proton"
                / PROTON_DIRECTORY
            )

            destination.mkdir(
                parents=True,
            )

            marker = destination / "keep-me"
            marker.write_text("existing")

            with self.assertRaises(ArtifactError):
                install_proton(
                    app_data=root / "data",
                    artifact_cache=root / "cache",
                )

            self.assertEqual(
                marker.read_text(),
                "existing",
            )


if __name__ == "__main__":
    unittest.main()
