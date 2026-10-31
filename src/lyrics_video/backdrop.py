"""The picture under the spectrum, as an audio-spectrum-app backdrop (ADR-001).

Everything that is the same in every frame (background and title) is composed once per process and size, also with
the credits fully shown; per frame only the caption of the moment is blended over a copy, and the credits only while
they fade. Credits lie under the caption.
"""

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from lyrics_video.config import Song
from lyrics_video.design import Design, scale_for
from lyrics_video.layers import Layer, background, blend, caption_layer, credits_layer, title_layer


@dataclass(frozen=True)
class TimedCaption:
    """A caption shown from `start` to `end` (seconds of the song)."""

    start: float
    end: float
    rows: tuple[str, ...]


def fade_opacity(seconds: float, start: float, end: float, fade: float) -> float:
    """1 between `start` and `end`, rising over `fade` seconds after `start` and falling over `fade` before `end`.

    The fades shrink to half the shown time each when it is shorter than two fades; infinite ends have no fade.
    """
    if not start <= seconds < end:
        return 0.0
    fade = min(fade, (end - start) / 2)
    if fade <= 0:
        return 1.0
    rising = (seconds - start) / fade if math.isfinite(start) else 1.0
    falling = (end - seconds) / fade if math.isfinite(end) else 1.0
    return max(0.0, min(1.0, rising, falling))


@dataclass
class _Prepared:
    base: np.ndarray
    credits: Layer | None
    with_credits: np.ndarray | None
    captions: dict[tuple[str, ...], Layer]


class LyricsBackdrop:
    """Picklable: holds settings and paths only; pictures are built lazily in each process."""

    def __init__(
        self,
        design: Design,
        captions: list[TimedCaption],
        duration: float,
        background_image: Path | None = None,
        title: str = "",
        credits: tuple[str, ...] = (),
        default_font: Path | None = None,
    ):
        self.design = design
        self.captions = captions
        self.duration = duration
        self.background_image = background_image
        self.title = title
        self.credits = credits
        self.default_font = default_font
        self._prepared: dict[tuple[int, int], _Prepared] = {}

    @classmethod
    def for_song(cls, song: Song, captions: list[TimedCaption], duration: float) -> "LyricsBackdrop":
        return cls(
            design=song.design,
            captions=captions,
            duration=duration,
            background_image=song.background_image,
            title=song.title,
            credits=song.credits,
            default_font=song.default_font,
        )

    def __getstate__(self) -> dict:
        state = self.__dict__.copy()
        state["_prepared"] = {}
        return state

    def prepare(self, width: int, height: int) -> None:
        """Build the pictures for this frame size now, so errors (missing files or fonts) surface before rendering."""
        prepared = self._prepared_for(width, height)
        for caption in self.captions:
            self._caption(prepared, caption.rows, width, height)

    def frame(self, index: int, seconds: float, width: int, height: int) -> np.ndarray:
        prepared = self._prepared_for(width, height)
        credits = self.credits_opacity(seconds)
        if prepared.credits is None or credits <= 0:
            picture = prepared.base.copy()
        elif credits >= 1:
            picture = prepared.with_credits.copy()
        else:
            picture = prepared.base.copy()
            blend(picture, prepared.credits, credits)
        caption = self.caption_at(seconds)
        if caption is not None:
            opacity = fade_opacity(seconds, caption.start, caption.end, self.design.caption.fade_seconds)
            blend(picture, self._caption(prepared, caption.rows, width, height), opacity)
        return picture

    def caption_at(self, seconds: float) -> TimedCaption | None:
        for caption in self.captions:
            if caption.start <= seconds < caption.end:
                return caption
        return None

    def credits_opacity(self, seconds: float) -> float:
        """Credits are shown from the start and towards the end of the song, fading out and in."""
        style = self.design.credits
        if not self.credits or not style.enabled or style.show_seconds <= 0:
            return 0.0
        opening = fade_opacity(seconds, -math.inf, style.show_seconds, style.fade_seconds)
        closing = fade_opacity(seconds, self.duration - style.show_seconds, math.inf, style.fade_seconds)
        return max(opening, closing)

    def _prepared_for(self, width: int, height: int) -> _Prepared:
        if (width, height) not in self._prepared:
            design, scale = self.design, scale_for(height)
            style = design.background
            base = background(self.background_image, width, height, style.focus, style.dim, style.blur * scale)
            title = title_layer(self.title, design.title, self.default_font, width, height, scale)
            if title is not None:
                blend(base, title)
            credits = credits_layer(self.credits, design.credits, self.default_font, width, height, scale, base)
            with_credits = None
            if credits is not None:
                with_credits = base.copy()
                blend(with_credits, credits)
            self._prepared[(width, height)] = _Prepared(base, credits, with_credits, captions={})
        return self._prepared[(width, height)]

    def _caption(self, prepared: _Prepared, rows: tuple[str, ...], width: int, height: int) -> Layer:
        if rows not in prepared.captions:
            style, scale = self.design.caption, scale_for(height)
            layer = caption_layer(rows, style, self.default_font, width, height, scale, prepared.base)
            prepared.captions[rows] = layer
        return prepared.captions[rows]
