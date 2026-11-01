"""The icon of Lyrics Video.app, drawn by code: a waveform between a green start mark and an orange end mark.

The drawing uses shapes and the page's colors only, inside macOS's rounded-square outline, so no image file enters the
repository. `write_icns` turns it, or the owner's own image, into an `.icns` file with macOS's `iconutil`.
"""

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from lyrics_video.errors import ConfigError

# The page's colors (web/static/app.css).
BACKGROUND_TOP = (44, 50, 60)
BACKGROUND_BOTTOM = (22, 24, 29)
MUTED = (139, 146, 156)
ACCENT = (79, 163, 255)
START = (79, 209, 139)
END = (255, 159, 67)

# macOS's icon grid, in units of a 1024 px icon: an 824 px rounded square with a 100 px margin.
GRID = 1024
MARGIN = 100
SIDE = 824
RADIUS = 185
# Below this size the waveform has fewer, wider bars, so it still reads in the Finder's list and the menu bar.
DETAILED = 128
# The images of an `.iconset`: name and size in pixels.
ICONSET = [
    (f"icon_{points}x{points}{suffix}.png", points * scale)
    for points in (16, 32, 128, 256, 512)
    for suffix, scale in (("", 1), ("@2x", 2))
]


def draw_icon(size: int) -> Image.Image:
    """The icon as an RGBA image of `size` x `size`, drawn larger and scaled down for smooth edges."""
    drawn = min(max(4 * size, 512), 2 * GRID)
    scale = drawn / GRID

    def px(value: float) -> int:
        return round(value * scale)

    column = Image.linear_gradient("L").resize((1, drawn))
    picture = ImageOps.colorize(column, BACKGROUND_TOP, BACKGROUND_BOTTOM).resize((drawn, drawn))
    draw = ImageDraw.Draw(picture)
    left, right, middle, start, end = 170, 854, 512, 380, 650
    step, width = (18, 10) if size >= DETAILED else (40, 24)
    for index, x in enumerate(range(left, right, step)):
        t = (x - left) / (right - left)
        loudness = abs(math.sin(3.1 * math.pi * t)) * (0.6 + 0.4 * math.sin(1.7 * index) ** 2)
        height = 200 * (0.25 + 0.75 * loudness)
        color = ACCENT if start <= x <= end else MUTED
        draw.rounded_rectangle(
            (px(x), px(middle - height), px(x + width), px(middle + height)), px(width / 2), fill=color
        )
    mark = 7 if size >= DETAILED else 14
    for x, color in ((start - 8, START), (end + 8, END)):
        draw.rounded_rectangle((px(x - mark), px(260), px(x + mark), px(764)), px(mark), fill=color)
        draw.polygon([(px(x - 34), px(240)), (px(x + 34), px(240)), (px(x), px(290))], fill=color)
    return _outline(picture).resize((size, size), Image.Resampling.LANCZOS)


def load_image(path: Path) -> Image.Image:
    """The owner's image for `--icon`, cropped to a square around its center."""
    try:
        with Image.open(path.expanduser()) as image:
            image.load()
            square = min(image.size)
            return ImageOps.fit(image.convert("RGBA"), (square, square))
    except (OSError, UnidentifiedImageError) as error:
        raise ConfigError(f"{path} cannot be read as an image: {error}") from error


def iconutil() -> Path | None:
    found = shutil.which("iconutil")
    return Path(found) if found else None


def write_icns(path: Path, source: Image.Image | None = None) -> None:
    """Write the icon, or `source`, as `path` (an `.icns` file). `source` is scaled down only, never up."""
    tool = iconutil()
    if tool is None:
        raise ConfigError("iconutil is not available (it comes with macOS)")
    with tempfile.TemporaryDirectory(prefix="lyrics-video-icon.") as folder:
        iconset = Path(folder) / "AppIcon.iconset"
        iconset.mkdir()
        for name, size in ICONSET:
            if source is None:
                draw_icon(size).save(iconset / name)
            elif size <= source.width:
                source.resize((size, size), Image.Resampling.LANCZOS).save(iconset / name)
        if not any(iconset.iterdir()):
            raise ConfigError(f"the icon image is smaller than {ICONSET[0][1]} px")
        result = subprocess.run(
            [str(tool), "-c", "icns", str(iconset), "-o", str(path)], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise ConfigError(f"iconutil could not make the icon: {result.stderr.strip()}")


def _outline(picture: Image.Image) -> Image.Image:
    size = picture.width
    scale = size / GRID
    mask = Image.new("L", (size, size), 0)
    low, high = round(MARGIN * scale), round((MARGIN + SIDE) * scale) - 1
    ImageDraw.Draw(mask).rounded_rectangle((low, low, high, high), round(RADIUS * scale), fill=255)
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.paste(picture, (0, 0), mask)
    return icon
