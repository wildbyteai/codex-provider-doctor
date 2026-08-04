# History and provider bindings

## What “history disappeared” can mean

An older task can still have its rollout file on disk while the local task index stores a different `model_provider` from the provider currently selected in `config.toml`.

In Codex builds or surfaces that filter task inventory by Provider, those rows may stop appearing in the current list. That looks like deletion, but it can be an indexing or filtering mismatch instead.

This is based on observed local database structure and behavior. It is not an official guarantee that every Codex version or surface applies the same filter.

## What the doctor checks

The tool does not assume the database is named `state_5.sqlite`.

It scans database-looking files directly under `$CODEX_HOME` and `$CODEX_HOME/sqlite`, opens candidates in read-only mode, and accepts only a schema containing `threads.model_provider`. It then reports aggregate counts for:

- all task rows;
- rows bound to the current Provider;
- rows bound to another Provider;
- unarchived rows bound to another Provider.

It does not select titles, messages, previews, task bodies, or rollout content.

## Why there is no one-click database repair

Changing every row to the current Provider can make tasks visible again in one observed setup, but it is riskier than editing a catalog JSON:

- Codex may be running and writing through SQLite WAL files.
- Database schemas and filtering behavior can change between versions.
- A task can contain model or tool assumptions tied to its original Provider.
- A broad update can change archived, child-agent, automated, or otherwise unrelated tasks.
- Copying only the main `.sqlite` file can produce an incomplete backup when `-wal` or `-shm` sidecars exist.

Version `0.1.0` therefore performs no update.

## Minimum safe procedure for a future repair tool

Any future migration command must, at minimum:

1. Require the user to quit every Codex or ChatGPT desktop process using the database.
2. Resolve the exact active database by schema, not filename alone.
3. Back up the database, `-wal`, `-shm`, and relevant session/rollout directories.
4. Show a dry-run count grouped by old Provider, current Provider, archived state, and task source.
5. Require a second confirmation naming the old and new Provider IDs and the expected row count.
6. Run a single scoped transaction, never an unqualified update.
7. Run SQLite integrity checks and compare the changed-row count with the dry run.
8. Reopen Codex and verify a sample before removing any backup.
9. Provide a tested rollback path.

Until that design exists, use the doctor report as evidence and treat database repair as a separate, explicitly authorized operation.
