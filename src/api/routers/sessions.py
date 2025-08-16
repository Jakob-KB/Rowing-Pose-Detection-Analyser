from fastapi import APIRouter, Depends, status
from typing import Dict, List
from pathlib import Path
import sqlite3
from src.adapters.sqlite import get_sqlite_client

from src.services.sessions import SessionServices
from src.services.sqlite import MyDB
from src.api.schemas import SessionRequest
from src.models.session import Session

from src.config import get_api_config

cfg = get_api_config()

sessions_router = APIRouter(
    prefix="/sessions",
    tags=["sessions"]
)

@sessions_router.get("")
def get_sessions(
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> List[Session]:
    db = MyDB(sqlite_client)
    sessions = db.get_all_sessions()
    return sessions

@sessions_router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    req: SessionRequest,
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> Session:

    db = MyDB(sqlite_client)
    service = SessionServices(db)
    res = service.create_session(
        name=req.name,
        video_path=Path(req.original_filepath)
    )
    service.process_session(res)
    return res

@sessions_router.get("/{session_id}")
def get_session(
    session_id: str,
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> Dict:
    db = MyDB(sqlite_client)
    result = db.get_session_from_id(session_id)
    return result

@sessions_router.delete("/{session_id}")
def delete_session(
    session_id:str,
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> Dict:
    db = MyDB(sqlite_client)
    service = SessionServices(db)
    # Then use service to set status of session to deleting, before attempting to remove files
    # then confirm files are removed, then delete row and cascade to linked rows on sub tables
    return {}
