"""audio-spectrum-app is installed and its backdrop API works as this app will use it."""

import numpy as np
from signals import write_sine

from audio_spectrum import load_preset, render_stills

WIDTH, HEIGHT, FPS = 320, 180, 30
BACKDROP_COLOR = (12, 34, 56)


class SolidBackdrop:
    def frame(self, index: int, seconds: float, width: int, height: int) -> np.ndarray:
        return np.full((height, width, 3), BACKDROP_COLOR, dtype=np.uint8)


def test_a_still_is_drawn_over_the_backdrop(tmp_path):
    audio = write_sine(tmp_path / "tone.wav")

    [frame] = render_stills(
        audio, load_preset("default"), [0.5], WIDTH, HEIGHT, FPS, backdrop=SolidBackdrop()
    )

    assert frame.shape == (HEIGHT, WIDTH, 3)
    assert tuple(frame[0, 0]) == BACKDROP_COLOR
    assert (frame != BACKDROP_COLOR).any(axis=2).any(), "the spectrum is drawn somewhere"
