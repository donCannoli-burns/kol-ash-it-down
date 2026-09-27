from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Config:
    kol_home: Path
    state_root: Path
    inbox: Path
    outbox: Path
    logs_root: Path
    db_path: Path
    token_path: Path
    status_path: Path
    host: str = "127.0.0.1"
    port: int = 61337

def load_config() -> Config:
    kol_home = Path(os.environ.get("KOLMAFIA_HOME", Path.home() / ".kolmafia")).expanduser().resolve()
    state_root = kol_home / "data" / "doc_edit"
    logs_root = state_root / "llm-session" / "state" / "memory" / "logs" / "doc"
    cfg = Config(
        kol_home=kol_home,
        state_root=state_root,
        inbox=state_root / "inbox",
        outbox=state_root / "outbox",
        logs_root=logs_root,
        db_path=state_root / "llm-session" / "state" / "memory" / "doc_edit.sqlite3",
        token_path=state_root / "service.token",
        status_path=state_root / "system-status.json",
        port=int(os.environ.get("KOL_DOC_EDIT_PORT", "61337")),
    )
    for p in [cfg.state_root, cfg.inbox, cfg.outbox, cfg.logs_root, cfg.db_path.parent]:
        p.mkdir(parents=True, exist_ok=True)
    return cfg
