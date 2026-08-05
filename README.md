# Codex Provider Doctor

[简体中文](README.zh-CN.md)

Codex Provider Doctor is a read-only recovery guide for the five problems users actually hit after switching Codex to a third-party model Provider: keeping the official sign-in, restoring plugins and Skills, fixing model names, recovering older tasks, and restoring Chrome calls.

Status: alpha. The tool reports findings and suggested diffs. It does not edit Codex configuration or task databases.

## Fix the five problems first

1. **Keep the official sign-in**: only for a custom third-party Provider that intentionally uses a direct token, put `requires_openai_auth = true` and `experimental_bearer_token` in that Provider's `[model_providers.<id>]` table. If `env_key/auth` already exists, migrate instead of stacking methods. Separately confirm that `codex login status` reports ChatGPT sign-in. Plaintext-token risk remains an independent warning.
2. **Restore plugins, official plugins, or Skills**: restart Codex completely and open a new task, then separate local Skill installation, Plugins/Settings enablement and authorization, and actual tool exposure. A failed CLI inventory is not a reason to reinstall.
3. **Fix the model name**: identify the effective `model_catalog_json`, make top-level `model` match exactly one `models[].slug`, and inspect that entry's `display_name`. When those fields are already correct, do not edit them again. If App Server `model/list` returns the model on Windows Desktop but the picker still omits it or shows only `Custom`, prioritize the matching Desktop-picker defect and use a config switcher, CLI, or Profiles as safe workarounds. The doctor provides a conditional reminder; it does not observe the UI or remote allowlist automatically.
4. **Recover older tasks**: aggregate the Providers stored on affected tasks. First switch back to those Providers, use an all-provider view when available, or update Codex. Consider binding migration only after quitting Codex, backing up the database plus WAL/SHM, showing the exact field diff, and obtaining another confirmation.
5. **Restore Chrome calls**: inspect the selected model's `supports_search_tool` early, but do not treat it as a complete exposure switch. In the 2026-08-05 official source, `false` forces the namespace-tool planning branch to Direct; `true` permits Deferred only when namespace tools are also enabled. Actual Chrome declarations and the live task tool list still require verification. Then check Plugins/Settings, official sign-in, the Chrome profile, connector authorization, and a live invocation.

## Default report shape

Instead of a loose technical narrative, every selected problem uses the same health-check card:

```text
1. Check [status]
   Current result: what is happening now
   Exact locations / key parameters: which file or UI surface, which field, and its redacted current value
   Controlled by: which settings, sign-in state, or runtime state decides it
   Desired state: what normal looks like
   How to change: ordered recovery actions
   How to verify: the observable acceptance check
```

The default report uses plain language and directly names the concrete locations and parameters needed for recovery. Paths are normalized to safe forms such as `$CODEX_HOME/...` and `$PROJECT_ROOT/...`; tokens are shown only as configured or not configured. Use `--details` for complete origin layers and technical evidence.

## Use as a Codex skill (recommended)

Send the repository link to Codex:

```text
Install this Skill for me: https://github.com/wildbyteai/codex-provider-doctor
```

Start a new task after installation; restart Codex if the skill list has not refreshed. Then ask:

```text
Check how to keep my official sign-in and fix plugins, Skills, model names, older tasks, and Chrome after I switched Codex to a third-party API.
```

Codex handles the repository path, Skill name, and installer arguments. If the current task does not match the Skill, explicitly ask it to use `$codex-provider-doctor`. Codex then runs the bundled read-only checker and explains the result. The skill and CLI share the same source, so the skill does not globally install the package or create a virtual environment. Python 3.11 or later is currently required.

The Skill uses the canonical human-readable report directly instead of asking an Agent to freely summarize raw JSON. Every emitted health-check card and all six fields must be preserved. Machine integrations may still use `--json` and should render `solutions.health_checks` in order.

If permissions require running from a temporary repository copy, keep the real `CODEX_HOME`, the original project working directory, and the same Profile. Pass `--cwd` when a launcher changes directories. Do not claim the result is unaffected until those three inputs match, because project configuration and project-Skill coverage can otherwise differ.

## What it checks

