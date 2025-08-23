import numpy as np
from dataclasses import dataclass
from typing import Tuple


@dataclass
class VideoClip:
    frames: np.ndarray
    times:  np.ndarray
    size:   Tuple[int, int]
    note:   str = ""

    @property
    def nframes(self) -> int:
        return int(self.frames.shape[0])

    @property
    def duration(self) -> float:
        return float(self.times[-1]) if self.nframes > 0 else 0.0

    @property
    def shape(self) -> Tuple[int, int, int, int]:
        return self.frames.shape
