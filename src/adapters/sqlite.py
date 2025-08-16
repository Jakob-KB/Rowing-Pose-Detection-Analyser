import sys
from pathlib import Path
import sqlite3
from typing import Generator

from src.config import get_api_config

cfg = get_api_config()

def resource_path(relative: str) -> Path:
    """
    Get path to bundled resources (read-only). Not used for DB since we don't ship a seed.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).parent / relative

def ensure_db() -> sqlite3.Connection:
    """
    Open a connection to the on-disk DB. No seed copy. Call init_schema() at startup.
    Use one connection per request (via dependency) to avoid cross-thread issues.
    """
    target = cfg.DB_PATH
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # sensible defaults
    conn.execute("PRAGMA journal_mode=WAL;")      # better concurrency/crash safety
    conn.execute("PRAGMA foreign_keys=ON;")       # enforce FK constraints
    conn.execute("PRAGMA busy_timeout = 5000;")   # ms to wait on locks
    return conn

def init_schema(conn: sqlite3.Connection) -> None:
    # Disable FKs to allow dropping in any order
    conn.execute("PRAGMA foreign_keys=OFF;")
    conn.commit()

    # Drop old objects if present
    conn.executescript("""
    DROP TABLE IF EXISTS landmarks_wide;
    DROP TABLE IF EXISTS sessions;
    """)
    conn.commit()

    # Reclaim file space
    conn.execute("VACUUM;")
    conn.commit()

    # Base PRAGMAs
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.commit()

    # Create fresh schema
    conn.executescript("""
    -- Sessions: one row per imported video/session
    CREATE TABLE sessions (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL UNIQUE,
      original_video_filepath TEXT NOT NULL,
      processed_video_filepath TEXT,
      session_status TEXT NOT NULL CHECK (session_status IN ('processing','done','error'))
    );

    -- Wide per-frame landmark storage (one row per frame per session)
    CREATE TABLE landmarks_wide (
      session_id  TEXT NOT NULL,
      frame_index INTEGER NOT NULL,
      t_seconds   REAL  NOT NULL,

      ear_x REAL,      ear_y REAL,
      shoulder_x REAL, shoulder_y REAL,
      elbow_x REAL,    elbow_y REAL,
      wrist_x REAL,    wrist_y REAL,
      hand_x REAL,     hand_y REAL,
      hip_x REAL,      hip_y REAL,
      knee_x REAL,     knee_y REAL,
      ankle_x REAL,    ankle_y REAL,

      PRIMARY KEY (session_id, frame_index),
      FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );

    -- Helpful indexes
    CREATE INDEX idx_landmarks_wide_session_time
      ON landmarks_wide(session_id, t_seconds);

    CREATE INDEX idx_sessions_status
      ON sessions(session_status);

    PRAGMA user_version = 1;
    """)
    conn.commit()

def get_sqlite_client() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency: yield a fresh connection and close it after the request.
    """
    conn = ensure_db()
    try:
        yield conn
    finally:
        conn.close()