- The effective system, user, profile, trusted-project, and command-line configuration layers.
- The actual `model_catalog_json` selected by those layers. It does not assume a filename such as `models.custom.json`.
- Catalog model count, without dumping every model entry.
- Relative catalog paths, resolved from the config file that declared the winning value.
- The active `model` and its exact `models[].slug` match.
- Model display metadata, `tool_mode`, `supports_search_tool`, `use_responses_lite`, context window, and compact limits.
- A conditional Windows Desktop picker reminder when the catalog fields are already valid, keeping catalog, App Server, picker, and live-request evidence separate.
- Five consistent health-check cards covering current result, exact locations/key parameters, controls, desired state, recovery actions, and verification before full technical evidence.
- Counts of locally discovered user and trusted-project Skills without reporting their names. Untrusted-project Skills are not scanned and make coverage explicitly partial.
- Symptom-aware Chrome compatibility triage for any selected third-party Responses model, including the runtime conditions around Direct versus Deferred namespace-tool exposure.
- Provider authentication conflicts involving `requires_openai_auth`, `env_key`, command authentication, or a direct bearer token, with acknowledged intent kept separate from security risk.
- Official Codex login state plus a plugin count and exact Chrome status when the redacted, read-only CLI probe succeeds; otherwise the inventory remains explicitly unverified. Other plugin names are not reported.
- Chrome installation and enablement signals, followed by a manual acceptance checklist.
- Read-only aggregate task counts grouped by `model_provider`, including total, unarchived, and archived rows.

## The five problems this solves

Select one problem for a focused report, or run without `--problem` to see all five:

1. Keep the official sign-in: `--problem keep-official-login`
2. Restore plugins and Skills: `--problem plugins-or-skills-unavailable`
3. Fix the model name: `--problem model-name-incorrect`
4. Recover older tasks: `--problem history-missing`
5. Restore Chrome calls: `--problem chrome-unavailable`

The default human report is a fixed action checklist rather than a diagnostic log. Add `--details` to expand technical diagnoses, configuration layers, field origins, catalog metadata, history aggregates, and all findings.

## How plugin evidence is interpreted

The CLI plugin probe is one evidence source, not the final authority on runtime availability. Evidence should be read in this order:

1. A successful live invocation.
2. The current task exposing the expected tool, or the Settings or Plugins page showing it.
3. A successful `codex plugin list --json` result.
4. Static configuration and manual inference.

If the CLI command fails or returns an unsupported format, the plugin inventory is `unverified`. The finding is informational and does not change exit code `0` by itself. A successful CLI inventory that does not confirm Chrome is also lower-priority evidence, not proof of a runtime failure. Do not reinstall plugins or clear caches when the UI or a live invocation already works; consider repair only when those stronger checks also fail.

When the user explicitly reports that Chrome is unavailable, prefer `--problem chrome-unavailable`; the lower-level `--symptom chrome-plugin-unavailable` flag remains available for existing integrations. In the official source snapshot dated 2026-08-05, `supports_search_tool = false` forces the namespace-tool planning branch to Direct, but does not prove that Chrome itself is directly exposed or present. `true` permits Deferred only when namespace tools are also enabled; otherwise Direct remains possible. The doctor therefore records the field near the front of triage but keeps the actual exposure path, tool declarations, Settings state, and live invocation unverified. It never infers or edits top-level `web_search` from this check.

## Windows Desktop model-picker reminder

This is intentionally not presented as fully automatic detection. The doctor cannot infer the remote `available_models` response from `config.toml` and a model catalog, and it cannot observe the final Desktop picker UI.

Treat additional Desktop picker filtering as the leading known compatibility suspect only when the manual evidence chain is complete:

1. The effective catalog uniquely matches the active `slug` and has a non-empty `display_name`.
2. App Server `model/list` returns that model.
3. The Windows Desktop picker still omits it or shows only `Custom`, `Custom High/Max`, an incorrect name, or incorrect metadata.
4. A real request in a new task or a CLI invocation is still required to prove actual model routing; the UI label is not proof.

