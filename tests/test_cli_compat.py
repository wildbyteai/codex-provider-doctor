from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_catalog import run_doctor


class CompatibilityRuleTests(unittest.TestCase):
    def test_deepseek_rule_is_not_applicable_to_builtin_openai_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "gpt-5.6",
                                "display_name": "GPT-5.6",
                                "tool_mode": "code_mode_only",
                                "supports_search_tool": True,
                                "use_responses_lite": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                '\n'.join(['model = "gpt-5.6"', 'model_catalog_json = "catalog.json"']),
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--compat-rule",
                "deepseek-direct-tools-2026-08-03",
                "--no-command-checks",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            rule = report["compatibility"]["rules"][0]
            self.assertEqual(
                {
                    "applicability": rule["applicability"],
                    "reason": rule["applicability_reason"],
                    "changes": rule["suggested_changes"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "applicability": "not_applicable",
                    "reason": "built_in_openai_provider",
                    "changes": [],
                    "finding_codes": [],
                },
            )

    def test_deepseek_rule_is_not_applicable_to_a_non_responses_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "unrelated-model",
                                "display_name": "Unrelated Model",
                                "tool_mode": "code_mode_only",
                                "supports_search_tool": True,
                                "use_responses_lite": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "unrelated-model"',
                        'model_provider = "unrelated"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.unrelated]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "chat"',
                    ]
                ),
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--compat-rule",
                "deepseek-direct-tools-2026-08-03",
                "--no-command-checks",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            rule = report["compatibility"]["rules"][0]
            self.assertEqual(
                {
                    "applicability": rule["applicability"],
                    "reason": rule["applicability_reason"],
                    "changes": rule["suggested_changes"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "applicability": "not_applicable",
                    "reason": "provider_wire_api_not_responses",
                    "changes": [],
                    "finding_codes": [],
                },
            )

    def test_deepseek_direct_tools_rule_returns_scoped_suggested_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "deepseek-v4-flash",
                                "display_name": "DeepSeek V4 Flash",
                                "tool_mode": "code_mode_only",
                                "supports_search_tool": True,
                                "use_responses_lite": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "deepseek-v4-flash"',
                        'model_provider = "deepseek"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.deepseek]",
                        'base_url = "https://api.deepseek.com/v1"',
                        'env_key = "DEEPSEEK_API_KEY"',
                    ]
                ),
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--compat-rule",
                "deepseek-direct-tools-2026-08-03",
                "--no-command-checks",
                "--json",
                extra_env={"DEEPSEEK_API_KEY": "test-only-placeholder"},
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            rule = report["compatibility"]["rules"][0]
            self.assertEqual(
                {
                    "id": rule["id"],
                    "scope": rule["scope"],
                    "changes": rule["suggested_changes"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "id": "deepseek-direct-tools-2026-08-03",
                    "scope": "Codex 0.146.0-alpha.9.2 + one observed third-party API combination",
                    "changes": [
                        {"field": "tool_mode", "from": "code_mode_only", "to": "direct"},
                        {"field": "supports_search_tool", "from": True, "to": False},
                        {"field": "use_responses_lite", "from": True, "to": False},
                    ],
                    "finding_codes": ["compat.deepseek_direct_tools.mismatch"],
                },
            )


if __name__ == "__main__":
    unittest.main()
