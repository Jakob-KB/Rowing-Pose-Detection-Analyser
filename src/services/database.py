# src/services/database.py
from __future__ import annotations
import sqlite3
from time import time
from typing import Iterable, List

from src.models import Session, RawVideo, ProcessedVideo, CoverImage, Evaluation, SessionView


class DatabaseServices:
    def __init__(self, sqlite_client: sqlite3.Connection):
        self.db = sqlite_client
        self.db.row_factory = sqlite3.Row

    @staticmethod
    def _chunked(it: Iterable[tuple], size: int = 1000) -> Iterable[list]:
        buf = []
        for row in it:
            buf.append(row)
            if len(buf) >= size:
                yield buf
                buf = []
        if buf:
            yield buf

    def _touch(self, session_id: str):
        self.db.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (int(time()), session_id))

    # Checks
    def session_name_exists(self, name: str) -> bool:
        cur = self.db.execute("SELECT 1 FROM sessions WHERE name = ? LIMIT 1", (name,))
        return cur.fetchone() is not None

    # Inserts
    def insert_session(self, session: Session) -> None:
        with self.db:
            self.db.execute(
                """
                INSERT INTO sessions (
                    id,
                    name,
                    status,
                    notes,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.name,
                    session.status,
                    session.notes,
                    session.created_at,
                    session.updated_at
                )
            )

    def insert_raw_video(self, raw_video: RawVideo) -> None:
        with self.db:
            self.db.execute(
                """
                INSERT INTO raw_videos (
                    id,
                    session_id,
                    path_local,
                    mime_type,
                    duration_s,
                    frame_count,
                    fps,
                    width,
                    height,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_video.id,
                    raw_video.session_id,
                    raw_video.path_local,
                    raw_video.mime_type,
                    raw_video.duration_s,
                    raw_video.frame_count,
                    raw_video.fps,
                    raw_video.width,
                    raw_video.height,
                    raw_video.created_at
                ),
            )
            self._touch(raw_video.session_id)

    def insert_processed_video(self, processed_video: ProcessedVideo) -> None:
        with self.db:
            self.db.execute(
                """
                INSERT INTO processed_videos (
                    id,
                    session_id,
                    path_local,
                    uri,
                    mime_type,
                    duration_s,
                    frame_count,
                    fps,
                    width,
                    height,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    processed_video.id,
                    processed_video.session_id,
                    processed_video.path_local,
                    processed_video.uri,
                    processed_video.mime_type,
                    processed_video.duration_s,
                    processed_video.frame_count,
                    processed_video.fps,
                    processed_video.width,
                    processed_video.height,
                    processed_video.created_at
                )
            )
            self._touch(processed_video.session_id)

    def insert_cover_image(self, cover_image: CoverImage) -> None:
        with self.db:
            self.db.execute(
                """
                INSERT INTO cover_images (
                    id,
                    session_id,
                    path_local,
                    uri,
                    mime_type,
                    width,
                    height,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cover_image.id,
                    cover_image.session_id,
                    cover_image.path_local,
                    cover_image.uri,
                    cover_image.mime_type,
                    cover_image.width,
                    cover_image.height,
                    cover_image.created_at
                )
            )
            self._touch(cover_image.session_id)

    def insert_evaluation(self, evaluation: Evaluation) -> None:
        with self.db:
            self.db.execute(
                """
                INSERT INTO evaluations (
                    id,
                    session_id,
                    video_id,
                    path_local,
                    uri,
                    avg_spm,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation.id,
                    evaluation.session_id,
                    evaluation.video_id,
                    evaluation.path_local,
                    evaluation.uri,
                    evaluation.avg_spm,
                    evaluation.created_at
                )
            )
            self._touch(evaluation.session_id)

    # Updates
    def update_session_status(self, session_id: str, status: str) -> None:
        with self.db:
            self.db.execute("UPDATE sessions SET status = ? WHERE id = ?", (status, session_id))
            self._touch(session_id)

    # Reads (Objects)
    def get_session(self, session_id: str) -> Session:
        row = self.db.execute(
            "SELECT id, name, status, notes, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Session not found: {session_id}")
        return Session(
            id=row["id"], name=row["name"], status=row["status"], notes=row["notes"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    def get_raw_video(self, session_id: str) -> RawVideo:
        row = self.db.execute(
            """SELECT * FROM raw_videos WHERE session_id = ? LIMIT 1""", (session_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"No raw video for session {session_id}")
        return RawVideo(**row)

    def get_processed_video(self, session_id: str) -> ProcessedVideo:
        row = self.db.execute(
            """SELECT * FROM processed_videos WHERE session_id = ? LIMIT 1""", (session_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"No processed video for session {session_id}")
        return ProcessedVideo(**row)

    def get_cover_image(self, session_id: str) -> CoverImage:
        row = self.db.execute(
            """SELECT * FROM cover_images WHERE session_id = ? LIMIT 1""", (session_id,)
        ).fetchone()
        return CoverImage(**row)

    # Read (Views)
    def get_session_views(self) -> List[SessionView]:
        ...

    def get_session_view(self) -> SessionView:
        ...
