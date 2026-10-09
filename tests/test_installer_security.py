import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ptcgl_linux.installer_security import (
    SignatureError,
    verify_pokemon_installer,
)
from ptcgl_linux.installer import (
    InstallError,
    acquire_ptcgl_installer,
)


class InstallerSecurityTests(unittest.TestCase):
    def test_missing_verifier_is_rejected(self):
        with patch(
            "ptcgl_linux.installer_security.shutil.which",
            return_value=None,
        ):
            with self.assertRaises(SignatureError):
                verify_pokemon_installer(Path("/tmp/example.msi"))

    def test_failed_signature_is_rejected(self):
        with (
            patch(
                "ptcgl_linux.installer_security.shutil.which",
                return_value="/app/bin/osslsigncode",
            ),
            patch(
                "ptcgl_linux.installer_security.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    args=[],
                    returncode=1,
                    stdout="Signature verification: failed\nFailed",
                    stderr="",
                ),
            ),
        ):
            with self.assertRaises(SignatureError):
                verify_pokemon_installer(Path("/tmp/example.msi"))

    def test_wrong_publisher_is_rejected(self):
        output = (
            "Signer's certificate:\n"
            "\t------------------\n"
            "\tSigner #0:\n"
            "\t\tSubject: CN=Other Company,O=Other Company,C=US\n"
            "Timestamp Server Signature CRL verification: ok\n"
            "Timestamp Server Signature verification: ok\n"
            "Signature CRL verification: ok\n"
            "Signature verification: ok\n"
            "Number of verified signatures: 1\n"
            "Succeeded\n"
        )

        with (
            patch(
                "ptcgl_linux.installer_security.shutil.which",
                return_value="/app/bin/osslsigncode",
            ),
            patch(
                "ptcgl_linux.installer_security.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout=output,
                    stderr="",
                ),
            ),
        ):
            with self.assertRaises(SignatureError):
                verify_pokemon_installer(Path("/tmp/example.msi"))

    def test_download_failure_preserves_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            existing = cache / "PokemonTCGLiveInstaller.msi"
            existing.write_bytes(b"previously validated installer")

            with patch(
                "ptcgl_linux.installer.urllib.request.build_opener"
            ) as opener:
                opener.return_value.open.side_effect = OSError(
                    "network unavailable"
                )

                with self.assertRaises(InstallError):
                    acquire_ptcgl_installer(artifact_cache=cache)

            self.assertEqual(
                existing.read_bytes(),
                b"previously validated installer",
            )

            self.assertEqual(
                sorted(p.name for p in cache.iterdir()),
                [".pokemon-installer.lock", "PokemonTCGLiveInstaller.msi"],
            )


if __name__ == "__main__":
    unittest.main()
