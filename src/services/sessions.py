# src/services/video.py
from __future__ import annotations
import uuid
from datetime import datetime

from src.config import get_api_config
from src.integrations import load_video_file, resize_video, cfr_video, save_video_file, save_cover_image
from src.services.sqlite import MyDB
from src.integrations.mediapipe import *
from src.models.session import Session


cfg = get_api_config()


class SessionServices:
    def __init__(self, db: MyDB):
        self.arb = True

        self.db = db
        self.target_width = cfg.VIDEO_WIDTH
        self.target_height = cfg.VIDEO_HEIGHT
        self.target_fps = cfg.VIDEO_FPS

        self.storage_dir = cfg.STORAGE_DIR

        # could move this to somewhere else
        (cfg.STORAGE_DIR / "media" / "videos").mkdir(parents=True, exist_ok=True)
        (cfg.STORAGE_DIR / "media" / "images").mkdir(parents=True, exist_ok=True)

    def create_session(self, name: str, video_path) -> Session:
        # Check that the name of the session is unique
        if self.db.session_name_exists(name):
            raise Exception("Session name already exists")

        # Create a unique UUID for the session
        s_id = None
        while s_id is None or self.db.session_id_exists(s_id):
            s_id = str(uuid.uuid4())

        # Check that this unique UUID doesn't already have a file
        processed_video_filepath = self.storage_dir / "media" / "videos" / f"{s_id}.mp4"
        processed_video_fileurl = f"media/videos/{s_id}.mp4"

        if processed_video_filepath.exists():
            raise Exception("Collision with existing file and new session ID")

        cover_image_filepath = self.storage_dir / "media" / "images" / f"{s_id}.png"
        cover_image_fileurl = f"media/images/{s_id}.png"
        if cover_image_filepath.exists():
            raise Exception("Collision with existing file and new session ID")

        # Create a session row
        current_time = datetime.now().timestamp()
        session = Session(
            id=s_id,
            name=name,
            original_video_filepath=video_path,
            processed_video_filepath=processed_video_filepath,
            processed_video_fileurl=processed_video_fileurl,
            cover_image_filepath=cover_image_filepath,
            cover_image_fileurl=cover_image_fileurl,
            status="new",
            created_at=current_time,
            updated_at=current_time
        )
        self.db.insert_session_row(session)
        return session

    def process_session(self, session: Session) -> Session:
        self.update_session_status(session, "processing")

        video_path = session.original_video_filepath

        if not video_path.exists():
            self.update_session_status(session, "error")
            raise FileNotFoundError(video_path)

        try:
            # Find output video path
            clip = load_video_file(video_path=video_path)
            clip_1080 = resize_video(clip, target_w=self.target_width, target_h=self.target_height)
            clip_30 = cfr_video(clip_1080, target_fps=self.target_fps)
            save_cover_image(clip_30, out_path=session.cover_image_filepath)
            save_video_file(clip_30, out_path=session.processed_video_filepath, fps=self.target_fps)

            df, _meta = process_landmarks_pts_df(video_file=session.processed_video_filepath)
            self.db.insert_landmark_data_to_session(session.id, df)

            self.update_session_status(session, "done")
            return session

        except Exception:
            self.update_session_status(session, "error")
            raise

    def delete_session(self, session: Session):
        if self.arb:
            pass

    def update_session_status(self, session: Session, status: str):
        self.db.update_session_status(session.id, status)
        session.status = status

    def validate_sessions(self):
        """
        Go through all sessions, check their status, and confirm their file.
        NOTE: That this may not be meant to go here, since all other methods focus on a single session
        """
        if self.arb:
            pass

        # 1. For all sessions get for List[Dict[Session]]
        sessions = [{}, {}]

        for session in sessions:
            status = session["status"]
            if status == "new":
                pass
            elif status == "processing":
                pass
            elif status == "error":
                # Check if session has a file, if so, delete it
                pass
            elif status == "done":
                # Check if session has a file, if not, raise error
                pass