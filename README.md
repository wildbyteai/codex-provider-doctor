# Codex Provider Doctor

[简体中文](README.zh-CN.md)

Codex Provider Doctor is a read-only companion to the built-in `codex doctor` command. It focuses on third-party model-provider setups where Codex can still chat, but skills, model names, Chrome, plugins, or older tasks behave differently.

Status: alpha. The tool reports findings and suggested diffs. It does not edit Codex configuration or task databases.

## Use as a Codex skill (recommended)

Send the repository link to Codex:

```text
Install this Skill for me: https://github.com/wildbyteai/codex-provider-doctor
```

Start a new task after installation; restart Codex if the skill list has not refreshed. Then ask:

```text
Check why skills, model names, Chrome, plugins, or older tasks changed after I configured a third-party API in Codex.
```

Codex handles the repository path, Skill name, and installer arguments. If the current task does not match the Skill, explicitly ask it to use `$codex-provider-doctor`. Codex then runs the bundled read-only checker and explains the result. The skill and CLI share the same source, so the skill does not globally install the package or create a virtual environment. Python 3.11 or later is currently required.

## What it checks

- The effective system, user, profile, trusted-project, and command-line configuration layers.
- The actual `model_catalog_json` selected by those layers. It does not assume a filename such as `models.custom.json`.
- Catalog model count, without dumping every model entry.
- Relative catalog paths, resolved from the config file that declared the winning value.
- The active `model` and its exact `models[].slug` match.
- Model display metadata, `tool_mode`, `supports_search_tool`, `use_responses_lite`, context window, and compact limits.
- Provider authentication conflicts involving `requires_openai_auth`, `env_key`, command authentication, or a direct bearer token, with acknowledged intent kept separate from security risk.
- Official Codex login state plus a plugin count and exact Chrome status when the redacted, read-only CLI probe succeeds; otherwise the inventory remains explicitly unverified. Other plugin names are not reported.
- Chrome installation and enablement signals, followed by a manual acceptance checklist.
- Read-only aggregate task counts grouped by `model_provider`, including total, unarchived, and archived rows.

## The four common symptoms

1. Skills no longer appear or cannot be invoked.
2. The model picker shows an unclear slug instead of a useful display name.
3. The Chrome plugin is installed but unavailable to a new Codex task.
4. Older tasks appear to be missing after switching providers.

The first three usually require inspecting both the effective `config.toml` and the model catalog JSON it references. The fourth can be a separate local-index issue: task files may still exist while their database rows remain bound to another provider.

## How plugin evidence is interpreted

The CLI plugin probe is one evidence source, not the final authority on runtime availability. Evidence should be read in this order:

1. A successful live invocation.
2. The current task exposing the expected tool, or the Settings or Plugins page showing it.
3. A successful `codex plugin list --json` result.
4. Static configuration and manual inference.

If the CLI command fails or returns an unsupported format, the plugin inventory is `unverified`. The finding is informational and does not change exit code `0` by itself. A successful CLI inventory that does not confirm Chrome is also lower-priority evidence, not proof of a runtime failure. Do not reinstall plugins or clear caches when the UI or a live invocation already works; consider repair only when those stronger checks also fail.

## Safety model

- Read-only by default and in version `0.1.0`.
- Never opens or parses `$CODEX_HOME/auth.json`; it only checks whether the file exists.
- Never prints token values, cookies, request headers, MCP environment values, or complete private endpoint URLs.
- Opens compatible SQLite task databases in read-only mode and only runs aggregate counts.
- Never updates task rows, changes provider bindings, installs plugins, or edits configuration.
- Does not upload configuration, reports, or logs.

## Optional CLI installation

Python 3.11 or later is required.

```shell
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Run

Basic read-only diagnosis:

```shell
codex-provider-doctor
```

Machine-readable report:

```shell
codex-provider-doctor --json
```

Select the same profile used to launch Codex:

```shell
codex-provider-doctor --profile work
```

After the user explicitly confirms that official sign-in plus an explicit provider token is intentional, record that intent without hiding the plaintext-token warning:

```shell
codex-provider-doctor \
  --acknowledge provider.auth.openai_with_direct_token
