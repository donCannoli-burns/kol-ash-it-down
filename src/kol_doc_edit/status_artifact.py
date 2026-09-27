from __future__ import annotations
from pathlib import Path
import html, json, os, platform, sys, time
from .config import Config
from .editor import atomic_write, sha256_text
from .db import record_artifact, log_event

def load_status(cfg: Config) -> dict:
    if not cfg.status_path.exists():
        return {}
    try:
        return json.loads(cfg.status_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status_error": str(exc)}

def build_status(cfg: Config) -> dict:
    kol = load_status(cfg)
    return {
        "schema": "kol-doc-edit/status-v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "kolmafia": kol,
        "bridge": {
            "host": cfg.host,
            "port": cfg.port,
            "state_root": str(cfg.state_root),
            "db": str(cfg.db_path),
            "inbox_pending": len(list(cfg.inbox.glob("*.json"))),
            "outbox_results": len(list(cfg.outbox.glob("*.json"))),
        },
        "system": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        }
    }

def render_markdown(status: dict) -> str:
    k = status.get("kolmafia", {})
    b = status.get("bridge", {})
    s = status.get("system", {})
    return f"""# KoLmafia Agent System Status

Generated: `{status.get('generated_at','')}`

## KoLmafia

- Player: `{k.get('player','unknown')}`
- Player ID: `{k.get('player_id','')}`
- Class: `{k.get('class','')}`
- Level: `{k.get('level','')}`
- Path: `{k.get('path','')}`
- Adventures: `{k.get('adventures','')}`
- Meat: `{k.get('meat','')}`
- Ascensions: `{k.get('ascensions','')}`
- Daycount: `{k.get('daycount','')}`
- Turns played: `{k.get('turns_played','')}`
- Can interact: `{k.get('can_interact','')}`
- gCLI correlation marker: `{k.get('marker','')}`

## Document Bridge

- Service: `http://{b.get('host')}:{b.get('port')}`
- State root: `{b.get('state_root')}`
- SQLite: `{b.get('db')}`
- Pending jobs: `{b.get('inbox_pending')}`
- Results: `{b.get('outbox_results')}`

## Host

- Python: `{s.get('python')}`
- Platform: `{s.get('platform')}`
- Conda env: `{s.get('conda_env')}`

## Authority boundary

This artifact reports local state and document-bridge status. It is evidence, not permission to mutate KoL state.
"""

def render_html(status: dict, md: str) -> str:
    # Keep the HTML status artifact dependency-free and agent-readable.
    body = html.escape(md)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KoLmafia Agent Status</title>
<style>body{{background:#10100e;color:#ffffe3;max-width:1000px;margin:auto;padding:32px;font:15px/1.55 ui-monospace,monospace}}pre{{white-space:pre-wrap}}</style>
</head><body><pre>{body}</pre></body></html>"""

def write_status_artifacts(cfg: Config, correlation_id: str = "") -> dict:
    status = build_status(cfg)
    md = render_markdown(status)
    h = render_html(status, md)
    md_path = cfg.state_root / "agent-status.md"
    html_path = cfg.state_root / "agent-status.html"
    json_path = cfg.state_root / "agent-status.json"
    atomic_write(md_path, md)
    atomic_write(html_path, h)
    atomic_write(json_path, json.dumps(status, indent=2, sort_keys=True) + "\n")
    for path, kind in [(md_path,"status-md"), (html_path,"status-html"), (json_path,"status-json")]:
        digest = sha256_text(path.read_text(encoding="utf-8"))
        record_artifact(cfg.db_path, str(path), kind, digest, "login/system status synthesis")
    log_event(cfg.db_path, correlation_id=correlation_id, actor="service", action="status-artifact",
              target=str(html_path), status="written", detail={"markdown":str(md_path),"json":str(json_path)})
    return {"status": status, "markdown": str(md_path), "html": str(html_path), "json": str(json_path)}
