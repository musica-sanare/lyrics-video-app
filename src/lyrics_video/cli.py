"""Command-line interface."""

import argparse
import sys
from pathlib import Path

from lyrics_video import __version__
from lyrics_video.captions import compare_fonts, make_captions
from lyrics_video.config import load_song
from lyrics_video.errors import LyricsVideoError
from lyrics_video.still import make_stills

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lyrics-video", description="Make lyrics videos, fully offline.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    captions = commands.add_parser(
        "captions",
        help="write one caption image per lyrics line",
        description="Write one PNG per non-empty line of the song's lyrics file, as the old lyrics image script did.",
    )
    captions.add_argument("song", type=Path, help="the song file (TOML)")
    captions.add_argument("--overwrite", action="store_true", help="replace existing images")

    compare = commands.add_parser(
        "compare",
        help="write the comparison text in many fonts",
        description=(
            "Write every line of the comparison text in every font, and contact_sheet.png with the first line in all "
            "fonts. Fonts given here replace the song file's compare.fonts and compare.font_dirs."
        ),
    )
    compare.add_argument("song", type=Path, help="the song file (TOML)")
    compare.add_argument("--font", type=Path, action="append", default=[], help="a font file (repeatable)")
    compare.add_argument(
        "--font-dir", type=Path, action="append", default=[], help="a folder whose fonts are all used (repeatable)"
    )
    compare.add_argument("--overwrite", action="store_true", help="replace existing images")

    still = commands.add_parser(
        "still",
        help="write frames of the video at chosen times",
        description=(
            "Write the frames the video will show at the given times, with the design's background, title, caption "
            "and credits and the spectrum on top, into stills/ next to the song file."
        ),
    )
    still.add_argument("song", type=Path, help="the song file (TOML)")
    still.add_argument("--time", type=float, nargs="+", required=True, metavar="SECONDS", help="times in the song")
    which = still.add_mutually_exclusive_group()
    which.add_argument(
        "--caption", type=int, metavar="LINE", help="the caption at this line index (0-based); by default the first"
    )
    which.add_argument("--no-caption", action="store_true", help="show no caption")
    still.add_argument(
        "--design",
        nargs="+",
        metavar="NAME",
        help="designs to draw instead of the song file's (built-in names or files); with several, also a comparison",
    )
    still.add_argument("--overwrite", action="store_true", help="replace existing images")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        song = load_song(args.song)
        if args.command == "captions":
            written = make_captions(song, overwrite=args.overwrite)
        elif args.command == "still":
            written = make_stills(
                song,
                args.time,
                args.caption,
                with_caption=not args.no_caption,
                overwrite=args.overwrite,
                designs=args.design,
            )
        else:
            fonts = [p.expanduser() for p in args.font]
            folders = [p.expanduser() for p in args.font_dir]
            written = compare_fonts(song, fonts, folders, overwrite=args.overwrite)
    except LyricsVideoError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_FAILED
    print(f"Wrote {len(written.files)} image(s) to {written.folder}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
