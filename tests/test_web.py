import io
import json
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from audio_spectrum import Cancelled
from fastapi.testclient import TestClient
from PIL import Image
from signals import write_sine
from test_render import probe

from lyrics_video.cli import EXIT_FAILED, main
from lyrics_video.config import load_song
from lyrics_video.still import make_stills
from lyrics_video.web import app as web_app
from lyrics_video.web.app import STATIC, SyncSession, create_app

TOKEN = "test-token"
HOST = "testserver"
LYRICS = "一行目\n\n三行目;下の行\n"
TIMED = [{"rows": ["一行目"], "start": 0.5, "end": None}, {"rows": ["三行目", "下の行"], "start": 1.5, "end": 2.5}]


def make_song(folder: Path, font: Path, timing: bool = True) -> Path:
    write_sine(folder / "tone.wav", seconds=3.0)
    Image.new("RGB", (640, 480), (30, 60, 90)).save(folder / "bg.png")
    (folder / "lyrics.txt").write_text(LYRICS, encoding="utf-8")
    song = folder / "song.toml"
    song.write_text(
        ('timing = "lyrics.lrc"\n' if timing else "")
        + 'audio = "tone.wav"\nbackground_image = "bg.png"\ntitle = "Title"\n'
        + f'[fonts]\ndefault = "{font}"\n[video]\nwidth = 480\nheight = 270\n',
        encoding="utf-8",
    )
    return song


@pytest.fixture
def song(tmp_path, sans_font):
    return make_song(tmp_path, sans_font)


@pytest.fixture
def client(song):
    return TestClient(create_app(SyncSession(load_song(song)), TOKEN, {HOST}))


def get(client, path, headers=None):
    return client.get(path, headers={"X-Token": TOKEN, **(headers or {})})


def post(client, path, body):
    return client.post(path, json=body, headers={"X-Token": TOKEN})


def test_api_requests_need_the_token(client):
    assert client.get("/api/song").status_code == 403
    assert client.get("/api/song", headers={"X-Token": "wrong"}).status_code == 403
    assert client.post("/api/timing", json={"lines": TIMED}).status_code == 403
    assert get(client, "/api/song").status_code == 200


def test_the_token_in_the_url_is_accepted_for_the_audio_only(client):
    assert client.get(f"/api/audio?token={TOKEN}").status_code == 200
    assert client.get("/api/audio?token=wrong").status_code == 403
    assert client.get("/api/audio?token=ü").status_code == 403
    assert client.get(f"/api/song?token={TOKEN}").status_code == 403
    assert client.post(f"/api/timing?token={TOKEN}", json={"lines": TIMED}).status_code == 403


def test_foreign_hosts_are_refused(client):
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 403
    assert get(client, "/api/song", headers={"Host": "evil.example"}).status_code == 403


def test_the_page_and_no_cross_origin_headers(client):
    response = client.get("/", headers={"Origin": "http://evil.example"})

    assert response.status_code == 200
    assert "app.js" in response.text
    assert not any(name.lower().startswith("access-control-") for name in response.headers)


def test_the_audio_can_be_read_in_ranges(client, song):
    whole = (song.parent / "tone.wav").read_bytes()

    response = client.get(f"/api/audio?token={TOKEN}", headers={"Range": "bytes=100-199"})

    assert response.status_code == 206
    assert response.content == whole[100:200]
    assert response.headers["content-range"] == f"bytes 100-199/{len(whole)}"


def test_first_load_takes_the_lines_from_the_lyrics(client):
    data = get(client, "/api/song").json()

    assert data["lines"] == [{"rows": ["一行目"], "start": None, "end": None}, {"rows": ["三行目", "下の行"], "start": None, "end": None}]
    assert (data["timing_exists"], data["timing_configured"], data["changes"]) == (False, True, [])
    assert (data["timing_file"], data["lyrics_file"], data["title"]) == ("lyrics.lrc", "lyrics.txt", "Title")
    assert data["duration"] == pytest.approx(3.0)
    assert (data["lead"], data["fade"], data["transition"]) == (0.2, 0.3, "sequential")


