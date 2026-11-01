import io
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from audio_spectrum import Cancelled
from PIL import Image
from signals import write_sine

from lyrics_video import cli
from lyrics_video.cli import EXIT_FAILED, EXIT_INTERRUPTED, EXIT_OK, TextProgress, main
from lyrics_video.config import VideoSettings, load_song
from lyrics_video.render import default_output, prepare_render, preview_size, render

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")

WIDTH, HEIGHT, FPS = 320, 180, 10


def make_song(folder: Path, font: Path, extra: str = "") -> Path:
    write_sine(folder / "tone.wav", seconds=2.0)
    Image.new("RGB", (640, 480), (30, 60, 90)).save(folder / "bg.png")
    (folder / "lyrics.lrc").write_text("[00:00.30]一行目\n[00:01.00]二行目\n[00:01.60]\n三行目\n", encoding="utf-8")
    song = folder / "song.toml"
    song.write_text(
        'audio = "tone.wav"\ntiming = "lyrics.lrc"\nbackground_image = "bg.png"\ntitle = "Title"\n'
        f'credits = ["Music: Someone"]\n[fonts]\ndefault = "{font}"\n'
        f"[video]\nwidth = {WIDTH}\nheight = {HEIGHT}\nfps = {FPS}\n{extra}",
        encoding="utf-8",
    )
    return song


def probe(video: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_entries",
         "stream=codec_type,width,height,nb_read_frames,duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    )
    return {stream["codec_type"]: stream for stream in json.loads(result.stdout)["streams"]}


def decoded_frames(video: Path) -> np.ndarray:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    )
    return np.frombuffer(result.stdout, dtype=np.uint8).reshape(-1, HEIGHT, WIDTH, 3)


def test_the_whole_video_with_its_audio(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font)

    assert main(["render", str(song), "--workers", "1"]) == EXIT_OK

    video = tmp_path / "videos" / "song.mp4"
    streams = probe(video)
    assert (streams["video"]["width"], streams["video"]["height"]) == (WIDTH, HEIGHT)
    assert int(streams["video"]["nb_read_frames"]) == 2.0 * FPS
    assert float(streams["audio"]["duration"]) == pytest.approx(2.0, abs=0.05)
    out = capsys.readouterr().out
    assert "Song: Title (tone.wav, 2.0 s)" in out
    assert "Design: soft; timed captions: 2" in out
    assert "1 line(s) have no time yet" in out and "三行目" in out
    assert f"Wrote {video}" in out
    assert [p.name for p in (tmp_path / "videos").iterdir()] == ["song.mp4"]


def test_the_frames_of_the_video_are_the_stills(tmp_path, sans_font):
    song = make_song(tmp_path, sans_font)
    main(["render", str(song), "--workers", "1", "--crf", "0"])
    frames = decoded_frames(tmp_path / "videos" / "song.mp4")

    for index in (2, 5, 13):
        assert main(["still", str(song), "--time", f"{index / FPS:g}"]) == EXIT_OK
        still = np.asarray(Image.open(tmp_path / "stills" / f"soft_{index / FPS:g}s.png"), dtype=np.int16)
        # H.264 stores colors at half resolution, so frames match the stills closely but not exactly.
        assert np.abs(frames[index].astype(np.int16) - still).mean() < 3


def test_several_workers_through_the_console_script(tmp_path, sans_font):
    song = make_song(tmp_path, sans_font)
    main(["render", str(song), "--workers", "1", "--output", str(tmp_path / "one.mp4")])
    script = Path(sys.executable).parent / "lyrics-video"

    result = subprocess.run(
        [str(script), "render", str(song), "--workers", "2", "--output", str(tmp_path / "two.mp4")],
        capture_output=True, text=True,
    )

    assert result.returncode == EXIT_OK, result.stderr
    assert np.array_equal(decoded_frames(tmp_path / "one.mp4"), decoded_frames(tmp_path / "two.mp4"))


def test_a_part_of_the_song(tmp_path, sans_font):
    song = make_song(tmp_path, sans_font)

    assert main(["render", str(song), "--workers", "1", "--start", "0.5", "--duration", "1"]) == EXIT_OK

    video = tmp_path / "videos" / "song_0.5s-1.5s.mp4"
    assert int(probe(video)["video"]["nb_read_frames"]) == 1.0 * FPS


