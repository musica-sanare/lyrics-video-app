import math
import pickle
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pytest
from PIL import Image
from signals import write_silence, write_sine

from audio_spectrum import load_preset, override_preset, render_stills
from lyrics_video.backdrop import WIDE_CAPTIONS, LyricsBackdrop, TimedCaption, fade_opacity, timed_captions
from lyrics_video.design import load_design
from lyrics_video.errors import ConfigError
from lyrics_video.layers import blend
from lyrics_video.timing import TimedLine

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


def test_timed_captions_end_at_a_pause_the_next_start_or_the_song_end():
    lines = [TimedLine(("a",), 1.0), TimedLine(("b",), 2.0, 3.0), TimedLine(("not timed",)), TimedLine(("c",), 5.0)]

    assert timed_captions(lines, 9.0) == [
        TimedCaption(1.0, 2.0, ("a",)),
        TimedCaption(2.0, 3.0, ("b",)),
        TimedCaption(5.0, 9.0, ("c",)),
    ]


# Sung back to back from 10 s to 12 s and 12 s to 15 s, a pause, then from 20 s to the end of the song at 30 s.
SUNG = [TimedCaption(10.0, 12.0, ("A",)), TimedCaption(12.0, 15.0, ("B",)), TimedCaption(20.0, 30.0, ("C",))]


def opacities(seconds, captions=SUNG, transition="crossfade", **caption):
    design = load_design("soft", {"caption": {"transition": transition, **caption}})
    backdrop = LyricsBackdrop(design, captions, duration=30.0)
    return [(shown.rows[0], round(opacity, 6)) for shown, opacity in backdrop.caption_opacities(seconds)]


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (9.7, []),
        (9.8, []),
        (9.95, [("A", 0.5)]),
        (10.1, [("A", 1.0)]),
        (11.95, [("A", 0.5), ("B", 0.5)]),
        (12.2, [("B", 1.0)]),
        (15.0, [("B", 1.0)]),
        (15.15, [("B", 0.5)]),
        (15.3, []),
        (19.95, [("C", 0.5)]),
        (29.85, [("C", 0.5)]),
    ],
)
def test_lead_crossfade_and_fades_around_a_pause(seconds, expected):
    assert opacities(seconds) == expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(11.5, [("A", 1.0)]), (11.65, [("A", 0.5)]), (11.8, []), (11.95, [("B", 0.5)]), (15.15, [("B", 0.5)])],
)
def test_sequential_fades_the_old_caption_out_before_the_new_one(seconds, expected):
    assert opacities(seconds, transition="sequential") == expected


def test_lead_and_fade_are_settings():
    assert opacities(9.5, lead_seconds=1.0, fade_seconds=1.0) == [("A", 0.5)]
    assert opacities(10.0, lead_seconds=0.0, fade_seconds=0.0) == [("A", 1.0)]


def test_captions_shorter_than_their_fades_show_at_most_two_at_once():
    short = [TimedCaption(10.0 + i * 0.1, 10.1 + i * 0.1, (str(i),)) for i in range(5)]

    for step in range(200):
        assert len(opacities(9.5 + step * 0.01, captions=short)) <= 2
    assert opacities(9.95, captions=short) == [("0", 0.5), ("1", 0.5)]


def test_a_chosen_caption_shows_at_every_time():
    fixed = [TimedCaption(-math.inf, math.inf, ("A",))]

    assert opacities(0.0, captions=fixed) == [("A", 1.0)]
    assert opacities(29.99, captions=fixed) == [("A", 1.0)]


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
    fading = backdrop.frame(0, 1.9, WIDTH, HEIGHT)
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


def test_two_captions_are_blended_during_a_crossfade(tmp_path, sans_font):
    captions = [TimedCaption(2.0, 4.0, ("一行目",)), TimedCaption(4.0, 6.0, ("二行目",))]
    backdrop = make_backdrop(tmp_path, sans_font, captions=captions, caption={"transition": "crossfade"})
    prepared = backdrop._prepared_for(WIDTH, HEIGHT)
    [(_, old), (_, new)] = backdrop.caption_opacities(3.95)
    expected = prepared.base.copy()
    blend(expected, backdrop._caption(prepared, ("一行目",), WIDTH, HEIGHT), old)
    blend(expected, backdrop._caption(prepared, ("二行目",), WIDTH, HEIGHT), new)

    middle = backdrop.frame(0, 3.95, WIDTH, HEIGHT)

    assert np.array_equal(middle, expected)
    assert not np.array_equal(middle, backdrop.frame(0, 3.5, WIDTH, HEIGHT))
    assert not np.array_equal(middle, backdrop.frame(0, 4.5, WIDTH, HEIGHT))


def test_only_a_few_captions_are_kept_ready_to_blend(tmp_path, sans_font):
    captions = [TimedCaption(1.0 + i, 2.0 + i, (f"行{i}",)) for i in range(6)]
    backdrop = make_backdrop(tmp_path, sans_font, captions=captions)
    fresh = make_backdrop(tmp_path, sans_font, captions=captions)

    frames = [backdrop.frame(0, 1.5 + i, WIDTH, HEIGHT) for i in range(6)]

    assert len(backdrop._prepared_for(WIDTH, HEIGHT).wide) == WIDE_CAPTIONS
    assert np.array_equal(backdrop.frame(0, 1.5, WIDTH, HEIGHT), frames[0])
    assert np.array_equal(fresh.frame(0, 6.5, WIDTH, HEIGHT), frames[5])


def test_a_title_box_over_the_background(tmp_path, sans_font):
    title = {"margin": 40, "panel": {"color": "#000000", "opacity": 0.5, "blur": 0, "padding": [30, 20]}}
    backdrop = make_backdrop(tmp_path, sans_font, captions=[], title=title)

    frame = backdrop.frame(0, 10.0, WIDTH, HEIGHT)

    assert frame[-1, 0].tolist() == [40, 80, 120], "the background elsewhere"
    assert [40, 80, 120] != frame[int(40 * HEIGHT / 1080) + 2, WIDTH // 2].tolist(), "the box darkens the top"
