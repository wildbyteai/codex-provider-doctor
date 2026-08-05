---
name: codex-provider-doctor
description: Diagnose Codex third-party model Provider setups with a bundled read-only checker. Use when skills stop working, a model name shows only a slug, Chrome or plugins are unavailable, older tasks appear missing after changing Provider, or the user needs help locating the effective config.toml, its actual model catalog JSON, supports_search_tool, requires_openai_auth, login state, or history Provider bindings.
---

# Codex Provider Doctor

Run the bundled doctor yourself. Do not ask the user to copy or execute terminal commands.

## Run the diagnosis

1. Keep the user's current project as the working directory so trusted project configuration is evaluated correctly.
2. Resolve the skill directory from this `SKILL.md`, then run its bundled entry point with Python 3.11 or later:

   ```text
   python3 <skill-directory>/scripts/run_skill.py --json
   ```

   Use `python` instead of `python3` only after confirming that it is Python 3.11 or later.
3. Pass `--profile <name>` only when the active Codex Profile is known from the current task or the user. If it is unknown, run the baseline diagnosis and clearly mark the Profile as unconfirmed; do not guess.
4. Add `--compat-rule deepseek-direct-tools-2026-08-03` only when the user explicitly asks about that dated DeepSeek compatibility case or asks to compare the observed `supports_search_tool: false` configuration. The rule applies only when the selected catalog model is a DeepSeek model on a third-party Responses provider. It does not apply to an official model merely because that model appears in the same custom catalog.
5. Add `--acknowledge provider.auth.openai_with_direct_token` only after the user explicitly confirms that `requires_openai_auth = true` plus `experimental_bearer_token` is intentional. This records intent; it does not suppress the separate plaintext-token warning.
6. Preserve the program's exit code interpretation:
   - `0`: no detected errors or warnings. Information, unverified CLI evidence, or acknowledged intent does not change exit code 0 by itself.
   - `1`: warnings need review.
   - `2`: configuration errors were detected.
   - `3`: the doctor could not finish safely.

The entry point loads the source bundled with this skill. Do not install the package globally or create a virtual environment. If the source is unavailable, report that the Skill installation is incomplete and reinstall the complete repository Skill.

## Explain the result

Reply in the user's language; default to Chinese. Lead with the error count, warning count, and the most likely cause. Then cover only the useful evidence:

1. Effective configuration layers and the source of each important field.
2. The actual `model_catalog_json` path, including how a relative path was resolved.
3. The model-catalog entry count plus the uniquely matched model and its display and compatibility fields.
4. Provider authentication, kept separate from official ChatGPT/Codex login state.
5. Skill, plugin, and Chrome findings plus any remaining manual checks.
6. Aggregate history Provider counts, including per-`model_provider` total, unarchived, and archived counts, without task titles or message content.
7. Suggested field-level changes that were not applied.

Do not paste the entire JSON report unless the user requests it. Translate findings into plain language suitable for a non-technical user.

Rank plugin and Chrome evidence from strongest to weakest:

1. A requested live smoke test or successful real invocation.
2. The current task exposing the expected tool, or the user confirming it on the Settings or Plugins page.
3. A successful `codex plugin list --json` probe.
4. Static configuration and manual inference.

A failed or unparseable CLI plugin probe means the checker could not verify the inventory. It does not prove that a plugin is absent or broken, is reported as `info` / `unverified`, and does not change exit code 0 by itself. A successful CLI inventory that does not confirm Chrome is also lower-priority evidence, not a runtime failure. If stronger evidence shows the plugin is visible or working, describe the CLI result as a verification or compatibility gap and do not recommend reinstalling the plugin or clearing caches. Consider repair only when the UI and live runtime also fail.

When the dated DeepSeek rule is selected, report all three field assessments. Treat `supports_search_tool = false` and `use_responses_lite = false` as the case values for the selected third-party DeepSeek Responses model. Treat `tool_mode = direct` as `review_if_symptomatic`: if `code_mode_only` already exposes the required direct tools, do not present a change as mandatory. Never infer that top-level `web_search` should be disabled.

Lead with actionable errors and warnings. Put the selected compatibility mismatch ahead of plaintext-token risk, acknowledged authentication intent, and plugin CLI verification gaps. Do not present acknowledged intent or an unverified CLI probe as the most likely cause.

If the current task exposes a Chrome control tool and the user asked to test Chrome, perform a minimal smoke test using a new blank tab, then close only that temporary tab. Do not inspect existing tabs or visit a private site. Report the live smoke test separately from configuration evidence.

## Fall back safely

If the bundled entry point cannot run, read [`prompts/agent-doctor.zh-CN.md`](prompts/agent-doctor.zh-CN.md) and follow its manual read-only workflow. Keep the same privacy and write restrictions. Explain why the deterministic checker could not run.

## Enforce safety boundaries

- Never open or parse `auth.json`; check only whether it exists.
- Never output tokens, cookies, request headers, MCP environment values, private plugin names, or complete private endpoint URLs.
- Never read task titles, messages, previews, rollout content, or dynamic tool schemas.
- Never edit `config.toml`, a model catalog JSON, plugin state, login state, or a task database during diagnosis.
- Never repair history Provider bindings automatically.
- When the user asks for a fix, first show the exact target, backup plan, and field-level diff. Obtain explicit confirmation before any write. Treat database repair as a separate high-risk operation.
