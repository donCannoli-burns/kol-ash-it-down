from __future__ import annotations
import argparse, json, sys
from .config import load_config
from .api import serve, ensure_token
from .guard import resolve_user_path
from .converters import convert_text
from .editor import atomic_write
from .session import capture_session_tail
from .db import query_readonly
from .jobs import process_pending
from .status_artifact import write_status_artifacts

def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kol-doc-edit", description="KoLmafia local document bridge")
    sp = p.add_subparsers(dest="cmd", required=True)

    sp.add_parser("serve")
    c = sp.add_parser("convert")
    c.add_argument("source")
    c.add_argument("target")
    c.add_argument("--write", action="store_true")

    t = sp.add_parser("session-tail")
    t.add_argument("--player", default="")
    t.add_argument("--lines", type=int, default=200)
    t.add_argument("--marker", default="")

    q = sp.add_parser("query")
    q.add_argument("sql")
    q.add_argument("--limit", type=int, default=500)

    sp.add_parser("process-jobs")
    sp.add_parser("status-artifact")
    sp.add_parser("paths")
    return p

def main(argv=None) -> int:
    args = parser().parse_args(argv)
    cfg = load_config()
    if args.cmd == "serve":
        ensure_token(cfg)
        serve(cfg)
        return 0
    if args.cmd == "convert":
        src = resolve_user_path(args.source, cfg)
        dst = resolve_user_path(args.target, cfg, for_write=True)
        out, meta = convert_text(src, dst)
        result = {"source": str(src), "target": str(dst), "meta": meta, "written": False}
        if args.write:
            atomic_write(dst, out)
            result["written"] = True
        else:
            result["preview"] = out
        print(json.dumps(result, indent=2))
        return 0
    if args.cmd == "session-tail":
        print(json.dumps(capture_session_tail(cfg, args.player, args.lines, args.marker), indent=2))
        return 0
    if args.cmd == "query":
        print(json.dumps(query_readonly(cfg.db_path, args.sql, args.limit), indent=2))
        return 0
    if args.cmd == "process-jobs":
        print(json.dumps(process_pending(cfg), indent=2))
        return 0
    if args.cmd == "status-artifact":
        print(json.dumps(write_status_artifacts(cfg), indent=2))
        return 0
    if args.cmd == "paths":
        print(json.dumps({
            "kol_home": str(cfg.kol_home),
            "state_root": str(cfg.state_root),
            "db": str(cfg.db_path),
            "token": str(cfg.token_path),
        }, indent=2))
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
