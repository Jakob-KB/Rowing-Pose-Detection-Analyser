# src/models/session_files.py

from pathlib import Path

from pydantic import BaseModel

from src.config import cfg

class SessionFiles(BaseModel):
    session_config: Path
    raw_video: Path
    landmark_data: Path
    analysis_data: Path
    annotated_video: Path

    @classmethod
    def from_session_directory(cls, session_directory: Path) -> "SessionFiles":

        session_config = session_directory / cfg.session.files.session_config
        raw_video = session_directory / cfg.session.files.raw_video
        landmark_data = session_directory / cfg.session.files.landmark_data
        analysis_data = session_directory / cfg.session.files.analysis_data
        annotated_video = session_directory / cfg.session.files.annotated_video

        return cls(
            session_config=session_config,
            raw_video=raw_video,
            landmark_data=landmark_data,
            analysis_data=analysis_data,
            annotated_video=annotated_video,
        )

    def expected_files(self) -> list[str]:
        return [
            self.session_config.name,
            self.raw_video.name,
            self.landmark_data.name,
            self.analysis_data.name,
            self.annotated_video.name
        ]
