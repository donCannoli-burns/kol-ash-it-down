# kol-ash-it-down

A local-first KoLmafia relay/document bridge inspired by the **conversion-first** ergonomics of Microsoft MarkItDown, the KoLmafia/Python reflection boundary demonstrated by **pymafia**, and the “HTML as a human-facing artifact” direction of **HTMLBook** / **html-anything**.

It gives a human or agent a bounded place to:

- read and edit local KoLmafia text files;
- cross-format `.md`, `.ash`, `.html`, `.html5`, `.txt`, `.xml`, and `.json`;
- use ASH on the gCLI to emit current KoLmafia state and correlation markers;
- capture the last *N* lines from `~/.kolmafia/sessions/active_session.<player>` into a local temp file;
- prove a gCLI bridge command really ran by checking for its unique marker in the active-session tail;
- write KoLmafia return/evidence snapshots under `data/doc_edit/llm-session/state/memory/logs/doc/`;
- keep an append-only-ish SQLite audit/event memory with read-only SQL queries;
- generate `agent-status.md`, `agent-status.html`, and `agent-status.json` whenever the login status file changes;
- use the same operations from relay HTML, Python CLI, JS, or TypeScript.

## What it deliberately does **not** do

The Python/Conda service is **not** a second KoL executor. It does not call pymafia mutation methods, KoL relay command endpoints, shell commands, or arbitrary network URLs. KoL state comes from the ASH/gCLI side and `active_session` evidence. Local document writes are previewed, backed up, atomic, path-guarded, and logged.

## Layout

```text
kol-ash-it-down/
├── relay/doc_edit.ash
├── scripts/
│   ├── doc_edit_common.ash
│   ├── doc_edit_cli.ash
│   └── doc_edit_login.ash
├── data/doc_edit/ui.html
├── src/kol_doc_edit/
│   ├── api.py
│   ├── cli.py
│   ├── config.py
│   ├── converters.py
│   ├── db.py
│   ├── editor.py
│   ├── guard.py
│   ├── jobs.py
│   ├── session.py
│   └── status_artifact.py
├── web/
│   ├── doc_edit.html
│   ├── src/client.ts
│   └── dist/client.js
├── tests/test_core.py
├── environment.yml
├── pyproject.toml
└── install.sh
```

## Install in KoLmafia

From the KoLmafia gCLI:

```text
git checkout https://github.com/donCannoli-burns/kol-ash-it-down.git
```

KoLmafia copies the repository's top-level `scripts/`, `relay/`, and `data/` files into the corresponding local KoLmafia directories. The checkout itself lives under KoLmafia's `git/` directory as `donCannoli-burns-kol-ash-it-down`.

After future releases:

```text
git update donCannoli-burns-kol-ash-it-down
```

### Install the Python/Conda side

The relay UI and ASH bridge arrive through KoLmafia's Git checkout. The local Python service is installed from the checked-out repository. On a normal Linux KoLmafia home:

```bash
cd ~/.kolmafia/git/donCannoli-burns-kol-ash-it-down
conda env create -f environment.yml
conda activate kol-doc-edit
pip install -e .
kol-doc-edit serve
```

If your KoLmafia home is elsewhere, use that installation's `git/donCannoli-burns-kol-ash-it-down` directory instead. `./install.sh` remains available for a conventional filesystem clone, but is not required for the KoLmafia-managed `scripts/`, `relay/`, and `data/` files after `git checkout`.

Start the document service:

```bash
kol-doc-edit serve
```

The service binds only to:

```text
127.0.0.1:61337
```

The relay page injects a locally generated 256-bit token from:

```text
~/.kolmafia/data/doc_edit/service.token
```

and the API also checks browser Origin against local KoLmafia relay origins.

Open:

```text
http://127.0.0.1:60080/relay/doc_edit.ash
```

For the first KoLmafia checkout smoke, run:

```text
call doc_edit_cli.ash help
call doc_edit_cli.ash status
```

Then start `kol-doc-edit serve`, refresh the relay page, and use **SESSION → CAPTURE TAIL** to verify the emitted gCLI correlation marker appears in `active_session.<player>`.

## gCLI command

Use the script directly:

```text
call doc_edit_cli.ash help
```

or create a normal KoLmafia alias:

```text
alias docedit => call doc_edit_cli.ash %%
```

Then:

```text
docedit status
docedit snapshot 250
docedit read data/doc_edit.md
docedit convert data/doc_edit.md | readme.html/doc_edit.html
docedit convert data/doc_edit.md => readme.html/doc_edit.html
docedit sql SELECT id,action,status,target FROM events ORDER BY id DESC LIMIT 20
```

`|` is parsed by `doc_edit_cli.ash` as a **document routing separator**. `=>` is supported too and is less visually confusable with a shell pipe.

### Path grammar

Virtual paths resolve only inside KoLmafia text roots:

```text
data/foo.md          -> ~/.kolmafia/data/foo.md
relay/foo.html       -> ~/.kolmafia/relay/foo.html
scripts/foo.ash      -> ~/.kolmafia/scripts/foo.ash
readme.html/foo.html -> ~/.kolmafia/data/doc_edit/foo.html
llm-session/...      -> ~/.kolmafia/data/doc_edit/llm-session/...
```

