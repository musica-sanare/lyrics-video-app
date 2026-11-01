import pytest

from lyrics_video.design import builtin_design_names, load_design, scale_for
from lyrics_video.errors import ConfigError


@pytest.mark.parametrize("name", builtin_design_names())
def test_every_builtin_design_loads(name):
    assert load_design(name).name == name


def test_overrides_are_merged_part_by_part():
    design = load_design("classic", {"caption": {"band_height": 200, "band_color": "#102030"}})

    assert design.caption.band_height == 200
    assert design.caption.band_color == (16, 32, 48)
    assert design.caption.text_color == (255, 255, 255)
    assert design.title.size == load_design("classic").title.size


def test_a_design_file(tmp_path):
    (tmp_path / "mine.toml").write_text('[title]\nposition = "top-left"\n', encoding="utf-8")

    design = load_design("mine.toml", base=tmp_path)

    assert design.name == "mine"
    assert design.title.position == "top-left"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"caption": {"band_color": "red"}}, "design.caption.band_color"),
        ({"title": {"position": "middle"}}, "design.title.position"),
        ({"background": {"dim": 2}}, "design.background.dim"),
        ({"unknown": {}}, "design.unknown"),
    ],
)
def test_invalid_overrides(overrides, message):
    with pytest.raises(ConfigError, match=message):
        load_design("classic", overrides)


def test_unknown_design():
    with pytest.raises(ConfigError, match="unknown design 'nothing'"):
        load_design("nothing")


def test_sizes_scale_with_the_frame_height():
    assert scale_for(1080) == 1.0
    assert scale_for(720) == pytest.approx(2 / 3)


def test_caption_timing_settings():
    caption = load_design("soft").caption

    assert (caption.lead_seconds, caption.fade_seconds, caption.transition) == (0.2, 0.3, "sequential")
    with pytest.raises(ConfigError, match="design.caption.transition"):
        load_design("soft", {"caption": {"transition": "wipe"}})
    with pytest.raises(ConfigError, match="design.caption.lead_seconds"):
        load_design("soft", {"caption": {"lead_seconds": -1}})


def test_text_faces_and_the_title_box():
    for name in builtin_design_names():
        design = load_design(name)
        for part in (design.title, design.caption, design.credits):
            assert (part.font_face, part.bold, part.italic) == (0, False, False)
        assert design.title.panel is None

    design = load_design(
        "soft", {"title": {"bold": True, "font_face": 2, "panel": {"color": "#202020", "blur": 0}}, "caption": {"italic": True}}
    )

    assert (design.title.bold, design.title.font_face, design.caption.italic) == (True, 2, True)
    assert design.title.panel.color == (32, 32, 32) and design.title.panel.blur == 0
    with pytest.raises(ConfigError, match="design.credits.font_face"):
        load_design("soft", {"credits": {"font_face": -1}})
