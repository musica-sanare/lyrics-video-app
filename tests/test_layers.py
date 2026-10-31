import numpy as np
import pytest
from PIL import Image, ImageDraw

from lyrics_video.design import CaptionStyle, CreditsStyle, TitleStyle
from lyrics_video.errors import ConfigError
from lyrics_video.layers import Layer, background, blend, caption_layer, credits_layer, title_layer

GREY, RED = (128, 128, 128), (255, 0, 0)


def image_with_square(path, size, square=40):
    """A grey image with a red square in the middle, to see whether cropping keeps proportions."""
    image = Image.new("RGB", size, GREY)
    cx, cy = size[0] // 2, size[1] // 2
    half = square // 2
    ImageDraw.Draw(image).rectangle([cx - half, cy - half, cx + half - 1, cy + half - 1], RED)
    image.save(path)
    return path


def red_box(picture):
    rows, columns = np.nonzero((picture[:, :, 0] > 200) & (picture[:, :, 1] < 60))
    return columns.max() - columns.min() + 1, rows.max() - rows.min() + 1


@pytest.mark.parametrize("size", [(800, 200), (200, 800), (300, 300), (1600, 900)])
def test_backgrounds_cover_and_crop_without_stretching(tmp_path, size):
    path = image_with_square(tmp_path / "bg.png", size)

    picture = background(path, 320, 180)

    assert picture.shape == (180, 320, 3)
    width, height = red_box(picture)
    assert abs(width - height) <= 1, "the square stays square"
    assert picture[0, 0].tolist() == list(GREY) and picture[-1, -1].tolist() == list(GREY), "no empty borders"


def test_focus_chooses_the_part_kept_in_view(tmp_path):
    image = Image.new("RGB", (400, 100), GREY)
    ImageDraw.Draw(image).rectangle([0, 0, 39, 99], RED)
    image.save(tmp_path / "bg.png")

    left = background(tmp_path / "bg.png", 100, 100, focus=(0.0, 0.5))
    middle = background(tmp_path / "bg.png", 100, 100)

    assert left[50, 5].tolist() == list(RED)
    assert middle[50, 5].tolist() == list(GREY)


def test_dim_and_blur(tmp_path):
    path = image_with_square(tmp_path / "bg.png", (100, 100))

    assert background(path, 100, 100, dim=0.5)[0, 0].tolist() == [64, 64, 64]
    plain, blurred = background(path, 100, 100), background(path, 100, 100, blur=5)
    assert np.abs(np.diff(blurred[50, :, 0].astype(int))).max() < np.abs(np.diff(plain[50, :, 0].astype(int))).max()


def test_no_image_is_black():
    assert not background(None, 10, 5).any()


def test_a_missing_image_is_reported(tmp_path):
    with pytest.raises(ConfigError, match="background image not found"):
        background(tmp_path / "nothing.jpg", 10, 10)


def test_blend_opacity():
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    layer = Layer(1, 0, np.array([[[200, 100, 0, 255]], [[200, 100, 0, 0]]], dtype=np.uint8))

    blend(frame, layer, 0.0)
    assert not frame.any()
    blend(frame, layer, 0.5)
    assert frame[0, 1].tolist() == [100, 50, 0]
    assert frame[1, 1].tolist() == [0, 0, 0], "transparent pixels change nothing"
    assert not frame[:, 0].any(), "outside the layer nothing changes"


def test_title_at_the_top_center(sans_font):
    layer = title_layer("Title", "Sub", TitleStyle(margin=50), sans_font, 1920, 1080, 1.0)

    height, width = layer.rgba.shape[:2]
    assert 40 <= layer.top <= 80
    assert abs((layer.left + width / 2) - 960) <= 4
    assert layer.top + height < 1080 / 3


def test_title_at_the_top_left_scales_with_the_frame(sans_font):
    layer = title_layer("Title", "", TitleStyle(position="top-left", margin=60), sans_font, 1280, 720, 720 / 1080)

    assert 35 <= layer.left <= 45


def test_title_off_or_empty(sans_font):
    assert title_layer("Title", "", TitleStyle(enabled=False), sans_font, 100, 100, 1.0) is None
    assert title_layer("", "", TitleStyle(), sans_font, 100, 100, 1.0) is None


def test_a_part_without_a_font_is_reported():
    with pytest.raises(ConfigError, match="no font for the title"):
        title_layer("Title", "", TitleStyle(), None, 100, 100, 1.0)


def test_caption_band_along_the_bottom(sans_font):
    style = CaptionStyle(band_color=(10, 20, 30), band_height=309)

    layer = caption_layer(("一行目", "二行目"), style, sans_font, 1920, 1080, 1.0)

    assert (layer.left, layer.top) == (0, 1080 - 309)
    assert layer.rgba.shape == (309, 1920, 4)
    assert layer.rgba[0, -1].tolist() == [10, 20, 30, 255]
    assert (layer.rgba[:, :, :3] == 255).all(axis=2).any(), "white text"


def test_a_translucent_band_keeps_its_text_opaque(sans_font):
    layer = caption_layer(("歌詞",), CaptionStyle(band_opacity=0.5), sans_font, 960, 540, 0.5)

    alpha = layer.rgba[:, :, 3]
    assert alpha[0, -1] == 128
    assert alpha.max() == 255


