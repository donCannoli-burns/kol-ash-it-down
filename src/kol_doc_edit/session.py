from __future__ import annotations
from pathlib import Path
import hashlib, re, tempfile, time
from .config import Config
from .db import record_session, log_event

SAFE_PLAYER = re.compile(r"[^A-Za-z0-9_.-]+")

def _tail_lines(path: Path, count: int) -> str:
    count = max(1, min(int(count), 10000))
    # Session logs are text and typically modest; keep the implementation predictable.
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-count:]) + ("\n" if lines else "")

def resolve_active_session(cfg: Config, player: str = "") -> Path:
    sessions = cfg.kol_home / "sessions"
    if player:
        safe = SAFE_PLAYER.sub("_", player)
        exact = sessions / f"active_session.{safe}"
        if exact.exists():
            return exact
    candidates = sorted(sessions.glob("active_session.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"no active_session.* found under {sessions}")
    return candidates[0]

def capture_session_tail(cfg: Config, player: str = "", lines: int = 200, marker: str = "", correlation_id: str = "") -> dict:
    src = resolve_active_session(cfg, player)
    body = _tail_lines(src, lines)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    player_key = SAFE_PLAYER.sub("_", player or src.name.split(".", 1)[-1])
    tmp_dir = Path(tempfile.gettempdir()) / "kol-doc-edit" / player_key
    tmp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = tmp_dir / "active-session.tail.txt"
    temp_path.write_text(body, encoding="utf-8")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    archive = cfg.logs_root / f"session-{player_key}-{stamp}.txt"
    archive.write_text(body, encoding="utf-8")
    marker_seen = bool(marker and marker in body)
    result = {
        "player": player or player_key,
        "source_path": str(src),
        "temp_path": str(temp_path),
        "archive_path": str(archive),
        "requested_lines": int(lines),
        "marker": marker,
        "marker_seen": marker_seen,
        "sha256": digest,
    }
    record_session(cfg.db_path, **result)
    log_event(cfg.db_path, correlation_id=correlation_id, actor="gcli-evidence",
              action="session-tail", source=str(src), target=str(temp_path),
              status="verified" if marker_seen else "captured",
              sha_after=digest, gcli_verified=marker_seen, detail=result)
    return result
