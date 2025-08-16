# src/services/video.py
from __future__ import annotations

from src.config import get_api_config
from src.integrations import load_video_file, resize_video, cfr_video, save_video_file
from src.services.sqlite import *
from src.integrations.mediapipe import *
from src.utils.misc import *


cfg = get_api_config()


@dataclass
class SessionRecord:
    id: str
    name: str
    original_video_filepath: Path
    processed_video_filepath: Optional[Path]
    session_status: str


class SessionServices:
    def __init__(self, db: MyDB):
        self.arb = True

        self.db = db
        self.target_width = cfg.VIDEO_WIDTH
        self.target_height = cfg.VIDEO_HEIGHT
        self.target_fps = cfg.VIDEO_FPS

        (cfg.STORAGE_DIR / "videos").mkdir(parents=True, exist_ok=True)

    # ---------- public API ----------
    def process_session(self, video_path: Path) -> SessionRecord:
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(video_path)

        session_name = get_random_name()
        session_id = str(uuid.uuid4())

        # Check if session name already exists in DB
        if self.db.session_name_exists(session_name):
            raise ValueError(f"Session '{session_name}' already exists")

        # Check if session id already exists in DB
        while self.db.session_id_exists(session_id):
            session_id = str(uuid.uuid4())

        # Create unique filepath for processed video
        processed_video_path = None
        while processed_video_path is None or processed_video_path.exists():
            processed_video_path = cfg.STORAGE_DIR / "videos" / f"{uuid.uuid4()}.mp4"

        rec = SessionRecord(
            id=session_id,
            name=session_name,
            original_video_filepath=video_path,
            processed_video_filepath=processed_video_path,
            session_status="processing",
        )
        self.db.insert_session_row(rec)

        try:
            clip = load_video_file(video_path=video_path)
            clip_1080 = resize_video(clip, target_w=self.target_width, target_h=self.target_height)
            clip_30 = cfr_video(clip_1080, target_fps=self.target_fps)
            save_video_file(clip_30, out_path=processed_video_path, fps=self.target_fps)

            df, _meta = process_landmarks_pts_df(video_file=processed_video_path)
            self.db.insert_landmark_data_to_session(session_id, df)

            self.db.update_session_status(session_name, "done")
            return SessionRecord(
                id=session_id,
                name=session_name,
                original_video_filepath=video_path,
                processed_video_filepath=processed_video_path,
                session_status="done",
            )
        except Exception:
            self.db.update_session_status(session_name, "error")
            raise
