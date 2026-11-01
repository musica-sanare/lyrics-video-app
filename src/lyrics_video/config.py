"""The song file: one TOML file per song, with paths relative to it."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomlkit
from audio_spectrum import AudioSpectrumError, Preset, load_preset, override_preset, preset_to_toml
from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt, ValidationError

from lyrics_video.design import Design, check_design_name, load_design, user_design_folder
from lyrics_video.errors import ConfigError, OutputExistsError
from lyrics_video.lyrics import read_lyrics
from lyrics_video.output import write_text

# Sections of the caption image commands, removed in version 0.2.0 (Phase 3 plan, "Removing captions and compare").
REMOVED_SECTIONS = ("captions", "compare")


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FontSettings(_Section):
    default: Path | None = None
    """The font of every part of the video that does not name its own."""


class SpectrumSettings(_Section):
    preset: str | None = None
    """An audio-spectrum-app preset: a name, or a path to a preset file. Wins over the design's; `default` when
    neither names one."""
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
    design_name: str = "soft"
    """The design as the song file names it: a built-in name or a design file."""
    design_overrides: dict[str, Any] = field(default_factory=dict)
    spectrum_preset: str | None = None
    """The song file's own preset, which wins over the design's."""
    spectrum_set: tuple[str, ...] = ()
    video: VideoSettings = field(default_factory=VideoSettings)


def resolve_path(value: Path, base: Path) -> Path:
    path = value.expanduser()
    return path if path.is_absolute() else base / path


def load_song(path: Path) -> Song:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError(f"{path}: song file not found") from None
    except (OSError, UnicodeDecodeError) as error:
        raise ConfigError(f"{path}: cannot read the song file ({error})") from None
    return parse_song(text, path)


def parse_song(text: str, path: Path) -> Song:
    """The song file's text, read as the song file at `path` (paths in it are relative to its folder)."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
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
    loaded = Song(
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
        design_name=_design_name(song.design)[0],
        design_overrides=_design_name(song.design)[1],
        spectrum_preset=_preset_name_or_path(song.spectrum.preset, base) if song.spectrum.preset else None,
        spectrum_set=tuple(song.spectrum.set),
        video=song.video,
    )
    spectrum_preset(loaded)  # so a wrong preset or preset key fails now, with the song file's name
    return loaded


def spectrum_preset(song: Song, design: Design | None = None) -> Preset:
    """The spectrum of `song` drawn with `design` (the song's by default).

    From the base to the most specific: the song file's `[spectrum] preset`, else the design's, else `default`; then
    the design's changes; then the song file's `[spectrum] set`. audio-spectrum-app checks every change.
    """
    design = design or song.design
    name = song.spectrum_preset
    if name is None:
        name = _preset_name_or_path(design.spectrum.preset, song.path.parent) if design.spectrum.preset else "default"
    try:
        return override_preset(load_preset(name), [*design.spectrum.overrides(), *song.spectrum_set])
    except AudioSpectrumError as error:
        raise ConfigError(f"{song.path}: spectrum of design {design.name!r}: {error}") from None


def preset_values(name: str, song: Song) -> dict[str, Any]:
    """Every key of a preset (a name, or a file relative to the song file) as a preset file writes it."""
    try:
        return tomllib.loads(preset_to_toml(load_preset(_preset_name_or_path(name, song.path.parent)), full=True))
    except AudioSpectrumError as error:
        raise ConfigError(f"{song.path}: {error}") from None


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


def write_design(path: Path, name: str, overrides: dict[str, Any]) -> Song:
    """Replace the song file's design with `name` and `overrides`, as a `[design]` table; keep a `.bak` copy.

    Everything outside `[design]` keeps its text and comments. The new file is loaded before it is written, so a
    design that does not load changes nothing. Returns the song as it is now.
    """
    text = path.read_text(encoding="utf-8")
    document = tomlkit.parse(text)
    table = _table({"name": name, **overrides})
    if isinstance(document.get("design"), dict):
        document["design"] = table
    else:
        # A design given by name is a key above the first table; a table goes at the end instead.
        document.pop("design", None)
        if not document.as_string().endswith("\n\n"):
            document.add(tomlkit.nl())
        document.add("design", table)
    new_text = tomlkit.dumps(document)
    song = parse_song(new_text, path)
    write_text(path, new_text, backup=True)
    return song


# The files a song file names, by key; the page lets the owner choose each again.
SONG_FILES = ("audio", "background_image", "lyrics")
# Top-level keys the page writes; the rest of the song file is kept as it is.
SONG_SETTINGS = ("title", "credits", *SONG_FILES)


def missing_files(song: Song) -> dict[str, str]:
    """The files the song file names that do not exist, by key (`fonts.default` for the font)."""
    files = {"audio": song.audio, "background_image": song.background_image, "lyrics": song.lyrics}
    files["fonts.default"] = song.default_font
    return {key: str(path) for key, path in files.items() if path is not None and not path.is_file()}


def path_in_song_file(path: Path, folder: Path) -> str:
    """How a song file in `folder` names `path`: relative inside the folder, else absolute with `~` for home."""
    path = path.expanduser().resolve()
    if path.is_relative_to(folder.resolve()):
        return str(path.relative_to(folder.resolve()))
    home = Path.home()
    return f"~/{path.relative_to(home)}" if path.is_relative_to(home) else str(path)


