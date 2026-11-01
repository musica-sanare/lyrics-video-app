import time

from lyrics_video import app_files
from lyrics_video.cli import EXIT_OK, main
from lyrics_video.web import server
from lyrics_video.web.app import Songs


def test_idle_after_a_while_without_requests():
    songs = Songs()
    songs.last_request = 100.0

    assert not server.idle(songs, now=100.0 + server.IDLE_SECONDS - 1)
    assert server.idle(songs, now=100.0 + server.IDLE_SECONDS + 1)


def test_never_idle_while_rendering(monkeypatch):
    songs = Songs()
    songs.last_request = 0.0
    monkeypatch.setattr(songs, "rendering", lambda: True)

    assert not server.idle(songs, now=time.monotonic())


def test_a_second_start_opens_the_running_app(monkeypatch):
    app_files.write_server(8123, "secret")
    opened, started = [], []
    monkeypatch.setattr(server, "answers", lambda port, token: (port, token) == (8123, "secret"))
    monkeypatch.setattr(server.webbrowser, "open", opened.append)
    monkeypatch.setattr(server, "run", lambda *args, **kwargs: started.append(kwargs))

    server.start()

    assert opened == ["http://127.0.0.1:8123/?token=secret"]
    assert started == []


def test_a_recorded_server_that_stopped_is_replaced(monkeypatch):
    app_files.write_server(8123, "secret")
    started = []
    monkeypatch.setattr(server, "answers", lambda port, token: False)
    monkeypatch.setattr(server, "run", lambda song, **kwargs: started.append((song, kwargs)))

    server.start(open_browser=False)

    assert started == [(None, {"port": 0, "open_browser": False, "app_mode": True})]


def test_nothing_answers_on_a_free_port():
    assert not server.answers(1, "secret")


def test_the_start_command(monkeypatch):
    calls = []
    monkeypatch.setattr("lyrics_video.cli.start_app", lambda **kwargs: calls.append(kwargs))

    assert main(["start", "--no-browser", "--port", "8124"]) == EXIT_OK
    assert calls == [{"port": 8124, "open_browser": False}]
