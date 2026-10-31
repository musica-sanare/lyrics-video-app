"""The pictures a frame is made of, each drawn once: the background, and RGBA layers placed over it.

Text is drawn with Pillow as a coverage mask and colored afterwards, so its edges blend correctly over any picture.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from lyrics_video.caption_image import CaptionFont, draw_caption
from lyrics_video.config import CaptionLook
from lyrics_video.design import CaptionStyle, CreditsStyle, Shadow, TitleStyle
from lyrics_video.errors import ConfigError
from lyrics_video.fonts import load_font

# Credits shrink until their widest line fits in this share of the frame width.
CREDITS_MAX_WIDTH = 0.9


@dataclass(frozen=True)
class Layer:
    """An RGBA picture (straight alpha) placed with its top left corner at (left, top) of the frame."""

    left: int
    top: int
    rgba: np.ndarray


def blend(frame: np.ndarray, layer: Layer, opacity: float = 1.0) -> None:
    """Draw `layer` over `frame` (RGB uint8, changed in place) at the given opacity."""
    if opacity <= 0:
        return
    height, width = layer.rgba.shape[:2]
    region = frame[layer.top : layer.top + height, layer.left : layer.left + width]
    alpha = layer.rgba[:, :, 3:4].astype(np.uint16)
    if opacity < 1:
        alpha = (alpha * round(opacity * 255) + 127) // 255
    color = layer.rgba[:, :, :3].astype(np.uint16)
    region[:] = ((region.astype(np.uint16) * (255 - alpha) + color * alpha + 127) // 255).astype(np.uint8)


def background(image_path: Path | None, width: int, height: int, focus=(0.5, 0.5), dim=0.0, blur=0.0) -> np.ndarray:
    """The image scaled to cover the frame and cropped around `focus`, never stretched; black without an image."""
    if image_path is None:
        return np.zeros((height, width, 3), dtype=np.uint8)
    try:
        with Image.open(image_path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
    except FileNotFoundError:
        raise ConfigError(f"{image_path}: background image not found") from None
    except OSError as error:
        raise ConfigError(f"{image_path}: cannot read the background image ({error})") from None
    factor = max(width / image.width, height / image.height)
    scaled_width, scaled_height = max(width, round(image.width * factor)), max(height, round(image.height * factor))
    image = image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
    left = round(min(max(focus[0] * scaled_width - width / 2, 0), scaled_width - width))
    top = round(min(max(focus[1] * scaled_height - height / 2, 0), scaled_height - height))
    image = image.crop((left, top, left + width, top + height))
    if blur > 0:
        image = image.filter(ImageFilter.GaussianBlur(blur))
    picture = np.array(image, dtype=np.uint8)
    if dim > 0:
        picture = (picture.astype(np.float32) * (1 - dim)).round().astype(np.uint8)
    return picture


def _font_for(part_font: Path | None, default_font: Path | None, part: str) -> Path:
    font = part_font or default_font
    if font is None:
        raise ConfigError(f"no font for the {part}: set fonts.default in the song file, or design.{part}.font")
    return font


def _colored(mask: Image.Image, color: tuple[int, int, int], opacity: float = 1.0) -> Image.Image:
    layer = Image.new("RGBA", mask.size, (*color, 0))
    alpha = mask if opacity >= 1 else mask.point(lambda value: round(value * opacity))
    layer.putalpha(alpha)
    return layer


def _with_shadow(mask: Image.Image, color: tuple[int, int, int], shadow: Shadow, scale: float) -> Image.Image:
    text = _colored(mask, color)
    if shadow.blur <= 0:
        return text
    offset = (round(shadow.offset[0] * scale), round(shadow.offset[1] * scale))
    shifted = Image.new("L", mask.size, 0)
    shifted.paste(mask, offset)
    blurred = shifted.filter(ImageFilter.GaussianBlur(shadow.blur * scale))
    return Image.alpha_composite(_colored(blurred, shadow.color, shadow.opacity), text)


def _cropped(image: Image.Image) -> Layer:
    box = image.getchannel("A").getbbox()
    if box is None:
        return Layer(0, 0, np.zeros((0, 0, 4), dtype=np.uint8))
    return Layer(box[0], box[1], np.asarray(image.crop(box), dtype=np.uint8))


def title_layer(
    title: str, subtitle: str, style: TitleStyle, default_font: Path | None, width: int, height: int, scale: float
) -> Layer | None:
    if not style.enabled or not (title or subtitle):
        return None
    font_path = _font_for(style.font, default_font, "title")
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    centered = style.position == "top-center"
    x = width / 2 if centered else style.margin * scale
    anchor = "ma" if centered else "la"
    y = style.margin * scale
    for text, size in ((title, style.size), (subtitle, style.subtitle_size)):
        if not text:
            continue
        font = load_font(font_path, max(1, round(size * scale)))
        draw.text((x, y), text, fill=255, font=font, anchor=anchor)
        ascent, descent = font.getmetrics()
        y += ascent + descent + style.gap * scale
    return _cropped(_with_shadow(mask, style.color, style.shadow, scale))


def caption_layer(
    rows: tuple[str, ...], style: CaptionStyle, default_font: Path | None, width: int, height: int, scale: float
) -> Layer:
    """A band along the bottom edge with the caption drawn by the old caption image rules, scaled to the band."""
    font = CaptionFont(_font_for(style.font, default_font, "caption"))
    band_height = max(1, round(style.band_height * scale))
    band_scale = band_height / 232
    look = CaptionLook(
        size=(width, band_height), background=style.band_color, text_color=style.text_color, separator=";"
    )
    band = np.asarray(draw_caption(rows, look, font, band_scale), dtype=np.uint8)
    coverage_look = CaptionLook(size=look.size, background=(0, 0, 0), text_color=(255, 255, 255), separator=";")
    coverage = np.asarray(draw_caption(rows, coverage_look, font, band_scale).convert("L"), dtype=np.uint8)
    alpha = np.maximum(coverage, round(style.band_opacity * 255)).astype(np.uint8)
    return Layer(0, height - band_height, np.dstack([band, alpha]))


def credits_layer(
    lines: tuple[str, ...], style: CreditsStyle, default_font: Path | None, width: int, height: int, scale: float
) -> Layer | None:
    """The credits centered on the frame, over the frame darkened by `style.dim`."""
    if not style.enabled or not lines:
        return None
    font_path = _font_for(style.font, default_font, "credits")
    size = max(1, round(style.size * scale))
    while True:
        font = load_font(font_path, size)
        widest = max(font.getlength(line) for line in lines)
        if widest <= width * CREDITS_MAX_WIDTH or size == 1:
            break
        size -= 1
    ascent, descent = font.getmetrics()
    step = (ascent + descent) * style.line_spacing
    top = height / 2 - step * (len(lines) - 1) / 2
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    for number, line in enumerate(lines):
        draw.text((width / 2, top + number * step), line, fill=255, font=font, anchor="mm")
    picture = Image.new("RGBA", (width, height), (0, 0, 0, round(style.dim * 255)))
    picture = Image.alpha_composite(picture, _with_shadow(mask, style.color, style.shadow, scale))
    return Layer(0, 0, np.asarray(picture, dtype=np.uint8))
