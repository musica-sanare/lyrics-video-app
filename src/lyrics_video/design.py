"""Designs: how the parts of a frame look. Sizes are in pixels of a 1080-pixel-high frame and scale with the height.

A design is a built-in name (a TOML file in `designs/`) or a path to a TOML file, with overrides from the song file's
`[design]` section merged over it.
"""

import re
import tomllib
from importlib import resources
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from lyrics_video.errors import ConfigError

REFERENCE_HEIGHT = 1080
HEX_COLOR = re.compile(r"#([0-9a-fA-F]{6})")


def _parse_color(value: Any) -> Any:
    if isinstance(value, str):
        match = HEX_COLOR.fullmatch(value)
        if not match:
            raise ValueError(f"{value!r} is not a #RRGGBB color")
        digits = match.group(1)
        return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
    return value


Color = Annotated[tuple[int, int, int], BeforeValidator(_parse_color)]
Fraction = Annotated[float, Field(ge=0.0, le=1.0)]
Pixels = Annotated[float, Field(ge=0.0)]


class _Part(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Shadow(_Part):
    blur: Pixels = 0.0
    """Blur radius of a soft shadow behind text; 0 turns it off."""
    offset: tuple[float, float] = (0.0, 3.0)
    color: Color = (0, 0, 0)
    opacity: Fraction = 0.6


class BackgroundStyle(_Part):
    focus: tuple[Fraction, Fraction] = (0.5, 0.5)
    """The point of the image kept in view when it is cropped, as fractions of its width and height."""
    dim: Fraction = 0.0
    """How much darker the image is drawn: 0 unchanged, 1 black."""
    blur: Pixels = 0.0


class TitleStyle(_Part):
    enabled: bool = True
    position: Literal["top-center", "top-left"] = "top-center"
    font: Path | None = None
    """A font for the title only; by default the song file's `fonts.default`."""
    size: Pixels = 72.0
    subtitle_size: Pixels = 36.0
    color: Color = (255, 255, 255)
    margin: Pixels = 64.0
    """Distance from the top edge (and the left edge for "top-left")."""
    gap: Pixels = 12.0
    """Space between the title and the subtitle."""
    shadow: Shadow = Shadow()


class CaptionStyle(_Part):
    style: Literal["band"] = "band"
    """"band": today's caption images at video resolution, an opaque band along the bottom edge."""
    align: Literal["left"] = "left"
    font: Path | None = None
    text_color: Color = (255, 255, 255)
    band_color: Color = (0, 0, 0)
    band_opacity: Fraction = 1.0
    band_height: Pixels = Field(default=309.0, gt=0)
    """Today's 1440 x 232 caption images are 309 pixels high when scaled to the frame width."""
    fade_seconds: Pixels = 2.0


class CreditsStyle(_Part):
    enabled: bool = True
    font: Path | None = None
    size: Pixels = 44.0
    color: Color = (255, 255, 255)
    line_spacing: float = Field(default=1.6, ge=1.0)
    dim: Fraction = 0.5
    """How much the frame is darkened behind the credits."""
    show_seconds: Pixels = 6.0
    """How long the credits stay at the start and at the end of the song."""
    fade_seconds: Pixels = 1.5
    shadow: Shadow = Shadow()


class SpectrumStyle(_Part):
    set: list[str] = []
    """Preset overrides for audio-spectrum-app, like its `--set`, applied before the song file's."""


class Design(_Part):
    name: str
    background: BackgroundStyle = BackgroundStyle()
    title: TitleStyle = TitleStyle()
    caption: CaptionStyle = CaptionStyle()
    credits: CreditsStyle = CreditsStyle()
    spectrum: SpectrumStyle = SpectrumStyle()


def builtin_design_names() -> list[str]:
    folder = resources.files("lyrics_video") / "designs"
    return sorted(item.name.removesuffix(".toml") for item in folder.iterdir() if item.name.endswith(".toml"))


def load_design(name_or_path: str, overrides: dict[str, Any] | None = None, base: Path = Path(".")) -> Design:
    """A built-in design by name, or a design file (relative to `base`), with `overrides` merged over it."""
    if name_or_path in builtin_design_names():
        text = (resources.files("lyrics_video") / "designs" / f"{name_or_path}.toml").read_text(encoding="utf-8")
        source = f"design {name_or_path!r}"
    else:
        path = Path(name_or_path).expanduser()
        path = path if path.is_absolute() else base / path
        if not path.is_file():
            known = ", ".join(builtin_design_names())
            raise ConfigError(f"unknown design {name_or_path!r}: not a built-in design ({known}) and no file at {path}")
        text = path.read_text(encoding="utf-8")
        source = str(path)
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{source}: cannot read ({error})") from None
    data.setdefault("name", Path(name_or_path).stem)
    merged = _merge(data, overrides or {})
    try:
        return Design.model_validate(merged)
    except ValidationError as error:
        details = "\n".join(
            f"  design.{'.'.join(str(p) for p in item['loc'])}: {item['msg']}" for item in error.errors()
        )
        raise ConfigError(f"{source}: invalid design\n{details}") from None


def scale_for(height: int) -> float:
    return height / REFERENCE_HEIGHT


def _merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged
