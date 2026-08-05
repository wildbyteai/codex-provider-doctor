# Sanitized examples

These files are synthetic. They do not contain a real account, endpoint, token, task, or Codex database.

- `config.example.toml` references a deliberately nonstandard relative catalog filename.
- `catalogs/vendor-models.release.json` contains one sanitized model entry.
- `report.example.json` shows the additive `skills`, detailed `solutions.items`, and fixed six-field `solutions.health_checks` shape with normalized paths, concrete parameters/current values, and no secret values.

The filename is not significant. `model_catalog_json` is the source of truth.
