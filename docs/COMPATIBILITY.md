# Compatibility rules

Compatibility advice must be tied to an observed version and interface combination. It must never become a silent default for every third-party provider.

## Windows Desktop model picker: manual reminder only

The doctor does not automatically inspect the final Windows Desktop picker or the remote `available_models` response. It therefore never infers this defect from a valid catalog alone.

When `--problem model-name-incorrect` finds the intended longest active slug-prefix match and a non-empty `display_name`, the JSON solution adds `windows_desktop_picker_reminder` with `automatic_detection: false`. Codex retries once after removing a single simple model namespace; if neither lookup matches, it uses fallback metadata rather than blocking the request. The reminder becomes actionable only after manual evidence also confirms:

1. App Server `model/list` returns the active model.
2. The Windows Desktop picker omits it or shows `Custom`, `Custom High/Max`, or incorrect metadata.
3. A real request or CLI invocation is used separately to verify actual routing.

Under that evidence chain, additional Desktop filtering is the leading known compatibility suspect, so repeatedly editing a valid catalog, clearing caches, or restarting is not the primary response. The safe workarounds are a `config.toml` switcher, `codex -m <slug>` when the active Provider is already correct, or separate Profiles when switching Providers. The UI label is never treated as proof of the routed model.

The dated reference snapshot is 2026-08-05 and records `openai/codex#19694` plus `openai/codex#36582`. Current issue status must be rechecked before saying the defect remains unresolved. The doctor never patches `app.asar`; experimental application patches require a backup, explicit confirmation, and a recovery path.

## General Chrome symptom triage

When the user explicitly reports that Chrome is unavailable under a third-party model, run:

```shell
codex-provider-doctor --problem chrome-unavailable
```

`--symptom chrome-plugin-unavailable` remains a lower-level compatibility trigger for existing integrations; it does not replace the user-facing recovery guide.

This check applies to any selected third-party `responses` provider; it is not limited to DeepSeek or to a dated compatibility rule. In the Codex source snapshot dated 2026-08-06, [`spec_plan.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/spec_plan.rs) maps `supports_search_tool` to `search_tool_enabled`, while [`mcp_tool_exposure.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/mcp_tool_exposure.rs) keeps MCP tools **Direct** when that flag is false and can make eligible namespace MCP tools **Deferred** behind `tool_search` when it is true. The doctor reads the selected catalog entry's actual value without treating it as the complete Chrome switch:

- `true`: eligible namespace MCP/plugin tools can move out of the initial tool list and behind `tool_search`. If the selected third-party model or Responses provider cannot expose or use that discovery path correctly, Chrome may disappear or become uncallable. For a reported Chrome failure, this is the leading static configuration compatibility suspect, but it does not prove a unique root cause.
- `false`: MCP/plugin tools do not enter that `tool_search`-based Deferred path. This matches the observed working DeepSeek combination and the public reproduction in [`openai/codex#36382`](https://github.com/openai/codex/issues/36382). It does not prove that Chrome is installed, enabled, authorized, or callable.
- missing or non-Boolean: report that the static field is unavailable and keep the runtime cause unverified.

The JSON report records this under `compatibility.symptom_assessments`. When the user reports Chrome unavailable and the selected third-party Responses model has `supports_search_tool = true`, the doctor reports a warning and proposes only a backed-up, controlled comparison to `false`; it never edits the catalog automatically. A live smoke test remains stronger than static configuration. Never infer or change top-level `web_search`, and never recommend reinstalling a plugin merely because `codex plugin list --json` failed.

Each assessment records the official-source date, the locally detected Codex version when available, the namespace-tools state as not checked, and `runtime_verification_required: true`. If the installed version was not detected or differs from the cited source snapshot, the branch inference remains dated static evidence rather than a claim about the user's live runtime.

This general symptom triage is independent of the dated rule below. The dated DeepSeek case provides the observed `false` comparison value, while the current report still keeps plugin state, authorization, the new-task tool list, and a live invocation as separate evidence.

## `deepseek-direct-tools-2026-08-03`

Observed scope:

- Date: 2026-08-03
- Codex: `0.146.0-alpha.9.2`
- Provider: one third-party DeepSeek Responses-compatible API combination
- Symptom: direct tool, Skill, and Chrome availability differed from the expected task tool list

Compared model-catalog metadata:

```json
{
  "tool_mode": "direct",
  "supports_search_tool": false,
  "use_responses_lite": false
}
```

Important boundaries:

- This rule proposes a diff and never writes it.
- The user must select the rule explicitly.
- The selected catalog model must itself be a DeepSeek model on a third-party `responses` provider. The rule is not applicable to the built-in OpenAI provider, a non-Responses provider, or an official model merely stored in the same custom catalog.
- Human reports explicitly state when the selected model or Provider is outside this scope. Official models keep their own `supports_search_tool` value, including `true`.
- `supports_search_tool` is model-catalog metadata and is not the same setting as top-level `web_search`.
- `supports_search_tool = false` is scoped to the selected third-party DeepSeek case. It is not a recommendation to change official models from `true`.
- `tool_mode = direct` is assessed as `review_if_symptomatic`. A differing `code_mode_only` value is recorded in `observed_differences`, but it is excluded from `suggested_changes` when direct tools already work and no matching symptom is established.
- Direct tool exposure can increase the initial tool list and context use, which is another reason not to require the change without symptoms.
- `use_responses_lite = true` omits hosted Responses tools; it is not the Chrome-plugin switch. `false` remains a suggested change when the selected DeepSeek case differs.
- When the rule is applicable, a different Codex version produces a warning even when all three values match.
- After any manual edit, fully restart Codex, create a new task, and test Skill loading, Chrome, Web Search, and other plugins separately.
- A passing Chrome test does not prove that every connector or MCP server is authorized.

## Adding a rule

A new rule needs:

1. Exact or bounded Codex version information.
2. A sanitized provider/interface description.
3. The observed symptom and independent reproduction.
4. The smallest field-level diff that changes the result.
5. A test proving that the tool reports, but does not apply, the diff.
6. A statement of what remains unknown.

## Report fields

Each selected rule reports all three fields through `field_assessments`:

- `aligned`: the observed value matches the dated case.
- `change_recommended`: the field is included in `suggested_changes`.
- `review_if_symptomatic`: the value differs, but the doctor does not claim a required change without the matching runtime symptom.

`observed_differences` preserves every raw field difference. `suggested_changes` contains only changes the dated rule currently recommends. This distinction is intentional and is documented in the Unreleased compatibility notes.
