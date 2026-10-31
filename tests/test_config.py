from pathlib import Path

import pytest
from PIL import Image

from lyrics_video.config import DEFAULT_CAPTION_SIZE, load_song
from lyrics_video.errors import ConfigError
from lyrics_video.lyrics import read_lyrics

EXAMPLES = Path(__file__).parent.parent / "examples"


def write_song(folder: Path, text: str) -> Path:
    path = folder / "song.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults(tmp_path):
    song = load_song(write_song(tmp_path, ""))

    assert song.lyrics == tmp_path / "lyrics.txt"
    assert song.caption_dir == tmp_path / "captions"
    assert song.look.size == DEFAULT_CAPTION_SIZE
    assert song.look.background == (0, 0, 0)
    assert song.look.text_color == (255, 255, 255)
    assert song.look.separator == ";"
    assert song.font is None


def test_paths_are_relative_to_the_song_file_and_expand_home(tmp_path):
    song = load_song(
        write_song(
            tmp_path,
            'lyrics = "texts/a.txt"\n[captions]\nfont = "~/fonts/x.otf"\noutput_dir = "/abs/out"\n'
            '[compare]\nfont_dirs = ["f"]\n',
        )
    )

    assert song.lyrics == tmp_path / "texts/a.txt"
    assert song.font == Path.home() / "fonts/x.otf"
    assert song.caption_dir == Path("/abs/out")
    assert song.compare_font_dirs == [tmp_path / "f"]


def test_colors_from_sample_images_and_their_size(tmp_path):
    Image.new("RGBA", (1500, 243), (4, 21, 123, 255)).save(tmp_path / "back.png")
    Image.new("RGB", (10, 10), (250, 240, 230)).save(tmp_path / "text.png")

    song = load_song(write_song(tmp_path, '[captions]\nbackground = "back.png"\ntext_color = "text.png"\n'))

    assert song.look.background == (4, 21, 123)
    assert song.look.text_color == (250, 240, 230)
    assert song.look.size == (1500, 243)


def test_an_explicit_size_wins_over_the_sample_image(tmp_path):
    Image.new("RGB", (1500, 243)).save(tmp_path / "back.png")

    song = load_song(write_song(tmp_path, '[captions]\nbackground = "back.png"\nsize = [800, 100]\n'))

    assert song.look.size == (800, 100)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[captions]\nsize = [0, 10]\n", "captions.size"),
        ("[captions]\nunknown = 1\n", "captions.unknown"),
        ('[captions]\nseparator = ""\n', "captions.separator"),
        ('[captions]\nbackground = "#12345"\n', "captions.background"),
        ("lyrics = \n", "cannot read"),
    ],
)
def test_invalid_files(tmp_path, text, message):
    with pytest.raises(ConfigError, match=message):
        load_song(write_song(tmp_path, text))


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_song(tmp_path / "nothing.toml")


def test_the_examples_are_valid():
    song = load_song(EXAMPLES / "song.example.toml")
    captions = read_lyrics(EXAMPLES / "lyrics.example.txt", song.look.separator)

    assert song.font is not None
    assert [c.index for c in captions] == [0, 1, 3, 4]