Absolute paths are accepted only if they still resolve under `data/`, `relay/`, or `scripts/`. `..`/symlink escapes are rejected by canonical-path checks.

## Login status artifact

`doc_edit_login.ash`:

1. emits a unique `KOL_DOC_EDIT_GCLI|<player>|<id>` marker to gCLI;
2. writes read-only character status to `data/doc_edit/system-status.json`;
3. queues a `login-sync` job;
4. the Python service notices the job/status file;
5. the service tails the active session and checks for the marker;
6. it writes:

```text
~/.kolmafia/data/doc_edit/agent-status.md
~/.kolmafia/data/doc_edit/agent-status.html
~/.kolmafia/data/doc_edit/agent-status.json
```

If you have no existing KoLmafia `loginScript`, set it to `doc_edit_login.ash`.

If you already have a login script, **do not overwrite it**. Call `doc_edit_login.ash` from your existing login script.

## Session evidence

Python resolves:

```text
~/.kolmafia/sessions/active_session.<player>
```

and copies the last requested lines to:

```text
${TMPDIR:-/tmp}/kol-doc-edit/<player>/active-session.tail.txt
```

It also archives the same evidence under:

```text
~/.kolmafia/data/doc_edit/llm-session/state/memory/logs/doc/
```

A marker match sets `marker_seen=true` / `gcli_verified=1` in SQLite.

This proves that the **gCLI bridge path emitted the marker**. It does not, by itself, prove that some unrelated KoL mutation succeeded.

## Conversion model

The bridge uses a Markdown-like intermediate representation.

### Inputs / outputs

| Format | Read | Write | Notes |
|---|---:|---:|---|
| `.md` | yes | yes | canonical LLM-friendly form |
| `.txt` | yes | yes | minimal markup |
| `.html` | yes | yes | HTML is converted through MarkItDown when available |
| `.html5` | yes | yes | human-facing single-file artifact |
| `.json` | yes | yes | pretty/structured document envelope |
| `.xml` | yes | yes | structured document envelope |
| `.ash` | yes | yes | existing ASH text can be edited; prose→ASH becomes comments only |

### Important `.ash` rule

Cross-converting prose/Markdown/HTML **to** `.ash` does *not* generate executable ASH. The output is a block-comment document container. This prevents a document conversion from silently becoming a runnable script.

Text-editing an existing `.ash` is supported, but execution remains outside this project.

## Edit API

Relay edits are two-phase by default.

A request with:

```json
{
  "path": "scripts/example.ash",
  "mode": "replace_literal",
  "find": "old text",
  "replace": "new text",
  "expected_sha256": "...",
  "confirm": false
}
```

returns a unified diff and proposed new hash without writing.

Set:

```json
"confirm": true
```

to make an atomic write. The original is first copied to:

```text
data/doc_edit/llm-session/state/memory/logs/doc/backups/
```

`expected_sha256` provides optimistic locking so an agent does not overwrite a file that changed after it was read.

Modes:

```text
replace_literal
replace_first
regex
append
overwrite
```

## SQLite

Database:

```text
~/.kolmafia/data/doc_edit/llm-session/state/memory/doc_edit.sqlite3
```

Tables:

```text
events
session_evidence
artifacts
kv_state
```

Examples:

```bash
kol-doc-edit query \
  "SELECT id,actor,action,status,target,gcli_verified FROM events ORDER BY id DESC LIMIT 50"
```

The query API accepts only `SELECT` or `WITH` and also enables SQLite `PRAGMA query_only=ON` for the connection.

## Python CLI

Preview conversion:

```bash
kol-doc-edit convert data/doc_edit.md readme.html/doc_edit.html
```

Write it:

```bash
kol-doc-edit convert data/doc_edit.md readme.html/doc_edit.html --write
```

Capture session evidence:

```bash
kol-doc-edit session-tail --player doncannoli --lines 300
```

Manually process queued ASH jobs:

```bash
kol-doc-edit process-jobs
```

Generate status artifacts:

```bash
kol-doc-edit status-artifact
```

## JS / TypeScript

Typed client:

```text
web/src/client.ts
```

plain ESM build:

```text
web/dist/client.js
```

The relay page uses the same API contract.

## Smoke test

```bash
./scripts/smoke.sh
```

It checks:

- Python compilation;
- path guard behavior;
- format conversion;
- non-executable prose→ASH conversion;
- preview → backup → atomic text edit;
- read-only SQLite enforcement;
- JS syntax;
- basic ASH structural balance.

A real KoLmafia install should still perform the final ASH compile/runtime smoke:

```text
call doc_edit_cli.ash help
call doc_edit_cli.ash status
```

Then start the Python service and confirm that the gCLI marker appears in a captured active-session tail.

## Reference ideas used

- **Microsoft MarkItDown** — narrow conversion API, LLM-oriented Markdown output, explicit I/O-security concerns.
- **MrFizzyBubbs/pymafia** — useful reference for the Python↔KoLmafia boundary and wrapped ASH access; this project intentionally does not expose pymafia as a second mutation path.
- **O’Reilly HTMLBook** — semantic HTML/document structure as a durable text artifact.
- **nexu-io/html-anything** — HTML as a human-facing final artifact while agents work from structured intermediate content.

## License

MIT.