As of 2026-08-05, matching reports were recorded in the official OpenAI repository as [#19694](https://github.com/openai/codex/issues/19694) and [#36582](https://github.com/openai/codex/issues/36582). Reports keep this as a dated reference snapshot and require rechecking current issue status before claiming the defect remains unresolved.

Safe workaround order:

1. Use a config switcher to change `model` and `model_provider` in `config.toml`.
2. Run `codex -m <slug>` when the active Provider is already correct; use separate Profiles when switching Providers.
3. Open a new task and send a real request to verify the routed model instead of trusting the Desktop label.
4. Return to Profile, configuration precedence, and provider-request diagnosis only when App Server listing or the real request also fails.

The doctor never patches `app.asar` automatically. Any experimental Desktop patch requires a backup, explicit confirmation, and a recovery path; it is not the default repair.

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

The command above shows all five recovery guides. For one focused problem:

```shell
codex-provider-doctor --problem keep-official-login
codex-provider-doctor --problem plugins-or-skills-unavailable
codex-provider-doctor --problem model-name-incorrect
codex-provider-doctor --problem history-missing
codex-provider-doctor --problem chrome-unavailable
```

Expand the technical evidence only when needed:

```shell
codex-provider-doctor --details
```

Machine-readable report:

```shell
codex-provider-doctor --json
```

`solutions.health_checks` mirrors the default human report. Each entry contains `current_result`, `exact_targets`, `controlled_by`, `desired_state`, `how_to_change`, and `how_to_verify`. Every `exact_targets` entry contains a normalized `location`, a `parameter`, and a redacted `current_value`; user-facing clients should render those fields instead of rebuilding a free-form summary from raw findings.

Select the same profile used to launch Codex:

```shell
codex-provider-doctor --profile work
```

After the user explicitly confirms that official sign-in plus an explicit provider token is intentional, record that intent without hiding the plaintext-token warning:

```shell
codex-provider-doctor \
  --acknowledge provider.auth.openai_with_direct_token
```

The lower-level Chrome symptom flag remains available for existing integrations:

```shell
codex-provider-doctor \
  --symptom chrome-plugin-unavailable
```

After the read-only report finds mismatched history Provider bindings, record a causal conclusion only when the user explicitly confirms it for the current incident:

```shell
codex-provider-doctor \
  --confirm-cause history.provider_mismatch
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

## Keep the official sign-in while using a third-party token

For the confirmed dual-authentication design, `requires_openai_auth` belongs inside the active Provider block, not at the TOML top level:

```toml
model = "vendor-model"
model_provider = "vendor"

[model_providers.vendor]
base_url = "https://provider.example/v1"
wire_api = "responses"
requires_openai_auth = true
experimental_bearer_token = "<third-party-token>"
```

This pattern is for a custom third-party Provider. Do not add it to the built-in `openai` Provider. If the active third-party Provider already uses `env_key` or an `[model_providers.<id>.auth]` command, do not stack the direct-token fields on top: back up the configuration, show one field-level migration diff, remove the old request-authentication method, and add the confirmed dual-authentication fields in the same controlled change.

As of 2026-08-05, the [current Codex provider-authentication path](https://github.com/openai/codex/blob/main/codex-rs/model-provider/src/provider.rs) retains the official ChatGPT/Codex account state with `requires_openai_auth = true`, while the explicit Provider bearer token takes precedence for third-party requests. `--problem keep-official-login` records this intent automatically. The legacy `--acknowledge provider.auth.openai_with_direct_token` form remains supported. Neither form hides the independent plaintext-token warning.

Diagnose these independently:

1. Official Codex sign-in: `codex login status`.
2. Third-party provider request authentication: the active `[model_providers.<id>]` block, where `requires_openai_auth = true` must be placed for this dual-auth design.
3. Plaintext-token risk: whether `experimental_bearer_token` is stored directly in configuration, regardless of acknowledged intent.

Plugin, connector, MCP, and Chrome installation or authorization are a separate runtime capability check after those three authentication questions.

## Why older tasks can disappear

The doctor looks for a compatible local database by schema, not by a hard-coded filename. It reports aggregate counts for every stored `model_provider`: total, unarchived, and archived. If unarchived rows use a different provider, it also explains why provider-filtered builds may not show them.

This is an observed local implementation detail, not a promise that every Codex version filters history the same way. See [History and provider bindings](docs/HISTORY-PROVIDER.md) before considering any database repair.

Without explicit user confirmation, that wording remains causal-neutral. If the user confirms that the mismatch caused the current visibility problem, `--confirm-cause history.provider_mismatch` marks the finding as a confirmed root cause while leaving the database read-only. Any future repair still requires a separate confirmation and a backup of the exact database plus its WAL/SHM sidecars.

## Use with the built-in doctor

Run the official diagnostic first when available:

```shell
codex doctor
```

Then use this project for provider-specific catalog resolution, compatibility metadata, Chrome/plugin checks, and history-provider mismatch reporting.

## Finding levels and JSON compatibility

`schema_version` remains `1`. Existing top-level fields and the plugin `probe` value are retained. This update adds fields rather than exposing raw evidence:

- Every finding now has `severity`, `status`, `category`, and `intentional`.
- Summary adds `info`, `unverified`, `acknowledged`, `confirmed_causes`, and `intentional` counts.
- Plugin reports add `inventory_status`; command failure, invalid JSON, or an unsupported JSON shape remains `probe: "failed"` with an honestly `unverified` inventory.
- Catalog reports add `model_count`.
- History reports add `provider_counts`.
- Reports add `skills` counts and a `solutions` section for the selected five-problem recovery guides; the sign-in guide carries independent official-login verification state, and the history guide carries aggregate counts for each affected old Provider.
- Compatibility reports add `symptom_assessments` for runtime-dependent Direct/Deferred Chrome triage plus `field_assessments` and `observed_differences` for selected dated rules. `suggested_changes` excludes symptom-only observations.
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
