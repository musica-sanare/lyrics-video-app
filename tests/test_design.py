import pytest

from lyrics_video.design import builtin_design_names, check_design_name, load_design, scale_for, user_design_names
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


def test_false_turns_off_a_box_of_the_base_design():
    design = load_design("panel", {"credits": {"panel": False}, "title": {"panel": False}})

    assert design.credits.panel is None and design.title.panel is None
    assert load_design("panel").credits.panel is not None


def test_spectrum_changes_become_preset_overrides():
    spectrum = load_design(
        "soft",
        {
            "spectrum": {
                "preset": "bars",
                "foreground": "#FFD84A",
                "look": {"max_height": 0.4, "mirror": False},
                "fill": {"colors": ["#FFFFFF", "#000000"]},
                "set": ["fx.glow_strength=0.5"],
            }
        },
    ).spectrum

    assert spectrum.preset == "bars"
    assert spectrum.overrides() == [
        'foreground="#FFD84A"',
        "look.max_height=0.4",
        "look.mirror=false",
        'fill.colors=["#FFFFFF", "#000000"]',
        "fx.glow_strength=0.5",
    ]
    assert load_design("soft").spectrum.overrides() == []


# --- User designs --------------------------------------------------------------------------------------------------


def test_a_user_design_is_found_by_name(user_designs, tmp_path):
    (user_designs / "夏の雨.toml").write_text('name = "夏の雨"\n[title]\nbold = true\n', encoding="utf-8")
    (user_designs / "夏の雨.toml.bak").write_text("", encoding="utf-8")
    (tmp_path / "夏の雨").write_text("[title]\nsize = 10\n", encoding="utf-8")

    assert user_design_names() == ["夏の雨"]
    assert load_design("夏の雨", base=tmp_path).title.bold, "the user design, not the file of the same name"
    assert load_design("夏の雨", {"title": {"italic": True}}).title.italic


@pytest.mark.parametrize("name", ["", " mine", "a/b", "a:b", ".hidden", "mine.toml", "soft", "x" * 201])
def test_names_a_user_design_cannot_have(name):
    with pytest.raises(ConfigError, match="cannot be a design name"):
        check_design_name(name)


def test_names_a_user_design_can_have():
    for name in ("mine", "夏の雨", "Summer Rain 2026", "a.b-c_d"):
        check_design_name(name)
