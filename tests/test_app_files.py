import os
import stat

from lyrics_video.app_files import (
    RECENT_LIMIT,
    add_recent,
    app_folder,
    read_server,
    recent_songs,
    remove_server,
    write_server,
)


def test_the_running_server_is_recorded_for_the_owner_only(app_files):
    write_server(8123, "secret")

    assert read_server() == {"port": 8123, "token": "secret", "pid": os.getpid()}
    assert stat.S_IMODE((app_files / "server.json").stat().st_mode) == 0o600
    remove_server()
    assert read_server() is None


def test_only_the_process_that_recorded_the_server_forgets_it(app_files):
    (app_files / "server.json").write_text('{"port": 1, "token": "t", "pid": 1}', encoding="utf-8")

    remove_server()

    assert read_server() == {"port": 1, "token": "t", "pid": 1}


def test_a_broken_server_file_is_ignored(app_files):
    (app_files / "server.json").write_text("not json", encoding="utf-8")

    assert read_server() is None


def test_recent_songs_newest_first_without_repeats(tmp_path):
    first, second = tmp_path / "a.toml", tmp_path / "b.toml"
    first.write_text("", encoding="utf-8")
    second.write_text("", encoding="utf-8")

    add_recent(first, "A")
    add_recent(second, "B")
    add_recent(first, "A again")

    songs = recent_songs()
    expected = [(str(first.resolve()), "A again"), (str(second.resolve()), "B")]
    assert [(entry["path"], entry["title"]) for entry in songs] == expected
    assert all(entry["exists"] for entry in songs)


def test_recent_songs_are_limited_and_report_missing_files(tmp_path):
    for number in range(RECENT_LIMIT + 3):
        add_recent(tmp_path / f"{number}.toml", str(number))

    songs = recent_songs()
    assert len(songs) == RECENT_LIMIT
    assert songs[0]["title"] == str(RECENT_LIMIT + 2)
    assert not songs[0]["exists"]


def test_the_app_folder_comes_from_the_environment(app_files):
    assert app_folder() == app_files
