"""The pictures a frame is made of, each drawn once: the background, and RGBA layers placed over it.

Text is drawn with Pillow as a coverage mask and colored afterwards, so its edges blend correctly over any picture.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from lyrics_video.caption_image import CaptionFont, CaptionLook, draw_caption
from lyrics_video.design import CaptionStyle, CreditsStyle, Panel, Shadow, TextFace, TitleStyle
from lyrics_video.errors import ConfigError
from lyrics_video.fonts import BOLD_STROKE, ITALIC_SLANT, load_font

# Credits shrink until their widest line fits in this share of the frame width.
CREDITS_MAX_WIDTH = 0.9


@dataclass(frozen=True)
class Layer:
    """An RGBA picture (straight alpha) placed with its top left corner at (left, top) of the frame."""

    left: int
    top: int
    rgba: np.ndarray


@dataclass(frozen=True)
class WideLayer:
    """A layer as 16-bit color and alpha, ready to blend. Twice the memory of the layer, so only a few are kept."""

    left: int
    top: int
    color: np.ndarray
    alpha: np.ndarray


def widen(layer: Layer) -> WideLayer:
    return WideLayer(
        layer.left, layer.top, layer.rgba[:, :, :3].astype(np.uint16), layer.rgba[:, :, 3:4].astype(np.uint16)
    )


def blend(frame: np.ndarray, layer: Layer | WideLayer, opacity: float = 1.0) -> None:
    """Draw `layer` over `frame` (RGB uint8, changed in place) at the given opacity."""
    if opacity <= 0:
        return
    wide = layer if isinstance(layer, WideLayer) else widen(layer)
    height, width = wide.alpha.shape[:2]
    region = frame[wide.top : wide.top + height, wide.left : wide.left + width]
    alpha = wide.alpha
    if opacity < 1:
        alpha = (alpha * round(opacity * 255) + 127) // 255
    mixed = region.astype(np.uint16)
    mixed *= 255 - alpha
    mixed += wide.color * alpha
    mixed += 127
    mixed //= 255
    region[:] = mixed


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


@dataclass(frozen=True)
class _Text:
    """A part's font at one size, with its synthetic bold (an outline `stroke` pixels wide) and italic (`slant`)."""

    font: ImageFont.FreeTypeFont
    stroke: float = 0.0
    slant: float = 0.0

    @property
    def ascent(self) -> int:
        return self.font.getmetrics()[0]

    @property
    def line_height(self) -> int:
        ascent, descent = self.font.getmetrics()
        return ascent + descent

    def width(self, text: str, spacing: float = 0.0) -> float:
        """The width the text covers, its outline and slant included."""
        if spacing <= 0:
            plain = self.font.getlength(text)
        else:
            plain = sum(self.font.getlength(character) for character in text) + spacing * (len(text) - 1)
        return plain + 2 * self.stroke + self.slant * self.ascent


def _text(style: TextFace, default_font: Path | None, part: str, size: float) -> _Text:
    size = max(1, round(size))
    font = load_font(_font_for(style.font, default_font, part), size, style.font_face)
    return _Text(font, BOLD_STROKE * size if style.bold else 0.0, ITALIC_SLANT if style.italic else 0.0)


def _fit(style: TextFace, default_font: Path | None, part: str, size: float, rows, max_width: float) -> _Text:
    """The text at `size`, or smaller until the widest row fits in `max_width`."""
    size = max(1, round(size))
    while True:
        text = _text(style, default_font, part, size)
        if max(text.width(row) for row in rows) <= max_width or size == 1:
            return text
        size -= 1


def _draw_text(mask: Image.Image, x: float, y: float, line: str, text: _Text, anchor: str = "la", spacing: float = 0.0):
    """Draw `line` into `mask` with its ascender line at `y`; `anchor` "la", "ma" or "ra" places it by its left edge,
    middle or right edge at `x`, slant included. `spacing` (extra space between characters) needs "la"."""
    lean = text.slant * text.ascent
    x -= {"la": 0.0, "ma": lean / 2, "ra": lean}[anchor]
    target = mask if text.slant == 0 else Image.new("L", mask.size, 0)
    draw = ImageDraw.Draw(target)
    outline = {"stroke_width": text.stroke, "stroke_fill": 255} if text.stroke > 0 else {}
    if spacing <= 0:
        draw.text((x, y), line, fill=255, font=text.font, anchor=anchor, **outline)
    else:
        for character in line:
            draw.text((x, y), character, fill=255, font=text.font, anchor="la", **outline)
            x += text.font.getlength(character) + spacing
    if text.slant:
        baseline = y + text.ascent
        slanted = target.transform(
            mask.size, Image.Transform.AFFINE, (1, text.slant, -text.slant * baseline, 0, 1, 0), Image.Resampling.BICUBIC
        )
        mask.paste(ImageChops.lighter(mask, slanted))


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


