from __future__ import annotations
import os, tempfile, unittest, json
from pathlib import Path

from kol_doc_edit.config import load_config
from kol_doc_edit.guard import resolve_user_path, PathDenied
from kol_doc_edit.converters import convert_text
from kol_doc_edit.editor import edit_text
from kol_doc_edit.db import query_readonly, log_event

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / ".kolmafia"
        for d in ["data", "relay", "scripts", "sessions"]:
            (self.home / d).mkdir(parents=True, exist_ok=True)
        self.old = os.environ.get("KOLMAFIA_HOME")
        os.environ["KOLMAFIA_HOME"] = str(self.home)
        self.cfg = load_config()

    def tearDown(self):
        if self.old is None:
            os.environ.pop("KOLMAFIA_HOME", None)
        else:
            os.environ["KOLMAFIA_HOME"] = self.old
        self.tmp.cleanup()

    def test_path_guard(self):
        self.assertTrue(str(resolve_user_path("data/x.md", self.cfg)).endswith("/data/x.md"))
        with self.assertRaises(PathDenied):
            resolve_user_path("/etc/passwd", self.cfg)

    def test_conversion(self):
        src = self.home / "data" / "x.json"
        dst = self.home / "data" / "x.html"
        src.write_text('{"b":2,"a":1}', encoding="utf-8")
        out, meta = convert_text(src, dst)
        self.assertIn("<!doctype html>", out.lower())
        self.assertEqual(meta["source_format"], "json")
        self.assertEqual(meta["target_format"], "html")

    def test_ash_output_is_non_executable_container(self):
        src = self.home / "data" / "x.md"
        dst = self.home / "scripts" / "x.ash"
        src.write_text("# Hello\nDo a thing.", encoding="utf-8")
        out, _ = convert_text(src, dst)
        self.assertTrue(out.startswith("/* DOC-EDIT DOCUMENT CONTAINER"))
        self.assertNotIn("void main", out)

    def test_edit_preview_then_write(self):
        p = self.home / "data" / "a.txt"
        p.write_text("hello world\n", encoding="utf-8")
        preview = edit_text(self.cfg, p, mode="replace_literal", find="world", replace="KoL", confirm=False)
        self.assertFalse(preview["written"])
        self.assertEqual(p.read_text(), "hello world\n")
        written = edit_text(self.cfg, p, mode="replace_literal", find="world", replace="KoL", confirm=True)
        self.assertTrue(written["written"])
        self.assertEqual(p.read_text(), "hello KoL\n")
        self.assertTrue(Path(written["backup"]).exists())

    def test_sql_readonly(self):
        log_event(self.cfg.db_path, actor="test", action="x", status="ok")
        q = query_readonly(self.cfg.db_path, "SELECT action,status FROM events")
        self.assertEqual(q["rows"][0]["action"], "x")
        with self.assertRaises(ValueError):
            query_readonly(self.cfg.db_path, "DELETE FROM events")

if __name__ == "__main__":
    unittest.main()
