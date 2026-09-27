#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KOL_HOME="${KOLMAFIA_HOME:-$HOME/.kolmafia}"

mkdir -p \
  "$KOL_HOME/relay" \
  "$KOL_HOME/scripts" \
  "$KOL_HOME/data/doc_edit/inbox" \
  "$KOL_HOME/data/doc_edit/outbox" \
  "$KOL_HOME/data/doc_edit/llm-session/state/memory/logs/doc"

install -m 0644 "$ROOT/relay/doc_edit.ash" "$KOL_HOME/relay/doc_edit.ash"
install -m 0644 "$ROOT/scripts/doc_edit_common.ash" "$KOL_HOME/scripts/doc_edit_common.ash"
install -m 0644 "$ROOT/scripts/doc_edit_cli.ash" "$KOL_HOME/scripts/doc_edit_cli.ash"
install -m 0644 "$ROOT/scripts/doc_edit_login.ash" "$KOL_HOME/scripts/doc_edit_login.ash"
install -m 0644 "$ROOT/data/doc_edit/ui.html" "$KOL_HOME/data/doc_edit/ui.html"

echo "Installed relay + ASH scripts under: $KOL_HOME"
echo
echo "Python/Conda:"
echo "  conda env create -f '$ROOT/environment.yml'"
echo "  conda activate kol-doc-edit"
echo "  pip install -e '$ROOT'"
echo "  kol-doc-edit serve"
echo
echo "KoLmafia gCLI:"
echo '  alias docedit => call doc_edit_cli.ash %%'
echo '  docedit status'
echo '  docedit snapshot 250'
echo '  docedit convert data/doc_edit.md | readme.html/doc_edit.html'
echo
echo "Relay URL:"
echo "  http://127.0.0.1:60080/relay/doc_edit.ash"
echo
echo "Login hook:"
echo "  If you do not already have a loginScript, set it to doc_edit_login.ash."
echo "  If you already have one, call doc_edit_login.ash from your existing login script instead of overwriting it."
