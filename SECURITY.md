# Security Policy

## Supported versions

The project is currently in alpha. Security fixes are applied to the latest released version.

## Reporting a vulnerability

Do not include API keys, cookies, `auth.json`, private endpoint URLs, company data, or unredacted Codex configuration in a public issue.

When this repository is hosted on GitHub, use a private security advisory if it is enabled. Otherwise contact the maintainer through a private channel listed by the repository owner. Include only the smallest sanitized reproduction needed to understand the issue.

## Sensitive files

Treat these as secrets or private operational data:

- `$CODEX_HOME/auth.json`
- Provider API keys and environment-variable values
- Cookie stores and browser profiles
- MCP headers, credentials, and environment values
- Private provider URLs beyond the hostname needed for diagnosis
- Codex task titles, prompts, previews, transcripts, and rollout files
- SQLite task databases and their `-wal` / `-shm` sidecars

The diagnostic tool must not read `auth.json` contents or task message fields. Changes that broaden data collection require an explicit privacy review and tests proving that secrets do not appear in output.
