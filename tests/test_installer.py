import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ptcgl_linux.installer import (
    InstallError,
    bootstrap_runtime,
    initialize_prefix,
    install_game,
    install_ptcgl,
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

    def test_install_game_runs_msi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = make_paths(root)
            create_prefix(paths)

            msiexec = (
                paths.prefix
                / "drive_c"
                / "windows"
                / "system32"
                / "msiexec.exe"
            )
            msiexec.parent.mkdir(parents=True, exist_ok=True)
            msiexec.write_text("", encoding="utf-8")

            installer = root / "PokemonTCGLiveInstaller.msi"
            installer.write_text("test installer", encoding="utf-8")

            def fake_run(argv, **kwargs):
                self.assertEqual(argv[0], str(paths.umu))
                self.assertEqual(argv[1], str(msiexec))
                self.assertEqual(argv[2], "/i")
                self.assertTrue(argv[3].startswith("Z:\\"))
                self.assertEqual(argv[4:], ["/quiet", "/norestart"])

                paths.game.parent.mkdir(parents=True, exist_ok=True)
                paths.game.write_text("", encoding="utf-8")

                return Mock(returncode=0)

            with (
                patch(
                    "ptcgl_linux.installer.acquire_ptcgl_installer",
                    return_value=installer,
                ),
                patch(
                    "ptcgl_linux.installer.subprocess.run",
                    side_effect=fake_run,
                ),
            ):
                result = install_game(paths)

            self.assertEqual(result, paths.game)

    def test_install_game_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_paths(Path(tmp))
            paths.game.parent.mkdir(parents=True, exist_ok=True)
            paths.game.write_text("", encoding="utf-8")

            with (
                patch(
                    "ptcgl_linux.installer.acquire_ptcgl_installer"
                ) as acquire_mock,
                patch(
                    "ptcgl_linux.installer.subprocess.run"
                ) as run_mock,
            ):
                result = install_game(paths)

            self.assertEqual(result, paths.game)
            acquire_mock.assert_not_called()
            run_mock.assert_not_called()

    def test_install_ptcgl_runs_bootstrap_then_game(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_paths(Path(tmp))

            with (
                patch(
                    "ptcgl_linux.installer.bootstrap_runtime",
                    return_value=paths,
                ) as bootstrap_mock,
                patch(
                    "ptcgl_linux.installer.install_game",
                    return_value=paths.game,
                ) as game_mock,
            ):
                result = install_ptcgl(paths=paths)

            self.assertEqual(result, paths)
            bootstrap_mock.assert_called_once_with(paths=paths)
            game_mock.assert_called_once_with(
                paths,
                artifact_cache=None,
            )


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
