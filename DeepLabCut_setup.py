import deeplabcut
from pathlib import Path

project_name = "RowingPoseModel"
author_name = "Jakob"
video_path = Path("data/videos/athlete_video_1.mp4").resolve()  # Ensure absolute path
videos = [str(video_path)]  # Convert to string for DeepLabCut

print(f"Using video path: {videos[0]}")  # Debugging step

# Create new DeepLabCut project
deeplabcut.create_new_project(project_name, author_name, videos, videotype=".mp4", multianimal=False)
