from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.test_cli_catalog import run_doctor


class ConfigFileTests(unittest.TestCase):
    def test_nested_provider_fields_report_their_effective_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            config_path = codex_home / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        'model = "third-party-model"',
                        'model_provider = "thirdparty"',
                        "",
                        "[model_providers.thirdparty]",
                        'base_url = "https://api.example.invalid/v1"',
                        'wire_api = "responses"',
                        'env_key = "THIRD_PARTY_API_KEY"',
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
                extra_env={"THIRD_PARTY_API_KEY": "test-only-placeholder"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            origins = report["effective"]["origins"]
            expected_source = str(config_path.resolve())
            self.assertEqual(
                {
                    "base_url": origins["model_providers.thirdparty.base_url"],
                    "wire_api": origins["model_providers.thirdparty.wire_api"],
                    "env_key": origins["model_providers.thirdparty.env_key"],
                },
                {
                    "base_url": expected_source,
                    "wire_api": expected_source,
                    "env_key": expected_source,
                },
            )

    def test_tool_failure_returns_exit_code_three_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--config",
                "missing-equals-sign",
                "--json",
            )

            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(
                json.loads(result.stdout),
                {
                    "schema_version": 1,
                    "summary": {
                        "status": "tool_error",
                        "errors": 0,
                        "warnings": 0,
                        "info": 0,
                        "unverified": 0,
                        "acknowledged": 0,
                        "intentional": 0,
                    },
                    "tool_error": {
                        "code": "doctor.internal_failure",
                        "message": "诊断工具未能安全完成；异常细节已隐藏，请检查参数、文件权限和文件格式。",
                    },
                },
            )

    def test_invalid_toml_returns_redacted_layer_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            secret = "invalid-config-secret-must-not-leak"
            (codex_home / "config.toml").write_text(
                "\n".join(
                    [
                        "[model_providers.broken]",
                        f'experimental_bearer_token = "{secret}"',
                        "this line is not valid toml",
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
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertNotIn(secret, serialized)
            user_layer = next(layer for layer in report["layers"] if layer["kind"] == "user")
            self.assertEqual(
                {
                    "applied": user_layer["applied"],
                    "parse_status": user_layer["parse_status"],
                    "finding_codes": [finding["code"] for finding in report["findings"]],
                },
                {
                    "applied": False,
                    "parse_status": "invalid_toml",
                    "finding_codes": ["config.invalid_toml"],
                },
            )

    def test_command_line_config_override_has_highest_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "catalog.json").write_text(
                json.dumps(
                    {
                        "models": [
                            {"slug": "base-model", "display_name": "Base Model"},
                            {
                                "slug": "override-model",
                                "display_name": "Override Model",
                                "supports_search_tool": False,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                '\n'.join(['model = "base-model"', 'model_catalog_json = "catalog.json"']),
                encoding="utf-8",
            )

            result = run_doctor(
                "--codex-home",
                str(codex_home),
                "--system-config",
                str(root / "missing-system.toml"),
                "--no-command-checks",
                "--config",
                'model="override-model"',
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "model": report["effective"]["model"],
                    "model_origin": report["effective"]["origins"]["model"],
                    "selected_slug": report["catalog"]["selected_model"]["slug"],
                    "cli_layer_applied": next(
                        layer["applied"] for layer in report["layers"] if layer["kind"] == "cli"
                    ),
                },
                {
                    "model": "override-model",
                    "model_origin": "<command-line>",
                    "selected_slug": "override-model",
                    "cli_layer_applied": True,
                },
            )


if __name__ == "__main__":
    unittest.main()