def test_credits_dim_the_frame_and_sit_in_the_middle(sans_font):
    layer = credits_layer(("Music: Someone", "Words: Someone Else"), CreditsStyle(dim=0.5), sans_font, 640, 360, 1 / 3)

    assert layer.rgba.shape == (360, 640, 4)
    assert layer.rgba[0, 0].tolist() == [0, 0, 0, 128]
    rows = np.nonzero((layer.rgba[:, :, 3] > 200).any(axis=1))[0]
    assert abs((rows.min() + rows.max()) / 2 - 180) <= 10


def test_credits_off_or_empty(sans_font):
    assert credits_layer(("A",), CreditsStyle(enabled=False), sans_font, 10, 10, 1.0) is None
    assert credits_layer((), CreditsStyle(), sans_font, 10, 10, 1.0) is None


def test_long_credits_shrink_to_fit(sans_font):
    line = "とても長いクレジットの行がここに入るので小さくなる" * 2

    layer = credits_layer((line,), CreditsStyle(dim=0), sans_font, 640, 360, 1.0)

    columns = np.nonzero((layer.rgba[:, :, 3] > 0).any(axis=0))[0]
    assert columns.max() - columns.min() <= 640 * 0.9 + 4


def test_title_letter_spacing_and_rule(sans_font):
    plain = title_layer("TITLE", "", TitleStyle(), sans_font, 1920, 1080, 1.0)
    spaced = title_layer("TITLE", "", TitleStyle(letter_spacing=10), sans_font, 1920, 1080, 1.0)
    ruled = title_layer("TITLE", "", TitleStyle(rule=True, rule_thickness=4), sans_font, 1920, 1080, 1.0)

    assert spaced.rgba.shape[1] - plain.rgba.shape[1] == pytest.approx(40, abs=3)
    assert ruled.rgba.shape[0] > plain.rgba.shape[0]
    assert (ruled.rgba[-3, :, 3] == 255).mean() > 0.9, "a solid line as wide as the title"


def test_gradient_caption_rises_from_the_bottom(sans_font):
    style = CaptionStyle(style="gradient", gradient={"height": 300, "opacity": 0.8}, margin_x=100)

    layer = caption_layer(("一行目", "二行目"), style, sans_font, 1920, 1080, 1.0)

    alpha = layer.rgba[:, :, 3]
    assert layer.top + alpha.shape[0] == 1080
    assert alpha[-1, -1] == 204, "full shade at the bottom edge"
    assert alpha[-300, -1] == 0, "transparent at the top of the shade"
    columns = np.nonzero((layer.rgba[:, :, :3] == 255).all(axis=2).any(axis=0))[0]
    assert 95 <= columns.min() <= 110, "left-aligned at the margin"


def test_long_gradient_rows_shrink_to_fit(sans_font):
    style = CaptionStyle(style="gradient", margin_x=100, size=120)

    layer = caption_layer(("とても長い歌詞の行" * 4,), style, sans_font, 1920, 1080, 1.0)

    columns = np.nonzero((layer.rgba[:, :, :3] == 255).all(axis=2).any(axis=0))[0]
    assert columns.max() <= 1920 - 100 + 2


def test_panel_caption_is_a_frosted_box(sans_font):
    base = np.zeros((1080, 1920, 3), dtype=np.uint8)
    base[:, ::2] = 255
    style = CaptionStyle(style="panel", margin_x=160, margin_bottom=56, panel={"opacity": 0.0, "blur": 10})

    layer = caption_layer(("歌詞",), style, sans_font, 1920, 1080, 1.0, base)

    assert layer.left == 160
    assert layer.top + layer.rgba.shape[0] == 1080 - 56
    assert layer.rgba[0, 0, 3] == 0, "rounded corner"
    middle = layer.rgba[layer.rgba.shape[0] // 2, -100, :3]
    assert 100 < middle[0] < 155, "the stripes behind it are blurred"


def test_panel_boxes_keep_their_size_for_one_and_two_rows(sans_font):
    base = np.zeros((540, 960, 3), dtype=np.uint8)
    style = CaptionStyle(style="panel")

    one = caption_layer(("一行",), style, sans_font, 960, 540, 0.5, base)
    two = caption_layer(("一行", "二行"), style, sans_font, 960, 540, 0.5, base)

    assert one.rgba.shape == two.rgba.shape


def test_credits_at_the_bottom_right(sans_font):
    style = CreditsStyle(position="bottom-right", dim=0, margin_x=50, margin_bottom=40)

    layer = credits_layer(("Music: Someone", "Words: Else"), style, sans_font, 1920, 1080, 1.0)

    assert abs(layer.left + layer.rgba.shape[1] - (1920 - 50)) <= 4
    assert abs(layer.top + layer.rgba.shape[0] - (1080 - 40)) <= 20


def test_credits_in_a_panel(sans_font):
    base = np.full((540, 960, 3), 200, dtype=np.uint8)
    style = CreditsStyle(dim=0, panel={"color": "#000000", "opacity": 0.5, "blur": 0})

    layer = credits_layer(("Music: Someone",), style, sans_font, 960, 540, 0.5, base)

    assert layer.rgba[layer.rgba.shape[0] // 2, 5].tolist() == [100, 100, 100, 255]