def test_default_names():
    song = SimpleNamespace(path=Path("work/my-song/song.toml"))

    assert default_output(song) == Path("work/my-song/videos/song.mp4")
    assert default_output(song, 60, 15) == Path("work/my-song/videos/song_60s-75s.mp4")
    assert default_output(song, 60) == Path("work/my-song/videos/song_60s-end.mp4")
    assert default_output(song, codec="prores") == Path("work/my-song/videos/song.mov")


@pytest.mark.parametrize(
    ("width", "height", "fps", "expected"),
    [
        (1920, 1080, 30, (960, 540, 15)),
        (1280, 720, 24, (960, 540, 15)),
        (3840, 2160, 60, (960, 540, 15)),
        (480, 270, 30, (480, 270, 15)),
        (1080, 1920, 30, (304, 540, 15)),
        (1920, 1080, 10, (960, 540, 10)),
    ],
)
def test_preview_size(width, height, fps, expected):
    song = SimpleNamespace(video=VideoSettings(width=width, height=height, fps=fps))

    assert preview_size(song) == expected


def test_refusals_before_any_work(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font)
    existing = tmp_path / "videos" / "song.mp4"
    existing.parent.mkdir()
    existing.write_bytes(b"kept")

    assert main(["render", str(song)]) == EXIT_FAILED
    assert "exists; nothing was rendered" in capsys.readouterr().err
    assert existing.read_bytes() == b"kept"
    assert main(["render", str(song), "--output", str(tmp_path / "video.mov")]) == EXIT_FAILED
    assert "needs the .mp4 extension" in capsys.readouterr().err
    assert main(["render", str(song), "--output", str(tmp_path / "late.mp4"), "--start", "5"]) == EXIT_FAILED
    assert "outside the audio" in capsys.readouterr().err

    (tmp_path / "lyrics.lrc").write_text("[00:03.00]too late\n", encoding="utf-8")
    assert main(["render", str(song), "--output", str(tmp_path / "late.mp4")]) == EXIT_FAILED
    assert "after the end of the song" in capsys.readouterr().err

    text = song.read_text()
    song.write_text(text.replace('timing = "lyrics.lrc"\n', ""), encoding="utf-8")
    assert main(["render", str(song)]) == EXIT_FAILED
    assert "timing is not set" in capsys.readouterr().err
    song.write_text(text.replace('audio = "tone.wav"\n', ""), encoding="utf-8")
    assert main(["render", str(song)]) == EXIT_FAILED
    assert "audio is not set" in capsys.readouterr().err
    assert not (tmp_path / "late.mp4").exists()


def test_a_missing_font_fails_before_rendering(tmp_path, sans_font, capsys, monkeypatch):
    song = make_song(tmp_path, tmp_path / "missing.otf")
    monkeypatch.setattr(cli, "render", lambda *args, **kwargs: pytest.fail("rendering started"))

    assert main(["render", str(song)]) == EXIT_FAILED

    assert "missing.otf" in capsys.readouterr().err
    assert not (tmp_path / "videos").exists()


def test_a_cancelled_render_leaves_no_file(tmp_path, sans_font):
    prepared = prepare_render(load_song(make_song(tmp_path, sans_font)), workers=1)

    with pytest.raises(Cancelled):
        render(prepared, cancel=lambda: True)

    assert list((tmp_path / "videos").iterdir()) == []


def test_ctrl_c_exits_with_130(tmp_path, sans_font, capsys, monkeypatch):
    song = make_song(tmp_path, sans_font)

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "render", interrupted)

    assert main(["render", str(song)]) == EXIT_INTERRUPTED
    assert "cancelled; no video was written" in capsys.readouterr().err


def test_progress_without_a_terminal_prints_a_line_per_tenth():
    stream = io.StringIO()
    progress = TextProgress(stream)

    for done in range(101):
        progress(done, 100)

    lines = stream.getvalue().splitlines()
    assert len(lines) == 11
    assert lines[0].startswith("  0 %  frame 0/100")
    assert lines[-1].startswith("100 %  frame 100/100")
