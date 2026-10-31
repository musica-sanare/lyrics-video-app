"""Finding and opening font files."""

import unicodedata
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from lyrics_video.errors import FontError

FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc"}


@lru_cache(maxsize=256)
def load_font(path: Path, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    if not path.is_file():
        raise FontError(f"{path}: font file not found")
    try:
        return ImageFont.truetype(str(path), size, index=index)
    except OSError as error:
        raise FontError(f"{path}: cannot open font (face {index}): {error}") from None


def collect_fonts(paths: list[Path], folders: list[Path]) -> list[Path]:
    """The given font files in order, then every font file under the folders (sorted), each once."""
    fonts = []
    for path in paths:
        if not path.is_file():
            raise FontError(f"{path}: font file not found")
        fonts.append(path)
    for folder in folders:
        if not folder.is_dir():
            raise FontError(f"{folder}: font folder not found")
        fonts.extend(
            sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in FONT_SUFFIXES)
        )
    unique = list(dict.fromkeys(fonts))
    if not unique:
        raise FontError("no fonts to compare: give font files or folders that contain .ttf, .otf, .ttc or .otc files")
    return unique


def font_labels(fonts: list[Path]) -> list[str]:
    """A label per font: its file name without extension, numbered when two are equal.

    macOS stores file names decomposed (NFD), which draws "ギ" as "キ" plus a separate mark; labels are composed (NFC).
    """
    labels = []
    seen: dict[str, int] = {}
    for font in fonts:
        stem = unicodedata.normalize("NFC", font.stem)
        seen[stem] = seen.get(stem, 0) + 1
        labels.append(stem if seen[stem] == 1 else f"{stem}-{seen[stem]}")
    return labels
