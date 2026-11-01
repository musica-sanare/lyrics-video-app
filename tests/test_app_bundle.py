import plistlib
import stat

import pytest
from PIL import Image

from lyrics_video import app_bundle
from lyrics_video.app_bundle import APP_NAME, BUNDLE_ID, REPOSITORY, has_icon, install_app
from lyrics_video.app_icon import iconutil
from lyrics_video.cli import EXIT_FAILED, EXIT_OK, main
from lyrics_video.errors import ConfigError, OutputExistsError


@pytest.fixture
def tools(monkeypatch):
    """uv and ffmpeg where Homebrew puts them, whether or not they are installed here."""
    found = {"uv": "/opt/homebrew/bin/uv", "ffmpeg": "/opt/homebrew/bin/ffmpeg"}
    which = app_bundle.shutil.which
    monkeypatch.setattr(app_bundle.shutil, "which", lambda name: found.get(name) if name in found else which(name))


def test_the_bundle_starts_this_repository_in_the_background(tmp_path, tools):
    bundle = install_app(tmp_path)

    assert bundle == tmp_path / f"{APP_NAME}.app"
    with (bundle / "Contents" / "Info.plist").open("rb") as file:
        info = plistlib.load(file)
    assert (info["CFBundleIdentifier"], info["CFBundleExecutable"]) == (BUNDLE_ID, "lyrics-video")
    assert info["LSUIElement"] is True
    script = bundle / "Contents" / "MacOS" / "lyrics-video"
    text = script.read_text(encoding="utf-8")
    assert script.stat().st_mode & stat.S_IXUSR
    assert "export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" in text
    assert f"nohup /opt/homebrew/bin/uv run --project {REPOSITORY} lyrics-video start >>" in text
    assert text.rstrip().endswith("2>&1 &"), "the script returns at once, so the next click runs it again"
    assert [path.name for path in tmp_path.iterdir()] == [f"{APP_NAME}.app"], "no staging folder left"


def test_an_existing_app_is_replaced_only_when_asked(tmp_path, tools):
    install_app(tmp_path)

    with pytest.raises(OutputExistsError, match="--overwrite"):
        install_app(tmp_path)
    install_app(tmp_path, overwrite=True)


def test_an_app_not_made_here_is_never_replaced(tmp_path, tools):
    other = tmp_path / f"{APP_NAME}.app" / "Contents"
    other.mkdir(parents=True)
    with (other / "Info.plist").open("wb") as file:
        plistlib.dump({"CFBundleIdentifier": "com.example.other"}, file)

    with pytest.raises(ConfigError, match="not made by lyrics-video"):
        install_app(tmp_path, overwrite=True)

    assert (other / "Info.plist").exists()


def test_without_uv_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr(app_bundle.shutil, "which", lambda name: None)

    with pytest.raises(ConfigError, match="uv is not installed"):
        install_app(tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_the_install_app_command(tmp_path, tools, capsys):
    assert main(["install-app", "--to", str(tmp_path)]) == EXIT_OK
    written = capsys.readouterr().out
    assert main(["install-app", "--to", str(tmp_path)]) == EXIT_FAILED

    assert f"Wrote {tmp_path / APP_NAME}.app" in written and "Dock" in written
    assert "--overwrite" in capsys.readouterr().err


needs_iconutil = pytest.mark.skipif(iconutil() is None, reason="iconutil comes with macOS only")


@needs_iconutil
def test_the_bundle_has_the_drawn_icon(tmp_path, tools):
    bundle = install_app(tmp_path)

    with (bundle / "Contents" / "Info.plist").open("rb") as file:
        assert plistlib.load(file)["CFBundleIconFile"] == "AppIcon"
    icns = bundle / "Contents" / "Resources" / "AppIcon.icns"
    assert icns.read_bytes()[:4] == b"icns"
    assert has_icon(bundle)


@needs_iconutil
def test_the_owners_image_becomes_the_icon(tmp_path, tools):
    image = tmp_path / "mine.png"
    Image.new("RGB", (1200, 1000), (200, 40, 40)).save(image)

    bundle = install_app(tmp_path / "apps", icon=image)

    with Image.open(bundle / "Contents" / "Resources" / "AppIcon.icns") as icon:
        icon.size = (512, 512)
        icon.load()
        assert icon.convert("RGB").getpixel((256, 256)) == (200, 40, 40)


def test_an_unreadable_icon_image_writes_nothing(tmp_path, tools):
    image = tmp_path / "not-an-image.png"
    image.write_text("text", encoding="utf-8")

    with pytest.raises(ConfigError, match="cannot be read as an image"):
        install_app(tmp_path / "apps", icon=image)

    assert not (tmp_path / "apps").exists()


def test_without_iconutil_the_app_has_the_default_icon(tmp_path, tools, monkeypatch, capsys):
    monkeypatch.setattr(app_bundle, "iconutil", lambda: None)

    assert main(["install-app", "--to", str(tmp_path)]) == EXIT_OK

    bundle = tmp_path / f"{APP_NAME}.app"
    assert not has_icon(bundle)
    with (bundle / "Contents" / "Info.plist").open("rb") as file:
        assert "CFBundleIconFile" not in plistlib.load(file)
    assert "default icon" in capsys.readouterr().err


def test_without_iconutil_an_icon_image_stops_the_install(tmp_path, tools, monkeypatch):
    monkeypatch.setattr(app_bundle, "iconutil", lambda: None)
    image = tmp_path / "mine.png"
    Image.new("RGB", (1024, 1024)).save(image)

    with pytest.raises(ConfigError, match="--icon"):
        install_app(tmp_path / "apps", icon=image)

    assert not (tmp_path / "apps").exists()
