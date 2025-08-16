# /src/integrations/mediapipe.py

from pathlib import Path
from typing import Dict, List
import numpy as np
import av
import mediapipe as mp

LandmarkData = Dict[str, np.ndarray]

def _iter_rgb_frames_with_time(video_file: Path):
    """
    Yield (rgb_uint8, t_seconds, (w,h)) in presentation order, i.e. PTS-aware.
    """
    container = av.open(str(video_file))
    stream = container.streams.video[0]
    tb = float(stream.time_base)  # seconds per tick
    for frame in container.decode(video=0):
        if frame.pts is None:
            continue
        t_seconds = frame.pts * tb
        rgb = frame.to_ndarray(format="rgb24")
        h, w = rgb.shape[:2]
        yield rgb, float(t_seconds), (w, h)

def process_landmarks_pts(video_file: Path) -> LandmarkData:
    order = ("ear","shoulder","elbow","wrist","hand","hip","knee","ankle")
    idx_map = {"ear":8, "shoulder":12, "elbow":14, "wrist":16, "hand":20, "hip":24, "knee":26, "ankle":28}

    pose = mp.solutions.pose.Pose()

    frame_idx: List[int] = []
    t_secs: List[float] = []
    cols: Dict[str, List[float]] = {}
    confs: Dict[str, List[float]] = {}

    for n in order:
        cols[f"{n}_x"] = []
        cols[f"{n}_y"] = []

    first_t = None
    W = H = None
    i = 0

    with pose as p:
        for rgb, t, (w, h) in _iter_rgb_frames_with_time(video_file):
            if first_t is None:
                first_t = t
            W, H = w, h
            t0 = t - first_t

            res = p.process(rgb)

            frame_idx.append(i + 1)
            t_secs.append(t0)

            # default fill = NaN
            for n in order:
                cols[f"{n}_x"].append(np.nan)
                cols[f"{n}_y"].append(np.nan)

            if res.pose_landmarks:
                lms = res.pose_landmarks.landmark
                for n in order:
                    lm = lms[idx_map[n]]
                    x = float(lm.x * w)
                    y = float(lm.y * h)
                    cols[f"{n}_x"][-1] = x
                    cols[f"{n}_y"][-1] = y
            i += 1

    out: LandmarkData = {
        "frame_index": np.asarray(frame_idx, dtype=np.int32),
        "t_seconds":   np.asarray(t_secs, dtype=np.float64),
        **{k: np.asarray(v, dtype=np.float32) for k, v in cols.items()},
        "meta": {
            "video_path": str(video_file),
            "width_px": W,
            "height_px": H,
            "landmarks": list(order),
            "pts_reference": "t_seconds starts at 0 (first decoded frame PTS as origin)"
        },
    }
    return out

def to_pandas(data: LandmarkData):
    import pandas as pd
    cols = {k: v for k, v in data.items() if k != "meta"}
    df = pd.DataFrame(cols)
    return df, data["meta"]

def process_landmarks_pts_df(video_file: Path):
    data = process_landmarks_pts(
        video_file=video_file
    )
    return to_pandas(data)
