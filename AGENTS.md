# Agent Contract

This repository is a local-first document bridge for KoLmafia.

## Authority boundaries

1. `relay/doc_edit.ash` is a UI gateway, not a KoL execution engine.
2. `doc_edit_cli.ash` may gather read-only state, write bridge job files, and emit correlation markers.
3. Python may read/write approved local text roots, convert formats, tail session evidence, create backups, and query its own SQLite database.
4. Python must not call KoLmafia mutation APIs, pymafia mutation methods, relay command endpoints, or arbitrary shell commands.
5. `active_session.<player>` is evidence that a gCLI path ran; it is not execution authority.
6. A successful service response is not proof of a KoL state transition.
7. Preserve file hashes, backups, correlation IDs, and event rows for every write.

## Safe edit workflow

Read → record SHA-256 → prepare diff → preview → explicit `confirm=true` → backup → atomic write → record SQLite event.

## Supported text surfaces

`.md`, `.ash`, `.html`, `.html5`, `.txt`, `.xml`, `.json`.

Converting prose *to* `.ash` deliberately produces a non-executable block-comment container. Editing an existing `.ash` file is allowed as text, but nothing in this project runs the edited file.
