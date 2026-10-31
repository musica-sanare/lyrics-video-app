"""The song file: one TOML file per song, with paths relative to it."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, ValidationError

from lyrics_video.errors import ConfigError

DEFAULT_CAPTION_SIZE = (1440, 232)
HEX_COLOR = re.compile(r"#([0-9a-fA-F]{6})")

type RGB = tuple[int, int, int]


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaptionSettings(_Section):
    output_dir: Path = Path("captions")
    size: tuple[PositiveInt, PositiveInt] | None = Field(
        default=None, description="Width and height; by default the background sample image's size, or 1440 x 232"
    )
    background: str = "#000000"
    text_color: str = "#FFFFFF"
    font: Path | None = None
    font_index: int = Field(default=0, ge=0)
    separator: str = Field(default=";", min_length=1)
    file_prefix: str = "lyrics"


class CompareSettings(_Section):
    text: Path = Path("compare.txt")
    output_dir: Path = Path("compare")
    fonts: list[Path] = []
    font_dirs: list[Path] = []


class SongFile(_Section):
    lyrics: Path = Path("lyrics.txt")
    captions: CaptionSettings = CaptionSettings()
    compare: CompareSettings = CompareSettings()


@dataclass(frozen=True)
class CaptionLook:
    """What every caption image of a song shares, resolved from the song file."""

    size: tuple[int, int]
    background: RGB
    text_color: RGB
    separator: str


@dataclass(frozen=True)
class Song:
    path: Path
    lyrics: Path
    look: CaptionLook
    font: Path | None
    font_index: int
    caption_dir: Path
    file_prefix: str
    compare_text: Path
    compare_dir: Path
    compare_fonts: list[Path]
    compare_font_dirs: list[Path]


def resolve_path(value: Path, base: Path) -> Path:
    path = value.expanduser()
    return path if path.is_absolute() else base / path


def load_song(path: Path) -> Song:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"{path}: song file not found") from None
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{path}: cannot read the song file ({error})") from None
    try:
        song = SongFile.model_validate(data)
    except ValidationError as error:
        raise ConfigError(f"{path}: invalid song file\n{_describe(error)}") from None

    base = path.parent
    captions = song.captions
    background, sample_size = _color(captions.background, base, "captions.background", path)
    text_color, _ = _color(captions.text_color, base, "captions.text_color", path)
    size = captions.size or sample_size or DEFAULT_CAPTION_SIZE
    return Song(
        path=path,
        lyrics=resolve_path(song.lyrics, base),
        look=CaptionLook(size=size, background=background, text_color=text_color, separator=captions.separator),
        font=resolve_path(captions.font, base) if captions.font else None,
        font_index=captions.font_index,
        caption_dir=resolve_path(captions.output_dir, base),
        file_prefix=captions.file_prefix,
        compare_text=resolve_path(song.compare.text, base),
        compare_dir=resolve_path(song.compare.output_dir, base),
        compare_fonts=[resolve_path(p, base) for p in song.compare.fonts],
        compare_font_dirs=[resolve_path(p, base) for p in song.compare.font_dirs],
    )


def _color(value: str, base: Path, key: str, song_path: Path) -> tuple[RGB, tuple[int, int] | None]:
    """A "#RRGGBB" color, or the center pixel of an image file and that image's size."""
    if match := HEX_COLOR.fullmatch(value):
        digits = match.group(1)
        return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)), None
    image_path = resolve_path(Path(value), base)
    try:
        with Image.open(image_path) as image:
            pixel = image.convert("RGB").getpixel((image.width // 2, image.height // 2))
            return pixel, image.size
    except FileNotFoundError:
        raise ConfigError(f"{song_path}: {key}: not a #RRGGBB color and no image at {image_path}") from None
    except (OSError, UnidentifiedImageError) as error:
        raise ConfigError(f"{song_path}: {key}: cannot read image {image_path} ({error})") from None


def _describe(error: ValidationError) -> str:
    lines = []
    for item in error.errors():
        where = ".".join(str(part) for part in item["loc"]) or "(file)"
        lines.append(f"  {where}: {item['msg']}")
    return "\n".join(lines)
