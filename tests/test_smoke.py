import unittest

from ptcgl_linux.cli import build_parser
from ptcgl_linux.paths import data_home


class SmokeTests(unittest.TestCase):
    def test_cli_parser_builds(self) -> None:
        parser = build_parser()
        self.assertEqual(parser.prog, "ptcgl-linux")

    def test_data_path_name(self) -> None:
        self.assertEqual(data_home().name, "ptcgl-linux")


if __name__ == "__main__":
    unittest.main()
