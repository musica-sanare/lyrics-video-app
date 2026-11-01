"""Captions in a band, drawn with the rules of the old lyrics image script (2022) on current Pillow.

The `classic` design draws its caption band this way. The rules are kept exactly, including their quirks, so captions
look like the old caption images (ADR-002): the font size starts
at 80 and shrinks in steps of 2 until every row fits with a margin; text is left-aligned; two rows are centered on
the quarter lines; both rows are placed with the height of the first row. With `scale`, every length (start size,
step, margins, left edge) is multiplied, so the same caption can be drawn for a band of another height. Synthetic
bold and italic (`fonts.BOLD_STROKE`, `fonts.ITALIC_SLANT`) are counted when the text is fitted.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lyrics_video.errors import CaptionError
from lyrics_video.fonts import BOLD_STROKE, ITALIC_SLANT, load_font

START_SIZE = 80
SIZE_STEP = 2
FIT_MARGIN_X = 50
FIT_MARGIN_Y = 50
LEFT = 20
LINE_SPACING = 4


type RGB = tuple[int, int, int]


@dataclass(frozen=True)
class CaptionLook:
    """A band of `size` filled with `background`, with the caption in `text_color`, synthetic bold or italic."""

    size: tuple[int, int]
    background: RGB
    text_color: RGB
    bold: bool = False
    italic: bool = False

    def stroke(self, size: int) -> float:
        return BOLD_STROKE * size if self.bold else 0.0

    @property
    def slant(self) -> float:
        return ITALIC_SLANT if self.italic else 0.0


@dataclass(frozen=True)
class CaptionFont:
    path: Path
    index: int = 0

    def at(self, size: int) -> ImageFont.FreeTypeFont:
        return load_font(self.path, size, self.index)


def _measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, stroke: float = 0.0) -> tuple[int, int]:
    """What `ImageDraw.textsize` returned before Pillow 10: the right and bottom edges of the text from its origin."""
    _, _, right, bottom = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    return right, bottom


def fit_font_size(
    draw: ImageDraw.ImageDraw,
    image_size: tuple[int, int],
    rows: tuple[str, ...],
    font: CaptionFont,
    scale: float = 1.0,
    look: CaptionLook | None = None,
) -> int:
    width, height = image_size
    size = round(START_SIZE * scale)
    step = max(1, round(SIZE_STEP * scale))
    for row in rows:
        while True:
            face = font.at(size)
            stroke = look.stroke(size) if look else 0.0
            row_width, row_height = _measure(draw, row, face, stroke)
            if look and look.slant:
                row_width += look.slant * face.getmetrics()[0]
            if row_width + FIT_MARGIN_X * scale < width and row_height + FIT_MARGIN_Y * scale < height:
                break
            size -= step
            if size <= 0:
                raise CaptionError(f"{row!r} does not fit in {width} x {height} at any font size")
    return size


def draw_caption(rows: tuple[str, ...], look: CaptionLook, font: CaptionFont, scale: float = 1.0) -> Image.Image:
    image = Image.new("RGB", look.size, look.background)
    draw = ImageDraw.Draw(image)
    size = fit_font_size(draw, image.size, rows, font, scale, look)
    face = font.at(size)
    stroke = look.stroke(size)
    outline = {"stroke_width": stroke, "stroke_fill": look.text_color} if stroke > 0 else {}
    _, first_height = _measure(draw, rows[0], face, stroke)
    if len(rows) == 1:
        positions = [image.height / 2 - first_height / 2]
    else:
        positions = [image.height / 4 - first_height / 2, image.height * 3 / 4 - first_height / 2]
    for row, top in zip(rows, positions, strict=True):
        if not look.slant:
            draw.text((LEFT * scale, top), row, fill=look.text_color, font=face, spacing=LINE_SPACING, **outline)
            continue
        mask = Image.new("L", image.size, 0)
        ImageDraw.Draw(mask).text((LEFT * scale, top), row, fill=255, font=face, stroke_width=stroke)
        shear = look.slant, -look.slant * (top + face.getmetrics()[0])
        mask = mask.transform(mask.size, Image.Transform.AFFINE, (1, *shear, 0, 1, 0), Image.Resampling.BICUBIC)
        image.paste(look.text_color, mask=mask)
    return image
