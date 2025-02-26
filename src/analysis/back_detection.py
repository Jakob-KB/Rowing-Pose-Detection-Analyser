import cv2
import json
import numpy as np
import math
import logging
from tqdm import tqdm
import pandas as pd

from sklearn.linear_model import RANSACRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration (replace with your paths and parameters)
VIDEO_PATH = "../../data/videos/athlete_3.mp4"
POSE_DATA_PATH = "analyses/athlete_3_report/athlete_3_pose_data.json"
SHOULDER_NAME, HIP_NAME = "ShoulderR", "HipR"
PERP_DIST = 150
ENABLE_MASKING = True

# Temporal smoothing window (number of frames before and after)
TEMPORAL_WINDOW = 2

# Extension parameters (in pixels along the vertical (rotated) direction)
EXTEND_DOWN_PIXELS = 20  # extend downward (at the bottom)
EXTEND_UP_PIXELS = 10    # extend upward (at the top)

# Load video_processing data
with open(POSE_DATA_PATH, "r") as file:
    pose_data = json.load(file)

# Open video capture and get properties
cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise ValueError("Error: Could not open video. Check file path.")
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
ret, first_frame = cap.read()
if not ret:
    raise ValueError("Error: Could not read first frame.")
height, width = first_frame.shape[:2]

# Define VideoWriter for final output
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
output_filename = "output_with_blue_line.mp4"
final_out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))

# ------------------------------
# Helper Functions
# ------------------------------
def get_landmark_position(frame_index, landmark_name):
    for frame in pose_data:
        if frame["frame"] == frame_index and landmark_name in frame["landmarks"]:
            landmark = frame["landmarks"][landmark_name]
            return landmark["x"], landmark["y"]
    return None

def to_pixel(x, y, width, height):
    return int(x * width), int(y * height)

def get_perpendicular_points(x1, y1, x2, y2, offset):
    dx, dy = x2 - x1, y2 - y1
    mag = math.hypot(dx, dy)
    if mag == 0:
        return (x1, y1), (x2, y2)
    dx, dy = dx / mag, dy / mag
    dx, dy = -dy, dx  # Rotate 90° leftward
    far_shoulder = (int(x1 + dx * offset), int(y1 + dy * offset))
    far_hip = (int(x2 + dx * offset), int(y2 + dy * offset))
    return far_shoulder, far_hip

def compute_motion_and_edges(frame1, frame2):
    frame_diff = cv2.absdiff(frame1, frame2)
    blurred = cv2.GaussianBlur(frame_diff, (5, 5), 0)
    edges = cv2.Canny(blurred, threshold1=50, threshold2=40)
    return frame_diff, edges

def apply_mask(frame, mask_shape, landmarks):
    if not landmarks:
        return frame
    shoulder_px, hip_px, far_hip, far_shoulder = landmarks
    mask = np.zeros(mask_shape, dtype=np.uint8)
    polygon = np.array([shoulder_px, hip_px, far_hip, far_shoulder], np.int32)
    cv2.fillPoly(mask, [polygon], (255, 255, 255))
    return cv2.bitwise_and(frame, mask)

def find_back_curve(edges, y_bottom, y_top, x_min, x_max):
    """
    Extract the left‑most edge pixel for each row between y_bottom (larger y)
    and y_top (smaller y) within the horizontal bounds [x_min, x_max].
    """
    curve_points = []
    kernel = np.ones((3, 3), np.uint8)
    edges_dilated = cv2.dilate(edges, kernel, iterations=1)
    for y in range(y_bottom, y_top - 1, -1):  # iterate upward (y decreases)
        row_slice = edges_dilated[y, x_min:x_max]
        x_indices = np.where(row_slice != 0)[0]
        if len(x_indices) > 0:
            x_val = np.min(x_indices) + x_min
            curve_points.append((x_val, y))
    return curve_points

def median_filter_curve(curve_points, kernel_size=5):
    """
    Apply a median filter to the x coordinates of curve_points.
    """
    if not curve_points:
        return curve_points
    xs = [pt[0] for pt in curve_points]
    ys = [pt[1] for pt in curve_points]
    filtered_xs = []
    half = kernel_size // 2
    for i in range(len(xs)):
        window = xs[max(0, i - half):min(len(xs), i + half + 1)]
        filtered_xs.append(int(np.median(window)))
    return list(zip(filtered_xs, ys))

# ------------------------------
# Step 1: Process each frame to compute and store fitted curves.
# ------------------------------
# Dictionary to store curve for each frame (if successful)
# Each entry: frame_index -> {'y_range': np.array, 'x_curve': np.array}
curves = {}

# Reset video capture to beginning
cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
ret, prev_frame = cap.read()
if not ret:
    raise ValueError("Error: Could not read first frame.")

