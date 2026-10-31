"""Lyrics files: one caption per line, a separator between the two rows of a caption."""

from dataclasses import dataclass
from pathlib import Path

from lyrics_video.errors import LyricsError

MAX_ROWS = 2


@dataclass(frozen=True)
class Caption:
    index: int
    """0-based line index in the file; empty lines count, so it matches the old file names."""
    rows: tuple[str, ...]

    @property
    def line_number(self) -> int:
        return self.index + 1


def parse_lyrics(text: str, separator: str, source: str = "lyrics") -> list[Caption]:
    """Split a lyrics text into captions, skipping empty and blank lines."""
    captions = []
    for index, line in enumerate(text.split("\n")):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        rows = tuple(line.split(separator))
        if len(rows) > MAX_ROWS:
            raise LyricsError(
                f"{source}, line {index + 1}: more than one {separator!r}; a caption has at most {MAX_ROWS} rows"
            )
        captions.append(Caption(index=index, rows=rows))
    return captions


def read_lyrics(path: Path, separator: str) -> list[Caption]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise LyricsError(f"{path}: file not found") from None
    except (OSError, UnicodeDecodeError) as error:
        raise LyricsError(f"{path}: cannot read as UTF-8 text ({error})") from None
    captions = parse_lyrics(text, separator, source=str(path))
    if not captions:
        raise LyricsError(f"{path}: no captions (the file has no non-empty lines)")
    return captions
