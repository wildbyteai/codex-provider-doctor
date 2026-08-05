from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_catalog import run_doctor
from tests.test_cli_runtime import install_fake_codex


class CompatibilityRuleTests(unittest.TestCase):
    def test_chrome_symptom_prioritizes_false_search_support_on_any_third_party_responses_model(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "vendor-model-v1",
                                "display_name": "Vendor Model V1",
                                "tool_mode": "code_mode_only",
                                "supports_search_tool": False,
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
                        'model = "vendor-model-v1"',
                        'model_provider = "vendor"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.vendor]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
                    ]
                ),
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--symptom",
                "chrome-plugin-unavailable",
                "--no-command-checks",
                "--json",
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            finding = report["findings"][0]
            self.assertEqual(
                {
                    "symptom_assessments": report["compatibility"]["symptom_assessments"],
                    "finding": {
                        key: finding[key]
                        for key in ("code", "severity", "status", "category")
                    },
                    "web_search": report["effective"]["web_search"],
                },
                {
                    "symptom_assessments": [
                        {
                            "id": "chrome-plugin-unavailable",
                            "applicability": "applicable",
                            "applicability_reason": None,
                            "evidence_source": "catalog.selected_model.supports_search_tool",
                            "observed_supports_search_tool": False,
                            "assessment": "primary_static_compatibility_suspect",
                            "causality": "not_proven",
                            "live_smoke_test": "not_run_by_doctor",
                            "next_step": "compare_static_field_with_live_and_plugin_evidence",
                        }
                    ],
                    "finding": {
                        "code": "compat.chrome.supports_search_tool_false",
                        "severity": "warning",
                        "status": "open",
                        "category": "diagnostic",
                    },
                    "web_search": None,
                },
            )
            self.assertIn("首要静态兼容性疑点", finding["message"])
            self.assertIn("不能证明它是唯一根因", finding["message"])
            self.assertIn("不要修改顶层 web_search", finding["remedy"])

    def test_chrome_symptom_does_not_blame_search_support_when_catalog_value_is_true(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "vendor-model-v1",
                                "display_name": "Vendor Model V1",
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
                        'model = "vendor-model-v1"',
                        'model_provider = "vendor"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.vendor]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
                    ]
                ),
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--symptom",
                "chrome-plugin-unavailable",
                "--no-command-checks",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            assessment = report["compatibility"]["symptom_assessments"][0]
            self.assertEqual(
                {
                    "observed": assessment["observed_supports_search_tool"],
                    "assessment": assessment["assessment"],
                    "causality": assessment["causality"],
                    "next_step": assessment["next_step"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "observed": True,
                    "assessment": "not_indicated_by_static_field",
                    "causality": "not_proven",
                    "next_step": "continue_plugin_and_live_checks",
                    "finding_codes": [],
                },
            )

    def test_deepseek_rule_is_not_applicable_to_builtin_openai_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            bin_directory = root / "bin"
            codex_home.mkdir()
            bin_directory.mkdir()
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
            install_fake_codex(bin_directory, version="0.999.0")

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--compat-rule",
                "deepseek-direct-tools-2026-08-03",
                "--json",
                extra_env={
                    "PATH": f"{bin_directory}{os.pathsep}{os.environ.get('PATH', '')}",
                },
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

    def test_deepseek_rule_is_not_applicable_to_an_official_model_in_a_custom_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "slug": "gpt-5.6-sol",
                                "display_name": "GPT-5.6-Sol",
                                "tool_mode": "code_mode_only",
                                "supports_search_tool": True,
                                "use_responses_lite": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        'model = "gpt-5.6-sol"',
                        'model_provider = "custom"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
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
                    "assessments": rule["field_assessments"],
                    "changes": rule["suggested_changes"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "applicability": "not_applicable",
                    "reason": "selected_model_outside_rule_scope",
                    "assessments": [],
                    "changes": [],
                    "finding_codes": [],
                },
            )

    def test_deepseek_direct_tools_rule_separates_required_and_symptom_driven_fields(self) -> None:
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
                                "use_responses_lite": False,
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
                    "field_assessments": rule["field_assessments"],
                    "observed_differences": rule["observed_differences"],
                    "changes": rule["suggested_changes"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "id": "deepseek-direct-tools-2026-08-03",
                    "scope": "Codex 0.146.0-alpha.9.2 + one observed third-party API combination",
                    "field_assessments": [
                        {
                            "field": "tool_mode",
                            "observed": "code_mode_only",
                            "case_value": "direct",
                            "status": "review_if_symptomatic",
                        },
                        {
                            "field": "supports_search_tool",
                            "observed": True,
                            "case_value": False,
                            "status": "change_recommended",
                        },
                        {
                            "field": "use_responses_lite",
                            "observed": False,
                            "case_value": False,
                            "status": "aligned",
                        },
                    ],
                    "observed_differences": [
                        {"field": "tool_mode", "from": "code_mode_only", "to": "direct"},
                        {"field": "supports_search_tool", "from": True, "to": False},
                    ],
                    "changes": [
                        {"field": "supports_search_tool", "from": True, "to": False},
                    ],
                    "finding_codes": ["compat.deepseek_direct_tools.mismatch"],
                },
            )

    def test_tool_mode_difference_alone_is_not_reported_as_a_required_change(self) -> None:
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
                                "supports_search_tool": False,
                                "use_responses_lite": False,
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
                        'model_provider = "thirdparty"',
                        'model_catalog_json = "catalog.json"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
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
                    "observed_differences": rule["observed_differences"],
                    "suggested_changes": rule["suggested_changes"],
                    "tool_mode_status": rule["field_assessments"][0]["status"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "observed_differences": [
                        {"field": "tool_mode", "from": "code_mode_only", "to": "direct"},
                    ],
                    "suggested_changes": [],
                    "tool_mode_status": "review_if_symptomatic",
                    "finding_codes": [],
                },
            )


if __name__ == "__main__":
    unittest.main()
