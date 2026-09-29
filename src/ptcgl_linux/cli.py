"""Command-line interface for ptcgl-linux."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .deeplink import CallbackError, handle_callback
from .diagnostics import print_doctor
from .installer import InstallError, install_ptcgl
from .launcher import LaunchError, launch_game


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

    if args.command == "doctor":
        return print_doctor()

    if args.command == "callback":
        try:
            return handle_callback(args.url)
        except CallbackError as exc:
            print(f"callback: {exc}", file=sys.stderr)
            return 2

    if args.command == "install":
        try:
            paths = install_ptcgl()
        except InstallError as exc:
            print(f"install: {exc}", file=sys.stderr)
            return 2

        print(f"install: ready: {paths.game}")
        return 0

    if args.command == "play":
        try:
            return launch_game()
        except LaunchError as exc:
            print(f"play: {exc}", file=sys.stderr)
            return 2

    print(f"{args.command}: not implemented yet")
    return 0
