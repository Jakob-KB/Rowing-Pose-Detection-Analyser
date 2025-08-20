PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;

-- Tables
CREATE TABLE sessions (
  id           TEXT PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  status       TEXT NOT NULL CHECK (status IN ('empty','processing','error')),
  notes        TEXT,
  created_at   INTEGER NOT NULL,
  updated_at   INTEGER NOT NULL
);

CREATE TABLE raw_videos (
  id           TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  path_local   TEXT NOT NULL,
  mime_type    TEXT,
  duration_s   REAL,
  frame_count  INTEGER,
  fps          REAL,
  width        INTEGER,
  height       INTEGER,
  created_at   INTEGER NOT NULL
);

CREATE TABLE processed_videos (
  id           TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  path_local   TEXT,
  uri          TEXT,
  mime_type    TEXT,
  duration_s   REAL,
  frame_count  INTEGER,
  fps          REAL,
  width        INTEGER,
  height       INTEGER,
  created_at   INTEGER NOT NULL
);

CREATE TABLE cover_images (
  id           TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  path_local   TEXT,
  uri          TEXT,
  mime_type    TEXT,
  width        INTEGER,
  height       INTEGER,
  created_at   INTEGER NOT NULL
);

CREATE TABLE evaluations (
  id         TEXT PRIMARY KEY,
  session_id TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  video_id   TEXT NOT NULL UNIQUE REFERENCES processed_videos(id) ON DELETE CASCADE,
  path_local TEXT,
  uri        TEXT,
  avg_spm    REAL,
  created_at INTEGER NOT NULL
);

-- Views
CREATE VIEW SessionView AS
SELECT
    s.created_at AS sort_created_at,
    json_object(
        'id', s.id,
        'name', s.name,
        'status', s.status,
        'notes', s.notes,

        'cover_image', json_object(
            'id', ci.id,
            'uri', ci.uri,
            'path_local', ci.path_local,
            'mime_type', ci.mime_type,
            'width', ci.width,
            'height', ci.height,
            'created_at', ci.created_at
        ),

        'evaluation', json_object(
            'id', e.id,
            'video_id', e.video_id,
            'path_local', e.path_local,
            'uri', e.uri,
            'avg_spm', e.avg_spm,
            'created_at', e.created_at
        ),

        'created_at', s.created_at,
        'updated_at', s.updated_at
    ) AS session_json
FROM sessions s
LEFT JOIN cover_images ci  ON ci.session_id = s.id
LEFT JOIN evaluations  e   ON e.session_id  = s.id;
