PRAGMA foreign_keys = ON;

-- Sessions
CREATE TABLE sessions (
  id           TEXT PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  status       TEXT NOT NULL CHECK (status IN ('new','processing','done','error')),
  notes        TEXT,
  created_at   INTEGER NOT NULL,
  updated_at   INTEGER NOT NULL
);

CREATE TABLE processes (
  id           TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  status       TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed')),
  tool_name    TEXT,
  phase        TEXT,
  progress     REAL,
  created_at   INTEGER NOT NULL
);

CREATE TABLE raw_videos (
  id           TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  path_local   TEXT NOT NULL,
  mime_type    TEXT,
  duration_s   REAL    CHECK (duration_s IS NULL OR duration_s >= 0),
  frame_count  INTEGER CHECK (frame_count IS NULL OR frame_count >= 0),
  fps          REAL    CHECK (fps IS NULL OR fps > 0),
  width        INTEGER CHECK (width IS NULL OR width > 0),
  height       INTEGER CHECK (height IS NULL OR height > 0),
  created_at   INTEGER NOT NULL
);

CREATE TABLE processed_videos (
  id           TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  path_local   TEXT,
  url_remote   TEXT,
  mime_type    TEXT,
  duration_s   REAL    CHECK (duration_s IS NULL OR duration_s >= 0),
  frame_count  INTEGER CHECK (frame_count IS NULL OR frame_count >= 0),
  fps          REAL    CHECK (fps IS NULL OR fps > 0),
  width        INTEGER CHECK (width IS NULL OR width > 0),
  height       INTEGER CHECK (height IS NULL OR height > 0),
  created_at   INTEGER NOT NULL,
  CHECK (path_local IS NOT NULL OR url_remote IS NOT NULL)
);

CREATE TABLE cover_images (
  id           TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  path_local   TEXT,
  url_remote   TEXT,
  mime_type    TEXT,
  width        INTEGER CHECK (width IS NULL OR width > 0),
  height       INTEGER CHECK (height IS NULL OR height > 0),
  created_at   INTEGER NOT NULL,
  CHECK (path_local IS NOT NULL OR url_remote IS NOT NULL)
);

-- Frames (per session)
CREATE TABLE frames (
  session_id  TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  frame_index INTEGER NOT NULL,
  pts_ms      INTEGER NOT NULL CHECK (pts_ms >= 0),
  timecode    TEXT,
  PRIMARY KEY (session_id, frame_index)
);

-- Landmarks (per frame)
CREATE TABLE landmarks (
  session_id  TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  frame_index INTEGER NOT NULL,
  keypoint    TEXT NOT NULL CHECK (keypoint IN ('ear','shoulder','elbow','wrist','hand','hip','knee','ankle')),
  x           REAL NOT NULL,
  y           REAL NOT NULL,
  PRIMARY KEY (session_id, frame_index, keypoint),
  FOREIGN KEY (session_id, frame_index) REFERENCES frames(session_id, frame_index) ON DELETE CASCADE
);

-- Metrics (per evaluation or per frame)
CREATE TABLE metrics (
  id           TEXT PRIMARY KEY,
  eval_id      TEXT NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
  frame_index  INTEGER,
  name         TEXT NOT NULL,
  value_real   REAL,
  value_text   TEXT,
  unit         TEXT
);

-- Helpful indexes
CREATE INDEX idx_frames_eval_pts      ON frames(eval_id, pts_ms);
CREATE INDEX idx_landmarks_eval_frame ON landmarks(eval_id, frame_index);
CREATE INDEX idx_evals_status         ON evaluations(status);

-- Optional: keep sessions.updated_at fresh on any direct UPDATE
CREATE TRIGGER IF NOT EXISTS tg_sessions_updated_at
AFTER UPDATE ON sessions
FOR EACH ROW BEGIN
  UPDATE sessions SET updated_at = strftime('%s','now') WHERE id = NEW.id;
END;