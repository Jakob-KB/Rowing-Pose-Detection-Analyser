PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;

-- Tables
CREATE TABLE sessions (
  id           TEXT PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  status       TEXT NOT NULL CHECK (status IN ('new', 'processing', 'done', 'error')),
  notes        TEXT,
  created_at   INTEGER NOT NULL,
  updated_at   INTEGER NOT NULL
);

CREATE TABLE raw_videos (
  id           TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  path         TEXT NOT NULL,
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
  path         TEXT,
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
  path         TEXT,
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
  path       TEXT,
  uri        TEXT,
  mime_type  TEXT,
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

        'processed_video', json_object(
            'id', pv.id,
            'session_id', pv.session_id,
            'path', pv.path,
            'uri', pv.uri,
            'mime_type', pv.mime_type,
            'duration_s', pv.duration_s,
            'frame_count', pv.frame_count,
            'fps', pv.fps,
            'width', pv.width,
            'height', pv.height,
            'created_at', pv.created_at
        ),

        'evaluation', json_object(
            'id', e.id,
            'session_id', e.session_id,
            'video_id', e.video_id,
            'path', e.path,
            'uri', e.uri,
            'mime_type', e.mime_type,
            'avg_spm', e.avg_spm,
            'created_at', e.created_at
        ),

        'cover_image', json_object(
            'id', ci.id,
            'session_id', ci.session_id,
            'path', ci.path,
            'uri', ci.uri,
            'mime_type', ci.mime_type,
            'width', ci.width,
            'height', ci.height,
            'created_at', ci.created_at
        ),

        'created_at', s.created_at,
        'updated_at', s.updated_at
    ) AS session_json
FROM sessions s
LEFT JOIN processed_videos pv ON pv.session_id = s.id
LEFT JOIN evaluations  e   ON e.session_id  = s.id
LEFT JOIN cover_images ci  ON ci.session_id = s.id;
