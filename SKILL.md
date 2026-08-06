---
name: codex-provider-doctor
description: Diagnose Codex third-party model Provider setups with a bundled read-only checker. Use when skills stop working, Windows Desktop shows Custom or the wrong model name, Chrome or plugins are unavailable, older tasks appear missing after changing Provider, or the user needs help locating the effective config.toml, its actual model catalog JSON, supports_search_tool, requires_openai_auth, login state, or history Provider bindings.
---

# Codex Provider Doctor

Run the bundled doctor yourself. Do not ask the user to copy or execute terminal commands.

## Select the user's problem

Map the request to one or more public recovery guides:

- Keep the official ChatGPT/Codex sign-in while a third-party provider uses a direct token: `--problem keep-official-login`
- Plugins, official plugins, or Skills disappeared after switching: `--problem plugins-or-skills-unavailable`
- Windows Desktop shows `Custom`, a slug, or the wrong model name: `--problem model-name-incorrect`
- Older tasks disappeared after switching Provider: `--problem history-missing`
- Chrome cannot be called under the third-party model: `--problem chrome-unavailable`

When no single problem is clear, omit `--problem`; the human report shows all five guides. Add `--details` only when the user asks for configuration layers, field origins, or full evidence.

## Run the diagnosis

1. Keep the user's current project as the working directory so trusted project configuration is evaluated correctly. Do not `cd` into the Skill directory. If a temporary repository copy or another launcher changes the working directory, pass the original project explicitly with `--cwd <original-project>`.
2. Resolve the skill directory from this file and run:

   ```text
   python3 <skill-directory>/scripts/run_skill.py --problem <problem-id>
   ```

   Omit `--problem` when all five checks are useful. Do not add `--json` for a normal diagnosis: the default output is already the canonical structured health-check report. Use `--json` only for a machine-readable integration.

   Python 3.11 or later is required. Do not globally install the package or create a virtual environment. Keep the real `CODEX_HOME`; do not point the checker at the temporary repository copy.
3. Pass `--profile <name>` only when the active Codex Profile is known. Never guess a Profile.
4. `--problem keep-official-login` selects the recovery guide; it does not confirm that the current direct-token combination is intentional. The correct location for `requires_openai_auth = true` is `[model_providers.<id>]`. It can coexist with `env_key` or `experimental_bearer_token`; request credentials use `env_key` first, then the direct token, then retained official authentication. A missing configured `env_key` does not fall back. Only command authentication (`auth`) is mutually exclusive. Add `--acknowledge provider.auth.openai_with_direct_token` only after explicit user confirmation, and keep plaintext-token risk separate.
5. `--problem chrome-unavailable` also enables the legacy `--symptom chrome-plugin-unavailable` assessment. In the official Codex source snapshot dated 2026-08-05, `supports_search_tool = false` disables `search_tool_enabled`; when namespace tools are enabled, Deferred exposure is removed and only the plugin's declared Direct or Code paths remain. For a reported Chrome failure on a third-party Responses Provider, this is the leading compatibility suspect but not a unique root cause. `true` only makes Deferred eligible. Require plugin evidence, a new-task tool check, and a live invocation. Never infer a top-level `web_search` change.
6. `--problem model-name-incorrect` follows Codex's longest slug-prefix lookup, then retries once after removing a single simple model namespace; if neither matches, Codex uses fallback metadata instead of blocking the request. The doctor cannot observe the Windows Desktop picker or its remote `available_models` response. Preserve a valid matched entry and non-empty display name, and only treat the picker defect as the leading suspect after App Server and Desktop evidence agree. A real request is still required to prove routing.
7. Add `--confirm-cause history.provider_mismatch` only after the user confirms that the detected Provider binding mismatch caused the current history visibility problem. This changes report wording only; it never repairs the database.
8. Add `--compat-rule deepseek-direct-tools-2026-08-03` only for that dated DeepSeek case. Keep `tool_mode = direct` as `review_if_symptomatic`.

Exit codes remain `0` for no errors or warnings, `1` for warnings, `2` for errors, and `3` when the doctor cannot finish safely.

## Explain the result

Lead with a fixed health-check card for each requested problem. Use this order every time: current result, exact locations/key parameters, what controls it, desired state, how to change it, and how to verify it. Use plain language first, but always name the concrete file or UI location, relevant parameter, and safe current value. Do not start with configuration layers.

Preserve every health-check card emitted by the checker, in the same order and with all six fields. Do not replace the cards with a free-form technical summary. A short upgrade note may come first, but it must not consume or substitute for the diagnostic cards. If a machine integration requires `--json`, render `solutions.health_checks` in order instead of inventing a new narrative from raw findings.

For the five guides:

1. Explain the correct dual-authentication block and keep plaintext-token risk separate.
2. Distinguish Skill installation from new-task loading and runtime tool exposure. Check `features.plugins` as the plugin-system gate; treat `features.apps` as the App/connector switch and `features.remote_plugin` as the remote-directory switch. Count project Skills only when the project is trusted; never trust a project merely to complete the probe. Do not recommend reinstalling a plugin from a failed CLI inventory alone.
3. Name the effective `model_catalog_json`, the winning longest `model`/`slug` prefix, any one-level namespace retry or fallback metadata, and the `display_name` fix. If the selected entry is already valid, do not keep changing JSON or clearing caches merely because Windows Desktop shows `Custom`. Explain the conditional App Server-versus-picker evidence chain, prefer config/CLI/Profile switching, and state that the UI label is not proof of actual routing. Never patch `app.asar` automatically.
4. Give no-write recovery first: switch back to the old Provider or use an all-Provider task view. Database migration remains a separately confirmed high-risk operation.
5. Separate static Direct/Deferred exposure, Plugins/Settings evidence, and a live Chrome smoke test.

The default human response must read like an action checklist, not a technical log. Its `exact_targets` section must show normalized locations such as `$CODEX_HOME/config.toml`, `$PROJECT_ROOT/.agents/skills`, the actual normalized model-catalog or database path, the relevant field, and a redacted current value. Put complete origin-layer dumps, raw compatibility assessments, and the original technical diagnosis behind `--details`.

Running the same source from a temporary clone does not by itself prove that the result is unaffected. State equivalence only after confirming the same real `CODEX_HOME`, original working directory, and active Profile were used; otherwise mark project configuration and project-Skill coverage as potentially different.

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
