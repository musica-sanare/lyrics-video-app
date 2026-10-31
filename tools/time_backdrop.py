"""Time the backdrop (the picture under the spectrum) per frame, for each design.

    uv run python tools/time_backdrop.py SONG_FILE [--design classic soft panel] [--frames 120]

Uses the song file's background, title, credits, fonts and video size, and its first caption shown from 10 s to
20 s. For each design it prints the time to prepare the pictures once and the mean time per frame in four states:
no caption, a caption, a caption fading, and the credits fading in. Only numbers and design names are printed.
"""

import argparse
import dataclasses
import sys
import time
from pathlib import Path

from lyrics_video.backdrop import LyricsBackdrop, TimedCaption
from lyrics_video.config import load_song, song_design
from lyrics_video.lyrics import read_lyrics

CAPTION_START, CAPTION_END = 10.0, 20.0
DURATION = 300.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("song", type=Path)
    parser.add_argument("--design", nargs="+", default=["classic", "soft", "panel"])
    parser.add_argument("--frames", type=int, default=120)
    args = parser.parse_args(argv)

    song = load_song(args.song)
    rows = read_lyrics(song.lyrics, song.look.separator)[0].rows
    width, height = song.video.width, song.video.height
    print(f"{width}x{height}, {args.frames} frames per state, times in ms per frame")
    print("design    prepare  no caption  caption  caption fading  credits fading")
    for name in args.design:
        design = song_design(song.path, name, song.design_overrides)
        backdrop = LyricsBackdrop.for_song(
            dataclasses.replace(song, design=design), [TimedCaption(CAPTION_START, CAPTION_END, rows)], DURATION
        )
        started = time.perf_counter()
        backdrop.prepare(width, height)
        prepare = time.perf_counter() - started
        fading_credits = design.credits.show_seconds - design.credits.fade_seconds / 2
        states = [30.0, 15.0, CAPTION_START + design.caption.fade_seconds / 2, fading_credits]
        timings = []
        for seconds in states:
            started = time.perf_counter()
            for _ in range(args.frames):
                backdrop.frame(0, seconds, width, height)
            timings.append((time.perf_counter() - started) / args.frames * 1000)
        print(f"{name:<9} {prepare * 1000:6.0f}  " + "  ".join(f"{value:10.1f}" for value in timings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
