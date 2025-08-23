# src/integrations/mediapipe.py
from pathlib import Path
from typing import Iterator, Tuple
import numpy as np
import av
import mediapipe as mp
from pandas import DataFrame

from src.utils.misc import format_timecode

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

def process_landmarks_pts_models(video_path: Path) -> DataFrame:
    order = ("ear","shoulder","elbow","wrist","hand","hip","knee","ankle")
    idx_map = {"ear": 8, "shoulder":12, "elbow":14, "wrist":16, "hand":20, "hip":24, "knee":26, "ankle":28}

    rows = []

    pose = mp.solutions.pose.Pose()
    first_t = None
    frame_idx = 0

    with pose as p:
        for rgb, t_abs, (w, h) in _iter_rgb_frames_with_time(video_path):
            if first_t is None:
                first_t = t_abs
            t0 = float(t_abs - first_t)
            pts_ms = max(int(round(t0 * 1000.0)), 0)
            frame_idx += 1

            res = p.process(rgb)
            if res.pose_landmarks:
                lms = res.pose_landmarks.landmark
                for name in order:
                    lm = lms[idx_map[name]]
                    x_px = float(lm.x * w)
                    y_px = float(lm.y * h)
                    if not (np.isnan(x_px) or np.isnan(y_px)):
                        rows.append({
                            "frame_index": frame_idx,
                            "pts_ms": pts_ms,
                            "timecode": format_timecode(t0),
                            "keypoint": name,
                            "x": x_px,
                            "y": y_px
                        })

    return DataFrame(rows)

def save_landmarks_to_file(df: DataFrame, output_path):
    cols = ["frame_index", "pts_ms", "timecode", "keypoint", "x", "y"]
    if all(c in df.columns for c in cols):
        df = df[cols]

    df.to_csv(output_path, index=False)
