"""macOS's own file dialogs, shown by the server on this Mac's screen; the page gets the chosen path back.

Only fixed scripts run, with the prompt and file types quoted as AppleScript strings, so the page cannot run
anything else.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from lyrics_video.errors import ConfigError

# AppleScript's error number when the person presses Cancel.
CANCELLED = "-128"
MAX_PROMPT = 200


# What each dialog of the page shows: file extensions, or None for a folder.
KINDS: dict[str, tuple[str, ...] | None] = {
    "song": ("toml",),
    "audio": ("wav", "aif", "aiff", "flac", "mp3", "m4a", "ogg"),
    "image": ("jpg", "jpeg", "png", "webp", "tif", "tiff", "bmp"),
    "lyrics": ("txt",),
    "font": ("ttf", "otf", "ttc", "otc"),
    "folder": None,
}


def choose(kind: str, prompt: str) -> Path | None:
    """The page's dialogs by kind (`KINDS`); None when cancelled."""
    extensions = KINDS[kind]
    return choose_folder(prompt) if extensions is None else choose_file(prompt, extensions)


def choose_file(prompt: str, extensions: tuple[str, ...] = ()) -> Path | None:
    """A file chosen in the Finder's dialog, or None when cancelled. `extensions` limits the files shown."""
    types = f" of type {{{', '.join(_quote(extension) for extension in extensions)}}}" if extensions else ""
    return _choose(f"choose file with prompt {_quote(prompt)}{types}")


def choose_folder(prompt: str) -> Path | None:
    return _choose(f"choose folder with prompt {_quote(prompt)}")


def _choose(command: str) -> Path | None:
    osascript = shutil.which("osascript")
    if sys.platform != "darwin" or osascript is None:
        raise ConfigError("file dialogs need macOS; type the path instead")
    result = subprocess.run([osascript, "-e", f"POSIX path of ({command})"], capture_output=True, text=True)
    if result.returncode != 0:
        if CANCELLED in result.stderr:
            return None
        raise ConfigError(f"the file dialog failed: {result.stderr.strip()}")
    chosen = result.stdout.strip()
    return Path(chosen) if chosen else None


def _quote(text: str) -> str:
    text = text[:MAX_PROMPT]
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
