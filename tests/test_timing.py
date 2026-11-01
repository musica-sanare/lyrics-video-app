import pytest

from lyrics_video.errors import LyricsError
from lyrics_video.lyrics import parse_lyrics
from lyrics_video.timing import (
    LyricsChange,
    TimedLine,
    check_inside,
    format_lrc,
    format_time,
    merge,
    parse_lrc,
    read_lrc,
    write_lrc,
)

LRC = "[ti:A made-up song]\n[00:12.40]first row;second row\n[00:17.85]the next caption\n[00:23.10]\n\n[01:41]after a pause\n"


def test_reading_captions_ends_and_rows():
    assert parse_lrc(LRC, ";") == [
        TimedLine(("first row", "second row"), 12.4),
        TimedLine(("the next caption",), 17.85, 23.1),
        TimedLine(("after a pause",), 101.0),
    ]


@pytest.mark.parametrize(("tag", "seconds"), [("[00:01.5]", 1.5), ("[00:01.25]", 1.25), ("[02:03.125]", 123.125)])
def test_fractions_of_any_length(tag, seconds):
    assert parse_lrc(f"{tag}text", ";")[0].start == pytest.approx(seconds)


def test_lines_without_a_time_are_kept_untimed():
    assert parse_lrc("[00:01.00]one\ntwo\n[00:05.00]three\n", ";")[1] == TimedLine(("two",))


def test_writing_and_a_round_trip(tmp_path):
    lines = parse_lrc(LRC, ";")
    text = format_lrc(lines, ";")

    assert text == (
        "[00:12.40]first row;second row\n[00:17.85]the next caption\n[00:23.10]\n[01:41.00]after a pause\n"
    )
    write_lrc(tmp_path / "lyrics.lrc", lines + [TimedLine(("not timed",))], ";")
    assert read_lrc(tmp_path / "lyrics.lrc", ";") == lines + [TimedLine(("not timed",))]
    assert [p.name for p in tmp_path.iterdir()] == ["lyrics.lrc"]


def test_times_are_written_to_the_hundredth():
    assert format_time(0.0) == "[00:00.00]"
    assert format_time(59.996) == "[01:00.00]"
    assert format_time(754.123) == "[12:34.12]"


def test_writing_an_invalid_timing_writes_nothing(tmp_path):
    with pytest.raises(LyricsError, match="before the time above"):
        write_lrc(tmp_path / "lyrics.lrc", [TimedLine(("a",), 5.0), TimedLine(("b",), 4.0)], ";")
    assert not (tmp_path / "lyrics.lrc").exists()


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[00:05.00]a\n[00:04.00]b\n", "line 2: .00:04.00. is before the time above"),
        ("[00:05.00]a\n[00:05.00]b\n", "line 2"),
        ("[00:05.00]a\n[00:08.00]\n[00:07.00]b\n", "line 3"),
        ("[00:05.00]a\n[00:05.00]\n", "line 1: the end time is not after"),
        ("[00:05.00]\n[00:06.00]a\n", "line 1: an end time must follow a timed caption"),
        ("[00:05.00]a\n[00:06.00]\n[00:07.00]\n", "line 3: an end time must follow"),
        ("untimed\n[00:06.00]\n", "line 2: an end time must follow"),
        ("[00:05.00]a;b;c\n", "line 1: more than one ';'"),
        ("[00:05.00][00:40.00]chorus\n", "line 1: more than one time"),
    ],
)
def test_invalid_files_name_the_line(text, message):
    with pytest.raises(LyricsError, match=message):
        parse_lrc(text, ";", source="lyrics.lrc")


def test_an_end_may_meet_the_next_start():
    assert parse_lrc("[00:05.00]a\n[00:06.00]\n[00:06.00]b\n", ";")[1].start == 6.0


def test_times_must_be_inside_the_song():
    lines = parse_lrc("[00:05.00]a\n[00:09.00]\n", ";")

    check_inside(lines, 9.5, "lyrics.lrc")
    with pytest.raises(LyricsError, match=r"lyrics.lrc: \[00:09.00\] is after the end of the song"):
        check_inside(lines, 8.0, "lyrics.lrc")


def test_a_missing_file(tmp_path):
    with pytest.raises(LyricsError, match="timing file not found"):
        read_lrc(tmp_path / "lyrics.lrc", ";")


def test_merging_keeps_the_times_of_unchanged_lines():
    timed = parse_lrc("[00:01.00]one\n[00:02.00]two\n[00:03.00]\n[00:05.00]three\n[00:07.00]four\n", ";")
    changed = parse_lyrics("one\nzero\ntwo\nthree, changed\nfour\nfive\n", ";")

    merged = merge(timed, changed)

    assert merged.lines == [
        TimedLine(("one",), 1.0),
        TimedLine(("zero",)),
        TimedLine(("two",), 2.0, 3.0),
        TimedLine(("three, changed",)),
        TimedLine(("four",), 7.0),
        TimedLine(("five",)),
    ]
    assert merged.changes == [
        LyricsChange("added", ("zero",)),
        LyricsChange("removed", ("three",)),
        LyricsChange("added", ("three, changed",)),
        LyricsChange("added", ("five",)),
    ]
    assert format_lrc(merged.lines, ";").splitlines()[1] == "zero"


def test_merging_unchanged_lyrics_changes_nothing():
    timed = parse_lrc(LRC, ";")

    merged = merge(timed, parse_lyrics("first row;second row\nthe next caption\nafter a pause\n", ";"))

    assert merged.lines == timed
    assert merged.changes == []
