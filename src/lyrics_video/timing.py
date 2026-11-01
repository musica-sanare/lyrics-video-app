"""Timed lyrics: an LRC file next to the lyrics file.

Each line is `[mm:ss.xx]` and a caption, with the separator between its two rows. A time with no text ends the
caption before it, where the singing pauses. A line without a time is a caption not timed yet; it is kept but not
shown. ID tags such as `[ti:...]` and empty lines are skipped.
"""

import difflib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lyrics_video.errors import LyricsError
from lyrics_video.lyrics import MAX_ROWS, Caption

TIME_TAG = re.compile(r"\[(\d+):(\d{2})(?:[.:](\d{1,3}))?\]")
ID_TAG = re.compile(r"\[[A-Za-z]+:[^\]]*\]\s*")


@dataclass(frozen=True)
class TimedLine:
    """A caption and when it is sung: from `start` to `end` (a pause), or to the next start when `end` is None."""

    rows: tuple[str, ...]
    start: float | None = None
    """Seconds of the song; None while the line is not timed."""
    end: float | None = None


@dataclass(frozen=True)
class LyricsChange:
    kind: Literal["added", "removed"]
    rows: tuple[str, ...]


@dataclass(frozen=True)
class Merged:
    lines: list[TimedLine]
    changes: list[LyricsChange]


def parse_lrc(text: str, separator: str, source: str = "timing") -> list[TimedLine]:
    lines: list[TimedLine] = []
    numbers: list[int] = []
    for index, line in enumerate(text.split("\n")):
        number = index + 1
        line = line.rstrip("\r")
        if not line.strip() or ID_TAG.fullmatch(line):
            continue
        match = TIME_TAG.match(line)
        if match is None:
            lines.append(TimedLine(_rows(line, separator, source, number)))
            numbers.append(number)
            continue
        seconds = _seconds(match)
        rest = line[match.end() :]
        if TIME_TAG.match(rest):
            raise LyricsError(f"{source}, line {number}: more than one time; write one line per time")
        if rest.strip():
            lines.append(TimedLine(_rows(rest, separator, source, number), seconds))
            numbers.append(number)
            continue
        previous = lines[-1] if lines else None
        if previous is None or previous.start is None or previous.end is not None:
            raise LyricsError(f"{source}, line {number}: an end time must follow a timed caption")
        lines[-1] = TimedLine(previous.rows, previous.start, seconds)
    _check_order(lines, numbers, source)
    return lines


def read_lrc(path: Path, separator: str) -> list[TimedLine]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise LyricsError(f"{path}: timing file not found") from None
    except (OSError, UnicodeDecodeError) as error:
        raise LyricsError(f"{path}: cannot read as UTF-8 text ({error})") from None
    return parse_lrc(text, separator, source=str(path))


def format_lrc(lines: list[TimedLine], separator: str) -> str:
    out = []
    for line in lines:
        text = separator.join(line.rows)
        if line.start is None:
            out.append(text)
            continue
        out.append(f"{format_time(line.start)}{text}")
        if line.end is not None:
            out.append(format_time(line.end))
    return "".join(f"{line}\n" for line in out)


def write_lrc(path: Path, lines: list[TimedLine], separator: str) -> None:
    """Write completely or not at all: a temporary file next to `path`, then a rename."""
    text = format_lrc(lines, separator)
    parse_lrc(text, separator, source=str(path))
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".lrc.tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def format_time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    minutes, rest = divmod(centiseconds, 6000)
    return f"[{minutes:02d}:{rest // 100:02d}.{rest % 100:02d}]"


def check_inside(lines: list[TimedLine], duration: float, source: str) -> None:
    for line in lines:
        for seconds in (line.start, line.end):
            if seconds is not None and seconds >= duration:
                raise LyricsError(
                    f"{source}: {format_time(seconds)} is after the end of the song ({format_time(duration)})"
                )


def merge(timed: list[TimedLine], captions: list[Caption]) -> Merged:
    """The captions of a changed lyrics file, keeping the times of lines whose text is unchanged (matched in order).

    New or changed lines are not timed; the changes list what was added and removed.
    """
    old = [line.rows for line in timed]
    new = [caption.rows for caption in captions]
    lines: list[TimedLine] = []
    changes: list[LyricsChange] = []
    for tag, old_from, old_to, new_from, new_to in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag == "equal":
            lines.extend(timed[old_from:old_to])
            continue
        changes.extend(LyricsChange("removed", rows) for rows in old[old_from:old_to])
        changes.extend(LyricsChange("added", rows) for rows in new[new_from:new_to])
        lines.extend(TimedLine(rows) for rows in new[new_from:new_to])
    return Merged(lines, changes)


def _rows(text: str, separator: str, source: str, number: int) -> tuple[str, ...]:
    rows = tuple(text.split(separator))
    if len(rows) > MAX_ROWS:
        raise LyricsError(f"{source}, line {number}: more than one {separator!r}; a caption has at most {MAX_ROWS} rows")
    return rows


def _seconds(match: re.Match) -> float:
    minutes, seconds, fraction = match.groups()
    value = int(minutes) * 60 + int(seconds)
    if fraction:
        value += int(fraction) / 10 ** len(fraction)
    return value


def _check_order(lines: list[TimedLine], numbers: list[int], source: str) -> None:
    last_start, last_end = -1.0, -1.0
    for line, number in zip(lines, numbers, strict=True):
        if line.start is None:
            continue
        if line.start <= last_start or line.start < last_end:
            raise LyricsError(f"{source}, line {number}: {format_time(line.start)} is before the time above it")
        if line.end is not None and line.end <= line.start:
            raise LyricsError(f"{source}, line {number}: the end time is not after {format_time(line.start)}")
        last_start, last_end = line.start, line.end if line.end is not None else line.start
