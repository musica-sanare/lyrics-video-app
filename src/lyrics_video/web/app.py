"""The sync page's HTTP API and page. Every request must come to an expected host, and API requests must carry the
session token, so other web pages in the browser cannot drive the server (Phase 2 plan, "The page")."""

import dataclasses
import hmac
import io
import mimetypes
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from audio_spectrum import AudioSpectrumError, Cancelled, Preview, builtin_preset_names, user_preset_names
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field

from lyrics_video.backdrop import LyricsBackdrop, timed_captions
from lyrics_video.config import Song, preset_values, save_user_design, song_design, spectrum_preset, write_design
from lyrics_video.design import Design, builtin_design_names, user_design_folder, user_design_names
from lyrics_video.errors import ConfigError, LyricsVideoError, OutputExistsError
from lyrics_video.fonts import FONT_FOLDERS, font_faces
from lyrics_video.lyrics import read_lyrics
from lyrics_video.render import PreparedRender, default_output, prepare_preview, prepare_render, preview_size, render
from lyrics_video.timing import Merged, TimedLine, check_inside, check_lines, merge, read_lrc, write_lrc

TOKEN_HEADER = "x-token"
# Audio and video elements cannot send headers, so these routes also take the token as a query parameter.
AUDIO_ROUTE = "/api/audio"
PREVIEW_ROUTE = "/api/preview/video"
MEDIA_ROUTES = {AUDIO_ROUTE, PREVIEW_ROUTE}
PREVIEW_FILE = "preview.mp4"
STATIC = Path(__file__).parent / "static"
# How long stopping the server waits for a cancelled render to remove its temporary file.
SHUTDOWN_WAIT_SECONDS = 10.0


class LineData(BaseModel):
    rows: list[str]
    start: float | None = None
    end: float | None = None


class TimingRequest(BaseModel):
    lines: list[LineData]


class DesignRequest(BaseModel):
    """A design as the Design mode edits it: the base design's name and the song file's overrides."""

    name: str
    overrides: dict[str, Any] = {}


class SaveAsRequest(BaseModel):
    """Save the page's design as a user design `name`; replacing one needs `overwrite`."""

    name: str
    design: DesignRequest
    overwrite: bool = False


class PreviewRequest(TimingRequest):
    design: DesignRequest | None = None
    """The page's design, saved or not; the song file's when missing."""


class StillRequest(PreviewRequest):
    time: float = Field(ge=0.0)


class RenderBusyError(LyricsVideoError):
    """A render is running; the page answers 409."""

    code = "busy"


class RenderOutputExistsError(LyricsVideoError):
    """The video exists; the page asks before replacing it."""

    code = "output_exists"


class PreviewMissingError(LyricsVideoError):
    """No preview has been rendered yet; the page answers 404."""

    code = "no_preview"


class RenderRequest(BaseModel):
    overwrite: bool = False


