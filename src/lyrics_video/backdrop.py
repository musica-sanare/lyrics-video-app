"""The picture under the spectrum, as an audio-spectrum-app backdrop (ADR-001).

Everything that is the same in every frame (background and title) is composed once per process and size, also with
the credits fully shown; per frame only the captions of the moment (at most two, while one replaces the other) are
blended over a copy, and the credits only while they fade. Credits lie under the captions.
"""

import bisect
import math
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from lyrics_video.config import Song
from lyrics_video.design import CaptionStyle, Design, scale_for
from lyrics_video.layers import Layer, WideLayer, background, blend, caption_layer, credits_layer, title_layer, widen
from lyrics_video.timing import TimedLine


@dataclass(frozen=True)
class TimedCaption:
    """A caption sung from `start` to `end` (seconds of the song).

    `end` is a pause, the next caption's start, or the end of the song. The design's lead and fades decide when the
    caption is actually shown.
    """

    start: float
    end: float
    rows: tuple[str, ...]


def timed_captions(lines: list[TimedLine], duration: float) -> list[TimedCaption]:
    """The captions of the timed lines; lines not timed yet are left out."""
    timed = [line for line in lines if line.start is not None]
    captions = []
    for index, line in enumerate(timed):
        following = timed[index + 1].start if index + 1 < len(timed) else duration
        captions.append(TimedCaption(line.start, line.end if line.end is not None else following, line.rows))
    return captions


@dataclass(frozen=True)
class _Window:
    """When a caption is shown, fades included."""

    start: float
    end: float


def caption_windows(captions: list[TimedCaption], style: CaptionStyle, duration: float) -> list[_Window]:
    """Shown from `lead` before the sung start, fading in over `fade`.

    Between captions sung back to back the old one fades out while the new one fades in ("crossfade"), or before
    it ("sequential"). At a pause the caption fades out after its end; the last one is gone at the end of the song.
    A window never reaches the start of the caption after next, so at most two captions are shown at once.
    """
    lead, fade = style.lead_seconds, style.fade_seconds
    starts = [caption.start - lead for caption in captions]
    windows = []
    for index, caption in enumerate(captions):
        if index + 1 == len(captions):
            end = min(caption.end + fade, max(duration, caption.end))
        elif style.transition == "crossfade":
            end = min(caption.end, starts[index + 1]) + fade
        else:
            end = min(caption.end + fade, starts[index + 1])
        if index + 2 < len(captions):
            end = min(end, starts[index + 2])
        windows.append(_Window(starts[index], end))
    return windows


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


# Captions kept ready to blend in each process; render workers take consecutive frames, so a few are enough.
WIDE_CAPTIONS = 3


@dataclass
class _Prepared:
    base: np.ndarray
    credits: Layer | None
    with_credits: np.ndarray | None
    captions: dict[tuple[str, ...], Layer]
    wide: OrderedDict[tuple[str, ...], WideLayer] = field(default_factory=OrderedDict)


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
        self.duration = duration
        self.set_captions(captions)
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

    def set_captions(self, captions: list[TimedCaption]) -> None:
        """Show other captions; pictures already built are kept (the sync page changes times between stills)."""
        self.captions = sorted(captions, key=lambda caption: caption.start)
        self._windows = caption_windows(self.captions, self.design.caption, self.duration)
        self._window_starts = [window.start for window in self._windows]

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
        for caption, opacity in self.caption_opacities(seconds):
            blend(picture, self._wide_caption(prepared, caption.rows, width, height), opacity)
        return picture

    def caption_opacities(self, seconds: float) -> list[tuple[TimedCaption, float]]:
        """The captions shown at `seconds` and their opacities, the older first; at most two."""
        latest = bisect.bisect_right(self._window_starts, seconds) - 1
        shown = []
        for index in range(max(latest - 1, 0), latest + 1):
            window = self._windows[index]
            opacity = fade_opacity(seconds, window.start, window.end, self.design.caption.fade_seconds)
            if opacity > 0:
                shown.append((self.captions[index], opacity))
        return shown

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

    def _wide_caption(self, prepared: _Prepared, rows: tuple[str, ...], width: int, height: int) -> WideLayer:
        if rows in prepared.wide:
            prepared.wide.move_to_end(rows)
        else:
            prepared.wide[rows] = widen(self._caption(prepared, rows, width, height))
            if len(prepared.wide) > WIDE_CAPTIONS:
                prepared.wide.popitem(last=False)
        return prepared.wide[rows]
