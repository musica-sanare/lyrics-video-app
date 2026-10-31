"""Caption images for a song, and the same text in many fonts for comparison."""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from lyrics_video.caption_image import CaptionFont, draw_caption
from lyrics_video.config import Song
from lyrics_video.contact_sheet import contact_sheet
from lyrics_video.errors import ConfigError
from lyrics_video.fonts import collect_fonts, font_labels
from lyrics_video.lyrics import read_lyrics
from lyrics_video.output import write_images

CONTACT_SHEET_NAME = "contact_sheet.png"


@dataclass(frozen=True)
class Written:
    folder: Path
    files: list[Path]


def make_captions(song: Song, overwrite: bool = False) -> Written:
    """One PNG per caption, named `<prefix>_<line index>.png` like the old script's."""
    if song.font is None:
        raise ConfigError(f"{song.path}: captions.font is not set")
    font = CaptionFont(song.font, song.font_index)
    captions = read_lyrics(song.lyrics, song.look.separator)
    images = {
        song.caption_dir / f"{song.file_prefix}_{caption.index}.png": draw_caption(caption.rows, song.look, font)
        for caption in captions
    }
    write_images(images, overwrite)
    return Written(song.caption_dir, list(images))


def compare_fonts(
    song: Song,
    fonts: list[Path] | None = None,
    font_dirs: list[Path] | None = None,
    overwrite: bool = False,
) -> Written:
    """Every line of the comparison text in every font, plus a contact sheet of the first line in all fonts.

    Fonts given here replace the song file's `compare.fonts` and `compare.font_dirs`.
    """
    if fonts or font_dirs:
        paths = collect_fonts(fonts or [], font_dirs or [])
    else:
        paths = collect_fonts(song.compare_fonts, song.compare_font_dirs)
    captions = read_lyrics(song.compare_text, song.look.separator)
    images: dict[Path, Image.Image] = {}
    sheet_entries = []
    for path, label in zip(paths, font_labels(paths), strict=True):
        font = CaptionFont(path)
        for caption in captions:
            image = draw_caption(caption.rows, song.look, font)
            images[song.compare_dir / f"{label}_{caption.index}.png"] = image
            if caption is captions[0]:
                sheet_entries.append((label, image))
    images[song.compare_dir / CONTACT_SHEET_NAME] = contact_sheet(sheet_entries)
    write_images(images, overwrite)
    return Written(song.compare_dir, list(images))
