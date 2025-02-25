import cv2
import json
import numpy as np
import math

# Load video and video_processing data
VIDEO_PATH = "../Rowing-Pose-Detection-Analyser/data/videos/athlete_1.mp4"
POSE_DATA_PATH = "analyses/athlete_1_report/athlete_1_pose_data.json"

FRAME_IDX = 60
SHOULDER_NAME, HIP_NAME = "ShoulderR", "HipR"
PERP_DIST = 150  # Distance for perpendicular points

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise ValueError("Error: Could not open video. Check file path.")

# Load video_processing data from JSON
with open(POSE_DATA_PATH, "r") as file:
    pose_data = json.load(file)


def get_frame(frame_number):
    """Retrieve a specific frame from the video."""
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    if not ret:
        raise ValueError(f"Error: Could not retrieve frame {frame_number}.")
    return frame


def get_landmark_position(frame_number, landmark_name):
    """Retrieve landmark position (x, y) for a given frame and landmark name."""
    for frame in pose_data:
        if frame["frame"] == frame_number:
            if landmark_name in frame["landmarks"]:
                landmark = frame["landmarks"][landmark_name]
                return landmark["x"], landmark["y"]
    return None


def to_pixel(x, y, width, height):
    """Convert normalized coordinates (0 to 1) to pixel coordinates."""
    return int(x * width), int(y * height)


def get_perpendicular_points(x1, y1, x2, y2, offset):
    """Compute perpendicular points at a fixed offset distance extending **leftward**."""
    dx, dy = x2 - x1, y2 - y1
    mag = math.hypot(dx, dy)
    if mag == 0:
        return (x1, y1), (x2, y2)  # Avoid division by zero if points are identical

    dx, dy = dx / mag, dy / mag
    dx, dy = -dy, dx  # Rotate 90 degrees **leftward** instead of rightward

    far_shoulder = (int(x1 + dx * offset), int(y1 + dy * offset))
    far_hip = (int(x2 + dx * offset), int(y2 + dy * offset))

    return far_shoulder, far_hip


# Process frame
frame = get_frame(FRAME_IDX)
height, width, _ = frame.shape

shoulder = get_landmark_position(FRAME_IDX, SHOULDER_NAME)
hip = get_landmark_position(FRAME_IDX, HIP_NAME)

if shoulder and hip:
    shoulder_px, hip_px = to_pixel(*shoulder, width, height), to_pixel(*hip, width, height)
    far_shoulder, far_hip = get_perpendicular_points(*shoulder_px, *hip_px, PERP_DIST)

    # Create a blank mask
    mask = np.zeros_like(frame, dtype=np.uint8)

    # Define bounding box polygon points (ordered correctly)
    polygon = np.array([shoulder_px, hip_px, far_hip, far_shoulder], np.int32)

    # Fill the bounding box area with white on the mask
    cv2.fillPoly(mask, [polygon], (255, 255, 255))

    # Apply mask: Keep only the region inside the bounding box
    frame_masked = cv2.bitwise_and(frame, mask)

    # Display result
    cv2.imshow("Clipped Bounding Box on Pose", frame_masked)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print(f"No valid landmarks detected for frame {FRAME_IDX}.")

cap.release()
