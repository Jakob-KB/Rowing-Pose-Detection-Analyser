from fastapi import APIRouter, Depends
from typing import Dict, List
from pathlib import Path
import sqlite3
from src.adapters.sqlite import get_sqlite_client

from src.services.sessions import SessionServices
from src.services.database import DatabaseServices
from src.api.schemas import SessionRequest
from src.models.session_view import SessionView
from src.models import Session

from src.config import get_api_config

cfg = get_api_config()

sessions_router = APIRouter(
    prefix="/sessions",
    tags=["sessions"]
)

@sessions_router.get("/")
def get_sessions(
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> List[SessionView]:
    db = DatabaseServices(sqlite_client)
    sessions = db.get_session_views()
    return sessions

@sessions_router.post("/")
def create_session(
    req: SessionRequest,
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> SessionView:
    db = DatabaseServices(sqlite_client)
    service = SessionServices(db)

    # Create session object
    session: Session = service.create_session(
        name=req.name,
        video_path=Path(req.original_filepath)
    )
    service.process_session(session.id)

    return db.get_session_view(session.id)


@sessions_router.delete("/{session_id}")
def delete_session(
    session_id:str,
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> Dict:
    db = DatabaseServices(sqlite_client)
    service = SessionServices(db)
    # Then use service to set status of session to deleting, before attempting to remove files
    # then confirm files are removed, then delete row and cascade to linked rows on sub tables
    return {}

@sessions_router.get("/{session_id}")
def get_session(
    session_id: str,
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> SessionView:
    db = DatabaseServices(sqlite_client)
    return db.get_session_view(session_id)