def test_saving_writes_the_timing_and_keeps_a_backup(client, song):
    timing = song.parent / "lyrics.lrc"

    assert post(client, "/api/timing", {"lines": TIMED}).json() == {"timing_file": "lyrics.lrc"}
    first = timing.read_text(encoding="utf-8")
    assert first == "[00:00.50]一行目\n[00:01.50]三行目;下の行\n[00:02.50]\n"
    assert not (song.parent / "lyrics.lrc.bak").exists()

    moved = [dict(TIMED[0], start=0.6), TIMED[1]]
    assert post(client, "/api/timing", moved).status_code == 422
    assert post(client, "/api/timing", {"lines": moved}).status_code == 200
    assert (song.parent / "lyrics.lrc.bak").read_text(encoding="utf-8") == first
    assert get(client, "/api/song").json()["lines"][0]["start"] == 0.6


def test_a_round_trip_keeps_the_times(client):
    lines = [{"rows": ["一行目"], "start": 0.37, "end": 1.01}, {"rows": ["三行目", "下の行"], "start": 1.42, "end": None}]

    post(client, "/api/timing", {"lines": lines})

    assert get(client, "/api/song").json()["lines"] == lines


@pytest.mark.parametrize(
    ("lines", "message"),
    [
        ([dict(TIMED[0], start=2.0), TIMED[1]], "line 2"),
        ([dict(TIMED[0], start=2.9, end=3.5)], "after the end of the song"),
        ([{"rows": ["a;b"], "start": 0.5, "end": None}], "line 1"),
        ([{"rows": [""], "start": 0.5, "end": None}], "line 1"),
        ([{"rows": ["a"], "start": None, "end": 1.0}], "an end time needs a start time"),
    ],
)
def test_invalid_timing_is_not_saved(client, song, lines, message):
    response = post(client, "/api/timing", {"lines": lines})

    assert response.status_code == 400
    assert message in response.json()["message"]
    assert not (song.parent / "lyrics.lrc").exists()


def test_a_changed_lyrics_file_keeps_the_times_of_unchanged_lines(client, song):
    post(client, "/api/timing", {"lines": TIMED})
    (song.parent / "lyrics.txt").write_text("一行目\n新しい行\n三行目;下の行\n", encoding="utf-8")

    data = get(client, "/api/song").json()

    assert data["lines"] == [TIMED[0], {"rows": ["新しい行"], "start": None, "end": None}, TIMED[1]]
    assert data["changes"] == [{"kind": "added", "rows": ["新しい行"]}]


def test_stills_are_the_frames_of_the_video(client, song):
    post(client, "/api/timing", {"lines": TIMED})
    make_stills(load_song(song), [1.0, 2.0])

    for seconds in (1.0, 2.0):
        response = post(client, "/api/still", {"lines": TIMED, "time": seconds})
        assert response.headers["content-type"] == "image/png"
        page = np.asarray(Image.open(io.BytesIO(response.content)))
        expected = np.asarray(Image.open(song.parent / f"stills/soft_{seconds:g}s.png"))
        assert np.array_equal(page, expected)


def test_stills_follow_unsaved_times(client):
    one = post(client, "/api/still", {"lines": TIMED, "time": 1.0}).content
    moved = post(client, "/api/still", {"lines": [dict(TIMED[0], start=1.2), TIMED[1]], "time": 1.0}).content

    assert one != moved


def test_a_still_outside_the_song_is_an_error(client):
    response = post(client, "/api/still", {"lines": TIMED, "time": 9.0})

    assert response.status_code == 400
    assert "outside" in response.json()["message"]


def test_without_a_timing_key_the_timing_goes_next_to_the_lyrics(tmp_path, sans_font):
    song = make_song(tmp_path, sans_font, timing=False)
    client = TestClient(create_app(SyncSession(load_song(song)), TOKEN, {HOST}))

    assert get(client, "/api/song").json()["timing_configured"] is False
    post(client, "/api/timing", {"lines": TIMED})
    assert (tmp_path / "lyrics.lrc").is_file()


def test_sync_reports_song_errors_before_serving(tmp_path, sans_font, capsys):
    song = make_song(tmp_path, sans_font)
    song.write_text(song.read_text(encoding="utf-8").replace('audio = "tone.wav"\n', ""), encoding="utf-8")

    assert main(["sync", str(song), "--no-browser"]) == EXIT_FAILED
    assert "audio is not set" in capsys.readouterr().err


def messages(code):
    return json.loads((STATIC / "i18n" / f"{code}.json").read_text(encoding="utf-8"))["messages"]


@pytest.mark.parametrize("code", ["ja", "es", "fr"])
def test_messages_are_complete_in_every_language(code):
    english = messages("en")
    translated = messages(code)

    assert translated.keys() == english.keys()
    for key, text in english.items():
        assert set(re.findall(r"\{\w+\}", translated[key])) == set(re.findall(r"\{\w+\}", text)), key
        assert len(re.findall(r"\[\[", translated[key])) == len(re.findall(r"\[\[", text)), key


