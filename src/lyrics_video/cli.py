"""Command-line interface."""

import argparse
import signal
import sys
import time
from pathlib import Path
from typing import TextIO

from audio_spectrum import RenderResult

from lyrics_video import __version__
from lyrics_video.app_bundle import APPLICATIONS, install_app
from lyrics_video.config import Song, load_song
from lyrics_video.errors import LyricsVideoError
from lyrics_video.render import DEFAULT_CRF, PreparedRender, prepare_render, render
from lyrics_video.still import make_stills
from lyrics_video.web.server import run as run_sync
from lyrics_video.web.server import start as start_app

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130
# A terminal's progress line is redrawn at most this often.
PROGRESS_INTERVAL = 0.25


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lyrics-video", description="Make lyrics videos, fully offline.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    still = commands.add_parser(
        "still",
        help="write frames of the video at chosen times",
        description=(
            "Write the frames the video will show at the given times, with the design's background, title, caption "
            "and credits and the spectrum on top, into stills/ next to the song file. With the song file's timing, "
            "each still shows the caption of its moment."
        ),
    )
    still.add_argument("song", type=Path, help="the song file (TOML)")
    still.add_argument("--time", type=float, nargs="+", required=True, metavar="SECONDS", help="times in the song")
    which = still.add_mutually_exclusive_group()
    which.add_argument(
        "--caption",
        type=int,
        metavar="LINE",
        help=(
            "show the caption at this line index (0-based) at every time; by default the captions of each moment from "
            "the song's timing, or the first caption without timing"
        ),
    )
    which.add_argument("--no-caption", action="store_true", help="show no caption")
    still.add_argument(
        "--design",
        nargs="+",
        metavar="NAME",
        help=(
            "designs to draw instead of the song file's (built-in or saved names, or files); with several, also a "
            "comparison"
        ),
    )
    still.add_argument("--overwrite", action="store_true", help="replace existing images")

    render_parser = commands.add_parser(
        "render",
        help="render the whole lyrics video",
        description=(
            "Render the lyrics video with the song's audio: the design's background, title, captions by the song's "
            "timing and credits, with the spectrum on top. By default it is written to videos/<song file name>.mp4 "
            "next to the song file."
        ),
    )
    render_parser.add_argument("song", type=Path, help="the song file (TOML)")
    render_parser.add_argument("-o", "--output", type=Path, help="the video file (.mp4 for h264, .mov for prores)")
    render_parser.add_argument("--overwrite", action="store_true", help="replace an existing video")
    render_parser.add_argument(
        "--start", type=_non_negative, default=0.0, metavar="SECONDS", help="render only part of the song, from here"
    )
    render_parser.add_argument("--duration", type=_positive, metavar="SECONDS", help="the length of that part")
    render_parser.add_argument("--design", metavar="NAME", help="another design (a built-in or saved name, or a file)")
    render_parser.add_argument(
        "--workers", type=_non_negative_int, default=0, help="render processes; 0 picks them automatically"
    )
    render_parser.add_argument(
        "--codec", choices=["h264", "prores"], default="h264", help="h264 (.mp4) or prores (.mov)"
    )
    render_parser.add_argument(
        "--crf", type=_crf, default=DEFAULT_CRF, help=f"H.264 quality from 0 to 51, lower is better ({DEFAULT_CRF})"
    )

    sync = commands.add_parser(
        "sync",
        help="time the captions in the browser",
        description=(
            "Open a page in the browser to tap the start and end of each caption while the song plays, adjust the "
            "times and save them to the timing file (the song file's timing, or the lyrics file's name with .lrc)."
        ),
    )
    sync.add_argument("song", type=Path, help="the song file (TOML)")
    sync.add_argument("--port", type=int, default=0, help="the port on 127.0.0.1; by default a free one")
    sync.add_argument("--no-browser", action="store_true", help="do not open the browser")

    start = commands.add_parser(
        "start",
        help="open the app in the browser, without a song",
        description=(
            "Open the app's start page in the browser: recent songs and Open song. If the app is already running, "
            "open its page instead of starting another. The app stops itself 10 minutes after its last page closed, "
            "or with Quit on the page."
        ),
    )
    start.add_argument("--port", type=int, default=0, help="the port on 127.0.0.1; by default a free one")
    start.add_argument("--no-browser", action="store_true", help="do not open the browser")

    install = commands.add_parser(
        "install-app",
        help="make Lyrics Video.app, to start the app from the Dock",
        description=(
            "Write a small app, Lyrics Video.app, that runs `lyrics-video start` from this repository. Drag it to the "
            "Dock once; clicking it opens the app's page. Run it again after moving the repository."
        ),
    )
    install.add_argument(
        "--to", type=Path, default=APPLICATIONS, metavar="FOLDER", help="where to put it (~/Applications)"
    )
    install.add_argument("--overwrite", action="store_true", help="replace an app made by this command")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "start":
        start_app(port=args.port, open_browser=not args.no_browser)
        return EXIT_OK
    if args.command == "install-app":
        return run_install(args.to, args.overwrite)
    try:
        song = load_song(args.song)
        if args.command == "render":
            return run_render(song, args)
        if args.command == "sync":
            run_sync(song, port=args.port, open_browser=not args.no_browser)
            return EXIT_OK
        written = make_stills(
            song,
            args.time,
            args.caption,
            with_caption=not args.no_caption,
            overwrite=args.overwrite,
            designs=args.design,
        )
    except LyricsVideoError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_FAILED
    print(f"Wrote {len(written.files)} image(s) to {written.folder}")
    return EXIT_OK


