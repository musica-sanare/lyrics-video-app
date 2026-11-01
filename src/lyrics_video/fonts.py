"""Opening font files."""

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from lyrics_video.errors import FontError


@lru_cache(maxsize=256)
def load_font(path: Path, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    if not path.is_file():
        raise FontError(f"{path}: font file not found")
    try:
        return ImageFont.truetype(str(path), size, index=index)
    except OSError as error:
        raise FontError(f"{path}: cannot open font (face {index}): {error}") from None
