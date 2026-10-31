import numpy as np
from PIL import Image
from signals import write_sine

from lyrics_video.cli import EXIT_FAILED, EXIT_OK, main


def make_song(folder, font, extra=""):
    write_sine(folder / "tone.wav", seconds=3.0)
    Image.new("RGB", (640, 480), (30, 60, 90)).save(folder / "bg.png")
    (folder / "lyrics.txt").write_text("一行目\n\n三行目;下の行\n", encoding="utf-8")
    song = folder / "song.toml"
    song.write_text(
        'audio = "tone.wav"\nbackground_image = "bg.png"\ntitle = "Title"\ncredits = ["Music: Someone"]\n'
        f'[fonts]\ndefault = "{font}"\n[video]\nwidth = 480\nheight = 270\n{extra}',
        encoding="utf-8",
    )
    return song


def test_stills_are_written_per_time(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font)

    assert main(["still", str(song), "--time", "0.5", "1.25", "--caption", "2"]) == EXIT_OK

    stills = tmp_path / "stills"
    assert sorted(p.name for p in stills.iterdir()) == ["classic_0.5s.png", "classic_1.25s.png"]
    image = Image.open(stills / "classic_1.25s.png")
    assert image.size == (480, 270)
    assert "Wrote 2 image(s)" in capsys.readouterr().out


def test_without_a_caption_the_band_is_not_drawn(tmp_path, sans_font):
    song = make_song(tmp_path, sans_font, "[design.credits]\nenabled = false\n")

    assert main(["still", str(song), "--time", "1.5", "--no-caption"]) == EXIT_OK

    corner = np.asarray(Image.open(tmp_path / "stills/classic_1.5s.png"))[-2, -2]
    assert corner.tolist() == [30, 60, 90]


def test_design_and_spectrum_from_the_song_file(tmp_path, sans_font):
    song = make_song(
        tmp_path,
        sans_font,
        '[design]\nname = "classic"\n[design.caption]\nband_color = "#FF0000"\n[spectrum]\nset = ["look.max_height=0.1"]\n',
    )

    assert main(["still", str(song), "--time", "1.5"]) == EXIT_OK

    corner = np.asarray(Image.open(tmp_path / "stills/classic_1.5s.png"))[-2, -2]
    assert corner.tolist() == [255, 0, 0]


def test_errors(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font)

    assert main(["still", str(song), "--time", "1", "--caption", "1"]) == EXIT_FAILED
    assert "no caption at line index 1" in capsys.readouterr().err
    assert main(["still", str(song), "--time", "9"]) == EXIT_FAILED
    assert "outside the audio" in capsys.readouterr().err
    song.write_text(song.read_text().replace('audio = "tone.wav"\n', ""), encoding="utf-8")
    assert main(["still", str(song), "--time", "1"]) == EXIT_FAILED
    assert "audio is not set" in capsys.readouterr().err
    assert not (tmp_path / "stills").exists()


def test_existing_stills_are_kept_unless_overwrite(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font)
    main(["still", str(song), "--time", "1"])

    assert main(["still", str(song), "--time", "1"]) == EXIT_FAILED
    assert main(["still", str(song), "--time", "1", "--overwrite"]) == EXIT_OK


def test_several_designs_and_a_comparison(tmp_path, sans_font):
    song = make_song(tmp_path, sans_font)

    assert main(["still", str(song), "--time", "1", "--design", "classic", "soft", "panel"]) == EXIT_OK

    names = sorted(p.name for p in (tmp_path / "stills").iterdir())
    assert names == ["classic_1s.png", "compare_1s.png", "panel_1s.png", "soft_1s.png"]
    sheet = Image.open(tmp_path / "stills/compare_1s.png")
    assert sheet.width == 240
    assert sheet.height > 3 * 135


def test_an_unknown_design_is_reported(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font)

    assert main(["still", str(song), "--time", "1", "--design", "fancy"]) == EXIT_FAILED
    assert "unknown design 'fancy'" in capsys.readouterr().err
