"""One image that shows a caption in many fonts, each under its font's name, to choose a font at a glance."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LABEL_HEIGHT = 44
LABEL_SIZE = 26
LABEL_LEFT = 20
LABEL_BACKGROUND = (40, 40, 40)
LABEL_COLOR = (230, 230, 230)
# Font names may be Japanese; Hiragino has the glyphs, Pillow's own font is the fallback elsewhere.
LABEL_FONT = Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc")


def contact_sheet(entries: list[tuple[str, Image.Image]]) -> Image.Image:
    width = max(image.width for _, image in entries)
    height = sum(LABEL_HEIGHT + image.height for _, image in entries)
    sheet = Image.new("RGB", (width, height), LABEL_BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    font = _label_font()
    top = 0
    for label, image in entries:
        draw.text((LABEL_LEFT, top + LABEL_HEIGHT / 2), label, fill=LABEL_COLOR, font=font, anchor="lm")
        sheet.paste(image, (0, top + LABEL_HEIGHT))
        top += LABEL_HEIGHT + image.height
    return sheet


def _label_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(LABEL_FONT), LABEL_SIZE)
    except OSError:
        return ImageFont.load_default(LABEL_SIZE)
