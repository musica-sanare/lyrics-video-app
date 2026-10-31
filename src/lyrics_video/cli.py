"""Command-line interface."""

import argparse
import sys

from lyrics_video import __version__

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lyrics-video", description="Make lyrics videos, fully offline.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
