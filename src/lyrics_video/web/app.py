"""The sync page's HTTP API and page. Every request must come to an expected host, and API requests must carry the
session token, so other web pages in the browser cannot drive the server (Phase 2 plan, "The page")."""

import dataclasses
import hmac
import io
import mimetypes
import subprocess
import threading
import time
from pathlib import Path

from audio_spectrum import AudioSpectrumError, Cancelled, Preview, load_preset, override_preset
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field

from lyrics_video.backdrop import LyricsBackdrop, timed_captions
from lyrics_video.config import Song
from lyrics_video.errors import ConfigError, LyricsVideoError
from lyrics_video.lyrics import read_lyrics
from lyrics_video.render import PreparedRender, default_output, prepare_render, render
from lyrics_video.timing import Merged, TimedLine, check_inside, check_lines, merge, read_lrc, write_lrc

TOKEN_HEADER = "x-token"
# The audio element cannot send headers, so this one route also takes the token as a query parameter.
AUDIO_ROUTE = "/api/audio"
STATIC = Path(__file__).parent / "static"
# How long stopping the server waits for a cancelled render to remove its temporary file.
SHUTDOWN_WAIT_SECONDS = 10.0


class LineData(BaseModel):
    rows: list[str]
    start: float | None = None
    end: float | None = None


class TimingRequest(BaseModel):
    lines: list[LineData]


class StillRequest(TimingRequest):
    time: float = Field(ge=0.0)


class RenderBusyError(LyricsVideoError):
    """A render is running; the page answers 409."""

    code = "busy"


class RenderOutputExistsError(LyricsVideoError):
    """The video exists; the page asks before replacing it."""

    code = "output_exists"


class RenderRequest(BaseModel):
    overwrite: bool = False


