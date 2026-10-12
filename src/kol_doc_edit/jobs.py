from __future__ import annotations
from pathlib import Path
import importlib.util, json, time, traceback
from .config import Config
from .guard import resolve_user_path
from .converters import convert_text
from .editor import atomic_write, sha256_text, backup_file
from .db import log_event, record_artifact, query_readonly
from .session import capture_session_tail
from .status_artifact import write_status_artifacts

def _write_result(cfg: Config, job_id: str, result: dict) -> Path:
    out = cfg.outbox / f"{job_id}.json"
    atomic_write(out, json.dumps(result, indent=2, sort_keys=True) + "\n")
    return out

def _run_don_combo_matrix(cfg: Config, correlation_id: str) -> dict:
    bridge_path = cfg.kol_home / "scripts" / "don_combo" / "watersheep_combo_bridge.py"
    if not bridge_path.exists():
        raise FileNotFoundError(f"don_combo matrix bridge not installed: {bridge_path}")

    spec = importlib.util.spec_from_file_location("don_combo_watersheep_bridge", bridge_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load don_combo bridge: {bridge_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    result = module.snapshot(
        cfg.kol_home,
        "http://127.0.0.1:8766/v1/systemone",
        6,
        15.0,
        False,
    )
    paths = module.write_runtime(cfg.kol_home, result)
    comparison = result.get("comparison") or {}
    observations = result.get("observations") or {}
    summary = {
        "runtime_schema": result.get("schema"),
        "watersheep_status": (result.get("watersheep") or {}).get("status"),
        "pool_size": comparison.get("pool_size"),
        "baseline_rank": comparison.get("baseline_rank"),
        "shadow_top_minute": comparison.get("shadow_top_minute"),
        "observed_fronts": observations.get("fronts_recorded"),
        "session_events_added": (observations.get("session_tail") or {}).get("events_added"),
        **paths,
    }
    log_event(
        cfg.db_path,
        correlation_id=correlation_id,
        actor="gcli-job",
        action="don-combo-matrix-refresh",
        source=str(bridge_path),
        target=paths["runtime_json"],
        status="written",
        detail=summary,
    )
    return summary

def process_job(cfg: Config, job_path: Path) -> dict:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    job_id = str(job.get("id") or job_path.stem)
    action = str(job.get("action") or "")
    correlation_id = str(job.get("correlation_id") or job_id)
    result = {"ok": True, "id": job_id, "action": action, "processed_at": time.time()}

    if action in {"login-sync", "status"}:
        result.update(write_status_artifacts(cfg, correlation_id))
        player = str(job.get("player") or "")
        marker = str(job.get("marker") or "")
        try:
            result["session"] = capture_session_tail(cfg, player, int(job.get("lines") or 200), marker, correlation_id)
        except FileNotFoundError as exc:
            result["session_warning"] = str(exc)

    elif action == "session-tail":
        result["session"] = capture_session_tail(
            cfg, str(job.get("player") or ""), int(job.get("lines") or 200),
            str(job.get("marker") or ""), correlation_id
        )

    elif action == "don-combo-matrix-refresh":
        result["don_combo_matrix"] = _run_don_combo_matrix(cfg, correlation_id)

    elif action == "convert":
        source = resolve_user_path(str(job.get("source") or ""), cfg)
        target = resolve_user_path(str(job.get("target") or ""), cfg, for_write=True)
        out_text, meta = convert_text(source, target)
        old = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        before = sha256_text(old)
        backup = str(backup_file(cfg, target, old)) if target.exists() else ""
        atomic_write(target, out_text)
        after = sha256_text(out_text)
        record_artifact(cfg.db_path, str(target), "conversion", after, f"converted from {source}")
        log_event(cfg.db_path, correlation_id=correlation_id, actor="gcli-job", action="convert",
                  source=str(source), target=str(target), status="written", sha_before=before, sha_after=after,
                  detail={"backup": backup, **meta})
        result.update({"source": str(source), "target": str(target), "sha_before": before,
                       "sha_after": after, "backup": backup, "meta": meta})

    elif action == "read":
        path = resolve_user_path(str(job.get("source") or ""), cfg)
        body = path.read_text(encoding="utf-8", errors="replace")
        result.update({"path": str(path), "sha256": sha256_text(body), "content": body})

    elif action == "sql":
        result["query"] = query_readonly(cfg.db_path, str(job.get("payload") or ""))

    else:
        raise ValueError(f"unsupported job action: {action}")

    out = _write_result(cfg, job_id, result)
    job_path.unlink(missing_ok=True)
    result["result_path"] = str(out)
    return result

def process_pending(cfg: Config) -> list[dict]:
    results = []
    for path in sorted(cfg.inbox.glob("*.json")):
        try:
            results.append(process_job(cfg, path))
        except Exception as exc:
            job_id = path.stem
            error = {"ok": False, "id": job_id, "error": str(exc), "traceback": traceback.format_exc()}
            _write_result(cfg, job_id, error)
            log_event(cfg.db_path, correlation_id=job_id, actor="worker", action="job",
                      source=str(path), status="error", detail={"error": str(exc)})
            path.unlink(missing_ok=True)
            results.append(error)
    return results
