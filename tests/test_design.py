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
