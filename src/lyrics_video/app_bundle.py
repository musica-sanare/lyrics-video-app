"""A small macOS app, "Lyrics Video.app", that starts this repository's app, for the Dock and Applications.

The bundle is an `Info.plist` and a shell script. The script runs `lyrics-video start` with `uv` from this repository,
in the background, and exits at once, so every click runs it again: a click while the app runs opens its page. Paths
are found when installing and written into the script, so the bundle is made on each Mac and never committed. Its
icon is drawn by `app_icon`, or made from the owner's image, when `iconutil` is available.
"""

import plistlib
import shlex
import shutil
import tempfile
from pathlib import Path

from PIL import Image

from lyrics_video import __version__
from lyrics_video.app_icon import iconutil, load_image, write_icns
from lyrics_video.errors import ConfigError, OutputExistsError

APP_NAME = "Lyrics Video"
BUNDLE_ID = "local.lyrics-video.app"
EXECUTABLE = "lyrics-video"
ICON = "AppIcon"
APPLICATIONS = Path("~/Applications")
LOG = Path("~/Library/Logs/lyrics-video.log")
# The repository holding this file: src/lyrics_video/app_bundle.py.
REPOSITORY = Path(__file__).resolve().parents[2]


def install_app(folder: Path = APPLICATIONS, overwrite: bool = False, icon: Path | None = None) -> Path:
    """Write `<folder>/Lyrics Video.app`. Replacing one needs `overwrite`, and only a bundle this command made.

    The icon is drawn, or made from the image `icon`. Without `iconutil` the drawn icon is left out (see `has_icon`);
    an image given as `icon` then stops the install.
    """
    folder = folder.expanduser()
    bundle = folder / f"{APP_NAME}.app"
    if bundle.exists():
        if not overwrite:
            raise OutputExistsError(f"{bundle} exists; nothing was written (use --overwrite to replace it)")
        if _bundle_id(bundle) != BUNDLE_ID:
            raise ConfigError(f"{bundle} was not made by lyrics-video; move it away first")
    source = load_image(icon) if icon is not None else None
    if source is not None and iconutil() is None:
        raise ConfigError("iconutil is not available (it comes with macOS), so --icon cannot be used")
    folder.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{APP_NAME}.", dir=folder))
    try:
        _write_bundle(staging, _script(_find_tools()), source)
        if bundle.exists():
            shutil.rmtree(bundle)
        staging.rename(bundle)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return bundle


def has_icon(bundle: Path) -> bool:
    return (bundle / "Contents" / "Resources" / f"{ICON}.icns").is_file()


def _find_tools() -> dict[str, Path]:
    if not (REPOSITORY / "pyproject.toml").is_file():
        raise ConfigError(f"{REPOSITORY} is not the lyrics-video-app repository; run install-app from it with uv")
    uv = shutil.which("uv")
    if uv is None:
        raise ConfigError("uv is not installed (brew install uv)")
    tools = {"uv": Path(uv)}
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is not None:
        tools["ffmpeg"] = Path(ffmpeg)
    return tools


def _script(tools: dict[str, Path]) -> str:
    """The bundle's script. An app started from the Finder gets a short PATH, so the tools' folders are added."""
    folders = dict.fromkeys(str(path.parent) for path in tools.values())
    path = ":".join([*folders, "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
    log = LOG.expanduser()
    command = [str(tools["uv"]), "run", "--project", str(REPOSITORY), "lyrics-video", "start"]
    return "\n".join(
        [
            "#!/bin/zsh",
            f"# Made by `lyrics-video install-app` {__version__}. Starts the app in {REPOSITORY}.",
            "# Run `uv run lyrics-video install-app --overwrite` again after moving the repository or uv.",
            f"export PATH={shlex.quote(path)}",
            f"mkdir -p {shlex.quote(str(log.parent))}",
            f"nohup {shlex.join(command)} >> {shlex.quote(str(log))} 2>&1 &",
            "",
        ]
    )


def _write_bundle(bundle: Path, script: str, icon: Image.Image | None) -> None:
    contents = bundle / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    if icon is not None or iconutil() is not None:
        (contents / "Resources").mkdir()
        write_icns(contents / "Resources" / f"{ICON}.icns", icon)
    info = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleExecutable": EXECUTABLE,
        "CFBundlePackageType": "APPL",
        "CFBundleVersion": __version__,
        "CFBundleShortVersionString": __version__,
        # No window of its own: the script starts the server and exits, and the page opens in the browser.
        "LSUIElement": True,
    }
    if has_icon(bundle):
        info["CFBundleIconFile"] = ICON
    with (contents / "Info.plist").open("wb") as file:
        plistlib.dump(info, file)
    executable = contents / "MacOS" / EXECUTABLE
    executable.write_text(script, encoding="utf-8")
    executable.chmod(0o755)


def _bundle_id(bundle: Path) -> str | None:
    try:
        with (bundle / "Contents" / "Info.plist").open("rb") as file:
            return plistlib.load(file).get("CFBundleIdentifier")
    except (OSError, plistlib.InvalidFileException):
        return None
