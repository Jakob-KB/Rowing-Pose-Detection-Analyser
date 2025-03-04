# src/models/session_files.py

from pathlib import Path

from pydantic import BaseModel


class SessionFiles(BaseModel):
    session_config: Path
    raw_video: Path
    landmark_data: Path
    analysis_data: Path
    annotated_video: Path

    def expected_files(self) -> list[str]:
        return [
            self.session_config.name,
            self.raw_video.name,
            self.landmark_data.name,
            self.analysis_data.name,
            self.annotated_video.name
        ]
