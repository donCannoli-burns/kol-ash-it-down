from __future__ import annotations
import json, sqlite3, time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  correlation_id TEXT,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  source TEXT,
  target TEXT,
  status TEXT NOT NULL,
  sha_before TEXT,
  sha_after TEXT,
  gcli_verified INTEGER NOT NULL DEFAULT 0,
  detail_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);

CREATE TABLE IF NOT EXISTS session_evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  player TEXT,
  source_path TEXT,
  temp_path TEXT,
  requested_lines INTEGER,
  marker TEXT,
  marker_seen INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
  path TEXT PRIMARY KEY,
  kind TEXT,
  sha256 TEXT,
  updated_at REAL,
  provenance TEXT
);

CREATE TABLE IF NOT EXISTS kv_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at REAL NOT NULL
);
"""

def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(path)
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA)
    return cx

def log_event(path: Path, *, correlation_id="", actor="service", action="", source="", target="",
              status="ok", sha_before="", sha_after="", gcli_verified=False, detail: Any=None) -> int:
    with connect(path) as cx:
        cur = cx.execute(
            """INSERT INTO events(ts,correlation_id,actor,action,source,target,status,sha_before,sha_after,gcli_verified,detail_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (time.time(), correlation_id, actor, action, source, target, status,
             sha_before, sha_after, int(bool(gcli_verified)), json.dumps(detail or {}, sort_keys=True)),
        )
        return int(cur.lastrowid)

def record_artifact(path: Path, artifact_path: str, kind: str, sha256: str, provenance: str) -> None:
    with connect(path) as cx:
        cx.execute(
            """INSERT INTO artifacts(path,kind,sha256,updated_at,provenance)
               VALUES(?,?,?,?,?)
               ON CONFLICT(path) DO UPDATE SET kind=excluded.kind,sha256=excluded.sha256,
                 updated_at=excluded.updated_at,provenance=excluded.provenance""",
            (artifact_path, kind, sha256, time.time(), provenance),
        )

def record_session(path: Path, **row: Any) -> None:
    with connect(path) as cx:
        cx.execute(
            """INSERT INTO session_evidence(ts,player,source_path,temp_path,requested_lines,marker,marker_seen,sha256)
               VALUES(?,?,?,?,?,?,?,?)""",
            (time.time(), row.get("player",""), row.get("source_path",""), row.get("temp_path",""),
             int(row.get("requested_lines",0)), row.get("marker",""),
             int(bool(row.get("marker_seen"))), row.get("sha256","")),
        )

def query_readonly(path: Path, sql: str, limit: int = 500) -> dict:
    q = (sql or "").strip()
    if not q:
        raise ValueError("empty SQL")
    first = q.split(None, 1)[0].upper()
    if first not in {"SELECT", "WITH"}:
        raise ValueError("only SELECT/WITH queries are allowed")
    cx = connect(path)
    try:
        cx.execute("PRAGMA query_only=ON")
        cur = cx.execute(q)
        rows = [dict(r) for r in cur.fetchmany(max(1, min(limit, 5000)))]
        return {"columns": [d[0] for d in (cur.description or [])], "rows": rows}
    finally:
        cx.close()
