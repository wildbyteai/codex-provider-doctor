---
name: codex-provider-doctor
description: Diagnose Codex third-party model Provider setups with a bundled read-only checker. Use when skills stop working, a model name shows only a slug, Chrome or plugins are unavailable, older tasks appear missing after changing Provider, or the user needs help locating the effective config.toml, its actual model catalog JSON, supports_search_tool, requires_openai_auth, login state, or history Provider bindings.
---

# Codex Provider Doctor

Run the bundled doctor yourself. Do not ask the user to copy or execute terminal commands.

## Select the user's problem

Map the request to one or more public recovery guides:

- Keep the official ChatGPT/Codex sign-in while a third-party provider uses a direct token: `--problem keep-official-login`
- Plugins, official plugins, or Skills disappeared after switching: `--problem plugins-or-skills-unavailable`
- The model picker shows a slug or the wrong name: `--problem model-name-incorrect`
- Older tasks disappeared after switching Provider: `--problem history-missing`
- Chrome cannot be called under the third-party model: `--problem chrome-unavailable`

When no single problem is clear, omit `--problem`; the human report shows all five guides. Add `--details` only when the user asks for configuration layers, field origins, or full evidence.

## Run the diagnosis

1. Keep the user's current project as the working directory so trusted project configuration is evaluated correctly.
2. Resolve the skill directory from this file and run:

   ```text
   python3 <skill-directory>/scripts/run_skill.py --json --problem <problem-id>
   ```

   Python 3.11 or later is required. Do not globally install the package or create a virtual environment.
3. Pass `--profile <name>` only when the active Codex Profile is known. Never guess a Profile.
4. `--problem keep-official-login` is an explicit confirmation of the intended dual-authentication design for a custom third-party Provider. The correct location is `[model_providers.<id>]`: keep `requires_openai_auth = true` there while the third-party request uses `experimental_bearer_token`. This retains the official account state; the separate plaintext-token warning must remain. Do not apply this pattern to the built-in `openai` Provider, and do not stack it on an existing `env_key` or command-auth method—report a controlled authentication-method migration instead. The legacy explicit form `--acknowledge provider.auth.openai_with_direct_token` is also supported.
5. `--problem chrome-unavailable` also enables the legacy `--symptom chrome-plugin-unavailable` assessment. In the official Codex source snapshot dated 2026-08-05, `supports_search_tool = false` forces the namespace-tool planning branch to Direct, but does not prove Chrome exposure. `true` permits Deferred only when namespace tools are also enabled; otherwise Direct remains possible. Record the detected local version, leave the namespace-tools state unverified unless stronger evidence exists, and require a live task check. Never infer a top-level `web_search` change.
6. Add `--confirm-cause history.provider_mismatch` only after the user confirms that the detected Provider binding mismatch caused the current history visibility problem. This changes report wording only; it never repairs the database.
7. Add `--compat-rule deepseek-direct-tools-2026-08-03` only for that dated DeepSeek case. Keep `tool_mode = direct` as `review_if_symptomatic`.

Exit codes remain `0` for no errors or warnings, `1` for warnings, `2` for errors, and `3` when the doctor cannot finish safely.

## Explain the result

Lead with the requested problem, its status, and the exact recovery steps. Do not start with configuration layers.

For the five guides:

1. Explain the correct dual-authentication block and keep plaintext-token risk separate.
2. Distinguish Skill installation from new-task loading and runtime tool exposure. Count project Skills only when the project is trusted; never trust a project merely to complete the probe. Do not recommend reinstalling a plugin from a failed CLI inventory alone.
3. Name the effective `model_catalog_json`, exact `model`/`slug` match, and `display_name` fix.
4. Give no-write recovery first: switch back to the old Provider or use an all-Provider task view. Database migration remains a separately confirmed high-risk operation.
5. Separate static Direct/Deferred exposure, Plugins/Settings evidence, and a live Chrome smoke test.

For the official sign-in guide, report three states separately: the Provider block is configured, `codex login status` has or has not confirmed a ChatGPT sign-in, and plaintext token storage still has an independent warning. Do not call an unrun login probe “confirmed.”

For history, distinguish “the read-only probe found zero mismatches” from “no compatible task database was found.” If affected tasks span multiple old Providers, report each Provider's aggregate unarchived count instead of assigning the total to one Provider.

Rank plugin and Chrome evidence from strongest to weakest: live invocation, current-task visibility or the Settings or Plugins page, successful CLI inventory, then static configuration. A failed or unparseable CLI probe does not prove that a plugin is absent or broken and does not change exit code 0 by itself.

If the current task exposes a Chrome control tool and the user asked to test Chrome, perform a minimal smoke test using a new blank tab, then close only that temporary tab. Do not inspect existing tabs or visit a private site. Report the live smoke test separately from configuration evidence.

## Fall back safely

If the bundled entry point cannot run, read [`prompts/agent-doctor.zh-CN.md`](prompts/agent-doctor.zh-CN.md) and follow its manual read-only workflow. Keep the same privacy and write restrictions. Explain why the deterministic checker could not run.

## Enforce safety boundaries

- Never open or parse `auth.json`; check only whether it exists.
- Never output tokens, cookies, request headers, MCP environment values, private plugin names, or complete private endpoint URLs.
- Never read task titles, messages, previews, rollout content, or dynamic tool schemas.
- Never edit `config.toml`, a model catalog JSON, plugin state, login state, or a task database during diagnosis.
- Never repair history Provider bindings automatically.
- When the user asks for a fix, first show the exact target, backup plan, and field-level diff. Obtain explicit confirmation before any write. Treat database repair as a separate high-risk operation; back up the exact database plus its WAL/SHM sidecars before any future write.
