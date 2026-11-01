"""Opening font files, and the strength of synthetic bold and italic."""

import math
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from lyrics_video.errors import FontError

# Synthetic bold widens the outline by this share of the font size on each side; synthetic italic slants by 12°.
BOLD_STROKE = 0.03
ITALIC_SLANT = math.tan(math.radians(12))


@lru_cache(maxsize=256)
def load_font(path: Path, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    if not path.is_file():
        raise FontError(f"{path}: font file not found")
    try:
        return ImageFont.truetype(str(path), size, index=index)
    except OSError as error:
        raise FontError(f"{path}: cannot open font (face {index}): {error}") from None
