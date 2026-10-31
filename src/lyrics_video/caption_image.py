"""Caption images as made by the old lyrics image script (2022), on current Pillow.

The rules are kept exactly, including their quirks, so new images match the old ones (ADR-002): the font size starts
at 80 and shrinks in steps of 2 until every row fits with a margin; text is left-aligned; two rows are centered on
the quarter lines; both rows are placed with the height of the first row.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lyrics_video.config import CaptionLook
from lyrics_video.errors import CaptionError
from lyrics_video.fonts import load_font

START_SIZE = 80
SIZE_STEP = 2
FIT_MARGIN_X = 50
FIT_MARGIN_Y = 50
LEFT = 20
LINE_SPACING = 4


@dataclass(frozen=True)
class CaptionFont:
    path: Path
    index: int = 0

    def at(self, size: int) -> ImageFont.FreeTypeFont:
        return load_font(self.path, size, self.index)


def _measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """What `ImageDraw.textsize` returned before Pillow 10: the right and bottom edges of the text from its origin."""
    _, _, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right, bottom


def fit_font_size(
    draw: ImageDraw.ImageDraw, image_size: tuple[int, int], rows: tuple[str, ...], font: CaptionFont
) -> int:
    width, height = image_size
    size = START_SIZE
    for row in rows:
        while True:
            row_width, row_height = _measure(draw, row, font.at(size))
            if row_width + FIT_MARGIN_X < width and row_height + FIT_MARGIN_Y < height:
                break
            size -= SIZE_STEP
            if size <= 0:
                raise CaptionError(f"{row!r} does not fit in {width} x {height} at any font size")
    return size


def draw_caption(rows: tuple[str, ...], look: CaptionLook, font: CaptionFont) -> Image.Image:
    image = Image.new("RGB", look.size, look.background)
    draw = ImageDraw.Draw(image)
    size = fit_font_size(draw, image.size, rows, font)
    face = font.at(size)
    _, first_height = _measure(draw, rows[0], face)
    if len(rows) == 1:
        positions = [image.height / 2 - first_height / 2]
    else:
        positions = [image.height / 4 - first_height / 2, image.height * 3 / 4 - first_height / 2]
    for row, top in zip(rows, positions, strict=True):
        draw.text((LEFT, top), row, fill=look.text_color, font=face, spacing=LINE_SPACING)
    return image
