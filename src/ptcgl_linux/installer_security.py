"""Verify the authenticity of Pokémon TCG Live installers."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


class SignatureError(RuntimeError):
    """Installer authenticity could not be established."""


EXPECTED_PUBLISHER = r"The Pokemon Company International\, Inc."


def verify_pokemon_installer(path: Path) -> None:
    """Require a trusted Authenticode signature from Pokémon's publisher."""

    verifier = shutil.which("osslsigncode")

    if verifier is None:
        raise SignatureError(
            "osslsigncode is unavailable; cannot authenticate installer"
        )

    try:
        result = subprocess.run(
            [verifier, "verify", "-in", str(path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SignatureError(
            "installer signature verification could not complete"
        ) from exc

    output = result.stdout + "\n" + result.stderr

    if result.returncode != 0:
        raise SignatureError(
            "installer signature or certificate validation failed"
        )

    required = (
        "Signature verification: ok",
        "Signature CRL verification: ok",
        "Timestamp Server Signature verification: ok",
        "Timestamp Server Signature CRL verification: ok",
        "Number of verified signatures: 1",
        "Succeeded",
    )

    if not all(item in output for item in required):
        raise SignatureError(
            "installer verification did not confirm all security checks"
        )

    # Read the primary signer's certificate, not the chain certificates
    # or the timestamp authority's certificate.
    match = re.search(
        r"^Signer's certificate:\s*\n"
        r"\s*-+\s*\n"
        r"\s*Signer #0:\s*\n"
        r"\s*Subject:\s*(.+)$",
        output,
        re.MULTILINE,
    )

    if match is None:
        raise SignatureError("installer signer identity is unavailable")

    subject = match.group(1).strip()

    # Certificate DN commas may be escaped. Match complete CN/O fields,
    # not arbitrary text elsewhere in the verification output.
    fields = re.split(r"(?<!\\),", subject)
    fields = [field.strip() for field in fields]

    expected_cn = "CN=" + EXPECTED_PUBLISHER
    expected_org = "O=" + EXPECTED_PUBLISHER

    if expected_cn not in fields or expected_org not in fields:
        raise SignatureError(
            "installer is not signed by the expected Pokémon publisher"
        )
