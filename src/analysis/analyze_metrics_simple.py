# src/analysis/analyze_metrics_simple.py
import cv2
import json
import math
from pathlib import Path
import pandas as pd

from src import SESSIONS_DIR


# ---------------------------
# Helper Functions
# ---------------------------
def load_pose_dataframe(json_path):
    """
    Loads the JSON video_processing data into a pandas DataFrame, sorts by frame, and
    extracts the relevant landmark x-positions.
    """
    try:
        df = pd.read_json(json_path)
        df.sort_values("frame", inplace=True)
        # Extract x-positions for HandR, AnkleR, and HipR
        df["hand_x"] = df["landmarks"].apply(lambda lm: lm.get("HandR", {}).get("x") if isinstance(lm, dict) else None)
        df["ankle_x"] = df["landmarks"].apply(
            lambda lm: lm.get("AnkleR", {}).get("x") if isinstance(lm, dict) else None)
        df["hip_x"] = df["landmarks"].apply(lambda lm: lm.get("HipR", {}).get("x") if isinstance(lm, dict) else None)
        return df
    except Exception as e:
        print(f"Error loading video_processing data from {json_path}: {e}")
        return pd.DataFrame()


def calculate_hand_speed_from_df(df, index, window=2):
    """
    Computes the average hand speed for frame 'index' using a symmetric window
    from the DataFrame, and determines the net direction.

    Returns:
      (avg_speed, net_direction)
    """
    speeds = []
    directions = []
    total_frames = len(df)
    start = max(1, index - window)
    end = min(total_frames - 1, index + window)

    for j in range(start, end + 1):
        current = df.iloc[j]["hand_x"]
        prev = df.iloc[j - 1]["hand_x"]
        if current is not None and prev is not None:
            delta = current - prev
            speeds.append(abs(delta))
            if delta > 0:
                directions.append("right")
            elif delta < 0:
                directions.append("left")

    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    net_direction = max(set(directions), key=directions.count) if directions else "stationary"
    return avg_speed, net_direction


def compute_slide_position(avg_ankle, min_hip, current_hip):
    """
    Computes the slide position as a percentage.
    Slide Position = 100 * (avg_ankle - current_hip) / (avg_ankle - min_hip)
    Clamped to [0, 100].
    """
    if current_hip is None or avg_ankle is None or (avg_ankle - min_hip) == 0:
        return None
    slide = 100 * (avg_ankle - current_hip) / (avg_ankle - min_hip)
    return max(0, min(100, slide))


# ---------------------------
# Main Routine
# ---------------------------
def main():
    title = "athlete_1"
    base_dir = SESSIONS_DIR / f"{title}_report"
    video_path = base_dir / f"{title}_labeled_video.mp4"
    json_path = base_dir / f"{title}_pose_data.json"

    # Load video_processing data into DataFrame.
    df = load_pose_dataframe(json_path)
    if df.empty:
        return

    total_frames = len(df)

    # Compute overall constants for slide position.
    avg_ankle = df["ankle_x"].mean() if not df["ankle_x"].isnull().all() else None
    min_hip = df["hip_x"].min() if not df["hip_x"].isnull().all() else None

    # Pre-calculate hand speed/direction and slide position for each frame.
    hand_speeds = []
    directions = []
    slide_positions = []
    print("Pre-calculating analysis...")
    for i in range(total_frames):
        avg_speed, net_direction = calculate_hand_speed_from_df(df, i, window=2)
        hand_speeds.append(avg_speed)
        directions.append(net_direction)
        current_hip = df.iloc[i]["hip_x"]
        slide_pos = compute_slide_position(avg_ankle, min_hip, current_hip)
        slide_positions.append(slide_pos)
        print(f"Frame {i}: Speed = {avg_speed:.4f}, Direction = {net_direction}, Slide = {slide_pos}")

    # Add calculated columns to the DataFrame.
    df["hand_speed"] = hand_speeds
    df["direction"] = directions
    df["slide_position"] = slide_positions

    print("Pre-calculation complete. Starting video playback...")

    # Open the video.
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return

    frame_index = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index < total_frames:
            speed = df.iloc[frame_index]["hand_speed"]
            direction = df.iloc[frame_index]["direction"]
            slide = df.iloc[frame_index]["slide_position"]
            text = f"Speed: {speed:.4f} | Dir: {direction} | Slide: {round(slide) if slide is not None else 'N/A'}%"
            cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2, cv2.LINE_AA)

        cv2.imshow("Video Playback", frame)
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break
        frame_index += 1

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