def _rounded_mask(size: tuple[int, int], radius: float) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=round(radius), fill=255)
    return mask


def _frosted(base: np.ndarray, box: tuple[int, int, int, int], panel: Panel, scale: float) -> Image.Image:
    """The full-frame RGBA picture of a panel: the base under `box` blurred, tinted and cut to a rounded box."""
    height, width = base.shape[:2]
    left, top, right, bottom = box
    margin = round(panel.blur * scale * 3)
    outer = (max(0, left - margin), max(0, top - margin), min(width, right + margin), min(height, bottom + margin))
    area = Image.fromarray(base[outer[1] : outer[3], outer[0] : outer[2]])
    if panel.blur > 0:
        area = area.filter(ImageFilter.GaussianBlur(panel.blur * scale))
    area = area.crop((left - outer[0], top - outer[1], right - outer[0], bottom - outer[1]))
    tint = Image.new("RGB", area.size, panel.color)
    glass = Image.blend(area, tint, panel.opacity).convert("RGBA")
    glass.putalpha(_rounded_mask(area.size, panel.radius * scale))
    picture = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    picture.paste(glass, (left, top))
    return picture


def title_layer(
    title: str,
    style: TitleStyle,
    default_font: Path | None,
    width: int,
    height: int,
    scale: float,
    base: np.ndarray | None = None,
) -> Layer | None:
    """The title at the top, with its rule and box. `base` (the frame under it) is needed for the box."""
    if not style.enabled or not title:
        return None
    text = _text(style, default_font, "title", style.size * scale)
    mask = Image.new("L", (width, height), 0)
    spacing = style.letter_spacing * scale
    title_width = text.width(title, spacing)
    left = (width - title_width) / 2 if style.position == "top-center" else style.margin * scale
    top = style.margin * scale
    _draw_text(mask, left, top, title, text, spacing=spacing)
    if style.rule:
        thickness = max(1, round(style.rule_thickness * scale))
        rule_top = round(top + text.line_height + style.rule_gap * scale)
        ImageDraw.Draw(mask).rectangle(
            [round(left), rule_top, round(left + title_width) - 1, rule_top + thickness - 1], fill=255
        )
    picture = _with_shadow(mask, style.color, style.shadow, scale)
    if style.panel is not None:
        if base is None:
            raise ValueError("a title panel needs the picture under it")
        box = _padded(mask.getbbox(), style.panel, scale, width, height)
        picture = Image.alpha_composite(_frosted(base, box, style.panel, scale), picture)
    return _cropped(picture)


def _padded(box, panel: Panel, scale: float, width: int, height: int) -> tuple[int, int, int, int]:
    """`box` (left, top, right, bottom) grown by the panel's padding, inside the frame."""
    pad_x, pad_y = panel.padding[0] * scale, panel.padding[1] * scale
    left, top, right, bottom = box
    return (
        max(0, round(left - pad_x)),
        max(0, round(top - pad_y)),
        min(width, round(right + pad_x)),
        min(height, round(bottom + pad_y)),
    )


def caption_layer(
    rows: tuple[str, ...],
    style: CaptionStyle,
    default_font: Path | None,
    width: int,
    height: int,
    scale: float,
    base: np.ndarray | None = None,
) -> Layer:
    """The caption in the design's style. `base` (the frame under it) is needed for the frosted panel."""
    if style.style == "band":
        return _band_caption(rows, style, default_font, width, height, scale)
    if style.style == "gradient":
        return _gradient_caption(rows, style, default_font, width, height, scale)
    if base is None:
        raise ValueError("a panel caption needs the picture under it")
    return _panel_caption(rows, style, default_font, base, scale)


def _band_caption(rows, style: CaptionStyle, default_font: Path | None, width: int, height: int, scale: float) -> Layer:
    """A band along the bottom edge with the caption drawn by the old caption image rules, scaled to the band."""
    font = CaptionFont(_font_for(style.font, default_font, "caption"), style.font_face)
    band_height = max(1, round(style.band_height * scale))
    band_scale = band_height / 232
    faces = {"bold": style.bold, "italic": style.italic}
    look = CaptionLook((width, band_height), style.band_color, style.text_color, **faces)
    band = np.asarray(draw_caption(rows, look, font, band_scale), dtype=np.uint8)
    coverage_look = CaptionLook(look.size, (0, 0, 0), (255, 255, 255), **faces)
    coverage = np.asarray(draw_caption(rows, coverage_look, font, band_scale).convert("L"), dtype=np.uint8)
    alpha = np.maximum(coverage, round(style.band_opacity * 255)).astype(np.uint8)
    return Layer(0, height - band_height, np.dstack([band, alpha]))


