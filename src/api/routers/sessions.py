from fastapi import APIRouter, Depends, Request, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, List
from pathlib import Path
import asyncio
import sqlite3

from src.adapters.sqlite import get_sqlite_client

from src.services.sessions import SessionServices
from src.services.database import DatabaseServices
from src.api.schemas import SessionRequest
from src.api.events import hub, sse_format
from src.models.session_view import SessionView
from src.models import Session

from src.config import get_api_config

cfg = get_api_config()

sessions_router = APIRouter(
    prefix="/sessions",
    tags=["sessions"]
)

@sessions_router.get("/")
def list_all_sessions(
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> List[SessionView]:
    db = DatabaseServices(sqlite_client)
    sessions = db.get_session_views()
    return sessions

@sessions_router.post("/")
def create_session(
    req: SessionRequest,
    background: BackgroundTasks,
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> SessionView:
    db = DatabaseServices(sqlite_client)
    service = SessionServices(db)

    # Create the session row
    session: Session = service.create_session(
        name=req.name,
        video_path=Path(req.original_filepath)
    )
    def worker():

        asyncio.run(hub.publish(session.id, {"type":"status","state":"running","progress":0}))
        try:
            for i in range(5):
                print(i)
            service.process_session(session.id)
            asyncio.run(hub.publish(session.id, {"type":"status","state":"succeeded","progress":100}))
        except Exception as e:
            asyncio.run(hub.publish(session.id, {"type":"status","state":"failed","error":str(e)}))

    # background.add_task(worker)
    service.process_session(session.id)
    return db.get_session_view(session.id)

@sessions_router.delete("/{session_id}")
def delete_session_by_id(
    session_id:str,
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> Dict:
    db = DatabaseServices(sqlite_client)
    service = SessionServices(db)
    # Then use service to set status of session to deleting, before attempting to remove files
    # then confirm files are removed, then delete row and cascade to linked rows on sub tables
    return {}

@sessions_router.get("/{session_id}")
def get_session_by_id(
    session_id: str,
    sqlite_client: sqlite3.Connection = Depends(get_sqlite_client)
) -> SessionView:
    db = DatabaseServices(sqlite_client)
    return db.get_session_view(session_id)


@sessions_router.get("/{session_id}/events")
async def get_session_events_by_id(session_id: str, request: Request):
    q = hub.subscribe(session_id)

    async def event_stream():
        try:
            # send last known event if we have one
            last = hub.last(session_id)
            if last:
                yield sse_format({"type":"snapshot", **last})
            else:
                yield sse_format({"type":"hello", "session_id": session_id})

            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=20)
                    yield sse_format(item)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                if await request.is_disconnected():
                    break
        finally:
            hub.unsubscribe(session_id, q)

    return StreamingResponse(event_stream(), media_type="text/event-stream")



