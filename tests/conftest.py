from pathlib import Path

import pytest

SANS = Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc")
SERIF = Path("/System/Library/Fonts/ヒラギノ明朝 ProN.ttc")


def _require(path: Path) -> Path:
    if not path.is_file():
        pytest.skip(f"system font missing: {path}")
    return path


@pytest.fixture
def sans_font() -> Path:
    return _require(SANS)


@pytest.fixture
def serif_font() -> Path:
    return _require(SERIF)
