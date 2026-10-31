"""Stills: frames of the future video at chosen moments, with the spectrum drawn over the backdrop."""

import math
from pathlib import Path

from audio_spectrum import AudioSpectrumError, Preview, load_preset, override_preset
from PIL import Image

from lyrics_video.backdrop import LyricsBackdrop, TimedCaption
from lyrics_video.captions import Written
from lyrics_video.config import Song
from lyrics_video.errors import ConfigError, LyricsError, SpectrumError
from lyrics_video.lyrics import read_lyrics
from lyrics_video.output import write_images

STILLS_DIR = "stills"


def make_stills(
    song: Song, times: list[float], caption_index: int | None = None, with_caption: bool = True, overwrite: bool = False
) -> Written:
    """One PNG per time, named `<design>_<time>s.png`, in `stills/` next to the song file.

    Until lyrics have timing (Phase 2) the still shows one caption: the line `caption_index` of the lyrics file
    (0-based, as in the caption image names), or the first caption.
    """
    if song.audio is None:
        raise ConfigError(f"{song.path}: audio is not set (the song file for the spectrum)")
    captions = [TimedCaption(-math.inf, math.inf, _caption_rows(song, caption_index))] if with_caption else []
    video = song.video
    try:
        preview = Preview(song.audio, video.fps)
        preset = override_preset(
            load_preset(song.spectrum_preset), [*song.design.spectrum.set, *song.spectrum_set]
        )
        backdrop = LyricsBackdrop.for_song(song, captions, preview.duration)
        backdrop.prepare(video.width, video.height)
        frames = preview.frames(preset, times, video.width, video.height, backdrop=backdrop)
    except AudioSpectrumError as error:
        raise SpectrumError(str(error)) from None
    folder = song.path.parent / STILLS_DIR
    images = {
        folder / f"{song.design.name}_{seconds:g}s.png": Image.fromarray(frame)
        for seconds, frame in zip(times, frames, strict=True)
    }
    write_images(images, overwrite)
    return Written(folder, list(images))


def _caption_rows(song: Song, caption_index: int | None) -> tuple[str, ...]:
    captions = read_lyrics(song.lyrics, song.look.separator)
    if caption_index is None:
        return captions[0].rows
    for caption in captions:
        if caption.index == caption_index:
            return caption.rows
    indexes = ", ".join(str(caption.index) for caption in captions)
    raise LyricsError(f"{song.lyrics}: no caption at line index {caption_index} (captions are at {indexes})")
