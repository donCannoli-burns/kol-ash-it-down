from __future__ import annotations
from pathlib import Path
from .config import Config

ALIASES = {
    "data/": "data",
    "relay/": "relay",
    "scripts/": "scripts",
    "readme.html/": "doc_edit",
    "llm-session/": "doc_edit/llm-session",
}

class PathDenied(ValueError):
    pass

def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False

def resolve_user_path(spec: str, cfg: Config, *, for_write: bool = False) -> Path:
    raw = (spec or "").strip().replace("\\", "/")
    if not raw:
        raise PathDenied("empty path")
    if "\x00" in raw:
        raise PathDenied("NUL byte in path")
    if raw.startswith("~/"):
        candidate = Path(raw).expanduser().resolve()
    elif raw.startswith("/"):
        candidate = Path(raw).expanduser().resolve()
    else:
        head, sep, tail = raw.partition("/")
        prefix = head + "/" if sep else ""
        if prefix in ALIASES:
            mapped = ALIASES[prefix]
            if mapped == "doc_edit":
                candidate = (cfg.state_root / tail).resolve()
            elif mapped.startswith("doc_edit/"):
                candidate = (cfg.state_root / mapped.split("/", 1)[1] / tail).resolve()
            else:
                candidate = (cfg.kol_home / mapped / tail).resolve()
        else:
            candidate = (cfg.state_root / raw).resolve()

    allowed = [
        (cfg.kol_home / "data").resolve(),
        (cfg.kol_home / "relay").resolve(),
        (cfg.kol_home / "scripts").resolve(),
    ]
    if not any(_within(candidate, root) for root in allowed):
        raise PathDenied(f"path is outside allowed KoLmafia roots: {candidate}")

    # Symlink-aware parent validation for writes.
    parent = candidate.parent.resolve()
    if for_write and not any(_within(parent, root) for root in allowed):
        raise PathDenied(f"write parent escapes allowed roots: {parent}")
    return candidate