def create_song(
    path: Path,
    audio: Path,
    background_image: Path,
    lyrics: Path,
    title: str,
    credits: list[str],
    design: str,
    font: Path | None = None,
) -> Song:
    """Write a new song file at `path` that names the files where they are; nothing is copied.

    The lyrics are read first, so a problem in them stops before anything is written. An existing song file is never
    replaced. The timing file will be `<song file name>.lrc` next to it.
    """
    if path.exists():
        raise OutputExistsError(f"{path} exists; choose another name or folder")
    for key, file in (("audio", audio), ("background image", background_image), ("lyrics", lyrics)):
        if not file.is_file():
            raise ConfigError(f"the {key} file {file} does not exist")
    read_lyrics(lyrics, ";")
    folder = path.parent
    document = tomlkit.document()
    document.add(tomlkit.comment("A song file made by lyrics-video's New song page. Paths are relative to this file."))
    document.add("title", title)
    document.add("credits", credits)
    document.add("audio", path_in_song_file(audio, folder))
    document.add("background_image", path_in_song_file(background_image, folder))
    document.add("lyrics", path_in_song_file(lyrics, folder))
    document.add("timing", f"{path.stem}.lrc")
    document.add("design", design)
    if font is not None:
        document.add(tomlkit.nl())
        document.add("fonts", _table({"default": path_in_song_file(font, folder)}))
    text = tomlkit.dumps(document)
    song = parse_song(text, path)
    folder.mkdir(parents=True, exist_ok=True)
    write_text(path, text)
    return song


def write_song_settings(path: Path, values: dict[str, Any]) -> Song:
    """Change the song file's title, credits, files (`SONG_SETTINGS`) and `font` (`fonts.default`, None to remove).

    File paths are written as `path_in_song_file` names them. Everything else, comments included, stays; the new text
    is loaded before it is written, and the previous file is kept as `.bak`.
    """
    text = path.read_text(encoding="utf-8")
    document = tomlkit.parse(text)
    missing = []
    for key in SONG_SETTINGS:
        if key not in values:
            continue
        value = values[key]
        if key in SONG_FILES:
            value = path_in_song_file(Path(value), path.parent)
        if key in document:
            document[key] = value
        else:
            missing.append(f"{key} = {tomlkit.item(value).as_string()}\n")
    if "font" in values:
        fonts = document.get("fonts")
        if values["font"] is None:
            if isinstance(fonts, dict):
                fonts.pop("default", None)
        elif isinstance(fonts, dict):
            fonts["default"] = path_in_song_file(Path(values["font"]), path.parent)
        else:
            document.add("fonts", _table({"default": path_in_song_file(Path(values["font"]), path.parent)}))
    # Top-level keys must come before the first table, so missing ones go at the top.
    new_text = "".join(missing) + tomlkit.dumps(document)
    song = parse_song(new_text, path)
    write_text(path, new_text, backup=True)
    return song


def save_user_design(song: Song, design: Design, name: str, overwrite: bool = False) -> Path:
    """Save `design` (as drawn for `song`) as the user design `name`, which any song file can then name.

    Only keys that differ from the defaults are written. Text parts without a font of their own get the song's
    `fonts.default`, so the design carries its fonts. Font and preset files become absolute paths (with `~` for the
    home folder), so the design works from any song folder. Replacing a design needs `overwrite` and keeps the
    previous file as `.bak`.
    """
    check_design_name(name)
    if song.default_font is not None:
        fonts = {
            part: getattr(design, part).model_copy(update={"font": song.default_font})
            for part in ("title", "caption", "credits")
            if getattr(design, part).font is None
        }
        design = design.model_copy(update=fonts)
    path = user_design_folder() / f"{name}.toml"
    if path.exists() and not overwrite:
        raise OutputExistsError(f"the design {name!r} exists")
    data = design.model_dump(mode="json", exclude_defaults=True)
    data["name"] = name
    preset = design.spectrum.preset
    if preset and preset.endswith(".toml"):
        data["spectrum"]["preset"] = _preset_name_or_path(preset, song.path.parent)
    text = tomlkit.dumps(_portable(data))
    Design.model_validate(tomllib.loads(text))  # what is written reads back as a design
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text(path, text, backup=True)
    return path


def _portable(value: Any, key: str = "") -> Any:
    """Colors as `#RRGGBB` and paths under the home folder with `~`, as people write them in design files."""
    if isinstance(value, dict):
        return {item: _portable(inner, item) for item, inner in value.items()}
    if (key == "color" or key.endswith("_color")) and isinstance(value, list) and len(value) == 3:
        return "#" + "".join(f"{channel:02X}" for channel in value)
    if isinstance(value, str) and key in {"font", "preset"}:
        home = str(Path.home())
        return "~" + value[len(home):] if value.startswith(home + "/") else value
    return value


def _table(data: dict[str, Any]) -> tomlkit.items.Table:
    table = tomlkit.table()
    for key, value in data.items():
        table.add(key, _table(value) if isinstance(value, dict) else value)
    return table


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
