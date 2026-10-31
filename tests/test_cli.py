import subprocess
import sys

import pytest
from PIL import Image

from lyrics_video import __version__
from lyrics_video.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, main


def make_song(folder, font, lyrics="一行目\n\n二行目;下の行\n", extra=""):
    (folder / "lyrics.txt").write_text(lyrics, encoding="utf-8")
    (folder / "compare.txt").write_text("比較の歌詞;二行目\n二つ目の行\n", encoding="utf-8")
    song = folder / "song.toml"
    song.write_text(f'[captions]\nfont = "{font}"\nsize = [720, 116]\n{extra}', encoding="utf-8")
    return song


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == EXIT_OK
    assert capsys.readouterr().out.strip() == f"lyrics-video {__version__}"


def test_runs_as_a_module():
    result = subprocess.run(
        [sys.executable, "-m", "lyrics_video.cli", "--version"], capture_output=True, text=True, check=True
    )

    assert __version__ in result.stdout


def test_a_command_is_required(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main([])

    assert exit_info.value.code == EXIT_USAGE


def test_captions_are_named_by_line_index(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font)

    assert main(["captions", str(song)]) == EXIT_OK

    files = sorted(p.name for p in (tmp_path / "captions").iterdir())
    assert files == ["lyrics_0.png", "lyrics_2.png"]
    assert Image.open(tmp_path / "captions/lyrics_2.png").size == (720, 116)
    assert "Wrote 2 image(s)" in capsys.readouterr().out


def test_existing_images_are_kept_unless_overwrite(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font)
    main(["captions", str(song)])
    first = tmp_path / "captions/lyrics_0.png"
    before = first.read_bytes()
    make_song(tmp_path, sans_font, lyrics="別の歌詞\n\n二行目;下の行\n")

    assert main(["captions", str(song)]) == EXIT_FAILED
    assert "use --overwrite" in capsys.readouterr().err
    assert first.read_bytes() == before

    assert main(["captions", str(song), "--overwrite"]) == EXIT_OK
    assert first.read_bytes() != before


def test_failures_leave_no_files(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font, lyrics="良い行\na;b;c\n")

    assert main(["captions", str(song)]) == EXIT_FAILED
    assert "line 2" in capsys.readouterr().err
    assert not (tmp_path / "captions").exists()


def test_a_missing_font_is_reported(tmp_path, capsys):
    song = make_song(tmp_path, tmp_path / "missing.otf")

    assert main(["captions", str(song)]) == EXIT_FAILED
    assert "font file not found" in capsys.readouterr().err


def test_captions_need_a_font(tmp_path, capsys):
    (tmp_path / "song.toml").write_text("", encoding="utf-8")

    assert main(["captions", str(tmp_path / "song.toml")]) == EXIT_FAILED
    assert "captions.font is not set" in capsys.readouterr().err


def test_compare_writes_every_line_in_every_font_and_a_contact_sheet(tmp_path, sans_font, serif_font):
    song = make_song(tmp_path, sans_font, extra=f'[compare]\nfonts = ["{sans_font}", "{serif_font}"]\n')

    assert main(["compare", str(song)]) == EXIT_OK

    folder = tmp_path / "compare"
    assert sorted(p.name for p in folder.iterdir()) == sorted(
        [f"{font.stem}_{index}.png" for font in (sans_font, serif_font) for index in (0, 1)] + ["contact_sheet.png"]
    )
    sheet = Image.open(folder / "contact_sheet.png")
    assert sheet.width == 720
    assert sheet.height > 2 * 116


def test_compare_fonts_from_the_command_line_replace_the_file(tmp_path, sans_font):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    (fonts / "nested").mkdir()
    (fonts / "nested" / "copy.ttc").write_bytes(sans_font.read_bytes())
    (fonts / "notes.txt").write_text("not a font", encoding="utf-8")
    song = make_song(tmp_path, sans_font, extra='[compare]\nfonts = ["/no/such/font.otf"]\n')

    assert main(["compare", str(song), "--font-dir", str(fonts)]) == EXIT_OK

    assert sorted(p.name for p in (tmp_path / "compare").iterdir()) == [
        "contact_sheet.png",
        "copy_0.png",
        "copy_1.png",
    ]


def test_compare_without_fonts_is_an_error(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font)

    assert main(["compare", str(song)]) == EXIT_FAILED
    assert "no fonts to compare" in capsys.readouterr().err
