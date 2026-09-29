"""Read-only runtime diagnostics."""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .runtime import (
    KNOWN_GOOD_PROTON,
    KNOWN_GOOD_UMU_VERSION,
    RuntimePaths,
    runtime_paths,
    vc_runtime_paths,
)


@dataclass(frozen=True)
class Check:
    status: str
    name: str
    detail: str


def _run(
    argv: list[str],
    *,
    timeout: float = 5.0,
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _umu_version(path: Path) -> str | None:
    if not path.is_file():
        return None

    result = _run([str(path), "--version"])

    if result is None or result.returncode != 0:
        return None

    output = (result.stdout + result.stderr).strip()

    marker = "umu-launcher version "
    if marker not in output:
        return None

    return output.split(marker, 1)[1].split()[0]


def _uri_handler() -> str | None:
    xdg_mime = shutil.which("xdg-mime")

    if not xdg_mime:
        return None

    result = _run(
        [
            xdg_mime,
            "query",
            "default",
            "x-scheme-handler/tpcitcgapp",
        ]
    )

    if result is None or result.returncode != 0:
        return None

    value = result.stdout.strip()
    return value or None


def collect_checks(paths: RuntimePaths | None = None) -> list[Check]:
    if paths is None:
        paths = runtime_paths()

    checks: list[Check] = []

    arch = platform.machine()
    checks.append(
        Check(
            "PASS" if arch == "x86_64" else "FAIL",
            "Architecture",
            arch,
        )
    )

    if paths.umu.is_file():
        version = _umu_version(paths.umu)

        if version == KNOWN_GOOD_UMU_VERSION:
            checks.append(Check("PASS", "UMU", f"{version} at {paths.umu}"))
        elif version:
            checks.append(
                Check(
                    "WARN",
                    "UMU",
                    f"{version} found; PoC baseline is {KNOWN_GOOD_UMU_VERSION}",
                )
            )
        else:
            checks.append(
                Check("WARN", "UMU", f"present but version unreadable: {paths.umu}")
            )
    else:
        checks.append(Check("FAIL", "UMU", f"not found: {paths.umu}"))

    manifest = paths.proton / "toolmanifest.vdf"
    if paths.proton.is_dir() and manifest.is_file():
        checks.append(
            Check(
                "PASS",
                "GE-Proton",
                f"{KNOWN_GOOD_PROTON} with toolmanifest.vdf",
            )
        )
    else:
        checks.append(
            Check(
                "FAIL",
                "GE-Proton",
                f"known-good runtime not found: {paths.proton}",
            )
        )

    if paths.steamrt4.is_dir():
        checks.append(Check("PASS", "steamrt4", str(paths.steamrt4)))
    else:
        checks.append(Check("FAIL", "steamrt4", f"not found: {paths.steamrt4}"))

    required_prefix_files = (
        paths.prefix / "drive_c",
        paths.prefix / "system.reg",
        paths.prefix / "user.reg",
        paths.prefix / "userdef.reg",
    )

    missing_prefix = [path.name for path in required_prefix_files if not path.exists()]

    if missing_prefix:
        checks.append(
            Check(
                "FAIL",
                "Prefix",
                "missing: " + ", ".join(missing_prefix),
            )
        )
    else:
        checks.append(Check("PASS", "Prefix", str(paths.prefix)))

    missing_vc = [path.name for path in vc_runtime_paths(paths) if not path.is_file()]

    if missing_vc:
        checks.append(
            Check(
                "FAIL",
                "VC++ runtime",
                "missing: " + ", ".join(missing_vc),
            )
        )
    else:
        checks.append(Check("PASS", "VC++ runtime", "vcrun2019 DLL set present"))

    if paths.game.is_file():
        checks.append(Check("PASS", "Game", str(paths.game)))
    else:
        checks.append(Check("FAIL", "Game", f"not found: {paths.game}"))

    handler = _uri_handler()

    if handler == "ptcgl-deeplink.desktop":
        checks.append(Check("PASS", "URI handler", handler))
    elif handler:
        checks.append(
            Check(
                "WARN",
                "URI handler",
                f"tpcitcgapp is handled by {handler}",
            )
        )
    else:
        checks.append(
            Check(
                "FAIL",
                "URI handler",
                "no handler registered for tpcitcgapp",
            )
        )

    vulkaninfo = shutil.which("vulkaninfo")

    if vulkaninfo:
        result = _run([vulkaninfo, "--summary"], timeout=10.0)

        if result is not None and result.returncode == 0:
            checks.append(Check("PASS", "Vulkan", "vulkaninfo --summary succeeded"))
        else:
            checks.append(Check("WARN", "Vulkan", "vulkaninfo returned an error"))
    else:
        checks.append(
            Check(
                "WARN",
                "Vulkan",
                "vulkaninfo not installed; Vulkan was not independently checked",
            )
        )

    return checks


def print_doctor(paths: RuntimePaths | None = None) -> int:
    checks = collect_checks(paths)

    print("ptcgl-linux doctor")
    print()

    for check in checks:
        print(f"[{check.status:<4}] {check.name:<14} {check.detail}")

    failures = sum(check.status == "FAIL" for check in checks)
    warnings = sum(check.status == "WARN" for check in checks)

    print()
    print(f"Result: {failures} failure(s), {warnings} warning(s)")

    return 1 if failures else 0