def run_install(folder: Path, overwrite: bool) -> int:
    try:
        bundle = install_app(folder, overwrite)
    except LyricsVideoError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_FAILED
    print(f"Wrote {bundle}\nOpen it, or drag it to the Dock; its log is ~/Library/Logs/lyrics-video.log.")
    return EXIT_OK


def run_render(song: Song, args: argparse.Namespace) -> int:
    """Raises LyricsVideoError for the caller to report; Ctrl+C and SIGTERM leave no file and exit with 130."""
    previous_sigterm = signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    try:
        prepared = prepare_render(
            song,
            output=args.output,
            overwrite=args.overwrite,
            start=args.start,
            duration=args.duration,
            design=args.design,
            workers=args.workers,
            codec=args.codec,
            crf=args.crf,
        )
        print_summary(prepared)
        result = render(prepared, progress=TextProgress(sys.stderr))
    except KeyboardInterrupt:
        print("\ncancelled; no video was written", file=sys.stderr)
        return EXIT_INTERRUPTED
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
    print_result(prepared, result)
    return EXIT_OK


def print_summary(prepared: PreparedRender) -> None:
    job = prepared.job
    print(f"Song: {prepared.title or '(no title)'} ({job.audio_path.name}, {prepared.song_seconds:.1f} s)")
    print(f"Design: {prepared.design}; timed captions: {prepared.timed}")
    if prepared.untimed:
        print(f"Warning: {len(prepared.untimed)} line(s) have no time yet and are left out:")
        for line in prepared.untimed:
            print(f"  {' / '.join(line.rows)}")
    part = ""
    if job.start > 0 or job.duration is not None:
        part = f" from {job.start:g} s" + (f" for {job.duration:g} s" if job.duration is not None else " to the end")
    print(f"Rendering {job.output_path}{part}")


def print_result(prepared: PreparedRender, result: RenderResult) -> None:
    video_seconds = result.frames / prepared.job.fps
    share = result.seconds / video_seconds * 100 if video_seconds > 0 else 0
    print(f"Wrote {result.output_path} in {result.seconds:.1f} s ({share:.0f} % of its length)")


class TextProgress:
    """Progress of a render: one line redrawn in place on a terminal, a line per tenth otherwise."""

    def __init__(self, stream: TextIO):
        self.stream = stream
        self.terminal = stream.isatty()
        self.started: float | None = None
        self.shown = 0.0
        self.tenth = -1

    def __call__(self, done: int, total: int) -> None:
        now = time.monotonic()
        if self.started is None:
            self.started = now
        if total <= 0:
            return
        if self.terminal:
            if done < total and now - self.shown < PROGRESS_INTERVAL:
                return
            self.shown = now
            self.stream.write(f"\r{self.line(done, total, now)}" + ("\n" if done >= total else ""))
        else:
            tenth = done * 10 // total
            if tenth == self.tenth:
                return
            self.tenth = tenth
            self.stream.write(f"{self.line(done, total, now)}\n")
        self.stream.flush()

    def line(self, done: int, total: int, now: float) -> str:
        elapsed = now - self.started
        left = f"{elapsed * (total - done) / done:.0f} s" if done > 0 else "?"
        return f"{done * 100 // total:3d} %  frame {done}/{total}  elapsed {elapsed:.0f} s  left {left}  "


def _raise_keyboard_interrupt(signum, frame) -> None:
    raise KeyboardInterrupt


def _non_negative(value: str) -> float:
    number = float(value)
    if not number >= 0:
        raise argparse.ArgumentTypeError(f"must be 0 or more, got {value}")
    return number


def _positive(value: str) -> float:
    number = float(value)
    if not number > 0:
        raise argparse.ArgumentTypeError(f"must be above 0, got {value}")
    return number


def _non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError(f"must be 0 or more, got {value}")
    return number


def _crf(value: str) -> int:
    number = int(value)
    if not 0 <= number <= 51:
        raise argparse.ArgumentTypeError(f"must be from 0 to 51, got {value}")
    return number


if __name__ == "__main__":
    sys.exit(main())
