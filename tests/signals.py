"""Synthetic test signals. Tests never use real songs."""

from pathlib import Path

import numpy as np
import soundfile

SAMPLE_RATE = 48000


def write_sine(path: Path, frequency: float = 440.0, seconds: float = 1.0, amplitude: float = 0.5) -> Path:
    t = np.arange(round(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    tone = (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
    soundfile.write(path, np.stack([tone, tone], axis=1), SAMPLE_RATE)
    return path


def write_silence(path: Path, seconds: float = 1.0) -> Path:
    return write_sine(path, seconds=seconds, amplitude=0.0)
