import tomllib
from pathlib import Path

import pytest
from audio_spectrum import load_preset, override_preset

from lyrics_video.config import (
    create_song,
    load_song,
    missing_files,
    save_user_design,
    song_design,
    spectrum_preset,
    write_design,
    write_song_settings,
)
from lyrics_video.design import load_design
from lyrics_video.errors import ConfigError, LyricsVideoError, OutputExistsError
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


# --- User designs --------------------------------------------------------------------------------------------------


def test_saving_a_user_design_for_other_songs(tmp_path, user_designs):
    (tmp_path / "one").mkdir()
    (tmp_path / "one" / "preset.toml").write_text('name = "mine"\nforeground = "#FF0000"\n', encoding="utf-8")
    song = load_song(write_song(tmp_path / "one", ""))
    font = Path.home() / "fonts" / "title.otf"
    design = song_design(
        song.path,
        "soft",
        {"title": {"font": str(font), "bold": True, "color": "#FFD84A"}, "spectrum": {"preset": "preset.toml", "look": {"max_height": 0.4}}},
    )

    path = save_user_design(song, design, "夏の雨")

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert path == user_designs / "夏の雨.toml"
    assert data["title"]["font"] == "~/fonts/title.otf" and data["title"]["color"] == "#FFD84A"
    assert data["spectrum"]["preset"] == str(tmp_path / "one" / "preset.toml")
    assert "caption" not in data or "text_color" not in data["caption"], "defaults are left out"
    (tmp_path / "two").mkdir()
    other = load_song(write_song(tmp_path / "two", 'design = "夏の雨"\n'))
    absolute = design.spectrum.model_copy(update={"preset": str(tmp_path / "one" / "preset.toml")})
    assert other.design == design.model_copy(update={"name": "夏の雨", "spectrum": absolute})
    assert spectrum_preset(other).foreground == (255, 0, 0)


def test_a_user_design_is_replaced_only_when_asked(tmp_path, user_designs):
    song = load_song(write_song(tmp_path, ""))
    save_user_design(song, load_design("soft"), "mine")

    with pytest.raises(OutputExistsError, match="'mine' exists"):
        save_user_design(song, load_design("panel"), "mine")
    save_user_design(song, load_design("panel"), "mine", overwrite=True)

    assert load_design("mine").caption.style == "panel"
    assert "gradient" in (user_designs / "mine.toml.bak").read_text(encoding="utf-8")


def test_built_in_names_are_not_saved(tmp_path, user_designs):
    with pytest.raises(ConfigError, match="built-in"):
        save_user_design(load_song(write_song(tmp_path, "")), load_design("soft"), "soft")

    assert list(user_designs.iterdir()) == []


# --- New songs and song settings ------------------------------------------------------------------------------------


def song_inputs(folder: Path) -> tuple[Path, Path, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    audio, image, lyrics = folder / "tone.wav", folder / "bg.png", folder / "words.txt"
    for path in (audio, image):
        path.write_bytes(b"x")
    lyrics.write_text("一行目\n二行目;下の段\n", encoding="utf-8")
    return audio, image, lyrics


def test_a_new_song_names_its_files_where_they_are(tmp_path):
    audio, image, lyrics = song_inputs(tmp_path / "music")
    elsewhere = tmp_path / "pictures"
    elsewhere.mkdir()
    image = image.rename(elsewhere / "bg.png")

    song = create_song(tmp_path / "music" / "tone.toml", audio, image, lyrics, "Title", ["by Me"], "panel")

    data = tomllib.loads((tmp_path / "music" / "tone.toml").read_text(encoding="utf-8"))
    assert data["audio"] == "tone.wav" and data["lyrics"] == "words.txt" and data["timing"] == "tone.lrc"
    assert Path(data["background_image"]).resolve() == image.resolve() and data["design"] == "panel"
    assert "fonts" not in data
    assert (song.audio, song.background_image) == (audio, image.resolve())
    assert (song.title, song.credits) == ("Title", ("by Me",))
    names = sorted(path.name for path in (tmp_path / "music").iterdir())
    assert names == ["tone.toml", "tone.wav", "words.txt"], "nothing copied"


def test_a_new_song_with_a_font_under_the_home_folder(tmp_path):
    audio, image, lyrics = song_inputs(tmp_path)
    font = Path.home() / "Fonts" / "mine.otf"

    create_song(tmp_path / "tone.toml", audio, image, lyrics, "T", [], "soft", font)

    assert tomllib.loads((tmp_path / "tone.toml").read_text(encoding="utf-8"))["fonts"]["default"] == "~/Fonts/mine.otf"


def test_a_new_song_is_refused_before_anything_is_written(tmp_path):
    audio, image, lyrics = song_inputs(tmp_path)
    (tmp_path / "taken.toml").write_text("", encoding="utf-8")
    broken = tmp_path / "broken.txt"
    broken.write_text("a;b;c\n", encoding="utf-8")

    with pytest.raises(OutputExistsError):
        create_song(tmp_path / "taken.toml", audio, image, lyrics, "T", [], "soft")
    with pytest.raises(LyricsVideoError, match="broken.txt"):
        create_song(tmp_path / "new.toml", audio, image, broken, "T", [], "soft")
    with pytest.raises(ConfigError, match="audio file"):
        create_song(tmp_path / "new.toml", tmp_path / "none.wav", image, lyrics, "T", [], "soft")

    assert not (tmp_path / "new.toml").exists()


def test_changing_song_settings_keeps_the_rest(tmp_path):
    audio, image, lyrics = song_inputs(tmp_path)
    path = write_song(tmp_path, '# my notes\naudio = "tone.wav"\ntitle = "Old"\n\n[video]\nfps = 25  # kept\n')
    other = tmp_path / "other.wav"
    other.write_bytes(b"x")

    song = write_song_settings(path, {"title": "New", "credits": ["a", "b"], "audio": str(other), "font": "/f/x.otf"})

    text = path.read_text(encoding="utf-8")
    data = tomllib.loads(text)
    assert "# my notes" in text and "fps = 25  # kept" in text
    assert (data["title"], data["credits"]) == ("New", ["a", "b"])
    assert (data["audio"], data["fonts"]["default"]) == ("other.wav", "/f/x.otf")
    assert song.video.fps == 25 and (tmp_path / "song.toml.bak").exists()
    write_song_settings(path, {"font": None})
    assert "default" not in tomllib.loads(path.read_text(encoding="utf-8")).get("fonts", {})


def test_missing_files(tmp_path):
    audio, image, lyrics = song_inputs(tmp_path)
    song = load_song(write_song(tmp_path, 'audio = "tone.wav"\nbackground_image = "gone.png"\nlyrics = "words.txt"\n'))

    assert missing_files(song) == {"background_image": str(tmp_path / "gone.png")}


def test_a_named_design_carries_the_songs_font(tmp_path, user_designs):
    text = '[fonts]\ndefault = "~/Fonts/mine.otf"\n[design]\nname = "soft"\n[design.title]\nfont = "/t.otf"\n'
    song = load_song(write_song(tmp_path, text))

    save_user_design(song, song.design, "mine")

    data = tomllib.loads((user_designs / "mine.toml").read_text(encoding="utf-8"))
    assert data["title"]["font"] == "/t.otf"
    assert data["caption"]["font"] == data["credits"]["font"] == "~/Fonts/mine.otf"
