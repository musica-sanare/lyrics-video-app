"""Opening and listing font files, and the strength of synthetic bold and italic."""

import math
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from lyrics_video.errors import FontError

# Synthetic bold widens the outline by this share of the font size on each side; synthetic italic slants by 12°.
BOLD_STROKE = 0.03
ITALIC_SLANT = math.tan(math.radians(12))


@lru_cache(maxsize=256)
def load_font(path: Path, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    if not path.is_file():
        raise FontError(f"{path}: font file not found")
    try:
        return ImageFont.truetype(str(path), size, index=index)
    except OSError as error:
        raise FontError(f"{path}: cannot open font (face {index}): {error}") from None


# Where macOS keeps fonts; the sync page lists these and the folders of the fonts a song file names.
FONT_FOLDERS = (Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path("~/Library/Fonts").expanduser())
FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc"}
# More faces than any font collection on macOS has; a guard against a broken file.
MAX_FACES = 64


@dataclass(frozen=True)
class FontFace:
    path: Path
    face: int
    family: str
    style: str


def font_faces(folders: list[Path]) -> list[FontFace]:
    """Every face of every font file in `folders` and their subfolders, by family and style. Faces whose family
    starts with a dot are macOS's own interface fonts and are left out."""
    files = sorted({file for folder in folders if folder.is_dir() for file in folder.rglob("*") if _is_font(file)})
    faces = []
    for file in files:
        collection = file.suffix.lower() in {".ttc", ".otc"}
        for index in range(MAX_FACES if collection else 1):
            try:
                family, style = ImageFont.truetype(str(file), 12, index=index).getname()
            except OSError:
                break
            if family and not family.startswith("."):
                faces.append(FontFace(_composed(file), index, family, style or ""))
    return sorted(faces, key=lambda face: (face.family.casefold(), face.style.casefold(), str(face.path), face.face))


def _is_font(path: Path) -> bool:
    return path.suffix.lower() in FONT_SUFFIXES and not path.name.startswith(".") and path.is_file()


def _composed(path: Path) -> Path:
    """The path with composed characters (NFC), as people type it: macOS lists names such as ヒラギノ decomposed."""
    return Path(unicodedata.normalize("NFC", str(path)))
