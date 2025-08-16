#!/usr/bin/env python3

import sqlite3
from pathlib import Path
from typing import Iterable, Any

from src.config import get_api_config


def connect() -> tuple[sqlite3.Connection, Path]:
    cfg = get_api_config()
    db_path = Path(cfg.DB_PATH)
    if not db_path.exists():
        raise FileNotFoundError(f"DB file not found: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn, db_path


def _q(conn: sqlite3.Connection, sql: str, args: Iterable[Any] = ()):
    return conn.execute(sql, args).fetchall()


def _print_table(rows: list[sqlite3.Row]):
    if not rows:
        print("(no rows)")
        return
    cols = rows[0].keys()
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    header = " | ".join(c.ljust(widths[c]) for c in cols)
    sep = "-+-".join("-" * widths[c] for c in cols)
    print(header)
    print(sep)
    for r in rows:
        print(" | ".join(str(r[c]).ljust(widths[c]) for c in cols))


def print_info(conn: sqlite3.Connection, db_path: Path):
    ver = _q(conn, "PRAGMA user_version")[0][0]
    print(f"DB: {db_path}")
    print(f"user_version: {ver}")
    tables = _q(conn, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    if not tables:
        print("(no tables)")
        return
    for t in tables:
        name = t["name"]
        cnt = _q(conn, f"SELECT COUNT(*) AS n FROM {name}")[0]["n"]
        print(f"  - {name}: {cnt} rows")


def print_schema(conn: sqlite3.Connection):
    tables = _q(conn, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    if not tables:
        print("\n-- schema --\n(no tables)")
        return
    print("\n-- schema --")
    for t in tables:
        name = t["name"]
        sql = _q(conn, "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,))
        print(f"\n-- {name} --")
        print(sql[0]["sql"] if sql else "(no sql)")

def print_latest_session_details(conn: sqlite3.Connection):
    latest = _q(conn, "SELECT id FROM sessions ORDER BY rowid DESC LIMIT 1")
    if not latest:
        print("\n(no sessions)")
        return
    sid = latest[0]["id"]

    print("\n== latest session ==")
    srow = _q(conn, "SELECT * FROM sessions WHERE id=?", (sid,))
    _print_table(srow)

    print("\n== landmarks_wide summary ==")
    summary = _q(
        conn,
        """
        SELECT
          COUNT(*) AS n_rows,
          MIN(frame_index) AS min_frame,
          MAX(frame_index) AS max_frame,
          ROUND(MIN(t_seconds),6) AS t_min,
          ROUND(MAX(t_seconds),6) AS t_max
        FROM landmarks_wide
        WHERE session_id = ?
        """,
        (sid,),
    )
    _print_table(summary)

    # columns actually present
    cols = [r["name"] for r in _q(conn, "PRAGMA table_info(landmarks_wide)")]
    sample_cols = [c for c in [
        "frame_index","t_seconds",
        "ear_x","ear_y","shoulder_x","shoulder_y",
        "wrist_x","wrist_y","hand_x","hand_y", "hip_x"
    ] if c in cols]

    print("\n-- landmarks_wide head --")
    head = _q(
        conn,
        f"""
        SELECT {", ".join(sample_cols)}
        FROM landmarks_wide
        WHERE session_id = ?
        ORDER BY frame_index
        LIMIT 10
        """,
        (sid,),
    )
    _print_table(head)


def main():
    conn, db_path = connect()
    try:
        print_info(conn, db_path)
        print_schema(conn)
        print_latest_session_details(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
