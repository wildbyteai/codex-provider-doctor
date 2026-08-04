# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Installable Codex Skill metadata with implicit natural-language invocation.
- A bundled Skill runner that uses the repository source without global package installation.
- Skill entry-point tests and natural-language installation instructions.

### Changed

- Simplified the user-facing Skill installation prompt to require only the GitHub repository URL.

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
