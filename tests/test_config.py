import tomllib
from pathlib import Path

import pytest
from audio_spectrum import load_preset, override_preset

from lyrics_video.config import load_song, spectrum_preset, write_design
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
    assert song.separator == ";"
    assert song.timing is None
    assert song.design.name == "soft"


def test_paths_are_relative_to_the_song_file_and_expand_home(tmp_path):
    song = load_song(
        write_song(tmp_path, 'lyrics = "texts/a.txt"\ntiming = "/abs/a.lrc"\n[fonts]\ndefault = "~/fonts/x.otf"\n')
    )

    assert song.lyrics == tmp_path / "texts/a.txt"
    assert song.timing == Path("/abs/a.lrc")
    assert song.default_font == Path.home() / "fonts/x.otf"


def test_a_custom_separator(tmp_path):
    assert load_song(write_song(tmp_path, 'separator = "/"\n')).separator == "/"


@pytest.mark.parametrize("section", ["captions", "compare"])
def test_removed_sections_are_named(tmp_path, section):
    with pytest.raises(ConfigError, match=rf"\[{section}\] is no longer used.*Delete it"):
        load_song(write_song(tmp_path, f"[{section}]\n"))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("unknown = 1\n", "unknown"),
        ('separator = ""\n', "separator"),
        ("[video]\nwidth = 0\n", "video.width"),
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
    captions = read_lyrics(EXAMPLES / "lyrics.example.txt", song.separator)

    assert song.default_font is not None
    assert [c.index for c in captions] == [0, 1, 3, 4]


SONG_WITH_COMMENTS = """# My song
audio = "tone.wav"   # the audio
design = "soft"
title = "Title"

[fonts]
default = "~/fonts/x.otf"  # my font
"""


def test_saving_a_design_named_by_a_key(tmp_path):
    path = write_song(tmp_path, SONG_WITH_COMMENTS)

    song = write_design(path, "panel", {"title": {"bold": True, "panel": {"color": "#202020"}}})

    text = path.read_text(encoding="utf-8")
    assert "# My song" in text and "# the audio" in text and "# my font" in text
    assert tomllib.loads(text)["design"] == {"name": "panel", "title": {"bold": True, "panel": {"color": "#202020"}}}
    assert (song.design.name, song.design.title.bold, song.design.title.panel.color) == ("panel", True, (32, 32, 32))
    assert load_song(path).design == song.design
    assert (tmp_path / "song.toml.bak").read_text(encoding="utf-8") == SONG_WITH_COMMENTS


def test_saving_replaces_a_design_table_in_place(tmp_path):
    path = write_song(tmp_path, '[design]\nname = "soft"\n[design.title]\nsize = 60\n\n[fonts]\ndefault = "a.otf"\n')

    write_design(path, "soft", {"caption": {"italic": True}})

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert data == {"design": {"name": "soft", "caption": {"italic": True}}, "fonts": {"default": "a.otf"}}
    assert path.read_text(encoding="utf-8").index("[design]") < path.read_text(encoding="utf-8").index("[fonts]")


def test_a_design_that_does_not_load_is_not_saved(tmp_path):
    path = write_song(tmp_path, SONG_WITH_COMMENTS)

    with pytest.raises(ConfigError, match="design.title.size"):
        write_design(path, "soft", {"title": {"size": -1}})

    assert path.read_text(encoding="utf-8") == SONG_WITH_COMMENTS
    assert not (tmp_path / "song.toml.bak").exists()


def test_the_song_keeps_the_design_name_as_written(tmp_path):
    (tmp_path / "mine.toml").write_text("[title]\nsize = 50\n", encoding="utf-8")

    song = load_song(write_song(tmp_path, 'design = "mine.toml"\n'))

    assert (song.design_name, song.design.name, song.design.title.size) == ("mine.toml", "mine", 50)


# --- The spectrum ---------------------------------------------------------------------------------------------------


def test_without_spectrum_settings_the_default_preset(tmp_path):
    assert spectrum_preset(load_song(write_song(tmp_path, ""))) == load_preset("default")


def test_the_song_files_spectrum_as_before(tmp_path):
    song = load_song(write_song(tmp_path, '[spectrum]\npreset = "glow"\nset = ["look.max_height=0.2"]\n'))

    assert spectrum_preset(song) == override_preset(load_preset("glow"), ["look.max_height=0.2"])


def test_the_designs_spectrum(tmp_path):
    song = load_song(
        write_song(
            tmp_path,
            '[design]\nname = "soft"\n[design.spectrum]\npreset = "bars"\n[design.spectrum.look]\nmax_height = 0.4\n',
        )
    )

    assert spectrum_preset(song) == override_preset(load_preset("bars"), ["look.max_height=0.4"])


def test_the_song_files_spectrum_wins_over_the_designs(tmp_path):
    song = load_song(
        write_song(
            tmp_path,
            '[spectrum]\npreset = "glow"\nset = ["look.max_height=0.2"]\n'
            '[design]\nname = "soft"\n[design.spectrum]\npreset = "bars"\n[design.spectrum.look]\nmax_height = 0.4\n'
            "mirror = false\n",
        )
    )

    expected = override_preset(load_preset("glow"), ["look.max_height=0.4", "look.mirror=false", "look.max_height=0.2"])
    assert spectrum_preset(song) == expected


def test_a_preset_file_named_by_the_design_is_relative_to_the_song_file(tmp_path):
    (tmp_path / "mine.toml").write_text('name = "mine"\nforeground = "#FF0000"\n', encoding="utf-8")

    song = load_song(write_song(tmp_path, '[design]\nname = "soft"\n[design.spectrum]\npreset = "mine.toml"\n'))

    assert spectrum_preset(song).foreground == load_preset(str(tmp_path / "mine.toml")).foreground


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ('[design.spectrum.look]\nkind = "perspective"\n', "look.kind"),
        ("[design.spectrum.look]\nheight = 3\n", r"look\.flat\.height: Extra inputs"),
    ],
)
def test_wrong_spectrum_changes_fail_when_the_song_file_loads(tmp_path, table, message):
    path = write_song(tmp_path, f'[design]\nname = "soft"\n{table}')

    with pytest.raises(ConfigError, match=message) as error:
        load_song(path)

    assert str(path) in str(error.value)
