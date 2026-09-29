import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ptcgl_linux.installer import (
    InstallError,
    bootstrap_runtime,
    initialize_prefix,
    install_vcrun2019,
)
from ptcgl_linux.runtime import RuntimePaths, vc_runtime_paths


def make_paths(root: Path) -> RuntimePaths:
    data = root / "data"
    prefix = data / "prefix"
    proton = data / "toolchain" / "proton" / "GE-Proton11-7-x86_64"

    return RuntimePaths(
        data_dir=data,
        prefix=prefix,
        umu=root / "umu-run",
        proton=proton,
        steamrt4=root / "steamrt4",
        game=prefix / "game.exe",
    )


def create_prefix(paths: RuntimePaths) -> None:
    (paths.prefix / "drive_c").mkdir(parents=True, exist_ok=True)

    for name in ("system.reg", "user.reg", "userdef.reg"):
        (paths.prefix / name).write_text("", encoding="utf-8")


class InstallerTests(unittest.TestCase):
    def test_initialize_prefix_uses_umu(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_paths(Path(tmp))
            paths.umu.write_text("", encoding="utf-8")
            paths.proton.mkdir(parents=True)

            def fake_run(argv, **kwargs):
                self.assertEqual(argv, [str(paths.umu), ""])
                self.assertEqual(
                    kwargs["env"]["WINEPREFIX"],
                    str(paths.prefix),
                )
                self.assertEqual(
                    kwargs["env"]["PROTONPATH"],
                    str(paths.proton),
                )

                create_prefix(paths)
                return Mock(returncode=1)

            with patch(
                "ptcgl_linux.installer.subprocess.run",
                side_effect=fake_run,
            ):
                initialize_prefix(paths)

    def test_initialize_prefix_rejects_incomplete_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_paths(Path(tmp))

            with patch(
                "ptcgl_linux.installer.subprocess.run",
                return_value=Mock(returncode=1),
            ):
                with self.assertRaises(InstallError):
                    initialize_prefix(paths)

    def test_vcrun2019_installation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_paths(Path(tmp))
            create_prefix(paths)

            def fake_run(argv, **kwargs):
                self.assertEqual(
                    argv,
                    [
                        str(paths.umu),
                        "winetricks",
                        "-q",
                        "vcrun2019",
                    ],
                )

                for dll in vc_runtime_paths(paths):
                    dll.parent.mkdir(parents=True, exist_ok=True)
                    dll.write_text("", encoding="utf-8")

                return Mock(returncode=0)

            with patch(
                "ptcgl_linux.installer.subprocess.run",
                side_effect=fake_run,
            ):
                install_vcrun2019(paths)

    def test_bootstrap_is_idempotent_when_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_paths(Path(tmp))

            paths.umu.write_text("", encoding="utf-8")
            paths.proton.mkdir(parents=True)
            create_prefix(paths)

            for dll in vc_runtime_paths(paths):
                dll.parent.mkdir(parents=True, exist_ok=True)
                dll.write_text("", encoding="utf-8")

            with (
                patch(
                    "ptcgl_linux.installer.install_umu"
                ) as install_umu_mock,
                patch(
                    "ptcgl_linux.installer.install_proton",
                    return_value=paths.proton,
                ),
                patch(
                    "ptcgl_linux.installer.subprocess.run"
                ) as run_mock,
            ):
                result = bootstrap_runtime(paths=paths)

            self.assertEqual(result, paths)
            install_umu_mock.assert_not_called()
            run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
