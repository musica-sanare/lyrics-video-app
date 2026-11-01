"""The app's own files in Application Support: the running server, so a second start reuses it, the recent songs,
and what the page remembers (the last design and font of a new song).

All are small JSON files written through a temporary file, readable by the owner only (the server file holds the
session token).
"""

import json
import os
from datetime import datetime
from pathlib import Path

from lyrics_video.output import write_text

APP_ENVIRONMENT = "LYRICS_VIDEO_APP_DIR"
APP_FOLDER = Path("~/Library/Application Support/lyrics-video")
SERVER_FILE = "server.json"
RECENT_FILE = "recent.json"
SETTINGS_FILE = "settings.json"
RECENT_LIMIT = 20


def app_folder() -> Path:
    """The folder in $LYRICS_VIDEO_APP_DIR, or the app's folder in Application Support."""
    configured = os.environ.get(APP_ENVIRONMENT)
    return Path(configured).expanduser() if configured else APP_FOLDER.expanduser()


def _read(name: str):
    try:
        return json.loads((app_folder() / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(name: str, data) -> None:
    folder = app_folder()
    folder.mkdir(parents=True, exist_ok=True)
    write_text(folder / name, json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def read_server() -> dict | None:
    """The running server as the last `start` recorded it: port, token and process id. It may have stopped since."""
    data = _read(SERVER_FILE)
    if isinstance(data, dict) and isinstance(data.get("port"), int) and isinstance(data.get("token"), str):
        return data
    return None


def write_server(port: int, token: str) -> None:
    _write(SERVER_FILE, {"port": port, "token": token, "pid": os.getpid()})


def remove_server() -> None:
    """Forget the server, if this process recorded it; another `start` may have replaced the file."""
    data = read_server()
    if data is not None and data.get("pid") == os.getpid():
        (app_folder() / SERVER_FILE).unlink(missing_ok=True)


def read_settings() -> dict:
    """What the page remembers between songs, such as the last design and font chosen for a new song."""
    data = _read(SETTINGS_FILE)
    return data if isinstance(data, dict) else {}


def remember(**values) -> None:
    _write(SETTINGS_FILE, {**read_settings(), **values})


def recent_songs() -> list[dict]:
    """The song files opened lately, newest first, each with whether it still exists."""
    data = _read(RECENT_FILE)
    entries = [entry for entry in data if isinstance(entry, dict) and "path" in entry] if isinstance(data, list) else []
    return [{**entry, "exists": Path(entry["path"]).is_file()} for entry in entries]


def add_recent(path: Path, title: str) -> None:
    """Put a song file at the top of the recent songs, keeping at most `RECENT_LIMIT`."""
    path = path.resolve()
    entries = [entry for entry in recent_songs() if entry["path"] != str(path)]
    entry = {"path": str(path), "title": title, "opened": datetime.now().isoformat(timespec="seconds")}
    _write(RECENT_FILE, [entry, *({key: e[key] for key in e if key != "exists"} for e in entries)][:RECENT_LIMIT])
