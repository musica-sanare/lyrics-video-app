import pytest
from PIL import Image, ImageChops, ImageDraw, ImageFont

from lyrics_video.caption_image import START_SIZE, CaptionFont, CaptionLook, draw_caption, fit_font_size
from lyrics_video.errors import CaptionError

LOOK = CaptionLook(size=(1440, 232), background=(0, 10, 67), text_color=(255, 255, 255))

LINES = [
    "short",
    "短い歌詞",
    "an English line that is long enough to need a smaller font than the starting size",
    "一行目の歌詞はここまで;二行目はもう少しだけ長く続いていく歌詞",
    "とても長い一行目の歌詞で、文字の大きさが小さくなるまで続けてみる;短い二行目",
    "空の二行目;",
]


def old_script_caption(line, font_path, look):
    """The old script's drawing, transcribed with `textbbox` in place of the removed `textsize`."""

    def textsize(draw, text, font):
        box = draw.textbbox((0, 0), text, font=font)
        return box[2], box[3]

    ret_img = Image.new("RGB", look.size, look.background)
    draw = ImageDraw.Draw(ret_img)
    lines = line.split(";")
    font_size = 80
    for row in lines:
        while True:
            font = ImageFont.truetype(str(font_path), font_size, index=0)
            text_width, text_height = textsize(draw, row, font)
            if text_width + 50 < ret_img.width and text_height + 50 < ret_img.height:
                break
            font_size -= 2
    font = ImageFont.truetype(str(font_path), font_size, index=0)
    text_width, text_height = textsize(draw, lines[0], font)
    if len(lines) == 1:
        draw.text((20, ret_img.height / 2 - text_height / 2), lines[0], fill=look.text_color, font=font, spacing=4)
    else:
        draw.text((20, ret_img.height / 4 - text_height / 2), lines[0], fill=look.text_color, font=font, spacing=4)
        draw.text((20, ret_img.height * 3 / 4 - text_height / 2), lines[1], fill=look.text_color, font=font, spacing=4)
    return ret_img


@pytest.mark.parametrize("line", LINES)
def test_same_pixels_as_the_old_script(sans_font, line):
    new = draw_caption(tuple(line.split(";")), LOOK, CaptionFont(sans_font))
    old = old_script_caption(line, sans_font, LOOK)

    assert ImageChops.difference(new, old).getbbox() is None


def test_image_size_and_colors(sans_font):
    image = draw_caption(("歌詞",), LOOK, CaptionFont(sans_font))

    assert image.size == LOOK.size
    assert image.mode == "RGB"
    assert image.getpixel((0, 0)) == LOOK.background
    assert LOOK.text_color in {color for _, color in image.getcolors(maxcolors=100_000)}


def test_short_text_keeps_the_start_size_and_long_text_shrinks_in_even_steps(sans_font):
    draw = ImageDraw.Draw(Image.new("RGB", LOOK.size))
    font = CaptionFont(sans_font)

    assert fit_font_size(draw, LOOK.size, ("short",), font) == START_SIZE
    shrunk = fit_font_size(draw, LOOK.size, (LINES[2],), font)
    assert shrunk < START_SIZE
    assert (START_SIZE - shrunk) % 2 == 0


def test_both_rows_share_the_size_of_the_longer_one(sans_font):
    draw = ImageDraw.Draw(Image.new("RGB", LOOK.size))
    font = CaptionFont(sans_font)

    long_size = fit_font_size(draw, LOOK.size, (LINES[2],), font)

    assert fit_font_size(draw, LOOK.size, ("short", LINES[2]), font) == long_size


def test_two_rows_sit_in_the_upper_and_lower_half(sans_font):
    image = draw_caption(("上の行", "下の行"), LOOK, CaptionFont(sans_font))
    mask = ImageChops.difference(image, Image.new("RGB", LOOK.size, LOOK.background)).convert("L")
    height = LOOK.size[1]

    assert mask.crop((0, 0, LOOK.size[0], height // 2)).getbbox() is not None
    assert mask.crop((0, height // 2, LOOK.size[0], height)).getbbox() is not None
    left = mask.getbbox()[0]
    assert 15 <= left <= 30, "left-aligned near x = 20"


def test_text_that_never_fits_is_an_error(sans_font):
    tiny = CaptionLook(size=(60, 52), background=(0, 0, 0), text_color=(255, 255, 255))

    with pytest.raises(CaptionError, match="does not fit"):
        draw_caption(("x",), tiny, CaptionFont(sans_font))
