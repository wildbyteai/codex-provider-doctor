# Compatibility rules

Compatibility advice must be tied to an observed version and interface combination. It must never become a silent default for every third-party provider.

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
- `use_responses_lite = false` remains a suggested change when the selected DeepSeek case differs.
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
