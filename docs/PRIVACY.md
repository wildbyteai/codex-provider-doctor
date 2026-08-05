# Privacy model

Codex Provider Doctor is designed for local diagnosis without collecting configuration content that is not needed for the result.

## Data it may read

- Codex TOML configuration layers selected by the command.
- The model catalog JSON referenced by the effective `model_catalog_json` value.
- Whether the provider environment variable named by `env_key` is present and non-empty. The value is never copied.
- Redacted status output from `codex --version`, `codex login status`, and `codex plugin list --json`.
- SQLite schema metadata and aggregate task counts grouped by `model_provider` and archive state from a compatible local `threads` table.

## Data it does not read or report

- Contents of `$CODEX_HOME/auth.json`.
- Token, cookie, authorization header, environment-variable, or MCP-secret values.
- Complete provider URLs. Reports keep only the parsed hostname.
- Plugin names or identifiers. Reports keep only the aggregate inventory count and the exact Chrome installed/enabled result.
- Task title, first message, preview, transcript, rollout content, dynamic tool schema, or memory content.
- Browser history or Chrome profile data.

## Paths

Configuration-layer and model-catalog paths are reported because locating the winning file is part of the diagnosis. The task database path is normalized to `$CODEX_HOME/...` so a shared report does not expose the user's home-directory name.

## Network

The tool itself does not upload reports or call remote diagnostic services. A configured local Codex command may use its own normal runtime behavior, but the probes used here are local status commands and their raw output is discarded after extracting approved fields.

## Database access

Candidate database filenames are discovered under `$CODEX_HOME` and `$CODEX_HOME/sqlite`; the tool does not assume a fixed name. A candidate is accepted only when its schema contains `threads.model_provider`.

SQLite is opened with URI `mode=ro` and `PRAGMA query_only = ON`. Only aggregate counts are returned: total, current-provider, other-provider, and per-provider total/unarchived/archived counts. Version `0.1.0` contains no database update code.