class RenderTask:
    """The one render the page can run at a time, in a background thread. The page polls `snapshot`."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.thread: threading.Thread | None = None
        self.state = "idle"
        self.frame = 0
        self.frames = 0
        self.output: Path | None = None
        self.untimed = 0
        self.started = 0.0
        self.seconds: float | None = None
        self.error: dict | None = None

    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self, prepared: PreparedRender) -> None:
        self.cancel.clear()
        with self.lock:
            self.state, self.frame, self.frames, self.seconds, self.error = "running", 0, 0, None, None
            self.output, self.untimed, self.started = prepared.job.output_path, len(prepared.untimed), time.monotonic()
        self.thread = threading.Thread(target=self._run, args=(prepared,), daemon=True)
        self.thread.start()

    def _run(self, prepared: PreparedRender) -> None:
        try:
            render(prepared, progress=self._progress, cancel=self.cancel.is_set)
        except Cancelled:
            state, error = "cancelled", None
        except Exception as failure:  # reported to the page, which otherwise would wait for this render forever
            state, error = "failed", {"code": type(failure).__name__, "message": str(failure)}
        else:
            state, error = "done", None
        with self.lock:
            self.state, self.error, self.seconds = state, error, time.monotonic() - self.started

    def _progress(self, done: int, total: int) -> None:
        with self.lock:
            self.frame, self.frames = done, total

    def snapshot(self, folder: Path) -> dict:
        with self.lock:
            output = self.output
            name = None
            if output is not None:
                name = str(output.relative_to(folder)) if output.is_relative_to(folder) else str(output)
            elapsed = self.seconds if self.seconds is not None else time.monotonic() - self.started
            return {
                "state": self.state, "frame": self.frame, "frames": self.frames, "output": name,
                "untimed": self.untimed, "elapsed": elapsed if self.state != "idle" else 0.0, "error": self.error,
            }

    def stop(self) -> None:
        """Cancel a running render and wait for it, so no temporary file is left when the server stops."""
        self.cancel.set()
        if self.thread is not None:
            self.thread.join(SHUTDOWN_WAIT_SECONDS)


class SyncSession:
    """One song: its audio decoded once, and one backdrop whose captions change between stills."""

    def __init__(self, song: Song):
        if song.audio is None:
            raise ConfigError(f"{song.path}: audio is not set (the song file for the spectrum)")
        self.song = song
        self.timing_path = song.timing or song.lyrics.with_suffix(".lrc")
        self.lock = threading.Lock()
        try:
            self.preview = Preview(song.audio, song.video.fps)
            self.preset = override_preset(
                load_preset(song.spectrum_preset), [*song.design.spectrum.set, *song.spectrum_set]
            )
        except AudioSpectrumError as error:
            raise ConfigError(str(error)) from None
        self.duration = self.preview.duration
        self.backdrop = LyricsBackdrop.for_song(song, [], self.duration)
        self.backdrop.prepare(song.video.width, song.video.height)
        self.render = RenderTask()
        # Held while a render is checked and started, so two requests cannot start two renders.
        self.starting = threading.Lock()

    def load(self) -> dict:
        """The lines to time: the timing file merged with the lyrics file, or the lyrics file alone at first."""
        separator = self.song.separator
        if self.timing_path.exists():
            timed = read_lrc(self.timing_path, separator)
            merged = merge(timed, read_lyrics(self.song.lyrics, separator)) if self.song.lyrics.exists() else Merged(
                timed, []
            )
        else:
            merged = Merged([TimedLine(c.rows) for c in read_lyrics(self.song.lyrics, separator)], [])
        style = self.song.design.caption
        return {
            "title": self.song.title or self.song.path.parent.name,
            "song_file": self.song.path.name,
            "timing_file": self.timing_path.name,
            "timing_exists": self.timing_path.exists(),
            "timing_configured": self.song.timing is not None,
            "lyrics_file": self.song.lyrics.name,
            "duration": self.duration,
            "separator": separator,
            "lead": style.lead_seconds,
            "fade": style.fade_seconds,
            "transition": style.transition,
            "lines": [dataclasses.asdict(line) for line in merged.lines],
            "changes": [dataclasses.asdict(change) for change in merged.changes],
        }

    def lines(self, request: TimingRequest) -> list[TimedLine]:
        lines = [TimedLine(tuple(line.rows), line.start, line.end) for line in request.lines]
        check_lines(lines, self.song.separator)
        check_inside(lines, self.duration, "timing")
        return lines

    def save(self, request: TimingRequest) -> dict:
        if self.render.running():
            raise RenderBusyError("a video is being rendered; save after it is done or cancelled")
        lines = self.lines(request)
        write_lrc(self.timing_path, lines, self.song.separator, backup=True)
        return {"timing_file": self.timing_path.name}

    def start_render(self, overwrite: bool) -> None:
        """Render the saved timing file, never the page's unsaved edits, to the `render` command's default file."""
        if not self.starting.acquire(blocking=False):
            raise RenderBusyError("a video is already being rendered")
        try:
            if self.render.running():
                raise RenderBusyError("a video is already being rendered")
            song = dataclasses.replace(self.song, timing=self.timing_path)
            if not self.timing_path.exists():
                raise ConfigError(f"{self.timing_path.name} does not exist yet; save the timing first")
            output = default_output(song)
            if output.exists() and not overwrite:
                raise RenderOutputExistsError(f"{output.relative_to(self.song.path.parent)} exists")
            self.render.start(prepare_render(song, output=output, overwrite=overwrite))
        finally:
            self.starting.release()

    def reveal(self) -> None:
        """Select the finished video in the Finder; only the file this session rendered."""
        output = self.render.output
        if self.render.state != "done" or output is None or not output.exists():
            raise ConfigError("there is no finished video to show")
        subprocess.run(["open", "-R", str(output)], check=False)

    def still(self, request: StillRequest) -> bytes:
        lines = self.lines(request)
        video = self.song.video
        with self.lock:
            self.backdrop.set_captions(timed_captions(lines, self.duration))
            try:
                [frame] = self.preview.frames(self.preset, [request.time], video.width, video.height, backdrop=self.backdrop)
            except AudioSpectrumError as error:
                raise ConfigError(str(error)) from None
        buffer = io.BytesIO()
        Image.fromarray(frame).save(buffer, format="PNG", compress_level=1)
        return buffer.getvalue()


def create_app(session: SyncSession, token: str, allowed_hosts: set[str]) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    expected = token.encode()

    @app.middleware("http")
    async def guard(request: Request, call_next):
        # A foreign Host header means DNS rebinding; a missing token means another page in the browser.
        if request.headers.get("host") not in allowed_hosts:
            return _error(403, "forbidden", "unexpected host")
        if request.url.path.startswith("/api/"):
            supplied = request.headers.get(TOKEN_HEADER, "")
            if request.url.path == AUDIO_ROUTE and not supplied:
                supplied = request.query_params.get("token", "")
            if not hmac.compare_digest(supplied.encode(), expected):
                return _error(403, "forbidden", "missing or wrong session token")
        return await call_next(request)

    @app.exception_handler(LyricsVideoError)
    async def app_error(request: Request, error: LyricsVideoError):
        if isinstance(error, (RenderBusyError, RenderOutputExistsError)):
            return _error(409, error.code, str(error))
        return _error(400, type(error).__name__, str(error))

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return (STATIC / "index.html").read_text(encoding="utf-8")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/api/song")
    def song() -> dict:
        return session.load()

    @app.get(AUDIO_ROUTE)
    def audio() -> FileResponse:
        media_type = mimetypes.guess_type(session.song.audio.name)[0] or "application/octet-stream"
        return FileResponse(session.song.audio, media_type=media_type)

    @app.post("/api/timing")
    def save(request: TimingRequest) -> dict:
        return session.save(request)

    @app.post("/api/still")
    def still(request: StillRequest) -> Response:
        return Response(session.still(request), media_type="image/png")

    @app.get("/api/render")
    def render_state() -> dict:
        return session.render.snapshot(session.song.path.parent)

    @app.post("/api/render")
    def start_render(request: RenderRequest) -> dict:
        session.start_render(request.overwrite)
        return session.render.snapshot(session.song.path.parent)

    @app.post("/api/render/cancel")
    def cancel_render() -> dict:
        session.render.cancel.set()
        return session.render.snapshot(session.song.path.parent)

    @app.post("/api/render/reveal")
    def reveal() -> dict:
        session.reveal()
        return {}

    return app


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status_code=status)
