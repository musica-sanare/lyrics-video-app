"""The song file: one TOML file per song, with paths relative to it."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt, ValidationError

from lyrics_video.design import Design, load_design
from lyrics_video.errors import ConfigError

# Sections of the caption image commands, removed in version 0.2.0 (Phase 3 plan, "Removing captions and compare").
REMOVED_SECTIONS = ("captions", "compare")


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


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
    separator: str = Field(default=";", min_length=1)
    """Splits a caption into two rows, in the lyrics and the timing file."""
    timing: Path | None = None
    """The timed lyrics (LRC); without it, stills show one chosen caption."""
    audio: Path | None = None
    title: str = ""
    credits: list[str] = []
    background_image: Path | None = None
    design: str | dict[str, Any] = "soft"
    """A design name or file, or a table with `name` and overrides of the design's parts."""
    fonts: FontSettings = FontSettings()
    spectrum: SpectrumSettings = SpectrumSettings()
    video: VideoSettings = VideoSettings()


@dataclass(frozen=True)
class Song:
    path: Path
    lyrics: Path
    separator: str = ";"
    timing: Path | None = None
    audio: Path | None = None
    title: str = ""
    credits: tuple[str, ...] = ()
    background_image: Path | None = None
    default_font: Path | None = None
    design: Design | None = None
    design_overrides: dict[str, Any] = field(default_factory=dict)
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
    removed = [f"[{name}]" for name in REMOVED_SECTIONS if name in data]
    if removed:
        verb, pronoun = ("is", "it") if len(removed) == 1 else ("are", "them")
        raise ConfigError(
            f"{path}: {' and '.join(removed)} {verb} no longer used: the caption image commands were removed in version "
            f'0.2.0. Delete {pronoun}; if [captions] set a separator, write it at the top as separator = "...".'
        )
    try:
        song = SongFile.model_validate(data)
    except ValidationError as error:
        raise ConfigError(f"{path}: invalid song file\n{_describe(error)}") from None

    base = path.parent
    return Song(
        path=path,
        lyrics=resolve_path(song.lyrics, base),
        separator=song.separator,
        timing=resolve_path(song.timing, base) if song.timing else None,
        audio=resolve_path(song.audio, base) if song.audio else None,
        title=song.title,
        credits=tuple(song.credits),
        background_image=resolve_path(song.background_image, base) if song.background_image else None,
        default_font=resolve_path(song.fonts.default, base) if song.fonts.default else None,
        design=song_design(path, *_design_name(song.design)),
        design_overrides=_design_name(song.design)[1],
        spectrum_preset=_preset_name_or_path(song.spectrum.preset, base),
        spectrum_set=tuple(song.spectrum.set),
        video=song.video,
    )


def _design_name(value: str | dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if isinstance(value, str):
        return value, {}
    overrides = dict(value)
    return overrides.pop("name", "soft"), overrides


def song_design(song_path: Path, name: str, overrides: dict[str, Any]) -> Design:
    """The design `name` with the song file's overrides; paths are relative to the song file."""
    base = song_path.parent
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


def _describe(error: ValidationError) -> str:
    lines = []
    for item in error.errors():
        where = ".".join(str(part) for part in item["loc"]) or "(file)"
        lines.append(f"  {where}: {item['msg']}")
    return "\n".join(lines)
