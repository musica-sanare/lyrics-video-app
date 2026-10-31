import unicodedata
from pathlib import Path

import pytest

from lyrics_video.errors import FontError
from lyrics_video.fonts import collect_fonts, font_labels


def test_labels_are_composed_and_unique():
    decomposed = Path(unicodedata.normalize("NFD", "/fonts/ヒラギノ.ttc"))

    labels = font_labels([decomposed, Path("/a/Same.otf"), Path("/b/Same.ttf"), Path("/c/x.1.02.otf")])

    assert labels == ["ヒラギノ", "Same", "Same-2", "x.1.02"]
    assert unicodedata.is_normalized("NFC", labels[0])


def test_files_first_then_folders_sorted_and_each_once(tmp_path):
    for name in ["b.otf", "a.TTF", "sub/c.ttc", "readme.txt"]:
        (tmp_path / name).parent.mkdir(exist_ok=True)
        (tmp_path / name).write_bytes(b"")
    first = tmp_path / "b.otf"

    fonts = collect_fonts([first], [tmp_path])

    assert fonts == [first, tmp_path / "a.TTF", tmp_path / "sub/c.ttc"]


def test_missing_files_and_folders(tmp_path):
    with pytest.raises(FontError, match="font file not found"):
        collect_fonts([tmp_path / "x.otf"], [])
    with pytest.raises(FontError, match="font folder not found"):
        collect_fonts([], [tmp_path / "nothing"])
