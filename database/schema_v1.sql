-- Sessions: one row per imported video/session
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  original_video_filepath TEXT NOT NULL,
  processed_video_filepath TEXT,
  processed_video_fileurl TEXT,
  cover_image_filepath TEXT,
  cover_image_fileurl TEXT,
  status TEXT NOT NULL CHECK (status IN ('new','processing','done','error')),
  created_at FLOAT NOT NULL,
  updated_at FLOAT NOT NULL
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
  ON sessions(status);

PRAGMA user_version = 1;