def test_every_message_the_page_uses_exists():
    script = (STATIC / "app.js").read_text(encoding="utf-8")
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    used = set(re.findall(r'\bt\("([a-z_]+\.[a-z_.]+)"', script)) | set(re.findall(r'data-i18n="([^"]+)"', page))
    used |= {"play.pause", "help.tap", "help.adjust", "notice.added", "notice.removed"}
    used |= {"transition.crossfade", "transition.sequential"}

    assert used - messages("en").keys() == set()


# --- Rendering from the page ---------------------------------------------------------------------------------------


@pytest.fixture
def session(song):
    session = SyncSession(load_song(song))
    yield session
    session.close()


@pytest.fixture
def render_client(session):
    return TestClient(create_app(session, TOKEN, {HOST}))


def wait_for_render(client, timeout=60.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = get(client, "/api/render").json()
        if snapshot["state"] != "running":
            return snapshot
        time.sleep(0.05)
    raise AssertionError("the render did not finish")


class HeldRender:
    """Stands in for the real render: runs until released or cancelled, so tests can act while it runs."""

    def __init__(self):
        self.release = threading.Event()

    def __call__(self, prepared, progress=None, cancel=None):
        progress(0, 10)
        while not self.release.is_set():
            if cancel():
                raise Cancelled("cancelled")
            time.sleep(0.01)
        progress(10, 10)


@pytest.fixture
def held(monkeypatch):
    held = HeldRender()
    monkeypatch.setattr(web_app, "render", held)
    yield held
    held.release.set()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_the_page_renders_the_saved_timing(render_client, song):
    post(render_client, "/api/timing", {"lines": TIMED})

    started = post(render_client, "/api/render", {})
    snapshot = wait_for_render(render_client)

    assert started.status_code == 200 and started.json()["state"] == "running"
    assert snapshot["state"] == "done", snapshot
    assert snapshot["output"] == "videos/song.mp4"
    assert snapshot["frame"] == snapshot["frames"] == 90
    assert (song.parent / "videos" / "song.mp4").stat().st_size > 0


def test_rendering_needs_saved_timing(render_client):
    response = post(render_client, "/api/render", {})

    assert response.status_code == 400
    assert "save the timing first" in response.json()["message"]


def test_one_render_at_a_time_and_no_saving_while_it_runs(render_client, held):
    post(render_client, "/api/timing", {"lines": TIMED})
    assert post(render_client, "/api/render", {}).json()["state"] == "running"

    second = post(render_client, "/api/render", {})
    saving = post(render_client, "/api/timing", {"lines": TIMED})

    assert (second.status_code, second.json()["code"]) == (409, "busy")
    assert (saving.status_code, saving.json()["code"]) == (409, "busy")
    held.release.set()
    assert wait_for_render(render_client)["state"] == "done"
    assert post(render_client, "/api/timing", {"lines": TIMED}).status_code == 200


def test_an_existing_video_is_replaced_only_when_asked(render_client, song, held):
    post(render_client, "/api/timing", {"lines": TIMED})
    video = song.parent / "videos" / "song.mp4"
    video.parent.mkdir()
    video.write_bytes(b"kept")

    refused = post(render_client, "/api/render", {})
    allowed = post(render_client, "/api/render", {"overwrite": True})

    assert (refused.status_code, refused.json()["code"]) == (409, "output_exists")
    assert refused.json()["message"] == "videos/song.mp4 exists"
    assert allowed.json()["state"] == "running"


def test_cancelling_a_render(render_client, held):
    post(render_client, "/api/timing", {"lines": TIMED})
    post(render_client, "/api/render", {})

    post(render_client, "/api/render/cancel", {})

    assert wait_for_render(render_client)["state"] == "cancelled"


def test_stopping_the_server_cancels_the_render(render_client, session, held):
    post(render_client, "/api/timing", {"lines": TIMED})
    post(render_client, "/api/render", {})

    session.render.stop()

    assert not session.render.running()
    assert session.render.snapshot(session.song.path.parent)["state"] == "cancelled"


def test_show_in_finder_only_for_the_finished_video(render_client, song, held, monkeypatch):
    opened = []
    monkeypatch.setattr(web_app.subprocess, "run", lambda command, check: opened.append(command))
    post(render_client, "/api/timing", {"lines": TIMED})
    assert post(render_client, "/api/render/reveal", {}).status_code == 400

    post(render_client, "/api/render", {})
    held.release.set()
    wait_for_render(render_client)
    (song.parent / "videos").mkdir(exist_ok=True)
    (song.parent / "videos" / "song.mp4").write_bytes(b"video")

    assert post(render_client, "/api/render/reveal", {}).status_code == 200
    assert opened == [["open", "-R", str(song.parent / "videos" / "song.mp4")]]


def test_render_routes_need_the_token(render_client):
    assert render_client.get("/api/render").status_code == 403
    for path in ("/api/render", "/api/render/cancel", "/api/render/reveal"):
        assert render_client.post(path, json={}).status_code == 403


def test_an_unexpected_failure_is_reported(render_client, monkeypatch):
    def broken(prepared, progress=None, cancel=None):
        raise OSError("disk full")

    monkeypatch.setattr(web_app, "render", broken)
    post(render_client, "/api/timing", {"lines": TIMED})
    post(render_client, "/api/render", {})

    snapshot = wait_for_render(render_client)

    assert snapshot["state"] == "failed"
    assert snapshot["error"] == {"code": "OSError", "message": "disk full"}


# --- The preview video ---------------------------------------------------------------------------------------------


def preview_url(token=TOKEN):
    return f"/api/preview/video?token={token}"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_the_preview_is_made_from_unsaved_lines(render_client, session, song):
    started = post(render_client, "/api/preview", {"lines": TIMED})
    snapshot = wait_for_render(render_client)
    response = render_client.get(preview_url())

    assert started.json()["kind"] == "preview"
    assert snapshot["state"] == "done", snapshot
    assert snapshot["output"] is None
    assert not (song.parent / "lyrics.lrc").exists() and not (song.parent / "videos").exists()
    assert response.status_code == 200 and response.headers["content-type"] == "video/mp4"
    video = session.preview_folder / web_app.PREVIEW_FILE
    streams = probe(video)
    assert "audio" not in streams
    assert (streams["video"]["width"], streams["video"]["height"]) == (480, 270)
    assert int(streams["video"]["nb_read_frames"]) == 3 * 15


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_the_preview_shows_the_captions_of_the_stills(render_client, session):
    post(render_client, "/api/preview", {"lines": TIMED})
    wait_for_render(render_client)
    frames = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(session.preview_folder / web_app.PREVIEW_FILE), "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    ).stdout
    frames = np.frombuffer(frames, dtype=np.uint8).reshape(-1, 270, 480, 3).astype(int)

    for seconds in (0.2, 1.0, 2.0):
        still = np.asarray(Image.open(io.BytesIO(post(render_client, "/api/still", {"lines": TIMED, "time": seconds}).content)))
        frame = frames[round(seconds * 15)]
        assert np.abs(frame - still).mean() < 6, seconds
    # The captions differ between those times, so the comparison above would notice a wrong caption.
    assert np.abs(frames[3] - frames[30]).mean() > 1


def test_no_preview_before_one_is_made(render_client):
    assert render_client.get(preview_url()).status_code == 404


def test_the_preview_needs_the_token(render_client):
    assert render_client.get(preview_url("wrong")).status_code == 403
    assert render_client.post("/api/preview", json={"lines": TIMED}).status_code == 403


def test_invalid_lines_make_no_preview(render_client, session):
    response = post(render_client, "/api/preview", {"lines": [dict(TIMED[0], start=9.0)]})

    assert response.status_code == 400
    assert session.preview_folder is None


def test_one_preview_or_render_at_a_time_and_saving_during_a_preview(render_client, held):
    post(render_client, "/api/timing", {"lines": TIMED})
    assert post(render_client, "/api/preview", {"lines": TIMED}).json()["state"] == "running"

    render_refused = post(render_client, "/api/render", {})
    preview_refused = post(render_client, "/api/preview", {"lines": TIMED})
    saving = post(render_client, "/api/timing", {"lines": TIMED})

    assert (render_refused.status_code, render_refused.json()["code"]) == (409, "busy")
    assert "preview" in render_refused.json()["message"]
    assert preview_refused.status_code == 409
    assert saving.status_code == 200
    held.release.set()
    assert wait_for_render(render_client)["state"] == "done"
    held.release.clear()
    assert post(render_client, "/api/render", {}).json()["kind"] == "video"
    assert post(render_client, "/api/preview", {"lines": TIMED}).status_code == 409


def test_show_in_finder_is_not_for_the_preview(render_client, held, monkeypatch):
    monkeypatch.setattr(web_app.subprocess, "run", lambda command, check: None)
    post(render_client, "/api/preview", {"lines": TIMED})
    held.release.set()
    wait_for_render(render_client)

    assert post(render_client, "/api/render/reveal", {}).status_code == 400


def test_closing_the_session_removes_the_preview(render_client, session, held):
    post(render_client, "/api/preview", {"lines": TIMED})
    folder = session.preview_folder

    session.close()

    assert not session.render.running()
    assert not folder.exists() and session.preview_folder is None


def test_the_page_learns_the_preview_size(client):
    assert get(client, "/api/song").json()["preview"] == {"width": 480, "height": 270, "fps": 15.0}


# --- The Design mode -----------------------------------------------------------------------------------------------

BOLD_TITLE = {"name": "soft", "overrides": {"title": {"bold": True}}}


def test_the_page_learns_the_design_and_its_bases(client):
    design = get(client, "/api/song").json()["design"]

    assert (design["name"], design["overrides"]) == ("soft", {})
    assert set(design["bases"]) == {"classic", "panel", "soft"}
    assert design["bases"]["soft"]["caption"]["style"] == "gradient"
    assert design["bases"]["soft"]["title"]["color"] == [255, 255, 255]


def test_stills_follow_the_unsaved_design(client, song):
    saved = post(client, "/api/still", {"lines": TIMED, "time": 1.0}).content
    bold = post(client, "/api/still", {"lines": TIMED, "time": 1.0, "design": BOLD_TITLE}).content
    again = post(client, "/api/still", {"lines": TIMED, "time": 1.0}).content

    assert bold != saved
    assert again == saved
    assert "bold" not in song.read_text(encoding="utf-8")


def test_an_invalid_design_is_named(client):
    response = post(client, "/api/still", {"lines": TIMED, "time": 1.0, "design": {"name": "soft", "overrides": {"title": {"size": -5}}}})

    assert response.status_code == 400
    assert "design.title.size" in response.json()["message"]


def test_saving_the_design_writes_the_song_file(client, song):
    response = post(client, "/api/design", BOLD_TITLE)

    assert response.json() == {"song_file": "song.toml"}
    assert "[design.title]\nbold = true" in song.read_text(encoding="utf-8")
    assert (song.parent / "song.toml.bak").exists()
    assert get(client, "/api/song").json()["design"]["overrides"] == {"title": {"bold": True}}
    assert load_song(song).design.title.bold


def test_no_design_is_saved_while_a_video_renders(render_client, song, held):
    post(render_client, "/api/timing", {"lines": TIMED})
    post(render_client, "/api/render", {})

    response = post(render_client, "/api/design", BOLD_TITLE)

    assert (response.status_code, response.json()["code"]) == (409, "busy")
    assert "bold" not in song.read_text(encoding="utf-8")


def test_the_preview_uses_the_unsaved_design(render_client, monkeypatch):
    started = []
    monkeypatch.setattr(web_app, "render", lambda prepared, progress=None, cancel=None: started.append(prepared))

    post(render_client, "/api/preview", {"lines": TIMED, "design": BOLD_TITLE})
    wait_for_render(render_client)

    assert started[0].job.backdrop.design.title.bold


def test_the_fonts_of_this_mac_and_of_the_song(client, sans_font, monkeypatch):
    monkeypatch.setattr(web_app, "FONT_FOLDERS", ())

    fonts = get(client, "/api/fonts").json()

    assert {"path": str(sans_font), "face": 0, "name": "Hiragino Sans W3"} in fonts
    assert all(not font["name"].startswith(".") for font in fonts)


def test_stills_follow_an_unsaved_spectrum(client):
    taller = {"name": "soft", "overrides": {"spectrum": {"look": {"max_height": 0.9}}}}
    wrong = {"name": "soft", "overrides": {"spectrum": {"look": {"kind": "perspective"}}}}

    saved = post(client, "/api/still", {"lines": TIMED, "time": 1.0}).content
    tall = post(client, "/api/still", {"lines": TIMED, "time": 1.0, "design": taller}).content
    refused = post(client, "/api/still", {"lines": TIMED, "time": 1.0, "design": wrong})

    assert tall != saved
    assert refused.status_code == 400 and "look.kind" in refused.json()["message"]
