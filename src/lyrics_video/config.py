"""The song file: one TOML file per song, with paths relative to it."""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt, ValidationError

from lyrics_video.design import Design, load_design
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


class FontSettings(_Section):
    default: Path | None = None
    """The font of every part of the video that does not name its own."""


class SpectrumSettings(_Section):
    preset: str = "default"
    """An audio-spectrum-app preset: a name, or a path to a preset file."""
    set: list[str] = []
    """Overrides like audio-spectrum-app's `--set`, applied after the design's."""


class VideoSettings(_Section):
    width: PositiveInt = 1920
    height: PositiveInt = 1080
    fps: PositiveFloat = 30.0


class SongFile(_Section):
    lyrics: Path = Path("lyrics.txt")
    audio: Path | None = None
    title: str = ""
    subtitle: str = ""
    credits: list[str] = []
    background_image: Path | None = None
    design: str | dict[str, Any] = "classic"
    """A design name or file, or a table with `name` and overrides of the design's parts."""
    fonts: FontSettings = FontSettings()
    spectrum: SpectrumSettings = SpectrumSettings()
    video: VideoSettings = VideoSettings()
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
    audio: Path | None = None
    title: str = ""
    subtitle: str = ""
    credits: tuple[str, ...] = ()
    background_image: Path | None = None
    default_font: Path | None = None
    design: Design | None = None
    spectrum_preset: str = "default"
    spectrum_set: tuple[str, ...] = ()
    video: VideoSettings = field(default_factory=VideoSettings)


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
        audio=resolve_path(song.audio, base) if song.audio else None,
        title=song.title,
        subtitle=song.subtitle,
        credits=tuple(song.credits),
        background_image=resolve_path(song.background_image, base) if song.background_image else None,
        default_font=resolve_path(song.fonts.default, base) if song.fonts.default else None,
        design=_design(song.design, base, path),
        spectrum_preset=_preset_name_or_path(song.spectrum.preset, base),
        spectrum_set=tuple(song.spectrum.set),
        video=song.video,
    )


def _design(value: str | dict[str, Any], base: Path, song_path: Path) -> Design:
    if isinstance(value, str):
        name, overrides = value, {}
    else:
        overrides = dict(value)
        name = overrides.pop("name", "classic")
    try:
        design = load_design(name, overrides, base)
    except ConfigError as error:
        raise ConfigError(f"{song_path}: {error}") from None
    fonts = {
        part: getattr(design, part).model_copy(update={"font": resolve_path(getattr(design, part).font, base)})
        for part in ("title", "caption", "credits")
        if getattr(design, part).font is not None
    }
    return design.model_copy(update=fonts)


def _preset_name_or_path(value: str, base: Path) -> str:
    if value.endswith(".toml"):
        return str(resolve_path(Path(value), base))
    return value


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
