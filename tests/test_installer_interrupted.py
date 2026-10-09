import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ptcgl_linux.installer import (
    InstallError,
    PTCGL_INSTALLER_NAME,
    acquire_ptcgl_installer,
)


class InterruptedResponse:
    headers = {"Content-Length": "196512768"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        if not hasattr(self, "started"):
            self.started = True
            return bytes.fromhex("D0CF11E0A1B11AE1") + b"A" * 65536

        raise OSError("connection lost during download")


class InterruptedDownloadTests(unittest.TestCase):
    def test_interrupted_download_preserves_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            existing = cache / PTCGL_INSTALLER_NAME
            existing.write_bytes(b"previous installer")

            with patch(
                "ptcgl_linux.installer.urllib.request.build_opener"
            ) as opener:
                opener.return_value.open.return_value = InterruptedResponse()

                with self.assertRaises(InstallError):
                    acquire_ptcgl_installer(artifact_cache=cache)

            self.assertEqual(
                existing.read_bytes(),
                b"previous installer",
            )

            self.assertEqual(
                sorted(path.name for path in cache.iterdir()),
                [".pokemon-installer.lock", PTCGL_INSTALLER_NAME],
            )


if __name__ == "__main__":
    unittest.main()
