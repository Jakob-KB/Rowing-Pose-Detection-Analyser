from fastapi import APIRouter, Depends, status
import os
from pathlib import Path
from pydantic import BaseModel
import sqlite3
from src.adapters.sqlite import get_sqlite_client

from src.services.sessions import SessionServices
from src.services.sqlite import MyDB

from src.config import get_api_config

cfg = get_api_config()

sessions_router = APIRouter(
    prefix="/sessions",
    tags=["sessions"]
)

class VideoIn(BaseModel):
    filepath: str

@sessions_router.get("")
def list_videos(db: sqlite3.Connection = Depends(get_sqlite_client)):
    rows = db.execute("SELECT id, name FROM videos ORDER BY id").fetchall()
    return [dict(r) for r in rows]

@sessions_router.post("", status_code=status.HTTP_201_CREATED)
def process_video(payload: VideoIn, sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)):
    print(f"starting process on {payload.filepath}")
    db = MyDB(sqlite_client)
    service = SessionServices(db=db)
    result = service.process_session(Path(payload.filepath))
    return {"id": result.id}


def path_to_media_url(abs_path: str) -> str:
    rel = os.path.relpath(abs_path, start=str(cfg.STORAGE_DIR))
    return "" + rel.replace(os.sep, "/")

@sessions_router.get("/{session_id}")
def get_video(session_id: str, sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)):
    db = MyDB(sqlite_client)
    result = db.get_session_from_id(session_id)
    # Add URL for the browser
    p = result.get("processed_video_filepath")
    if p:
        result["processed_video_url"] = path_to_media_url(p)
    return result