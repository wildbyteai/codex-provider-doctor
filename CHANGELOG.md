# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

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

- Simplified the user-facing Skill installation prompt to require only the GitHub repository URL.
- Ranked live invocation and Settings evidence above the CLI plugin inventory probe.
- Kept failed, unparseable, missing, or disabled CLI-only plugin evidence at `info` / `unverified`; those findings no longer change exit code `0` by themselves.
- Separated acknowledged authentication intent from the independent plaintext-token security warning.
- Separated official ChatGPT/Codex sign-in state, third-party Provider request authentication, and plaintext-token risk in structured and human-readable output.
- Prioritized `supports_search_tool = false` as a static Chrome compatibility suspect only when the user reports the Chrome symptom, while keeping causality unproven and `true` as a contrasting non-indicator.
- Allowed a history Provider mismatch to be rendered as a user-confirmed root cause only after explicit confirmation; unconfirmed reports retain possibility language.
- Prioritized actionable compatibility mismatches ahead of security reminders, acknowledged intent, and plugin CLI verification gaps in human-readable output.
- Kept JSON finding order in diagnostic generation order; priority sorting now applies only to human-readable output.
- Scoped `deepseek-direct-tools-2026-08-03` to a selected DeepSeek model on a third-party Responses provider; official models remain outside the rule even when stored in the same custom catalog.
- Made human reports explicitly state when the selected model or Provider is outside the DeepSeek rule, including that official models keep their own `supports_search_tool` value.
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
