# src/integrations/mediapipe.py
from pathlib import Path
from typing import Iterator, List, Tuple
import numpy as np
import av
import mediapipe as mp

from src.models.session_b import ProcessedVideo
from pydantic import BaseModel

# Minimal transient types for DB insert (no need to reuse API DTO)
class _Frame(BaseModel):
    session_id: str
    frame_index: int
    pts_ms: int
    timecode: str

class _Landmark(BaseModel):
    session_id: str
    frame_index: int
    keypoint: str
    x: float
    y: float

class _Evaluation(BaseModel):
    session_id: str
    frames: List[_Frame]
    landmarks: List[_Landmark]
    status: str

def _iter_rgb_frames_with_time(video_file: Path) -> Iterator[Tuple[np.ndarray, float, Tuple[int, int]]]:
    with av.open(str(video_file)) as container:
        stream = container.streams.video[0]
        tb = float(stream.time_base)
        for frame in container.decode(video=0):
            if frame.pts is None:
                continue
            t_seconds = frame.pts * tb
            rgb = frame.to_ndarray(format="rgb24")
            h, w = rgb.shape[:2]
            yield rgb, float(t_seconds), (w, h)

def _format_timecode(t_sec: float) -> str:
    ms_total = int(round(t_sec * 1000.0))
    s, ms = divmod(max(ms_total, 0), 1000)
    h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def process_landmarks_pts_models(video: ProcessedVideo) -> _Evaluation:
    order = ("ear","shoulder","elbow","wrist","hand","hip","knee","ankle")
    idx_map = {"ear": 8, "shoulder":12, "elbow":14, "wrist":16, "hand":20, "hip":24, "knee":26, "ankle":28}

    frames: List[_Frame] = []
    landmarks: List[_Landmark] = []

    pose = mp.solutions.pose.Pose()
    first_t = None
    frame_idx = 0

    with pose as p:
        for rgb, t_abs, (w, h) in _iter_rgb_frames_with_time(video.path_local):
            if first_t is None:
                first_t = t_abs
            t0 = float(t_abs - first_t)
            pts_ms = max(int(round(t0 * 1000.0)), 0)
            frame_idx += 1

            frames.append(_Frame(
                session_id=video.session_id,
                frame_index=frame_idx,
                pts_ms=pts_ms,
                timecode=_format_timecode(t0),
            ))

            res = p.process(rgb)
            if res.pose_landmarks:
                lms = res.pose_landmarks.landmark
                for name in order:
                    lm = lms[idx_map[name]]
                    x_px = float(lm.x * w); y_px = float(lm.y * h)
                    if not (np.isnan(x_px) or np.isnan(y_px)):
                        landmarks.append(_Landmark(
                            session_id=video.session_id,
                            frame_index=frame_idx,
                            keypoint=name,
                            x=x_px, y=y_px
                        ))

    return _Evaluation(session_id=video.session_id, frames=frames, landmarks=landmarks, status="done")