def _rows_mask(rows, text: _Text, left: float, top: float, step: float, size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    for number, row in enumerate(rows):
        _draw_text(mask, left, top + number * step, row, text)
    return mask


def _gradient_caption(rows, style: CaptionStyle, default_font: Path | None, width: int, height: int, scale: float):
    """Left-aligned rows near the bottom edge over a shade that rises from it."""
    margin_x = style.margin_x * scale
    text = _fit(style, default_font, "caption", style.size * scale, rows, width - 2 * margin_x)
    line = text.line_height
    step = line * style.line_spacing
    block = step * (len(rows) - 1) + line
    shade_height = round(style.gradient.height * scale)
    region_height = min(height, max(shade_height, round(block + style.margin_bottom * scale + 2 * line)))
    text_top = region_height - style.margin_bottom * scale - block
    ramp = np.zeros(region_height)
    shown = min(shade_height, region_height)
    ramp[region_height - shown :] = np.linspace(0.0, 1.0, shown) ** 1.5
    alpha = np.round(ramp * style.gradient.opacity * 255).astype(np.uint8)
    shade = Image.new("RGBA", (width, region_height), (*style.gradient.color, 0))
    shade.putalpha(Image.fromarray(np.repeat(alpha[:, None], width, axis=1)))
    mask = _rows_mask(rows, text, margin_x, text_top, step, (width, region_height))
    picture = Image.alpha_composite(shade, _with_shadow(mask, style.text_color, style.shadow, scale))
    return Layer(0, height - region_height, np.asarray(picture, dtype=np.uint8))


def _panel_caption(rows, style: CaptionStyle, default_font: Path | None, base: np.ndarray, scale: float) -> Layer:
    """Left-aligned rows in a frosted box near the bottom edge; the box has the same size for one and two rows."""
    height, width = base.shape[:2]
    pad_x, pad_y = style.panel.padding[0] * scale, style.panel.padding[1] * scale
    left, right = round(style.margin_x * scale), round(width - style.margin_x * scale)
    text = _fit(style, default_font, "caption", style.size * scale, rows, right - left - 2 * pad_x)
    line = _text(style, default_font, "caption", style.size * scale).line_height
    step = line * style.line_spacing
    box_height = round(step + line + 2 * pad_y)
    bottom = round(height - style.margin_bottom * scale)
    top = bottom - box_height
    picture = _frosted(base, (left, top, right, bottom), style.panel, scale)
    own_line = text.line_height
    block = own_line * style.line_spacing * (len(rows) - 1) + own_line
    text_top = top + (box_height - block) / 2
    mask = _rows_mask(rows, text, left + pad_x, text_top, own_line * style.line_spacing, (width, height))
    picture = Image.alpha_composite(picture, _with_shadow(mask, style.text_color, style.shadow, scale))
    return _cropped(picture)


def credits_layer(
    lines: tuple[str, ...],
    style: CreditsStyle,
    default_font: Path | None,
    width: int,
    height: int,
    scale: float,
    base: np.ndarray | None = None,
) -> Layer | None:
    """The credits, centered or at the bottom right, over the frame darkened by `style.dim` and an optional panel."""
    if not style.enabled or not lines:
        return None
    text = _fit(style, default_font, "credits", style.size * scale, lines, width * CREDITS_MAX_WIDTH)
    line = text.line_height
    step = line * style.line_spacing
    block = step * (len(lines) - 1) + line
    widest = max(text.width(credit) for credit in lines)
    if style.position == "center":
        top, right = height / 2 - block / 2, width / 2 + widest / 2
    else:
        top, right = height - style.margin_bottom * scale - block, width - style.margin_x * scale
    left = right - widest
    mask = Image.new("L", (width, height), 0)
    for number, credit in enumerate(lines):
        y = top + number * step
        if style.position == "center":
            _draw_text(mask, width / 2, y, credit, text, anchor="ma")
        else:
            _draw_text(mask, right, y, credit, text, anchor="ra")
    picture = Image.new("RGBA", (width, height), (0, 0, 0, round(style.dim * 255)))
    if style.panel is not None:
        if base is None:
            raise ValueError("a credits panel needs the picture under it")
        box = _padded((left, top, right, top + block), style.panel, scale, width, height)
        picture = Image.alpha_composite(picture, _frosted(base, box, style.panel, scale))
    picture = Image.alpha_composite(picture, _with_shadow(mask, style.color, style.shadow, scale))
    if style.dim > 0:
        return Layer(0, 0, np.asarray(picture, dtype=np.uint8))
    return _cropped(picture)