class RenderTask:
    """The one render the page can run at a time, in a background thread: the video, or the preview before it
    (`kind`). The page polls `snapshot`."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.thread: threading.Thread | None = None
        self.kind = "video"
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

    def running_video(self) -> bool:
        return self.running() and self.kind == "video"

    def start(self, prepared: PreparedRender, kind: str = "video") -> None:
        self.cancel.clear()
        with self.lock:
            self.kind, self.state, self.frame, self.frames, self.seconds, self.error = kind, "running", 0, 0, None, None
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
            if output is not None and self.kind == "video":
                name = str(output.relative_to(folder)) if output.is_relative_to(folder) else str(output)
            elapsed = self.seconds if self.seconds is not None else time.monotonic() - self.started
            return {
                "kind": self.kind, "state": self.state, "frame": self.frame, "frames": self.frames, "output": name,
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
            self.preset = spectrum_preset(song)
        except AudioSpectrumError as error:
            raise ConfigError(str(error)) from None
        self.duration = self.preview.duration
        self.fonts: list[dict] | None = None
        self.backdrop = LyricsBackdrop.for_song(song, [], self.duration)
        self.backdrop.prepare(song.video.width, song.video.height)
        self.render = RenderTask()
        # Held while a render is checked and started, so two requests cannot start two renders.
        self.starting = threading.Lock()
        # The preview video lives in a temporary folder of the session, made on first use and removed by `close`.
        self.preview_folder: Path | None = None

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
        width, height, fps = preview_size(self.song)
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
            "preview": {"width": width, "height": height, "fps": fps},
            "design": self.design_state(),
            "lines": [dataclasses.asdict(line) for line in merged.lines],
            "changes": [dataclasses.asdict(change) for change in merged.changes],
        }

    def design_state(self) -> dict:
        """The song file's design, and the values of each design the page can start from (to show what changed)."""
        names = [*builtin_design_names(), *user_design_names()]
        if self.song.design_name not in names:
            names.append(self.song.design_name)
        bases = {name: self._design(DesignRequest(name=name)).model_dump(mode="json") for name in names}
        return {
            "name": self.song.design_name,
            "overrides": self.song.design_overrides,
            "bases": bases,
            "builtins": builtin_design_names(),
            "spectrum": self.spectrum_state(bases),
        }

    def spectrum_state(self, bases: dict[str, dict]) -> dict:
        """The presets the page can start the spectrum from, with their values, and what the song file's own
        `[spectrum]` sets: it wins over the design, so the page says so."""
        names = [*builtin_preset_names(), *user_preset_names()]
        chosen = [base["spectrum"]["preset"] for base in bases.values()]
        chosen += [self.song.design_overrides.get("spectrum", {}).get("preset"), self.song.spectrum_preset]
        names += [name for name in dict.fromkeys(chosen) if name and name not in names]
        return {
            "presets": {name: preset_values(name, self.song) for name in names},
            "song_preset": self.song.spectrum_preset,
            "song_set": list(self.song.spectrum_set),
        }

    def _design(self, request: DesignRequest | None) -> Design:
        if request is None:
            return self.song.design
        return song_design(self.song.path, request.name, request.overrides)

    def _preset_for(self, design: Design):
        if design.spectrum == self.song.design.spectrum:
            return self.preset
        return spectrum_preset(self.song, design)

    def font_list(self) -> list[dict]:
        """The faces of the font files on this Mac and next to the song file's fonts; listed once per session."""
        if self.fonts is None:
            design = self.song.design
            named = [self.song.default_font, design.title.font, design.caption.font, design.credits.font]
            folders = [*FONT_FOLDERS, *{font.parent for font in named if font is not None}]
            home = Path.home()
            self.fonts = [
                {
                    "path": f"~/{face.path.relative_to(home)}" if face.path.is_relative_to(home) else str(face.path),
                    "face": face.face,
                    "name": f"{face.family} {face.style}".strip(),
                }
                for face in font_faces(folders)
            ]
        return self.fonts

    def save_design(self, request: DesignRequest) -> dict:
        """Write the design into the song file's `[design]` (keeping a `.bak`); the session then uses the saved file."""
        if self.render.running_video():
            raise RenderBusyError("a video is being rendered; save after it is done or cancelled")
        self._design(request)
        song = write_design(self.song.path, request.name, request.overrides)
        with self.lock:
            self.song = song
            self.preset = self._preset_for(song.design)
            self.backdrop.set_design(song.design)
        return {"song_file": song.path.name}

    def save_as(self, request: SaveAsRequest) -> dict:
        """Save the page's design, saved in the song file or not, as a user design; returns its values as a base."""
        design = self._design(request.design)
        self._preset_for(design)
        save_user_design(self.song, design, request.name, request.overwrite)
        return {"name": request.name, "base": self._design(DesignRequest(name=request.name)).model_dump(mode="json")}

    def lines(self, request: TimingRequest) -> list[TimedLine]:
        lines = [TimedLine(tuple(line.rows), line.start, line.end) for line in request.lines]
        check_lines(lines, self.song.separator)
        check_inside(lines, self.duration, "timing")
        return lines

    def save(self, request: TimingRequest) -> dict:
        if self.render.running_video():
            raise RenderBusyError("a video is being rendered; save after it is done or cancelled")
        lines = self.lines(request)
        write_lrc(self.timing_path, lines, self.song.separator, backup=True)
        return {"timing_file": self.timing_path.name}

    def start_render(self, overwrite: bool) -> None:
        """Render the saved timing file, never the page's unsaved edits, to the `render` command's default file."""
        if not self.starting.acquire(blocking=False):
            raise RenderBusyError("a video is already being rendered")
        try:
            self._refuse_while_running()
            song = dataclasses.replace(self.song, timing=self.timing_path)
            if not self.timing_path.exists():
                raise ConfigError(f"{self.timing_path.name} does not exist yet; save the timing first")
            output = default_output(song)
            if output.exists() and not overwrite:
                raise RenderOutputExistsError(f"{output.relative_to(self.song.path.parent)} exists")
            self.render.start(prepare_render(song, output=output, overwrite=overwrite))
        finally:
            self.starting.release()

    def start_preview(self, request: PreviewRequest) -> None:
        """Render the preview from the page's current lines and design, saved or not, into a temporary folder."""
        lines = self.lines(request)
        song = dataclasses.replace(self.song, design=self._design(request.design))
        if not self.starting.acquire(blocking=False):
            raise RenderBusyError("a video is already being rendered")
        try:
            self._refuse_while_running()
            if self.preview_folder is None:
                self.preview_folder = Path(tempfile.mkdtemp(prefix="lyrics-video-preview-"))
            output = self.preview_folder / PREVIEW_FILE
            self.render.start(prepare_preview(song, lines, self.duration, output), kind="preview")
        finally:
            self.starting.release()

    def _refuse_while_running(self) -> None:
        if self.render.running():
            kind = "a preview" if self.render.kind == "preview" else "a video"
            raise RenderBusyError(f"{kind} is already being rendered")

    def preview_video(self) -> Path:
        """The last finished preview; a preview being rendered replaces it only when it is done."""
        if self.preview_folder is None or not (self.preview_folder / PREVIEW_FILE).exists():
            raise PreviewMissingError("there is no preview video yet")
        return self.preview_folder / PREVIEW_FILE

    def close(self) -> None:
        """Stop a running render and remove the preview, when the server stops."""
        self.render.stop()
        if self.preview_folder is not None:
            shutil.rmtree(self.preview_folder, ignore_errors=True)
            self.preview_folder = None

    def reveal(self) -> None:
        """Select the finished video in the Finder; only the file this session rendered."""
        output = self.render.output
        if self.render.kind != "video" or self.render.state != "done" or output is None or not output.exists():
            raise ConfigError("there is no finished video to show")
        subprocess.run(["open", "-R", str(output)], check=False)

    def still(self, request: StillRequest) -> bytes:
        lines = self.lines(request)
        design = self._design(request.design)
        video = self.song.video
        with self.lock:
            self.backdrop.set_design(design)
            self.backdrop.set_captions(timed_captions(lines, self.duration))
            preset = self._preset_for(design)
            try:
                [frame] = self.preview.frames(preset, [request.time], video.width, video.height, backdrop=self.backdrop)
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
            if request.url.path in MEDIA_ROUTES and not supplied:
                supplied = request.query_params.get("token", "")
            if not hmac.compare_digest(supplied.encode(), expected):
                return _error(403, "forbidden", "missing or wrong session token")
        return await call_next(request)

    @app.exception_handler(LyricsVideoError)
    async def app_error(request: Request, error: LyricsVideoError):
        if isinstance(error, (RenderBusyError, RenderOutputExistsError)):
            return _error(409, error.code, str(error))
        if isinstance(error, OutputExistsError):
            return _error(409, "output_exists", str(error))
        if isinstance(error, PreviewMissingError):
            return _error(404, error.code, str(error))
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

    @app.post("/api/preview")
    def start_preview(request: PreviewRequest) -> dict:
        session.start_preview(request)
        return session.render.snapshot(session.song.path.parent)

    @app.post("/api/design")
    def save_design(request: DesignRequest) -> dict:
        return session.save_design(request)

    @app.post("/api/design/save-as")
    def save_as(request: SaveAsRequest) -> dict:
        return session.save_as(request)

    @app.post("/api/design/folder")
    def show_design_folder() -> dict:
        folder = user_design_folder()
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(folder)], check=False)
        return {}

    @app.get("/api/fonts")
    def fonts() -> list[dict]:
        return session.font_list()

    @app.get(PREVIEW_ROUTE)
    def preview_video() -> FileResponse:
        return FileResponse(session.preview_video(), media_type="video/mp4", headers={"Cache-Control": "no-store"})

    @app.post("/api/render/reveal")
    def reveal() -> dict:
        session.reveal()
        return {}

    return app


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status_code=status)
