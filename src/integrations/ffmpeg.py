from __future__ import annotations
import av
import numpy as np
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Tuple


@dataclass
class VideoClip:
    frames: np.ndarray          # [N, H, W, 3] uint8 RGB
    times:  np.ndarray          # [N] float seconds, monotonic from 0
    size:   Tuple[int, int]     # (width, height)
    note:   str = ""            # optional metadata tag

    @property
    def nframes(self) -> int:
        return int(self.frames.shape[0])

    @property
    def duration(self) -> float:
        return float(self.times[-1]) if self.nframes > 0 else 0.0

    @property
    def shape(self) -> Tuple[int, int, int, int]:
        return self.frames.shape


# ---------- helpers ----------

def _normalize_times(times: np.ndarray) -> np.ndarray:
    """Start at t=0 and enforce monotonic non-decreasing times."""
    if times.size == 0:
        return times
    t = times.astype(float, copy=True)
    t -= t[0]
    np.maximum.accumulate(t, out=t)
    return t

def _cover_size_and_crop(src_w: int, src_h: int, tgt_w: int, tgt_h: int):
    """Compute scale-to-fill size and centered crop to reach tgt size."""
    scale = max(tgt_w / src_w, tgt_h / src_h)
    new_w = int(round(src_w * scale))
    new_h = int(round(src_h * scale))
    x0 = (new_w - tgt_w) // 2
    y0 = (new_h - tgt_h) // 2
    return new_w, new_h, x0, y0


# ---------- API ----------

def load_video_file(video_path: Path) -> VideoClip:
    """Decode to RGB frames with true timestamps (VFR-aware)."""
    container = av.open(str(video_path))
    stream = container.streams.video[0]
    tb: Fraction = stream.time_base

    frames, times = [], []
    for frame in container.decode(video=0):          # presentation order
        if frame.pts is None:
            continue
        t = float(frame.pts * tb)                    # seconds
        img = frame.to_ndarray(format="rgb24")       # HxWx3 uint8
        frames.append(img)
        times.append(t)

    frames = np.asarray(frames, dtype=np.uint8)
    times = _normalize_times(np.asarray(times, dtype=float))

    if frames.size == 0:
        return VideoClip(frames=np.empty((0, 0, 0, 3), np.uint8),
                         times=np.array([], dtype=float),
                         size=(0, 0),
                         note="empty")

    h, w = frames.shape[1], frames.shape[2]
    return VideoClip(frames=frames, times=times, size=(w, h), note="loaded")


def resize_video(clip: VideoClip, target_w: int, target_h: int) -> VideoClip:
    """
    Uniform scale-to-fill + center crop to (target_w, target_h).
    Preserves timestamps exactly.
    """
    if clip.nframes == 0:
        return VideoClip(frames=clip.frames, times=clip.times, size=(target_w, target_h),
                         note="resized-empty")

    src_w, src_h = clip.size
    new_w, new_h, x0, y0 = _cover_size_and_crop(src_w, src_h, target_w, target_h)

    # Scale each frame, then crop center
    out = np.empty((clip.nframes, target_h, target_w, 3), dtype=np.uint8)
    for i, img in enumerate(clip.frames):
        # Create an AV frame from ndarray to use its scaler
        f = av.VideoFrame.from_ndarray(img, format="rgb24")
        f_scaled = f.reformat(width=new_w, height=new_h)   # uniform scaling
        arr = f_scaled.to_ndarray(format="rgb24")
        out[i] = arr[y0:y0+target_h, x0:x0+target_w]

    return VideoClip(frames=out, times=clip.times.copy(), size=(target_w, target_h),
                     note=f"resized_to_{target_w}x{target_h}")


def cfr_video(clip: VideoClip, target_fps: float = 30.0) -> VideoClip:
    """
    Resample frames to CONSTANT frame rate (CFR) without time warping.
    Uses nearest-timestamp selection (drop/duplicate) so wall-clock duration is preserved.
    """
    if clip.nframes == 0:
        return VideoClip(frames=clip.frames, times=clip.times, size=clip.size,
                         note=f"cfr_{target_fps}_empty")

    times = _normalize_times(clip.times)
    dt = 1.0 / float(target_fps)
    t_end = times[-1]
    # Include last step within epsilon so duration matches expectation
    t_uniform = np.arange(0.0, t_end + 0.5 * dt, dt, dtype=float)

    # Map each uniform time to nearest source timestamp
    idx_right = np.searchsorted(times, t_uniform, side="left")
    idx_right[idx_right == len(times)] = len(times) - 1
    idx_left = np.clip(idx_right - 1, 0, len(times) - 1)

    choose_left = (idx_right > 0) & (np.abs(times[idx_left] - t_uniform) <= np.abs(times[idx_right] - t_uniform))
    src_idx = idx_right
    src_idx[choose_left] = idx_left[choose_left]

    frames_cfr = clip.frames[src_idx]
    return VideoClip(frames=frames_cfr, times=t_uniform, size=clip.size,
                     note=f"cfr_{target_fps}Hz")

def save_video_file(clip: VideoClip, out_path: Path, fps: float):
    """
    Save a VideoClip to an MP4 file at the given constant frame rate.
    Frames must already be in RGB24 and all the same size.
    """
    if clip.nframes == 0:
        raise ValueError("Cannot save empty VideoClip.")

    h, w = clip.frames.shape[1:3]

    container = av.open(str(out_path), mode='w')
    stream = container.add_stream('libx264', rate=fps)  # h264 video
    stream.width = w
    stream.height = h
    stream.pix_fmt = 'yuv420p'  # widely compatible
    stream.time_base = Fraction(1, int(fps))

    for img in clip.frames:
        frame = av.VideoFrame.from_ndarray(img, format='rgb24')
        for packet in stream.encode(frame):
            container.mux(packet)

    # flush encoder
    for packet in stream.encode():
        container.mux(packet)

    container.close()
    print(f"Saved {clip.nframes} frames to {out_path} at {fps} fps.")
