from pathlib import Path
import sqlite3
from typing import Generator

from src.config import get_api_config

cfg = get_api_config()

def ensure_db() -> sqlite3.Connection:
    """
    Open a connection to the on-disk DB. No seed copy. Call init_schema() at startup.
    Use one connection per request (via dependency) to avoid cross-thread issues.
    """
    target = cfg.DB_PATH
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # PRAGMA defaults
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn

def init_schema(conn: sqlite3.Connection) -> None:
    # Create fresh schema
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(schema_sql)

def get_sqlite_client() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency: yield a fresh connection and close it after the request.
    """
    conn = ensure_db()
    try:
        yield conn
    finally:
        conn.close()
