"""Compare two folders of PNG images, for example the old lyrics image script's output with this app's.

    uv run python tools/compare_images.py OLD_FOLDER NEW_FOLDER [--out work/compare_images]

Images are paired by file name. A new image without an old one of the same name is also paired with the old name cut
at the first dot (`my-font-2.04_0.png` -> `my-font-2_0.png`), as the old script named its font comparisons. For each
pair it prints the sizes, the share of differing pixels, the largest channel difference and the box that holds the
differences, and writes old, new and difference stacked into the output folder. Only numbers are printed; file names
are replaced by their position unless --names is given, so the output can be pasted into reports.
"""

import argparse
import sys
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def old_name_for(new_name: str, old_names: set[str]) -> str | None:
    if new_name in old_names:
        return new_name
    stem, _, index = Path(new_name).stem.rpartition("_")
    cut = f"{stem.split('.')[0]}_{index}.png"
    return cut if cut in old_names else None


def stacked(old: np.ndarray, new: np.ndarray, difference: np.ndarray) -> Image.Image:
    spacer = np.full((4, old.shape[1], 3), (255, 0, 0), dtype=np.uint8)
    return Image.fromarray(np.concatenate([old, spacer, new, spacer, difference], axis=0))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--out", type=Path, default=Path("work/compare_images"))
    parser.add_argument("--names", action="store_true", help="print file names instead of positions")
    args = parser.parse_args(argv)

    old_files = {nfc(p.name): p for p in args.old.glob("*.png")}
    args.out.mkdir(parents=True, exist_ok=True)
    print("pair  size       differing  max  box")
    identical = compared = 0
    for position, new_path in enumerate(sorted(args.new.glob("*.png")), start=1):
        label = nfc(new_path.name) if args.names else f"{position:4d}"
        old_name = old_name_for(nfc(new_path.name), set(old_files))
        if old_name is None:
            print(f"{label}  no old image")
            continue
        old = np.asarray(Image.open(old_files[old_name]).convert("RGB"))
        new = np.asarray(Image.open(new_path).convert("RGB"))
        if old.shape != new.shape:
            print(f"{label}  sizes differ: old {old.shape[1]}x{old.shape[0]}, new {new.shape[1]}x{new.shape[0]}")
            continue
        compared += 1
        difference = np.abs(old.astype(np.int16) - new.astype(np.int16)).astype(np.uint8)
        changed = difference.max(axis=2) > 0
        if not changed.any():
            identical += 1
            print(f"{label}  {new.shape[1]}x{new.shape[0]}  identical")
            continue
        rows, columns = np.nonzero(changed)
        box = (int(columns.min()), int(rows.min()), int(columns.max()) + 1, int(rows.max()) + 1)
        print(f"{label}  {new.shape[1]}x{new.shape[0]}  {changed.mean() * 100:6.2f} %  {difference.max():3d}  {box}")
        stacked(old, new, difference).save(args.out / f"{new_path.stem}_compare.png")
    print(f"{compared} pair(s) compared, {identical} identical; stacked images of the others in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
