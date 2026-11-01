"""Whole videos: the backdrop under the spectrum, rendered by audio-spectrum-app's `render_video` (ADR-001)."""

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from audio_spectrum import (
    AudioSpectrumError,
    Cancelled,
    EncodeSettings,
    Preview,
    RenderJob,
    RenderResult,
    load_preset,
    override_preset,
    render_video,
)

from lyrics_video.backdrop import LyricsBackdrop, timed_captions
from lyrics_video.config import Song, song_design
from lyrics_video.errors import ConfigError, OutputExistsError, SpectrumError
from lyrics_video.timing import TimedLine, check_inside, read_lrc

VIDEOS_DIR = "videos"
# H.264 quality. audio-spectrum-app's 14 keeps thin lines clean for chroma keying, which a finished video does not
# need; 18 looks the same and gives smaller files.
DEFAULT_CRF = 18
SUFFIXES = {"h264": ".mp4", "prores": ".mov"}
# The preview before rendering: small, light and silent (the page plays it in step with the song's audio).
PREVIEW_HEIGHT = 540
PREVIEW_FPS = 15.0
PREVIEW_ENCODE = EncodeSettings(crf=26, x264_preset="veryfast", include_audio=False)

Codec = Literal["h264", "prores"]
Progress = Callable[[int, int], None]
CancelCheck = Callable[[], bool]


@dataclass(frozen=True)
class PreparedRender:
    """A render checked and ready to start: everything that can fail quickly has been tried."""

    job: RenderJob
    title: str
    design: str
    song_seconds: float
    timed: int
    untimed: list[TimedLine]


def default_output(song: Song, start: float = 0.0, duration: float | None = None, codec: Codec = "h264") -> Path:
    """`videos/<song file name>.mp4` next to the song file; a part adds its times, as `song_60s-75s.mp4`."""
    name = song.path.stem
    if start > 0 or duration is not None:
        end = f"{start + duration:g}s" if duration is not None else "end"
        name += f"_{start:g}s-{end}"
    return song.path.parent / VIDEOS_DIR / f"{name}{SUFFIXES[codec]}"


def prepare_render(
    song: Song,
    output: Path | None = None,
    overwrite: bool = False,
    start: float = 0.0,
    duration: float | None = None,
    design: str | None = None,
    workers: int = 0,
    codec: Codec = "h264",
    crf: int = DEFAULT_CRF,
) -> PreparedRender:
    """Check everything before the long part: the song file, the output, the times, the pictures and fonts.

    The backdrop draws its pictures here once, so a missing image or font fails before any worker starts.
    """
    if song.audio is None:
        raise ConfigError(f"{song.path}: audio is not set (the song file for the spectrum)")
    if song.timing is None:
        raise ConfigError(f"{song.path}: timing is not set; time the captions with `lyrics-video sync` first")
    output = output.expanduser() if output is not None else default_output(song, start, duration, codec)
    if output.suffix.lower() != SUFFIXES[codec]:
        raise ConfigError(f"{output}: a {codec} video needs the {SUFFIXES[codec]} extension")
    if output.exists() and not overwrite:
        raise OutputExistsError(f"{output} exists; nothing was rendered (use --overwrite to replace it)")
    chosen = song_design(song.path, design, song.design_overrides) if design else song.design
    timing = read_lrc(song.timing, song.separator)
    video = song.video
    try:
        song_seconds = Preview(song.audio, video.fps).duration
        if start >= song_seconds:
            raise SpectrumError(f"the start {start:g} s is outside the audio (the song lasts {song_seconds:.2f} s)")
        check_inside(timing, song_seconds, str(song.timing))
        captions = timed_captions(timing, song_seconds)
        backdrop = LyricsBackdrop.for_song(dataclasses.replace(song, design=chosen), captions, song_seconds)
        backdrop.prepare(video.width, video.height)
        preset = override_preset(load_preset(song.spectrum_preset), [*chosen.spectrum.set, *song.spectrum_set])
    except AudioSpectrumError as error:
        raise SpectrumError(str(error)) from None
    job = RenderJob(
        audio_path=song.audio,
        output_path=output,
        preset=preset,
        width=video.width,
        height=video.height,
        fps=video.fps,
        encode=EncodeSettings(codec=codec, crf=crf),
        workers=workers,
        overwrite=overwrite,
        start=start,
        duration=duration,
        backdrop=backdrop,
    )
    untimed = [line for line in timing if line.start is None]
    return PreparedRender(job, song.title, chosen.name, song_seconds, len(captions), untimed)


def preview_size(song: Song) -> tuple[int, int, float]:
    """The preview's width, height and frame rate: at most 540 pixels high and 15 frames a second (Phase 4 plan)."""
    video = song.video
    height = min(PREVIEW_HEIGHT, video.height)
    width = max(2, round(video.width * height / video.height / 2) * 2)
    return width, height - height % 2, min(PREVIEW_FPS, video.fps)


def prepare_preview(song: Song, lines: list[TimedLine], song_seconds: float, output: Path) -> PreparedRender:
    """A quick, silent, low-resolution video of the whole song from `lines` (saved or not), replacing `output`.

    The backdrop and the spectrum scale with the frame height, so the preview shows the video's design, captions and
    spectrum; only text and thin lines are softer.
    """
    if song.audio is None:
        raise ConfigError(f"{song.path}: audio is not set (the song file for the spectrum)")
    width, height, fps = preview_size(song)
    try:
        check_inside(lines, song_seconds, "timing")
        captions = timed_captions(lines, song_seconds)
        backdrop = LyricsBackdrop.for_song(song, captions, song_seconds)
        backdrop.prepare(width, height)
        preset = override_preset(load_preset(song.spectrum_preset), [*song.design.spectrum.set, *song.spectrum_set])
    except AudioSpectrumError as error:
        raise SpectrumError(str(error)) from None
    job = RenderJob(
        audio_path=song.audio,
        output_path=output,
        preset=preset,
        width=width,
        height=height,
        fps=fps,
        encode=PREVIEW_ENCODE,
        overwrite=True,
        backdrop=backdrop,
    )
    untimed = [line for line in lines if line.start is None]
    return PreparedRender(job, song.title, song.design.name, song_seconds, len(captions), untimed)


def render(
    prepared: PreparedRender, progress: Progress | None = None, cancel: CancelCheck | None = None
) -> RenderResult:
    """Render the video; a failed, cancelled or interrupted render leaves no file. `Cancelled` passes through."""
    prepared.job.output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return render_video(prepared.job, progress, cancel)
    except Cancelled:
        raise
    except AudioSpectrumError as error:
        raise SpectrumError(str(error)) from None
