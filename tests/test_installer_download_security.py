import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ptcgl_linux.installer import (
    InstallError,
    PTCGL_INSTALLER_NAME,
    acquire_ptcgl_installer,
)


MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.offset = 0
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        chunk = self.payload[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


class InstallerDownloadSecurityTests(unittest.TestCase):
    def check_rejected(self, payload, *, signature_valid=False):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            existing = cache / PTCGL_INSTALLER_NAME
            existing.write_bytes(b"previous installer")

            with (
                patch(
                    "ptcgl_linux.installer.urllib.request.build_opener"
                ) as opener,
                patch(
                    "ptcgl_linux.installer.verify_pokemon_installer"
                ) as verify,
            ):
                opener.return_value.open.return_value = (
                    FakeResponse(payload)
                )

                if not signature_valid:
                    from ptcgl_linux.installer_security import SignatureError
                    verify.side_effect = SignatureError(
                        "invalid signature"
                    )

                with self.assertRaises(InstallError):
                    acquire_ptcgl_installer(artifact_cache=cache)

            self.assertEqual(
                existing.read_bytes(),
                b"previous installer",
            )
            self.assertEqual(
                sorted(p.name for p in cache.iterdir()),
                [".pokemon-installer.lock", PTCGL_INSTALLER_NAME],
            )

    def test_invalid_msi_header(self):
        self.check_rejected(b"X" * 65544)

    def test_invalid_signature(self):
        self.check_rejected(MAGIC + b"A" * 65536)

    def test_oversized_download(self):
        with patch(
            "ptcgl_linux.installer.PTCGL_INSTALLER_MAX_BYTES",
            65536,
        ):
            self.check_rejected(
                MAGIC + b"A" * 65536,
                signature_valid=True,
            )

    def test_truncated_download_preserves_cache(self):
        payload = MAGIC + b"A" * 65536

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            existing = cache / PTCGL_INSTALLER_NAME
            existing.write_bytes(b"previous installer")

            response = FakeResponse(payload)
            response.headers = {
                "Content-Length": str(len(payload) + 100000)
            }

            with (
                patch(
                    "ptcgl_linux.installer.urllib.request.build_opener"
                ) as opener,
                patch(
                    "ptcgl_linux.installer.verify_pokemon_installer"
                ) as verify,
            ):
                opener.return_value.open.return_value = response

                with self.assertRaisesRegex(
                    InstallError, "download is incomplete"
                ):
                    acquire_ptcgl_installer(artifact_cache=cache)

                verify.assert_not_called()

            self.assertEqual(
                existing.read_bytes(),
                b"previous installer",
            )
            self.assertEqual(
                sorted(path.name for path in cache.iterdir()),
                [".pokemon-installer.lock", PTCGL_INSTALLER_NAME],
            )

    def test_redirect_is_rejected(self):
        from ptcgl_linux.installer import _RejectRedirects

        handler = _RejectRedirects()

        with self.assertRaises(InstallError):
            handler.redirect_request(
                None,
                None,
                302,
                "Found",
                {},
                "https://untrusted.example/installer.msi",
            )


if __name__ == "__main__":
    unittest.main()