```

Compare the selected model with one dated compatibility case:

```shell
codex-provider-doctor \
  --compat-rule deepseek-direct-tools-2026-08-03
```

The compatibility rule proposes, but never applies:

```json
{
  "tool_mode": "direct",
  "supports_search_tool": false,
  "use_responses_lite": false
}
```

This combination was observed with Codex `0.146.0-alpha.9.2` and one third-party DeepSeek Responses API setup. The rule applies only when the selected catalog model is a DeepSeek model on that kind of third-party provider. An official model remains outside the rule even when it appears in the same custom catalog.

The report evaluates all three fields, but it does not treat them identically:

- `supports_search_tool = false`: recommended for the selected third-party DeepSeek case; it is not a recommendation for official models.
- `use_responses_lite = false`: recommended for the same dated case.
- `tool_mode = direct`: `review_if_symptomatic`; keep `code_mode_only` when direct tools already work and no matching symptom has been observed.

`supports_search_tool` is model-catalog metadata and is not the same setting as top-level `web_search`.

## Authentication is three separate questions

`requires_openai_auth = true` means that the selected provider uses OpenAI authentication. Codex then ignores that provider's `env_key`. It is not a general switch for preserving an official ChatGPT login while another provider uses its own API key.

Some observed setups combine `requires_openai_auth = true` with `experimental_bearer_token` to keep the official sign-in surface while supplying an explicit token for provider requests. The doctor reports the combination as `info` / `unverified` until the user confirms the intent. After explicit confirmation, pass `--acknowledge provider.auth.openai_with_direct_token`; the finding becomes acknowledged and intentional instead of a suspected root cause. The independent plaintext-token warning remains.

Diagnose these independently:

1. Official Codex sign-in: `codex login status`.
2. Third-party provider credentials: the active `[model_providers.<id>]` block.
3. Plugin, connector, MCP, and Chrome installation or authorization.

## Why older tasks can disappear

The doctor looks for a compatible local database by schema, not by a hard-coded filename. It reports aggregate counts for every stored `model_provider`: total, unarchived, and archived. If unarchived rows use a different provider, it also explains why provider-filtered builds may not show them.

This is an observed local implementation detail, not a promise that every Codex version filters history the same way. See [History and provider bindings](docs/HISTORY-PROVIDER.md) before considering any database repair.

## Use with the built-in doctor

Run the official diagnostic first when available:

```shell
codex doctor
```

Then use this project for provider-specific catalog resolution, compatibility metadata, Chrome/plugin checks, and history-provider mismatch reporting.

## Finding levels and JSON compatibility

`schema_version` remains `1`. Existing top-level fields and the plugin `probe` value are retained. This update adds fields rather than exposing raw evidence:

- Every finding now has `severity`, `status`, `category`, and `intentional`.
- Summary adds `info`, `unverified`, `acknowledged`, and `intentional` counts.
- Plugin reports add `inventory_status`; command failure, invalid JSON, or an unsupported JSON shape remains `probe: "failed"` with an honestly `unverified` inventory.
- Catalog reports add `model_count`.
- History reports add `provider_counts`.
- Compatibility reports add `field_assessments` and `observed_differences`. `suggested_changes` now excludes a symptom-only `tool_mode` difference.
- JSON findings keep diagnostic generation order for compatibility. Priority sorting is applied only when rendering the human-readable report.

Exit codes still depend only on errors and warnings: `0` for neither, `1` for warnings, `2` for errors, and `3` when the doctor cannot finish safely.

## Documentation

- [Chinese quick start](README.zh-CN.md)
- [Agent diagnosis prompt](prompts/agent-doctor.zh-CN.md)
- [Privacy model](docs/PRIVACY.md)
- [Compatibility rules](docs/COMPATIBILITY.md)
- [History and provider bindings](docs/HISTORY-PROVIDER.md)
- [Sanitized examples](examples/README.md)

## Development

```shell
python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts tests
```

## License

MIT. See [LICENSE](LICENSE).