for frame_index in tqdm(range(1, total_frames), desc="Processing Frames"):
    ret, curr_frame = cap.read()
    if not ret:
        break
    try:
        # Convert frames to grayscale for processing.
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        # Compute motion-based edges.
        _, edges = compute_motion_and_edges(prev_gray, curr_gray)
        # Retrieve video_processing landmarks.
        shoulder = get_landmark_position(frame_index, SHOULDER_NAME)
        hip = get_landmark_position(frame_index, HIP_NAME)
        landmarks = None
        if shoulder and hip:
            shoulder_px = to_pixel(*shoulder, width, height)
            hip_px = to_pixel(*hip, width, height)
            far_shoulder, far_hip = get_perpendicular_points(*shoulder_px, *hip_px, PERP_DIST)
            # Extend the bounding box.
            top_center = ((shoulder_px[0] + far_shoulder[0]) / 2.0, (shoulder_px[1] + far_shoulder[1]) / 2.0)
            bottom_center = ((hip_px[0] + far_hip[0]) / 2.0, (hip_px[1] + far_hip[1]) / 2.0)
            vdx = bottom_center[0] - top_center[0]
            vdy = bottom_center[1] - top_center[1]
            vmag = math.hypot(vdx, vdy)
            if vmag != 0:
                vdx, vdy = vdx / vmag, vdy / vmag
            else:
                vdx, vdy = 0, 1
            tx_down, ty_down = vdx * EXTEND_DOWN_PIXELS, vdy * EXTEND_DOWN_PIXELS
            tx_up, ty_up = vdx * EXTEND_UP_PIXELS, vdy * EXTEND_UP_PIXELS
            new_hip_px = (hip_px[0] + int(tx_down), hip_px[1] + int(ty_down))
            new_far_hip = (far_hip[0] + int(tx_down), far_hip[1] + int(ty_down))
            new_shoulder_px = (shoulder_px[0] - int(tx_up), shoulder_px[1] - int(ty_up))
            new_far_shoulder = (far_shoulder[0] - int(tx_up), far_shoulder[1] - int(ty_up))
            extended_landmarks = (new_shoulder_px, new_hip_px, new_far_hip, new_far_shoulder)
            landmarks = extended_landmarks

        if ENABLE_MASKING and landmarks:
            edges = apply_mask(edges, curr_gray.shape, landmarks)

        if landmarks:
            pts = np.array([landmarks[0], landmarks[1], landmarks[2], landmarks[3]], np.int32)
            top_bound = min(landmarks[0][1], landmarks[3][1])
            bottom_bound = max(landmarks[1][1], landmarks[2][1])
        else:
            top_bound, bottom_bound = 0, curr_gray.shape[0] - 1
            pts = np.array([[0,0],[0,0],[0,0],[0,0]])

        raw_curve_points = find_back_curve(edges, bottom_bound, top_bound, np.min(pts[:, 0]), np.max(pts[:, 0]))
        if raw_curve_points:
            new_y_top = min(pt[1] for pt in raw_curve_points)
            new_y_bottom = max(pt[1] for pt in raw_curve_points)
        else:
            new_y_top, new_y_bottom = top_bound, bottom_bound

        filtered_curve_points = median_filter_curve(raw_curve_points, kernel_size=5)
        if len(filtered_curve_points) > 5:
            x_coords = np.array([pt[0] for pt in filtered_curve_points])
            y_coords = np.array([pt[1] for pt in filtered_curve_points])
            X = y_coords.reshape(-1, 1)
            y_target = x_coords
            model = make_pipeline(PolynomialFeatures(degree=2), RANSACRegressor(random_state=0))
            model.fit(X, y_target)
            y_range = np.arange(new_y_top, new_y_bottom + 1).reshape(-1, 1)
            fitted_x = model.predict(y_range)
            curves[frame_index] = {
                "y_range": y_range.flatten(),
                "x_curve": fitted_x.astype(int)
            }
        else:
            curves[frame_index] = None
    except Exception as e:
        logger.error(f"Frame {frame_index}: error during processing: {e}")
        curves[frame_index] = None

    prev_frame = curr_frame.copy()

# ------------------------------
# Step 2: Post-process curves across frames
# ------------------------------
all_y_ranges = [curve["y_range"] for curve in curves.values() if curve is not None]
if all_y_ranges:
    global_y_min = int(min(arr[0] for arr in all_y_ranges))
    global_y_max = int(max(arr[-1] for arr in all_y_ranges))
else:
    global_y_min, global_y_max = 0, height - 1
global_y = np.arange(global_y_min, global_y_max + 1)

curves_interp = {}
for idx, curve in curves.items():
    if curve is not None:
        interp_x = np.interp(global_y, curve["y_range"], curve["x_curve"])
        curves_interp[idx] = interp_x
    else:
        curves_interp[idx] = None

df_data = {}
for idx in range(1, total_frames):
    if curves_interp.get(idx) is not None:
        df_data[idx] = curves_interp[idx]
    else:
        df_data[idx] = np.nan * np.ones_like(global_y, dtype=float)
df_curves = pd.DataFrame(df_data, index=global_y).T

df_smoothed = df_curves.copy()
for i in df_smoothed.index:
    window = df_smoothed.loc[max(i - TEMPORAL_WINDOW, df_smoothed.index.min()):
                              min(i + TEMPORAL_WINDOW, df_smoothed.index.max())]
    df_smoothed.loc[i] = window.mean(axis=0)

# ------------------------------
# Step 3: Re-read video and draw the final smoothed curve on each frame.
# (Shift curves back by minus 1: draw the curve computed for frame i+1 on frame i)
# ------------------------------
cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
ret, _ = cap.read()
frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1
    output_frame = frame.copy()
    # Instead of drawing the curve computed for frame i-1, we now draw the curve computed for frame i+1.
    if (frame_idx + 1) in df_smoothed.index:
        x_vals = df_smoothed.loc[frame_idx + 1].values
        curve_points = [(int(x), int(y)) for x, y in zip(x_vals, global_y)]
        # Draw the curve with the specified parameters.
        cv2.polylines(output_frame, [np.array(curve_points, np.int32)],
                      isClosed=False, color=(0, 0, 255), thickness=10)
    final_out.write(output_frame)

cap.release()
final_out.release()
cv2.destroyAllWindows()

print(f"Output video saved to: {output_filename}")
