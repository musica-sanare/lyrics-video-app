import subprocess
import sys

import pytest

from lyrics_video import __version__
from lyrics_video.cli import main


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"lyrics-video {__version__}"


def test_runs_as_a_module():
    result = subprocess.run(
        [sys.executable, "-m", "lyrics_video.cli", "--version"], capture_output=True, text=True, check=True
    )

    assert __version__ in result.stdout
