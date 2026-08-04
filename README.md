# Codex Provider Doctor

[简体中文](README.zh-CN.md)

Codex Provider Doctor is a read-only companion to the built-in `codex doctor` command. It focuses on third-party model-provider setups where Codex can still chat, but skills, model names, Chrome, plugins, or older tasks behave differently.

Status: alpha. The tool reports findings and suggested diffs. It does not edit Codex configuration or task databases.

## What it checks

- The effective system, user, profile, trusted-project, and command-line configuration layers.
- The actual `model_catalog_json` selected by those layers. It does not assume a filename such as `models.custom.json`.
- Relative catalog paths, resolved from the config file that declared the winning value.
- The active `model` and its exact `models[].slug` match.
- Model display metadata, `tool_mode`, `supports_search_tool`, `use_responses_lite`, context window, and compact limits.
- Provider authentication conflicts involving `requires_openai_auth`, `env_key`, command authentication, or a direct bearer token.
- Official Codex login state plus a plugin count and exact Chrome status through redacted, read-only CLI probes; other plugin names are not reported.
- Chrome installation and enablement signals, followed by a manual acceptance checklist.
- Read-only aggregate counts for local tasks whose stored `model_provider` differs from the active provider.

## The four common symptoms

1. Skills no longer appear or cannot be invoked.
2. The model picker shows an unclear slug instead of a useful display name.
3. The Chrome plugin is installed but unavailable to a new Codex task.
4. Older tasks appear to be missing after switching providers.

The first three usually require inspecting both the effective `config.toml` and the model catalog JSON it references. The fourth can be a separate local-index issue: task files may still exist while their database rows remain bound to another provider.

## Safety model

- Read-only by default and in version `0.1.0`.
- Never opens or parses `$CODEX_HOME/auth.json`; it only checks whether the file exists.
- Never prints token values, cookies, request headers, MCP environment values, or complete private endpoint URLs.
- Opens compatible SQLite task databases in read-only mode and only runs aggregate counts.
- Never updates task rows, changes provider bindings, installs plugins, or edits configuration.
- Does not upload configuration, reports, or logs.

## Install from source

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

This combination was observed with Codex `0.146.0-alpha.9.2` and one third-party API setup. It is a troubleshooting case, not a universal default. `supports_search_tool` is also not the same setting as top-level `web_search`.

## Authentication is three separate questions

`requires_openai_auth = true` means that the selected provider uses OpenAI authentication. Codex then ignores that provider's `env_key`. It is not a general switch for preserving an official ChatGPT login while another provider uses its own API key.

Some observed setups combine `requires_openai_auth = true` with `experimental_bearer_token` to keep the official sign-in surface while supplying an explicit token for provider requests. The doctor reports this as version-sensitive and warns that the token is stored in plaintext; it does not automatically label the pair as a fatal conflict.

Diagnose these independently:

1. Official Codex sign-in: `codex login status`.
2. Third-party provider credentials: the active `[model_providers.<id>]` block.
3. Plugin, connector, MCP, and Chrome installation or authorization.

## Why older tasks can disappear

The doctor looks for a compatible local database by schema, not by a hard-coded filename. If unarchived task rows use a different `model_provider`, it reports the count and explains why provider-filtered builds may not show them.

This is an observed local implementation detail, not a promise that every Codex version filters history the same way. See [History and provider bindings](docs/HISTORY-PROVIDER.md) before considering any database repair.

## Use with the built-in doctor

Run the official diagnostic first when available:

```shell
codex doctor
```

Then use this project for provider-specific catalog resolution, compatibility metadata, Chrome/plugin checks, and history-provider mismatch reporting.

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
python3 -m compileall -q src tests
```

## License

MIT. See [LICENSE](LICENSE).
