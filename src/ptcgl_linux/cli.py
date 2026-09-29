"""Command-line interface for ptcgl-linux."""

from __future__ import annotations

import argparse

from . import __version__


COMMANDS = (
    "install",
    "play",
    "repair",
    "doctor",
    "uninstall",
    "callback",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ptcgl-linux",
        description="Linux launcher and compatibility environment for Pokémon TCG Live",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    for command in COMMANDS:
        subparser = subparsers.add_parser(command)

        if command == "callback":
            subparser.add_argument("url")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    print(f"{args.command}: not implemented yet")
    return 0
