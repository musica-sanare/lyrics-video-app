import pytest
from PIL import Image

from lyrics_video.app_icon import ICONSET, draw_icon, iconutil, write_icns
from lyrics_video.errors import ConfigError


@pytest.mark.parametrize("size", [16, 64, 128, 1024])
def test_the_icon_fills_the_rounded_square_and_leaves_the_corners_clear(size):
    icon = draw_icon(size)

    assert (icon.mode, icon.size) == ("RGBA", (size, size))
    for corner in [(0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)]:
        assert icon.getpixel(corner)[3] == 0
    assert icon.getpixel((size // 2, size // 2))[3] == 255


def test_the_icon_is_the_same_every_time():
    assert draw_icon(256).tobytes() == draw_icon(256).tobytes()


def test_the_icon_shows_the_start_and_end_marks():
    icon = draw_icon(1024)

    def near(color, pixel):
        return max(abs(a - b) for a, b in zip(color, pixel)) < 10

    assert near((79, 209, 139), icon.getpixel((372, 400))), "green start mark"
    assert near((255, 159, 67), icon.getpixel((658, 400))), "orange end mark"


def test_the_iconset_has_the_ten_sizes_of_macos():
    assert [size for _, size in ICONSET] == [16, 32, 32, 64, 128, 256, 256, 512, 512, 1024]


@pytest.mark.skipif(iconutil() is None, reason="iconutil comes with macOS only")
def test_a_tiny_image_is_refused(tmp_path):
    with pytest.raises(ConfigError, match="smaller than 16 px"):
        write_icns(tmp_path / "AppIcon.icns", Image.new("RGBA", (8, 8)))
