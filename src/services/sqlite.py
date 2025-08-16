# src/services/video.py
from __future__ import annotations
import uuid
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
import sqlite3
from pandas import DataFrame

@dataclass
class SessionRecord:
    id: str
    name: str
    original_video_filepath: Path
    processed_video_filepath: Optional[Path]
    session_status: str

class MyDB:
    def __init__(self, sqlite_client: sqlite3.Connection):
        self.db = sqlite_client

    def session_name_exists(self, name: str) -> bool:
        cur = self.db.execute("SELECT 1 FROM sessions WHERE name = ? LIMIT 1", (name,))
        return cur.fetchone() is not None

    def session_id_exists(self, session_id: str) -> bool:
        cur = self.db.execute("SELECT 1 FROM sessions WHERE id = ? LIMIT 1", (session_id,))
        return cur.fetchone() is not None

    def insert_session_row(self, rec: SessionRecord) -> None:
        self.db.execute(
            """
            INSERT INTO sessions (id, name, original_video_filepath, processed_video_filepath, session_status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (rec.id, rec.name, str(rec.original_video_filepath),
             str(rec.processed_video_filepath) if rec.processed_video_filepath else None, rec.session_status),
        )
        self.db.commit()

    def update_session_status(self, session_id: str, status: str) -> None:
        self.db.execute("UPDATE sessions SET session_status = ? WHERE id = ?", (status, session_id))
        self.db.commit()

    def insert_landmark_data_to_session(self, session_id: str, data: DataFrame) -> None:
        # --- discover authoritative table columns ---
        table_cols = [row[1] for row in self.db.execute("PRAGMA table_info(landmarks_wide)").fetchall()]
        if not table_cols:
            raise RuntimeError("Table 'landmarks_wide' does not exist.")

        # --- sanity checks ---
        required = ["frame_index", "t_seconds"]
        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")

        df_cols = set(data.columns)

        # Maintain a stable landmark order
        lm_order = ("ear","shoulder","elbow","wrist","hand","hip","knee","ankle")

        # Landmark coordinate/optional columns in preferred order
        ordered_landmark_cols: List[str] = []
        for lm in lm_order:
            for suffix in ("_x", "_y"):
                col = f"{lm}{suffix}"
                if col in df_cols and col in table_cols:
                    ordered_landmark_cols.append(col)

        extras = [
            c for c in data.columns
            if c not in required and c not in ordered_landmark_cols and c in table_cols
        ]

        insert_cols = ["session_id"] + required + ordered_landmark_cols + extras
        placeholders = ", ".join(["?"] * len(insert_cols))
        col_list_sql = ", ".join(insert_cols)

        sql = f"INSERT OR REPLACE INTO landmarks_wide ({col_list_sql}) VALUES ({placeholders})"

        # Build a subset DataFrame in the right order (excluding session_id),
        # and convert NaN -> None so SQLite stores NULLs.
        subset = data[insert_cols[1:]]  # ['frame_index','t_seconds', ...]
        subset = subset.astype(object).where(pd.notna(subset), None)

        rows_iter = subset.itertuples(index=False, name=None)

        # Bulk insert in a single transaction
        with self.db:
            self.db.executemany(sql, ((session_id, *row) for row in rows_iter))

    def get_session_from_id(self, session_id: str) -> Dict[str, Any]:
        """
        Return:
        {
          "session_id": str,
          "session_name": str,
          "processed_video_filepath": str | None,
          "landmarks": { "<col>": [ ... ], ... }   # wide, columnar; empty {} if none
        }
        """
        # --- session row ---
        srow = self.db.execute(
            "SELECT id, name, processed_video_filepath FROM sessions WHERE id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
        if not srow:
            raise ValueError(f"Session not found: {session_id}")

        if isinstance(srow, sqlite3.Row):
            sid = srow["id"]
            sname = srow["name"]
            pvp = srow["processed_video_filepath"]
        else:
            sid, sname, pvp = srow  # fallback if row_factory not set

        # --- landmarks (wide) ---
        cur = self.db.execute(
            "SELECT * FROM landmarks_wide WHERE session_id = ? ORDER BY frame_index",
            (sid,),
        )
        rows = cur.fetchall()

        if not rows:
            landmarks: Dict[str, List[Any]] = {}
        else:
            col_names = [d[0] for d in cur.description]  # authoritative column order
            keep_cols = [c for c in col_names if c != "session_id"]  # exclude FK
            idx_map = {c: i for i, c in enumerate(col_names)}

            landmarks = {c: [] for c in keep_cols}
            if isinstance(rows[0], sqlite3.Row):
                # row_factory=sqlite3.Row path
                for r in rows:
                    for c in keep_cols:
                        landmarks[c].append(r[c])
            else:
                # tuple path
                for r in rows:
                    for c in keep_cols:
                        landmarks[c].append(r[idx_map[c]])

        return {
            "session_id": sid,
            "session_name": sname,
            "processed_video_filepath": pvp,
            "landmarks": landmarks,
        }
