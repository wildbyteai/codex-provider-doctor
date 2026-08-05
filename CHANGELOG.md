# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Five user-facing recovery guides selected with `--problem`: official sign-in, plugins/Skills, model names, history, and Chrome.
- A concise default human report plus `--details` for configuration layers, field origins, and complete evidence.
- Redacted local Skill counts and an additive JSON `solutions` section.
- Independent official-login verification state in the sign-in guide, plus per-Provider affected counts and an explicit not-checked state in the history guide.
- A Windows Desktop model-picker reminder that activates only after static catalog fields are valid, keeps App Server, picker, and live-request evidence separate, and never claims automatic UI detection.
- A consistent plain-language health-check layout for every problem: current result, controls, desired state, recovery actions, and verification, with technical diagnoses moved behind `--details`.
- Machine-readable `solutions.health_checks` cards that preserve the same five-field structure as the human report.
- Installable Codex Skill metadata with implicit natural-language invocation.
- A bundled Skill runner that uses the repository source without global package installation.
- Skill entry-point tests and natural-language installation instructions.
- Additive finding metadata: `status`, `category`, and `intentional`, plus summary counts for informational, unverified, acknowledged, and intentional findings.
- Explicit `--acknowledge provider.auth.openai_with_direct_token` support for a user-confirmed authentication intent.
- Explicit `--confirm-cause history.provider_mismatch` support for a user-confirmed incident root cause without database repair.
- General `--symptom chrome-plugin-unavailable` triage for the selected third-party Responses model's actual `supports_search_tool` value.
- Model-catalog `model_count` and read-only history `provider_counts` grouped by Provider, archive state, and total rows.
- Compatibility `field_assessments` and `observed_differences` for the dated DeepSeek rule.

### Changed

- Recognized `requires_openai_auth = true` under the active `[model_providers.<id>]` plus `experimental_bearer_token` as the confirmed dual-authentication design: official account state is retained while the explicit Provider token takes precedence for third-party requests.
- Kept the dual-authentication guide off the built-in OpenAI Provider and required a controlled authentication-method migration when `env_key` or command authentication already exists.
- Limited project Skill counting to trusted projects and marked skipped or unreadable coverage explicitly.
- Scoped Direct/Deferred Chrome branch inference to an official-source date, namespace-tools state, and the locally detected Codex version, with runtime verification always required.
- Reworked Chrome triage so `supports_search_tool` is not treated as a complete exposure switch: `false` forces the namespace planning branch to Direct, while `true` permits Deferred only when namespace tools are also enabled.
- Kept `features.remote_plugin = false` as a possible remote-directory limitation rather than proof that an already installed Chrome tool is unavailable.
- Put no-write history recovery first: switch back to the stored Provider, use an all-Provider view, or update Codex before considering database migration.
- Avoided false recovery advice when `display_name` is already correct, and avoided reporting “no Provider mismatch” when the task database was not found.
- Simplified the user-facing Skill installation prompt to require only the GitHub repository URL.
- Ranked live invocation and Settings evidence above the CLI plugin inventory probe.
- Kept failed, unparseable, missing, or disabled CLI-only plugin evidence at `info` / `unverified`; those findings no longer change exit code `0` by themselves.
- Separated acknowledged authentication intent from the independent plaintext-token security warning.
- Separated official ChatGPT/Codex sign-in state, third-party Provider request authentication, and plaintext-token risk in structured and human-readable output.
- Allowed a history Provider mismatch to be rendered as a user-confirmed root cause only after explicit confirmation; unconfirmed reports retain possibility language.
- Prioritized actionable compatibility mismatches ahead of security reminders, acknowledged intent, and plugin CLI verification gaps in human-readable output.
- Kept JSON finding order in diagnostic generation order; priority sorting now applies only to human-readable output.
- Scoped `deepseek-direct-tools-2026-08-03` to a selected DeepSeek model on a third-party Responses provider; official models remain outside the rule even when stored in the same custom catalog.
- Made human reports explicitly state when the selected model or Provider is outside the DeepSeek rule, including that official models keep their own `supports_search_tool` value.
- Made the Codex Skill consume the canonical human report by default instead of inviting a free-form JSON summary, while retaining `--json` for machine integrations.
- Required temporary-clone runs to preserve the real `CODEX_HOME`, original working directory, and active Profile before claiming equivalent diagnostic coverage.
- Treated `tool_mode = direct` as symptom-driven (`review_if_symptomatic`) while keeping `supports_search_tool = false` and `use_responses_lite = false` as the dated case values.
- Kept `schema_version = 1` and existing top-level fields. Summary adds `confirmed_causes`, compatibility adds `symptom_assessments`, and `suggested_changes` excludes symptom-only observations.

### Fixed

- Treat a failed or unparseable plugin CLI probe as a genuinely informational, unverified inventory instead of evidence that a plugin is missing or broken.
- Treat valid JSON with an unsupported plugin-inventory shape or unrecognized non-empty item as informational and unverified instead of a verified empty inventory.
- Avoid recommending plugin reinstalls or cache cleanup when the UI or live runtime already confirms the plugin works.

## [0.1.0] - 2026-08-04

### Added

- Read-only resolution of system, user, profile, trusted-project, and CLI config layers.
- Actual `model_catalog_json` path resolution without assuming a catalog filename.
- Model slug, display metadata, tool compatibility, context-window, and compact-limit checks.
- Provider authentication conflict and environment-presence checks without exposing secret values.
- Redacted Codex version, login-status, and plugin-list probes.
- Chrome installation, enablement, and manual acceptance checks.
- Versioned `deepseek-direct-tools-2026-08-03` compatibility rule.
- Read-only local task-history provider mismatch counts.
- Chinese and English human reports plus JSON output.

### Fixed

- Return exit code `3` with a stable redacted JSON error when the doctor itself cannot finish.
- Track nested Provider field origins and show parse status plus effective sources in human reports.
- Distinguish a missing catalog path from an existing non-file path and warn on a blank model display name.
- Keep dated compatibility advice off built-in OpenAI and non-Responses providers.
- Classify explicit signed-out login output before generic API-key wording.
- Hide arbitrary plugin names, count the inventory, and match Chrome exactly instead of by substring.
