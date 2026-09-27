from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json, secrets, threading, time
from .config import Config
from .guard import resolve_user_path
from .editor import edit_text, sha256_text, atomic_write, backup_file
from .converters import convert_text
from .db import connect, log_event, record_artifact, query_readonly
from .session import capture_session_tail
from .status_artifact import build_status, write_status_artifacts
from .jobs import process_pending

ALLOWED_ORIGINS = {
    "http://127.0.0.1:60080",
    "http://localhost:60080",
    "http://127.0.0.1",
    "http://localhost",
}

def ensure_token(cfg: Config) -> str:
    if cfg.token_path.exists():
        token = cfg.token_path.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_hex(32)
    cfg.token_path.write_text(token + "\n", encoding="utf-8")
    try:
        cfg.token_path.chmod(0o600)
    except OSError:
        pass
    return token

class Handler(BaseHTTPRequestHandler):
    cfg: Config = None
    token: str = ""

    def log_message(self, fmt, *args):
        return

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin", "")
        return not origin or origin in ALLOWED_ORIGINS

    def _auth_ok(self) -> bool:
        return secrets.compare_digest(self.headers.get("X-Kol-Doc-Edit-Token", ""), self.token)

    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Kol-Doc-Edit-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, status: int, obj):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        n = int(self.headers.get("Content-Length", "0") or 0)
        if n > 5_000_000:
            raise ValueError("request body too large")
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def do_OPTIONS(self):
        if not self._origin_ok():
            return self._json(403, {"ok": False, "error": "origin denied"})
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if not self._origin_ok():
            return self._json(403, {"ok": False, "error": "origin denied"})
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self._json(200, {"ok": True, "service": "kol-doc-edit", "version": "0.1.0"})
        if not self._auth_ok():
            return self._json(401, {"ok": False, "error": "missing or invalid relay token"})

        if parsed.path == "/api/status":
            return self._json(200, {"ok": True, "status": build_status(self.cfg)})
        if parsed.path == "/api/events":
            limit = min(int(parse_qs(parsed.query).get("limit", ["100"])[0]), 500)
            with connect(self.cfg.db_path) as cx:
                rows = [dict(r) for r in cx.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))]
            return self._json(200, {"ok": True, "events": rows})
        return self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if not self._origin_ok():
            return self._json(403, {"ok": False, "error": "origin denied"})
        if not self._auth_ok():
            return self._json(401, {"ok": False, "error": "missing or invalid relay token"})
        try:
            data = self._read_json()
            if self.path == "/api/read":
                path = resolve_user_path(str(data.get("path") or ""), self.cfg)
                body = path.read_text(encoding="utf-8", errors="replace")
                return self._json(200, {"ok": True, "path": str(path), "sha256": sha256_text(body), "content": body})

            if self.path == "/api/edit":
                path = resolve_user_path(str(data.get("path") or ""), self.cfg, for_write=True)
                result = edit_text(
                    self.cfg, path,
                    mode=str(data.get("mode") or "replace_literal"),
                    find=str(data.get("find") or ""),
                    replace=str(data.get("replace") or ""),
                    content=str(data.get("content") or ""),
                    expected_sha256=str(data.get("expected_sha256") or ""),
                    confirm=bool(data.get("confirm")),
                    correlation_id=str(data.get("correlation_id") or ""),
                )
                return self._json(200, {"ok": True, **result})

            if self.path == "/api/convert":
                source = resolve_user_path(str(data.get("source") or ""), self.cfg)
                target = resolve_user_path(str(data.get("target") or ""), self.cfg, for_write=True)
                out_text, meta = convert_text(source, target)
                old = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
                before, after = sha256_text(old), sha256_text(out_text)
                preview = {"ok": True, "source": str(source), "target": str(target), "sha_before": before,
                           "sha_after": after, "meta": meta, "preview": out_text[:20000], "written": False}
                if bool(data.get("confirm")):
                    backup = str(backup_file(self.cfg, target, old)) if target.exists() else ""
                    atomic_write(target, out_text)
                    record_artifact(self.cfg.db_path, str(target), "conversion", after, f"converted from {source}")
                    log_event(self.cfg.db_path, correlation_id=str(data.get("correlation_id") or ""),
                              actor="relay-agent", action="convert", source=str(source), target=str(target),
                              status="written", sha_before=before, sha_after=after,
                              detail={"backup": backup, **meta})
                    preview["written"] = True
                    preview["backup"] = backup
                return self._json(200, preview)

            if self.path == "/api/session-tail":
                result = capture_session_tail(
                    self.cfg, str(data.get("player") or ""),
                    int(data.get("lines") or 200),
                    str(data.get("marker") or ""),
                    str(data.get("correlation_id") or ""),
                )
                return self._json(200, {"ok": True, **result})

            if self.path == "/api/query":
                result = query_readonly(self.cfg.db_path, str(data.get("sql") or ""), int(data.get("limit") or 500))
                return self._json(200, {"ok": True, **result})

            if self.path == "/api/status-artifact":
                return self._json(200, {"ok": True, **write_status_artifacts(self.cfg, str(data.get("correlation_id") or ""))})

            return self._json(404, {"ok": False, "error": "not found"})
        except Exception as exc:
            return self._json(400, {"ok": False, "error": str(exc)})

def _worker_loop(cfg: Config, stop: threading.Event):
    last_status_mtime = 0.0
    while not stop.wait(1.0):
        try:
            process_pending(cfg)
            if cfg.status_path.exists():
                mtime = cfg.status_path.stat().st_mtime
                if mtime > last_status_mtime:
                    last_status_mtime = mtime
                    write_status_artifacts(cfg, "status-file-watch")
        except Exception as exc:
            log_event(cfg.db_path, actor="worker", action="loop", status="error", detail={"error": str(exc)})

def serve(cfg: Config) -> None:
    token = ensure_token(cfg)
    Handler.cfg = cfg
    Handler.token = token
    stop = threading.Event()
    worker = threading.Thread(target=_worker_loop, args=(cfg, stop), daemon=True)
    worker.start()
    server = ThreadingHTTPServer((cfg.host, cfg.port), Handler)
    print(f"kol-doc-edit listening on http://{cfg.host}:{cfg.port}")
    print(f"state root: {cfg.state_root}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
