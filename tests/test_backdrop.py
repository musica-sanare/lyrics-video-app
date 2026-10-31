import math
import pickle
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pytest
from PIL import Image
from signals import write_silence, write_sine

from audio_spectrum import load_preset, override_preset, render_stills
from lyrics_video.backdrop import LyricsBackdrop, TimedCaption, fade_opacity
from lyrics_video.design import load_design
from lyrics_video.errors import ConfigError

WIDTH, HEIGHT = 480, 270


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(9.9, 0.0), (10.0, 0.0), (10.5, 0.25), (12.0, 1.0), (19.0, 0.5), (20.0, 0.0)],
)
def test_fade_opacity(seconds, expected):
    assert fade_opacity(seconds, 10.0, 20.0, 2.0) == pytest.approx(expected)


def test_short_captions_fade_over_half_their_time():
    assert fade_opacity(10.5, 10.0, 11.0, 2.0) == pytest.approx(1.0)
    assert fade_opacity(10.25, 10.0, 11.0, 2.0) == pytest.approx(0.5)


def test_infinite_ends_do_not_fade():
    assert fade_opacity(-1e9, -math.inf, math.inf, 2.0) == 1.0
    assert fade_opacity(0.0, -math.inf, 6.0, 1.5) == 1.0


def make_backdrop(tmp_path, font, credits=(), captions=None, **design):
    Image.new("RGB", (800, 600), (40, 80, 120)).save(tmp_path / "bg.png")
    return LyricsBackdrop(
        design=load_design("classic", design),
        captions=captions if captions is not None else [TimedCaption(2.0, 6.0, ("一行目", "二行目"))],
        duration=20.0,
        background_image=tmp_path / "bg.png",
        title="Title",
        credits=credits,
        default_font=font,
    )


def band_row(frame):
    return frame[-5]


def test_frames_have_the_right_shape_and_type(tmp_path, sans_font):
    frame = make_backdrop(tmp_path, sans_font).frame(0, 0.0, WIDTH, HEIGHT)

    assert frame.shape == (HEIGHT, WIDTH, 3)
    assert frame.dtype == np.uint8


def test_the_caption_shows_only_in_its_time_and_fades(tmp_path, sans_font):
    backdrop = make_backdrop(tmp_path, sans_font)
    background = (40, 80, 120)

    before = backdrop.frame(0, 1.0, WIDTH, HEIGHT)
    fading = backdrop.frame(0, 2.5, WIDTH, HEIGHT)
    shown = backdrop.frame(0, 4.0, WIDTH, HEIGHT)

    assert band_row(before)[-1].tolist() == list(background)
    assert band_row(shown)[-1].tolist() == [0, 0, 0]
    assert 0 < band_row(fading)[-1][2] < background[2]


def test_credits_at_the_start_and_the_end(tmp_path, sans_font):
    backdrop = make_backdrop(tmp_path, sans_font, credits=("Music: Someone",), captions=[])

    assert backdrop.credits_opacity(0.0) == 1.0
    assert backdrop.credits_opacity(10.0) == 0.0
    assert backdrop.credits_opacity(19.9) == 1.0
    assert backdrop.frame(0, 0.0, WIDTH, HEIGHT)[0, 0].sum() < backdrop.frame(0, 10.0, WIDTH, HEIGHT)[0, 0].sum()


def test_frames_do_not_change_the_cached_pictures(tmp_path, sans_font):
    backdrop = make_backdrop(tmp_path, sans_font)

    first = backdrop.frame(0, 1.0, WIDTH, HEIGHT)
    first[:] = 0
    backdrop.frame(0, 4.0, WIDTH, HEIGHT)[:] = 0

    assert backdrop.frame(0, 1.0, WIDTH, HEIGHT).any()


def frame_in_another_process(backdrop, seconds):
    return backdrop.frame(0, seconds, WIDTH, HEIGHT)


def test_picklable_and_the_same_in_other_processes(tmp_path, sans_font):
    backdrop = make_backdrop(tmp_path, sans_font, credits=("Music: Someone",))
    expected = [backdrop.frame(0, seconds, WIDTH, HEIGHT) for seconds in (0.5, 4.0, 10.0)]

    copied = pickle.loads(pickle.dumps(backdrop))
    with ProcessPoolExecutor(max_workers=1) as pool:
        others = list(pool.map(frame_in_another_process, [backdrop] * 3, (0.5, 4.0, 10.0)))

    assert len(pickle.dumps(backdrop)) < 10_000, "pictures are not pickled"
    for seconds, frame, other in zip((0.5, 4.0, 10.0), expected, others, strict=True):
        assert np.array_equal(copied.frame(0, seconds, WIDTH, HEIGHT), frame)
        assert np.array_equal(other, frame)


def test_a_still_is_the_backdrop_with_the_spectrum_drawn_over_it(tmp_path, sans_font):
    backdrop = make_backdrop(tmp_path, sans_font, credits=("Music: Someone",))
    silent = override_preset(load_preset("default"), ["look.min_height_px=0"])

    silence, tone = write_silence(tmp_path / "silence.wav", 8.0), write_sine(tmp_path / "tone.wav", seconds=8.0)

    [still] = render_stills(silence, silent, [4.0], WIDTH, HEIGHT, 30, backdrop=backdrop)
    [loud] = render_stills(tone, silent, [4.0], WIDTH, HEIGHT, 30, backdrop=backdrop)

    assert np.array_equal(still, backdrop.frame(120, 4.0, WIDTH, HEIGHT))
    assert not np.array_equal(loud, still), "with sound the spectrum is drawn on top"


def test_errors_surface_when_preparing(tmp_path):
    backdrop = make_backdrop(tmp_path, None)

    with pytest.raises(ConfigError, match="no font for the title"):
        backdrop.prepare(WIDTH, HEIGHT)
