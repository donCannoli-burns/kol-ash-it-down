#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python -m compileall -q "$ROOT/src"
PYTHONPATH="$ROOT/src" python -m unittest discover -s "$ROOT/tests" -v
node --check "$ROOT/web/dist/client.js"
python - <<'PY' "$ROOT"
from pathlib import Path
import sys
root=Path(sys.argv[1])
for rel in ["relay/doc_edit.ash","scripts/doc_edit_common.ash","scripts/doc_edit_cli.ash","scripts/doc_edit_login.ash"]:
    s=(root/rel).read_text()
    assert s.count("{")==s.count("}"), f"brace mismatch in {rel}"
print("ASH_STATIC_SMOKE=PASS")
PY
echo "SMOKE=PASS"
