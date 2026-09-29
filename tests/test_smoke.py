import unittest
from unittest.mock import patch

from ptcgl_linux.cli import build_parser, main
from ptcgl_linux.paths import data_home


class SmokeTests(unittest.TestCase):
    def test_cli_parser_builds(self) -> None:
        parser = build_parser()
        self.assertEqual(parser.prog, "ptcgl-linux")

    def test_no_command_launches_desktop_app(self) -> None:
        with patch("ptcgl_linux.desktop.run_desktop_app", return_value=0) as run_app:
            self.assertEqual(main([]), 0)
            run_app.assert_called_once_with()

    def test_data_path_name(self) -> None:
        self.assertEqual(data_home().name, "ptcgl-linux")


if __name__ == "__main__":
    unittest.main()
