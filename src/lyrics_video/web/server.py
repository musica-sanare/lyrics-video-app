"""Start the page: a local server on 127.0.0.1 with a per-session token, and the page in the default browser.

`sync` serves one song from the terminal. `start` serves the start page, records itself in the app's folder so a
second start opens the running app instead of another one, and stops by itself when no page has been open for a while.
"""

import secrets
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

import uvicorn

from lyrics_video import app_files
from lyrics_video.config import Song
from lyrics_video.web.app import TOKEN_HEADER, Songs, SyncSession, create_app

HOST = "127.0.0.1"
# The page asks the server something at least every 30 seconds while it is open (see app.js).
IDLE_SECONDS = 600.0
IDLE_CHECK_SECONDS = 15.0


def run(song: Song | None, port: int = 0, open_browser: bool = True, app_mode: bool = False) -> None:
    """Serve until Ctrl+C, Quit, or (in app mode) a while without requests. Port 0 picks a free port.

    A song is loaded first, so its errors stop before serving. In app mode the server is recorded for `start`.
    """
    session = None
    if song is not None:
        session = SyncSession(song)
        session.load()
    songs = Songs(session)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((HOST, port))
    port = listener.getsockname()[1]
    token = secrets.token_urlsafe(24)
    server = uvicorn.Server(uvicorn.Config(None, log_level="warning"))
    app = create_app(songs, token, {f"{HOST}:{port}", f"localhost:{port}"}, stop=lambda: _stop_soon(server))
    server.config.app = app
    url = f"http://{HOST}:{port}/?token={token}"
    print(f"lyrics-video at {url}\nPress Ctrl+C to stop.", file=sys.stderr, flush=True)
    if open_browser:
        threading.Thread(target=_open_when_started, args=(server, url), daemon=True).start()
    if app_mode:
        app_files.write_server(port, token)
        threading.Thread(target=_stop_when_idle, args=(server, songs), daemon=True).start()
    try:
        server.run(sockets=[listener])
    except KeyboardInterrupt:
        pass  # uvicorn has shut down; Ctrl+C is the normal way to stop
    finally:
        songs.close()
        if app_mode:
            app_files.remove_server()


def start(port: int = 0, open_browser: bool = True) -> None:
    """Open the running app's page, or start the app without a song."""
    running = app_files.read_server()
    if running is not None and answers(running["port"], running["token"]):
        url = f"http://{HOST}:{running['port']}/?token={running['token']}"
        print(f"lyrics-video is already running at {url}", file=sys.stderr, flush=True)
        if open_browser:
            webbrowser.open(url)
        return
    run(None, port=port, open_browser=open_browser, app_mode=True)


def answers(port: int, token: str) -> bool:
    """Whether a lyrics-video server with this token answers on this port (a recorded one may have stopped)."""
    request = urllib.request.Request(f"http://{HOST}:{port}/api/ping", headers={TOKEN_HEADER: token})
    try:
        with urllib.request.urlopen(request, timeout=1.0) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def idle(songs: Songs, now: float, limit: float = IDLE_SECONDS) -> bool:
    """No page has asked anything for `limit` seconds, and nothing is rendering."""
    return now - songs.last_request > limit and not songs.rendering()


def _stop_when_idle(server: uvicorn.Server, songs: Songs) -> None:
    while not server.should_exit:
        time.sleep(IDLE_CHECK_SECONDS)
        if idle(songs, time.monotonic()):
            print("lyrics-video: no page open for a while; stopping.", file=sys.stderr, flush=True)
            server.should_exit = True


def _stop_soon(server: uvicorn.Server) -> None:
    """Stop after the current response is sent, so the page learns that Quit worked."""
    threading.Timer(0.3, lambda: setattr(server, "should_exit", True)).start()


def _open_when_started(server: uvicorn.Server, url: str) -> None:
    for _ in range(100):
        if server.started:
            webbrowser.open(url)
            return
        threading.Event().wait(0.05)
