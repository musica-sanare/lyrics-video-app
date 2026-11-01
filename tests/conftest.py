from pathlib import Path

import pytest

SANS = Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc")
SERIF = Path("/System/Library/Fonts/ヒラギノ明朝 ProN.ttc")
# A collection whose faces look different: 0 regular, 1 bold.
LATIN = Path("/System/Library/Fonts/Helvetica.ttc")


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


@pytest.fixture
def latin_collection() -> Path:
    return _require(LATIN)


@pytest.fixture(autouse=True)
def user_designs(tmp_path_factory, monkeypatch) -> Path:
    """Every test gets its own empty folder of user designs, never the owner's."""
    folder = tmp_path_factory.mktemp("designs")
    monkeypatch.setenv("LYRICS_VIDEO_DESIGN_DIR", str(folder))
    return folder


@pytest.fixture(autouse=True)
def app_files(tmp_path_factory, monkeypatch) -> Path:
    """Every test gets its own folder for the app's files (running server, recent songs), never the owner's."""
    folder = tmp_path_factory.mktemp("app")
    monkeypatch.setenv("LYRICS_VIDEO_APP_DIR", str(folder))
    return folder
