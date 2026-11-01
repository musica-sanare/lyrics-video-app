"""A small macOS app, "Lyrics Video.app", that starts this repository's app, for the Dock and Applications.

The bundle is an `Info.plist` and a shell script. The script runs `lyrics-video start` with `uv` from this repository,
in the background, and exits at once, so every click runs it again: a click while the app runs opens its page. Paths
are found when installing and written into the script, so the bundle is made on each Mac and never committed.
"""

import plistlib
import shlex
import shutil
import tempfile
from pathlib import Path

from lyrics_video import __version__
from lyrics_video.errors import ConfigError, OutputExistsError

APP_NAME = "Lyrics Video"
BUNDLE_ID = "local.lyrics-video.app"
EXECUTABLE = "lyrics-video"
APPLICATIONS = Path("~/Applications")
LOG = Path("~/Library/Logs/lyrics-video.log")
# The repository holding this file: src/lyrics_video/app_bundle.py.
REPOSITORY = Path(__file__).resolve().parents[2]


def install_app(folder: Path = APPLICATIONS, overwrite: bool = False) -> Path:
    """Write `<folder>/Lyrics Video.app`. Replacing one needs `overwrite`, and only a bundle this command made."""
    folder = folder.expanduser()
    bundle = folder / f"{APP_NAME}.app"
    if bundle.exists():
        if not overwrite:
            raise OutputExistsError(f"{bundle} exists; nothing was written (use --overwrite to replace it)")
        if _bundle_id(bundle) != BUNDLE_ID:
            raise ConfigError(f"{bundle} was not made by lyrics-video; move it away first")
    folder.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{APP_NAME}.", dir=folder))
    try:
        _write_bundle(staging, _script(_find_tools()))
        if bundle.exists():
            shutil.rmtree(bundle)
        staging.rename(bundle)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return bundle


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


def _write_bundle(bundle: Path, script: str) -> None:
    contents = bundle / "Contents"
    (contents / "MacOS").mkdir(parents=True)
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
