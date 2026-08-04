# Contributing

Codex Provider Doctor is intentionally small, read-only, and standard-library first.

## Before changing behavior

1. Describe the user-visible diagnostic behavior.
2. Add or update an integration test at the CLI, JSON report, or exit-code boundary.
3. Use sanitized temporary files. Never add a real `config.toml`, token, cookie, `auth.json`, task database, or private URL.
4. Keep compatibility advice versioned and narrowly scoped.
5. Do not add automatic configuration or database writes without a separate design and safety review.

## Verify locally

```shell
python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts tests
python3 scripts/run_skill.py --help
```

## Pull requests

- Explain the observed failure and the versions involved.
- State which fields or commands are read.
- Include a redaction review for every new report field.
- Document whether the behavior is official, observed locally, or inferred.
- Keep unrelated formatting or refactors out of the change.
