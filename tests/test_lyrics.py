import pytest

from lyrics_video.errors import LyricsError
from lyrics_video.lyrics import Caption, parse_lyrics, read_lyrics


def test_one_caption_per_line_with_old_indexes():
    captions = parse_lyrics("first\n\nsecond;row two\n   \nthird\n", ";")

    assert captions == [
        Caption(index=0, rows=("first",)),
        Caption(index=2, rows=("second", "row two")),
        Caption(index=4, rows=("third",)),
    ]


def test_windows_line_ends_are_removed():
    assert parse_lyrics("a\r\nb;c\r\n", ";") == [Caption(0, ("a",)), Caption(1, ("b", "c"))]


def test_a_custom_separator():
    assert parse_lyrics("a|b;c", "|") == [Caption(0, ("a", "b;c"))]


def test_more_than_two_rows_is_an_error_with_the_line_number():
    with pytest.raises(LyricsError, match="line 3"):
        parse_lyrics("a\nb\nc;d;e", ";")


def test_reading_a_file(tmp_path):
    path = tmp_path / "lyrics.txt"
    path.write_text("﻿one;two\n", encoding="utf-8")

    assert read_lyrics(path, ";") == [Caption(0, ("one", "two"))]


def test_missing_and_empty_files(tmp_path):
    with pytest.raises(LyricsError, match="not found"):
        read_lyrics(tmp_path / "missing.txt", ";")
    empty = tmp_path / "empty.txt"
    empty.write_text("\n\n", encoding="utf-8")
    with pytest.raises(LyricsError, match="no captions"):
        read_lyrics(empty, ";")
