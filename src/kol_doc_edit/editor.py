from __future__ import annotations
from pathlib import Path
import difflib, hashlib, os, re, tempfile, time
from .config import Config
from .db import log_event, record_artifact

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)

def backup_file(cfg: Config, path: Path, old_text: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = cfg.logs_root / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    safe = path.name.replace("/", "_")
    backup = backup_dir / f"{safe}.{stamp}.bak"
    backup.write_text(old_text, encoding="utf-8")
    return backup

def preview_diff(old: str, new: str, path: str) -> str:
    return "".join(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True),
        fromfile=path + ":before", tofile=path + ":after"
    ))

def edit_text(cfg: Config, path: Path, *, mode: str, find: str = "", replace: str = "",
              content: str = "", expected_sha256: str = "", confirm: bool = False,
              correlation_id: str = "") -> dict:
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    before = sha256_text(old)
    if expected_sha256 and expected_sha256 != before:
        raise ValueError("expected_sha256 does not match current file")

    if mode == "overwrite":
        new = content
    elif mode == "append":
        new = old + content
    elif mode == "replace_literal":
        if not find:
            raise ValueError("find is required")
        new = old.replace(find, replace)
    elif mode == "replace_first":
        if not find:
            raise ValueError("find is required")
        new = old.replace(find, replace, 1)
    elif mode == "regex":
        if not find:
            raise ValueError("regex pattern is required")
        new = re.sub(find, replace, old, flags=re.M)
    else:
        raise ValueError(f"unsupported edit mode: {mode}")

    after = sha256_text(new)
    diff = preview_diff(old, new, str(path))
    result = {"path": str(path), "sha_before": before, "sha_after": after, "changed": old != new, "diff": diff}

    if not confirm:
        result["written"] = False
        return result

    backup = backup_file(cfg, path, old)
    atomic_write(path, new)
    result["written"] = True
    result["backup"] = str(backup)
    record_artifact(cfg.db_path, str(path), "edited-text", after, "relay/api edit")
    log_event(cfg.db_path, correlation_id=correlation_id, actor="relay-agent", action=f"edit:{mode}",
              target=str(path), status="written", sha_before=before, sha_after=after,
              detail={"backup": str(backup)})
    return result
