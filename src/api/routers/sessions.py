from fastapi import APIRouter, Depends
from typing import Dict, List
from pathlib import Path
import sqlite3
from src.adapters.sqlite import get_sqlite_client

from src.services.sessions import SessionServices
from src.services.database import DatabaseServices
from src.api.schemas import SessionRequest, SessionResponse
from src.models import Session

from src.config import get_api_config

cfg = get_api_config()

sessions_router = APIRouter(
    prefix="/sessions",
    tags=["sessions"]
)

@sessions_router.get("")
def get_sessions(
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> List[SessionResponse]:
    db = DatabaseServices(sqlite_client)
    sessions = db.get_sessions()
    return sessions

@sessions_router.post("")
def create_session(
    req: SessionRequest,
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> SessionResponse:
    db = DatabaseServices(sqlite_client)
    service = SessionServices(db)

    # Create session object
    session: Session = service.create_session(
        name=req.name,
        video_path=Path(req.original_filepath)
    )

    # Process and Save Standardised Video
    processed_video = service.create_processed_video(session.id)

    # Process and save cover image
    cover_image = service.create_cover_image(session.id)

    service.process_session(session_id)
    return session


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
) -> None:
    db = DatabaseServices(sqlite_client)
    pass



