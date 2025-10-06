import cv2
import pandas as pd
import numpy as np
from collections import defaultdict
from typing import Dict, Tuple, Optional

# ---------------------------
# CONFIG: define the skeleton
# ---------------------------
# Keypoints expected in the CSV
EXPECTED_KPS = [
    "ear", "shoulder", "elbow", "wrist", "hand",
    "hip", "knee", "ankle"
]

# Edges to draw for a side-on rower (facing right)
SKELETON_EDGES = [
    ("ear", "shoulder"),
    ("shoulder", "elbow"),
    ("elbow", "wrist"),
    ("wrist", "hand"),
    ("shoulder", "hip"),
    ("hip", "knee"),
    ("knee", "ankle"),
]

# Colors (BGR)
COLORS = {
    "kp": (60, 220, 255),        # keypoints: light orange
    "edge": (36, 170, 79),       # edges: greenish
    "text": (255, 255, 255),     # text: white
    "shadow": (0, 0, 0),         # text shadow
}

def _draw_text(img, text, org, color=COLORS["text"], scale=0.6, thickness=1):
    x, y = org
    cv2.putText(img, text, (x+1, y+1), cv2.FONT_HERSHEY_SIMPLEX, scale, COLORS["shadow"], thickness+2, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

def _safe_pt(frame_kps: Dict[str, Tuple[float, float]], name: str) -> Optional[Tuple[int, int]]:
    pt = frame_kps.get(name)
    if pt is None:
        return None
    x, y = pt
    if x is None or y is None:
        return None
    if np.isnan(x) or np.isnan(y):
        return None
    return (int(round(x)), int(round(y)))

def _auto_scale_needed(all_xmax, all_ymax) -> bool:
    # If coordinates look normalized (<= 2), assume [0,1] or [0,1.xxx] and scale to frame size.
    return (all_xmax <= 2.0 and all_ymax <= 2.0)

def annotate_rower_skeleton(
        csv_path: str,
        video_in_path: str,
        video_out_path: str,
        *,
        use_time_sync: bool = False,
        fps_override: Optional[float] = None,
        dot_radius: int = 5,
        edge_thickness: int = 3,
        show_labels: bool = False,
):
    """
    Overlay a side-view rowing skeleton onto a video based on CSV keypoints.

    CSV columns required:
      frame_index, pts_ms, timecode, keypoint, x, y

    Parameters
    ----------
    csv_path : str
        Path to keypoint CSV.
    video_in_path : str
        Path to input video.
    video_out_path : str
        Path to output annotated video.
    use_time_sync : bool
        If True, synchronize by pts_ms. Otherwise, by frame_index.
    fps_override : float or None
        If set, forces output FPS (and used for time sync math).
    dot_radius : int
        Circle radius for keypoints.
    edge_thickness : int
        Line thickness for skeleton edges.
    show_labels : bool
        Draw keypoint names next to dots.
    """
    # --- Load CSV ---
    df = pd.read_csv(csv_path)
    # Basic sanity checks
    required_cols = {"frame_index", "pts_ms", "timecode", "keypoint", "x", "y"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    # Keep only expected keypoints (optional)
    df = df[df["keypoint"].isin(EXPECTED_KPS)].copy()

    # Precompute maxima for auto-scale detection
    all_xmax = df["x"].max()
    all_ymax = df["y"].max()

    # Group by frame (either via frame_index or via pts_ms)
    if use_time_sync:
        # round pts_ms to int to be safe
        df["pts_ms"] = df["pts_ms"].astype(int)
        grp_key = "pts_ms"
    else:
        df["frame_index"] = df["frame_index"].astype(int)
        grp_key = "frame_index"

    frames_to_kps: Dict[int, Dict[str, Tuple[float, float]]] = defaultdict(dict)
    for _, row in df.iterrows():
        key = int(row[grp_key])
        kp = row["keypoint"]
        x = float(row["x"])
        y = float(row["y"])
        frames_to_kps[key][kp] = (x, y)

    # --- Open video ---
    cap = cv2.VideoCapture(video_in_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_in_path}")

    in_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    fps = float(fps_override) if fps_override else float(in_fps)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Auto-scale if CSV looks normalized
    need_scale = _auto_scale_needed(all_xmax, all_ymax)
    sx, sy = (width, height) if need_scale else (1.0, 1.0)

    # Prepare writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_out_path, fourcc, fps, (width, height))
    if not out.isOpened():
        cap.release()
        raise IOError(f"Cannot open VideoWriter for: {video_out_path}")

    # Helper: fetch keypoints for a given frame/time
    def get_frame_kps(frame_idx: int, t_ms: int) -> Dict[str, Tuple[float, float]]:
        if use_time_sync:
            # choose nearest pts_ms bucket if exact not present
            if t_ms in frames_to_kps:
                return frames_to_kps[t_ms]
            # find nearest by absolute difference
            if not frames_to_kps:
                return {}
            nearest_key = min(frames_to_kps.keys(), key=lambda k: abs(k - t_ms))
            return frames_to_kps[nearest_key]
        else:
            return frames_to_kps.get(frame_idx, {})

    # Main loop
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Compute current pts in ms for time sync
        # Note: CAP_PROP_POS_MSEC is unreliable while reading; compute from index and FPS
        t_ms = int(round((frame_idx / fps) * 1000.0))

        raw_kps = get_frame_kps(frame_idx + 1, t_ms)  # CSV sample uses 1-based frame_index
        # Scale if necessary
        frame_kps = {}
        for name, (x, y) in raw_kps.items():
            frame_kps[name] = (x * sx, y * sy)

        # Draw skeleton edges
        for a, b in SKELETON_EDGES:
            pa = _safe_pt(frame_kps, a)
            pb = _safe_pt(frame_kps, b)
            if pa is not None and pb is not None:
                cv2.line(frame, pa, pb, COLORS["edge"], edge_thickness, cv2.LINE_AA)

        # Draw keypoints
        for name in EXPECTED_KPS:
            pt = _safe_pt(frame_kps, name)
            if pt is not None:
                cv2.circle(frame, pt, dot_radius, COLORS["kp"], -1, cv2.LINE_AA)
                if show_labels:
                    _draw_text(frame, name, (pt[0] + 6, pt[1] - 6), color=COLORS["text"], scale=0.45, thickness=1)

        # HUD: frame/time
        _draw_text(frame, f"Frame: {frame_idx+1}/{total_frames}", (12, 26))
        if use_time_sync:
            _draw_text(frame, f"t={t_ms/1000.0:.3f}s", (12, 48))

        out.write(frame)
        frame_idx += 1

    cap.release()
    out.release()
    print(f"Annotated video saved to: {video_out_path}")


if __name__ == "__main__":
    annotate_rower_skeleton(
        csv_path="pose.csv",
        video_in_path="test_1.mp4",
        video_out_path="out.mp4"
    )
