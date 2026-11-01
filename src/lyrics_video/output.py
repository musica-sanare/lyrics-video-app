"""Writing images without overwriting by accident and without leaving half-written files."""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from lyrics_video.errors import OutputExistsError


@dataclass(frozen=True)
class Written:
    folder: Path
    files: list[Path]


def write_images(images: dict[Path, Image.Image], overwrite: bool) -> None:
    """Write every image as PNG, after checking that none exists unless `overwrite` is set."""
    if not overwrite:
        existing = [path for path in images if path.exists()]
        if existing:
            listed = "\n".join(f"  {path}" for path in existing)
            raise OutputExistsError(
                f"{len(existing)} output file(s) exist; nothing was written (use --overwrite to replace them):\n"
                f"{listed}"
            )
    for path, image in images.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_png(path, image)


def _write_png(path: Path, image: Image.Image) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".png.tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as file:
            image.save(file, format="PNG")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
