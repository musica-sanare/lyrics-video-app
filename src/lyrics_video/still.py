"""Stills: frames of the future video at chosen moments, with the spectrum drawn over the backdrop."""

import dataclasses
import math
from pathlib import Path

from audio_spectrum import AudioSpectrumError, Preview
from PIL import Image

from lyrics_video.backdrop import LyricsBackdrop, TimedCaption, timed_captions
from lyrics_video.config import Song, song_design, spectrum_preset
from lyrics_video.contact_sheet import contact_sheet
from lyrics_video.errors import ConfigError, LyricsError, SpectrumError
from lyrics_video.lyrics import read_lyrics
from lyrics_video.output import Written, write_images
from lyrics_video.timing import check_inside, read_lrc

STILLS_DIR = "stills"
# Stills are shown at this share of their size in the comparison sheet.
COMPARE_SCALE = 0.5


def make_stills(
    song: Song,
    times: list[float],
    caption_index: int | None = None,
    with_caption: bool = True,
    overwrite: bool = False,
    designs: list[str] | None = None,
) -> Written:
    """One PNG per design and time, named `<design>_<time>s.png`, in `stills/` next to the song file.

    `designs` replaces the song file's design name; the song file's design overrides apply to each. With more than
    one design, `compare_<time>s.png` shows the designs one under the other at half size.

    With timing, each still shows the captions of its moment, fading as in the video. `caption_index` shows the line
    of the lyrics file at that index (0-based, empty lines included) at every time instead; without timing
    the still shows that line, or the first caption.
    """
    if song.audio is None:
        raise ConfigError(f"{song.path}: audio is not set (the song file for the spectrum)")
    by_time = with_caption and caption_index is None and song.timing is not None
    timing = read_lrc(song.timing, song.separator) if by_time else []
    fixed = with_caption and not by_time
    captions = [TimedCaption(-math.inf, math.inf, _caption_rows(song, caption_index))] if fixed else []
    chosen = [song_design(song.path, name, song.design_overrides) for name in designs] if designs else [song.design]
    video = song.video
    folder = song.path.parent / STILLS_DIR
    images: dict[Path, Image.Image] = {}
    try:
        preview = Preview(song.audio, video.fps)
        if by_time:
            check_inside(timing, preview.duration, str(song.timing))
            captions = timed_captions(timing, preview.duration)
        for design in chosen:
            preset = spectrum_preset(song, design)
            backdrop = LyricsBackdrop.for_song(dataclasses.replace(song, design=design), captions, preview.duration)
            backdrop.prepare(video.width, video.height)
            frames = preview.frames(preset, times, video.width, video.height, backdrop=backdrop)
            for seconds, frame in zip(times, frames, strict=True):
                images[folder / f"{design.name}_{seconds:g}s.png"] = Image.fromarray(frame)
    except AudioSpectrumError as error:
        raise SpectrumError(str(error)) from None
    if len(chosen) > 1:
        size = (round(video.width * COMPARE_SCALE), round(video.height * COMPARE_SCALE))
        for seconds in times:
            entries = [
                (design.name, images[folder / f"{design.name}_{seconds:g}s.png"].resize(size, Image.Resampling.LANCZOS))
                for design in chosen
            ]
            images[folder / f"compare_{seconds:g}s.png"] = contact_sheet(entries)
    write_images(images, overwrite)
    return Written(folder, list(images))


def _caption_rows(song: Song, caption_index: int | None) -> tuple[str, ...]:
    captions = read_lyrics(song.lyrics, song.separator)
    if caption_index is None:
        return captions[0].rows
    for caption in captions:
        if caption.index == caption_index:
            return caption.rows
    indexes = ", ".join(str(caption.index) for caption in captions)
    raise LyricsError(f"{song.lyrics}: no caption at line index {caption_index} (captions are at {indexes})")
