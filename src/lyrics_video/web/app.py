"""The sync page's HTTP API and page. Every request must come to an expected host, and API requests must carry the
session token, so other web pages in the browser cannot drive the server (Phase 2 plan, "The page")."""

import dataclasses
import hmac
import io
import mimetypes
import threading
from pathlib import Path

from audio_spectrum import AudioSpectrumError, Preview, load_preset, override_preset
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field

from lyrics_video.backdrop import LyricsBackdrop, timed_captions
from lyrics_video.config import Song
from lyrics_video.errors import ConfigError, LyricsVideoError
from lyrics_video.lyrics import read_lyrics
from lyrics_video.timing import Merged, TimedLine, check_inside, check_lines, merge, read_lrc, write_lrc

TOKEN_HEADER = "x-token"
# The audio element cannot send headers, so this one route also takes the token as a query parameter.
AUDIO_ROUTE = "/api/audio"
STATIC = Path(__file__).parent / "static"


class LineData(BaseModel):
    rows: list[str]
    start: float | None = None
    end: float | None = None


class TimingRequest(BaseModel):
    lines: list[LineData]


class StillRequest(TimingRequest):
    time: float = Field(ge=0.0)


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

    def load(self) -> dict:
        """The lines to time: the timing file merged with the lyrics file, or the lyrics file alone at first."""
        separator = self.song.look.separator
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
        check_lines(lines, self.song.look.separator)
        check_inside(lines, self.duration, "timing")
        return lines

    def save(self, request: TimingRequest) -> dict:
        lines = self.lines(request)
        write_lrc(self.timing_path, lines, self.song.look.separator, backup=True)
        return {"timing_file": self.timing_path.name}

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

    return app


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status_code=status)
