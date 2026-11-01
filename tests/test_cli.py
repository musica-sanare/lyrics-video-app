import subprocess
import sys

import pytest

from lyrics_video import __version__
from lyrics_video.cli import EXIT_OK, EXIT_USAGE, main


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == EXIT_OK
    assert capsys.readouterr().out.strip() == f"lyrics-video {__version__}"


def test_runs_as_a_module():
    result = subprocess.run(
        [sys.executable, "-m", "lyrics_video.cli", "--version"], capture_output=True, text=True, check=True
    )

    assert __version__ in result.stdout


def test_a_command_is_required(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main([])

    assert exit_info.value.code == EXIT_USAGE


@pytest.mark.parametrize("command", ["captions", "compare"])
def test_the_caption_image_commands_are_gone(command, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main([command, "song.toml"])

    assert exit_info.value.code == EXIT_USAGE
