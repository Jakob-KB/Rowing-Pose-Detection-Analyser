# src/main.py

from config import DATA_DIR
from pathlib import Path
from rower_analysis import RowerAnalysis
from pose import detect_landmarks

def main() -> None:
    video_title = "athlete_1"
    input_video_path = DATA_DIR / "videos" / "athlete_1.mp4"

    current_report = RowerAnalysis(video_title, input_video_path, overwrite=True)

    detect_landmarks(current_report)



if __name__ == "__main__":
    main()
