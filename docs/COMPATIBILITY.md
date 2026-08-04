# Compatibility rules

Compatibility advice must be tied to an observed version and interface combination. It must never become a silent default for every third-party provider.

## `deepseek-direct-tools-2026-08-03`

Observed scope:

- Date: 2026-08-03
- Codex: `0.146.0-alpha.9.2`
- Provider: one third-party Responses-compatible API combination
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
- The user must select the rule explicitly. It is not applicable to the built-in OpenAI provider or to a provider whose active wire API is not `responses`.
- `supports_search_tool` is model-catalog metadata and is not the same setting as top-level `web_search`.
- Direct tool exposure can increase the initial tool list and context use.
- A different Codex version produces a warning even when all three values match.
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
