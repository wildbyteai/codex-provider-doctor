from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_catalog import run_doctor


class CompactConfigurationTests(unittest.TestCase):
    def test_compact_limit_must_be_below_effective_context_window(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "third-party-model",
                                "display_name": "Third-party Model",
                                "context_window": 128000,
                                "effective_context_window_percent": 95,
                                "auto_compact_token_limit": 110000,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config_path = codex_home / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "thirdparty"',
                        'model_catalog_json = "catalog.json"',
                        "model_context_window = 64000",
                        "model_auto_compact_token_limit = 70000",
                        'model_auto_compact_token_limit_scope = "total"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
                    ]
                ),
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--json",
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "compact": report["compact"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "compact": {
                        "context_window": 64000,
                        "context_source": str(config_path.resolve()),
                        "effective_context_window": 64000,
                        "auto_compact_token_limit": 70000,
                        "limit_source": str(config_path.resolve()),
                        "scope": "total",
                        "scope_source": str(config_path.resolve()),
                        "valid": False,
                    },
                    "finding_codes": ["compact.limit_not_below_window"],
                },
            )


if __name__ == "__main__":
    unittest.main()
